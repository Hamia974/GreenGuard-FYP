"""
train_lstm.py
--------------
Offline training + evaluation script for the forecast LSTM. Not part of
the running service -- run this once (or whenever you want to retrain) to
produce models/weather_lstm.pt and models/scaler.json, which
api/lstm_forecast.py loads at request time.

Data: Open-Meteo's free historical archive API (no key needed), self-
supervised -- for each of a handful of representative farm coordinates, we
pull ~2 years of daily [temperature, humidity, rainfall] and slide an
8-day window across it: the first 7 days are the input, the 8th is the
label. No manually labeled risk data is needed for this.

Evaluation: each location's series is split chronologically -- the last
TEST_FRACTION of its days are held out entirely from training, so the
reported metrics are genuine held-out performance, not training-set
recall. The LSTM is scored against two baselines it has to actually beat
to be worth deploying:
  - persistence: "tomorrow's weather = today's weather" (weather is
    highly autocorrelated day to day, so this is a deceptively strong
    baseline for a 1-day-ahead forecast)
  - climatology: "tomorrow's weather = the training-set average"

Run:
    cd Weather_Module/training
    python train_lstm.py
"""

import json
import os
import statistics
import sys
import time

import requests
import torch
import torch.nn as nn

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))
from lstm_model import WeatherLSTM, SEQUENCE_LENGTH  # noqa: E402

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FEATURE_NAMES = ["temperature (°C)", "humidity (%)", "rainfall (mm)"]

# Pakistani coordinates for geographic variety in the training data.
# Core Punjab agricultural belt (most of GreenGuard's likely farm base) is
# deliberately over-represented; a few non-Punjab cities are kept for
# broader climate diversity. Still weak on northern mountains (Gilgit-
# Baltistan, Chitral) and the Arabian Sea coast -- see MODEL_DOCUMENTATION.md.
TRAIN_COORDINATES = [
    (31.5204, 74.3587),   # Lahore
    (30.1575, 71.5249),   # Multan
    (31.4187, 73.0791),   # Faisalabad
    (30.8081, 73.4534),   # Okara
    (30.6682, 73.1114),   # Sahiwal
    (32.9425, 73.7257),   # Jhelum
    (31.1156, 74.4502),   # Kasur
    (31.7167, 73.9853),   # Sheikhupura
    (32.1877, 74.1945),   # Gujranwala
    (32.0836, 72.6711),   # Sargodha
    (29.3956, 71.6836),   # Bahawalpur
    (34.0151, 71.5249),   # Peshawar (KP diversity)
    (33.6844, 73.0479),   # Islamabad (highland diversity)
    (25.3960, 68.3578),   # Hyderabad (Sindh diversity)
]

START_DATE = "2024-08-25"
END_DATE = "2026-08-25"  # archive data lags a few days behind "today"

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
MODEL_PATH = os.path.join(MODEL_DIR, "weather_lstm.pt")
SCALER_PATH = os.path.join(MODEL_DIR, "scaler.json")
EVAL_REPORT_PATH = os.path.join(MODEL_DIR, "eval_report.json")

EPOCHS = 60
LEARNING_RATE = 0.01
TEST_FRACTION = 0.2  # last 20% of each location's days, chronologically


