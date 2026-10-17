"""
lstm_model.py
-------------
The LSTM architecture shared by training (training/train_lstm.py) and
inference (api/lstm_forecast.py) — kept in one place so the two can never
drift out of sync with each other.

Input: the last SEQUENCE_LENGTH days of [avg_temp, avg_humidity, rainfall]
(the exact daily_summary shape weather_service.py already builds for its
consecutive-day risk logic). Output: the same 3 values, predicted for the
day after the most recent one in the input window.
"""

import torch
import torch.nn as nn

SEQUENCE_LENGTH = 7
FEATURES = ["avg_temp", "avg_humidity", "rainfall"]


class WeatherLSTM(nn.Module):
    def __init__(self, input_size: int = 3, hidden_size: int = 32, num_layers: int = 1):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.head = nn.Linear(hidden_size, input_size)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, SEQUENCE_LENGTH, 3)
        out, _ = self.lstm(x)
        last_step = out[:, -1, :]
        return self.head(last_step)  # (batch, 3) -> next-day [temp, humidity, rainfall]