def fetch_daily_series(latitude: float, longitude: float) -> list:
    """Returns a list of [avg_temp, avg_humidity, rainfall] for each day
    in the date range, at one coordinate, oldest to newest."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": START_DATE,
        "end_date": END_DATE,
        "daily": "temperature_2m_mean,relative_humidity_2m_mean,precipitation_sum",
        "timezone": "auto",
    }
    response = requests.get(ARCHIVE_URL, params=params, timeout=30)
    response.raise_for_status()
    daily = response.json()["daily"]

    series = []
    for temp, hum, rain in zip(
        daily["temperature_2m_mean"],
        daily["relative_humidity_2m_mean"],
        daily["precipitation_sum"],
    ):
        if temp is None or hum is None:
            continue  # skip incomplete days rather than poison training with a fabricated value
        series.append([temp, hum, rain or 0.0])
    return series


def chronological_split(series: list, test_fraction: float = TEST_FRACTION) -> tuple:
    """Splits one location's series in time: everything before the cut is
    train-only; the test slice starts SEQUENCE_LENGTH days earlier so its
    windows have full lookback context, but every window's LABEL (the day
    being predicted) falls strictly after the cut -- so no test label is
    ever seen during training."""
    cut = int(len(series) * (1 - test_fraction))
    train_series = series[:cut]
    test_series = series[max(0, cut - SEQUENCE_LENGTH):]
    return train_series, test_series


def build_windows(series: list) -> list:
    """Slides an (SEQUENCE_LENGTH + 1)-day window across one location's
    daily series: first SEQUENCE_LENGTH days -> X, next day -> y."""
    windows = []
    for i in range(len(series) - SEQUENCE_LENGTH):
        x = series[i:i + SEQUENCE_LENGTH]
        y = series[i + SEQUENCE_LENGTH]
        windows.append((x, y))
    return windows


def compute_scaler(train_windows: list) -> dict:
    """Per-feature mean/std across every day seen in the TRAINING windows
    only (inputs + labels) -- computing this from test data would leak
    test-set statistics into normalization."""
    flat = [day for x, y in train_windows for day in x] + [y for x, y in train_windows]
    means, stds = [], []
    for feature_idx in range(3):
        values = [day[feature_idx] for day in flat]
        mean = statistics.mean(values)
        std = statistics.pstdev(values) or 1.0  # avoid div-by-zero on a degenerate feature
        means.append(mean)
        stds.append(std)
    return {"mean": means, "std": stds}


def normalize(day: list, scaler: dict) -> list:
    return [(v - m) / s for v, m, s in zip(day, scaler["mean"], scaler["std"])]


def mae_rmse(preds: torch.Tensor, actual: torch.Tensor) -> tuple:
    """Per-feature MAE and RMSE, each a list of 3 floats."""
    diff = preds - actual
    mae = diff.abs().mean(dim=0).tolist()
    rmse = (diff.pow(2).mean(dim=0)).sqrt().tolist()
    return mae, rmse


def evaluate_model(model: nn.Module, windows: list, scaler: dict) -> tuple:
    X = torch.tensor([[normalize(day, scaler) for day in x] for x, y in windows], dtype=torch.float32)
    actual = torch.tensor([y for x, y in windows], dtype=torch.float32)
    model.eval()
    with torch.no_grad():
        preds_norm = model(X)
    mean = torch.tensor(scaler["mean"])
    std = torch.tensor(scaler["std"])
    preds = preds_norm * std + mean
    return mae_rmse(preds, actual)


def evaluate_persistence(windows: list) -> tuple:
    """Baseline: predict tomorrow = the most recent day in the input window."""
    preds = torch.tensor([x[-1] for x, y in windows], dtype=torch.float32)
    actual = torch.tensor([y for x, y in windows], dtype=torch.float32)
    return mae_rmse(preds, actual)


def evaluate_climatology(windows: list, train_mean: list) -> tuple:
    """Baseline: predict tomorrow = the training-set average, always."""
    preds = torch.tensor([train_mean] * len(windows), dtype=torch.float32)
    actual = torch.tensor([y for x, y in windows], dtype=torch.float32)
    return mae_rmse(preds, actual)


def print_comparison(title: str, lstm: tuple, persistence: tuple, climatology: tuple) -> None:
    lstm_mae, lstm_rmse = lstm
    pers_mae, pers_rmse = persistence
    clim_mae, clim_rmse = climatology
    print(f"\n{title}")
    print(f"  {'feature':<18}{'model':<14}{'MAE':>8}{'RMSE':>8}")
    for i, name in enumerate(FEATURE_NAMES):
        print(f"  {name:<18}{'LSTM':<14}{lstm_mae[i]:>8.2f}{lstm_rmse[i]:>8.2f}")
        print(f"  {'':<18}{'persistence':<14}{pers_mae[i]:>8.2f}{pers_rmse[i]:>8.2f}")
        print(f"  {'':<18}{'climatology':<14}{clim_mae[i]:>8.2f}{clim_rmse[i]:>8.2f}")


def main():
    print(f"Fetching training data for {len(TRAIN_COORDINATES)} coordinates from Open-Meteo archive...")
    all_train_windows, all_test_windows = [], []
    for lat, lon in TRAIN_COORDINATES:
        series = fetch_daily_series(lat, lon)
        train_series, test_series = chronological_split(series)
        train_windows = build_windows(train_series)
        test_windows = build_windows(test_series)
        all_train_windows.extend(train_windows)
        all_test_windows.extend(test_windows)
        print(f"  ({lat}, {lon}): {len(series)} days -> {len(train_windows)} train windows, {len(test_windows)} held-out test windows")
        time.sleep(0.2)  # be polite to the free API between requests

    print(f"Total: {len(all_train_windows)} train windows, {len(all_test_windows)} held-out test windows")

    scaler = compute_scaler(all_train_windows)
    print(f"Scaler (computed from training data only): mean={scaler['mean']}, std={scaler['std']}")

    X = torch.tensor(
        [[normalize(day, scaler) for day in x] for x, y in all_train_windows],
        dtype=torch.float32,
    )
    Y = torch.tensor(
        [normalize(y, scaler) for x, y in all_train_windows],
        dtype=torch.float32,
    )

    model = WeatherLSTM()
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    loss_fn = nn.MSELoss()

    print(f"Training for {EPOCHS} epochs on the training split only...")
    model.train()
    for epoch in range(1, EPOCHS + 1):
        optimizer.zero_grad()
        predictions = model(X)
        loss = loss_fn(predictions, Y)
        loss.backward()
        optimizer.step()
        if epoch % 10 == 0 or epoch == 1:
            print(f"  epoch {epoch:3d}/{EPOCHS}  train mse={loss.item():.4f}")

    # Evaluate on the held-out test windows -- data the model never saw
    # during training, from the same locations but strictly later in time.
    lstm_scores = evaluate_model(model, all_test_windows, scaler)
    persistence_scores = evaluate_persistence(all_test_windows)
    climatology_scores = evaluate_climatology(all_test_windows, scaler["mean"])
    print_comparison(f"Held-out test set ({len(all_test_windows)} windows, never trained on):",
                      lstm_scores, persistence_scores, climatology_scores)

    beats_persistence_per_feature = [lstm_mae < pers_mae for lstm_mae, pers_mae in zip(lstm_scores[0], persistence_scores[0])]
    beats_persistence_all = all(beats_persistence_per_feature)
    print("\nLSTM vs. persistence, per feature (True = LSTM has lower MAE):")
    for name, wins in zip(FEATURE_NAMES, beats_persistence_per_feature):
        print(f"  {name:<18} {wins}")
    if not beats_persistence_all:
        print("(Not unusual for 1-day-ahead weather -- persistence is a strong baseline. "
              "Report this per-feature and honestly, rather than collapsing it into one pass/fail.)")

    os.makedirs(MODEL_DIR, exist_ok=True)
    torch.save(model.state_dict(), MODEL_PATH)
    with open(SCALER_PATH, "w") as f:
        json.dump(scaler, f, indent=2)
    with open(EVAL_REPORT_PATH, "w") as f:
        json.dump({
            "test_windows": len(all_test_windows),
            "train_windows": len(all_train_windows),
            "features": ["temperature_c", "humidity_pct", "rainfall_mm"],
            "lstm": {"mae": lstm_scores[0], "rmse": lstm_scores[1]},
            "persistence_baseline": {"mae": persistence_scores[0], "rmse": persistence_scores[1]},
            "climatology_baseline": {"mae": climatology_scores[0], "rmse": climatology_scores[1]},
            "lstm_beats_persistence_per_feature": dict(zip(
                ["temperature_c", "humidity_pct", "rainfall_mm"], beats_persistence_per_feature
            )),
        }, f, indent=2)

    print(f"\nSaved model -> {MODEL_PATH}")
    print(f"Saved scaler -> {SCALER_PATH}")
    print(f"Saved evaluation report -> {EVAL_REPORT_PATH}")


if __name__ == "__main__":
    main()
