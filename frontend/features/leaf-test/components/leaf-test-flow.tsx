"use client";

import {
  AlertCircle,
  Camera,
  Check,
  Focus,
  ImagePlus,
  Images,
  Leaf,
  Sun,
} from "lucide-react";
import Image from "next/image";
import { useMessages, useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";

import type { Farm } from "@/features/farms/types";
import { SUPPORTED_CROPS, type SupportedCrop } from "@/features/module1/types";
import { useAnalyzePrediction } from "@/features/predictions/hooks";
import type { Prediction } from "@/features/predictions/types";
import {
  MIN_HEIGHT,
  MIN_WIDTH,
  validateImage,
  type UploadError,
} from "@/features/predictions/components/upload-card";
import { labelFor } from "@/lib/i18n/labels";
import { useParseApiError } from "@/lib/i18n/use-api-error";
import { cn } from "@/lib/utils";

import styles from "../leaf-test.module.css";

const ACCEPT = "image/jpeg,image/jpg,image/png";

/** The dashed leaf outline that shows where to place the leaf. */
export function LeafGuide() {
  return (
    <svg viewBox="0 0 150 170" aria-hidden="true">
      <path
        className={styles.guideLine}
        d="M75 12 C 122 34 140 86 120 130 C 106 158 75 162 75 162 C 75 162 44 158 30 130 C 10 86 28 34 75 12 Z"
      />
      <path className={styles.guideVein} d="M75 160 C 75 120 75 80 75 36" />
    </svg>
  );
}

const RULER_TOP = Array.from({ length: 41 }, (_, index) => index);
const RULER_SIDE = Array.from({ length: 21 }, (_, index) => index);

/** The upload box's backdrop: a blurred field under Kombu, with rulers on three edges. */
function SceneBackdrop() {
  return (
    <>
      <div className={styles.sceneField} aria-hidden="true" />
      <div className={cn(styles.ruler, styles.rulerTop)} aria-hidden="true">
        {RULER_TOP.map((index) => (
          <i key={index} />
        ))}
      </div>
      <div className={cn(styles.ruler, styles.rulerStart)} aria-hidden="true">
        {RULER_SIDE.map((index) => (
          <i key={index} />
        ))}
      </div>
      <div className={cn(styles.ruler, styles.rulerEnd)} aria-hidden="true">
        {RULER_SIDE.map((index) => (
          <i key={index} />
        ))}
      </div>
    </>
  );
}

/** The reticle with its turning arc and sweeping line. Decoration only; no text, no analysis. */
function Reticle() {
  return (
    <div className={styles.reticleBlock} aria-hidden="true">
      <svg
        className={styles.reticle}
        viewBox="200 0 400 400"
        preserveAspectRatio="xMidYMid meet"
      >
        <line
          className={styles.reticleCross}
          x1="200"
          y1="200"
          x2="600"
          y2="200"
        />
        <line
          className={styles.reticleCross}
          x1="400"
          y1="0"
          x2="400"
          y2="400"
        />
        <circle className={styles.reticleOuter} cx="400" cy="200" r="150" />
        <circle className={styles.reticleRing} cx="400" cy="200" r="118" />
        <path
          className={styles.reticleArc}
          d="M 400 82 A 118 118 0 0 1 502 141"
        />
        <path
          className={styles.reticleBrackets}
          d="M344 160 V134 H370 M430 134 H456 V160 M456 240 V266 H430 M370 266 H344 V240"
        />
        <circle className={styles.reticleDot} cx="400" cy="200" r="3" />
      </svg>
      <span className={styles.reticleScan} />
    </div>
  );
}

export function Corners() {
  return (
    <span className={styles.corners} aria-hidden="true">
      <i />
      <i />
      <i />
      <i />
    </span>
  );
}

/** Crop, photo, result. The crop step counts as done because "Not sure" is a valid choice. */
function Steps() {
  const t = useTranslations("leafTest.steps");
  return (
    <ol className={styles.steps} aria-label={t("label")}>
      <li className={styles.stepDone}>{t("crop")}</li>
      <li className={styles.stepNow} aria-current="step">
        {t("photo")}
      </li>
      <li>{t("result")}</li>
    </ol>
  );
}

interface LeafTestFlowProps {
  farm: Farm;
  onComplete: (prediction: Prediction) => void;
}

/**
 * Guided leaf test: choose the crop, add one photo (camera or gallery), then
 * one honest checking state while the single analyze request runs. The
 * result itself is shown on the saved report page.
 */
export function LeafTestFlow({ farm, onComplete }: LeafTestFlowProps) {
  const t = useTranslations("leafTest");
  const tUpload = useTranslations("upload");
  const messages = useMessages();
  const parseApiError = useParseApiError();
  const cameraRef = useRef<HTMLInputElement>(null);
  const galleryRef = useRef<HTMLInputElement>(null);
  const [crop, setCrop] = useState<SupportedCrop | undefined>(undefined);
  const [image, setImage] = useState<{ file: File; previewUrl: string } | null>(
    null,
  );
  const [error, setError] = useState<UploadError | null>(null);
  const [dragging, setDragging] = useState(false);
  const analyze = useAnalyzePrediction(farm.farmId);

  useEffect(() => {
    return () => {
      if (image) URL.revokeObjectURL(image.previewUrl);
    };
  }, [image]);

  async function handleFile(file: File | undefined) {
    if (!file) return;
    setError(null);
    analyze.reset();
    const problem = await validateImage(file);
    if (problem) {
      setError(problem);
      return;
    }
    setImage({ file, previewUrl: URL.createObjectURL(file) });
  }

  function clearImage() {
    setImage(null);
    setError(null);
    analyze.reset();
  }

  const cropLabel = crop ? labelFor(messages.crops, crop) : null;

  // ---------- Checking ----------
  if (analyze.isPending && image) {
    return (
      <div className={styles.wrap}>
        <Steps />
        <div className={styles.checkingView} role="status" aria-live="polite">
          <span className={styles.shieldBig} aria-hidden="true">
            <Image
              src="/images/brand/shield.png"
              alt=""
              width={168}
              height={198}
              priority
            />
            <i className={styles.shieldScan} />
          </span>
          <div className={styles.checkingCopy}>
            <p className={styles.checkingTitle}>{t("checking.title")}</p>
            <p className={styles.checkingText}>
              {cropLabel
                ? t("checking.withCrop", { crop: cropLabel.toLowerCase() })
                : t("checking.detectCrop")}{" "}
              {t("checking.wait")}
            </p>
          </div>
        </div>
      </div>
    );
  }

  // ---------- Crop and photo ----------
  return (
    <div className={styles.wrap}>
      <Steps />

      <div className={styles.crops}>
        <p id="leaf-crop-question" className={styles.label}>
          {t("crop.question")}
        </p>
        <div
          className={styles.dial}
          role="radiogroup"
          aria-labelledby="leaf-crop-question"
        >
          {[...SUPPORTED_CROPS, undefined].map((item) => {
            const checked = crop === item;
            return (
              <button
                key={item ?? "none"}
                type="button"
                role="radio"
                aria-checked={checked}
                className={styles.dialOption}
                onClick={() => setCrop(item)}
              >
                <span className={styles.dialPhoto}>
                  {item ? (
                    <Image
                      src={`/images/crops/${item}.jpg`}
                      alt=""
                      width={64}
                      height={64}
                    />
                  ) : (
                    <span className={styles.dialUnsure} aria-hidden="true">
                      ?
                    </span>
                  )}
                  <span className={styles.dialTick} aria-hidden="true">
                    <Check strokeWidth={2.5} />
                  </span>
                </span>
                <span className={styles.dialName}>
                  {item ? labelFor(messages.crops, item) : t("crop.notSure")}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      <div
        className={cn(
          styles.dropBox,
          !image && styles.dropBoxScene,
          dragging && styles.dropBoxActive,
        )}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          void handleFile(event.dataTransfer.files?.[0]);
        }}
      >
        {image ? (
          <div className={styles.previewFrame}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              className={styles.stagePhoto}
              src={image.previewUrl}
              alt={t("photo.previewAlt")}
            />
            <Corners />
          </div>
        ) : (
          <>
            <SceneBackdrop />
            <Reticle />
            <p className={styles.dropTitle}>{tUpload("title")}</p>
            <p className={styles.dropText}>{tUpload("description")}</p>
          </>
        )}

        <div className={styles.actions}>
          {image ? (
            <>
              <button
                type="button"
                className={cn(styles.btn, styles.btnPrimary)}
                onClick={() =>
                  analyze
                    .mutateAsync({ image: image.file, crop })
                    .then(onComplete)
                    .catch(() => {})
                }
              >
                <Leaf strokeWidth={1.75} aria-hidden="true" />
                {t("photo.submit")}
              </button>
              <button
                type="button"
                className={cn(styles.btn, styles.btnSecondary)}
                onClick={clearImage}
              >
                <ImagePlus strokeWidth={1.75} aria-hidden="true" />
                {t("photo.change")}
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                className={cn(styles.btn, styles.heroPrimary)}
                onClick={() => cameraRef.current?.click()}
              >
                <Camera strokeWidth={1.75} aria-hidden="true" />
                {t("photo.take")}
              </button>
              <button
                type="button"
                className={cn(styles.btn, styles.heroSecondary)}
                onClick={() => galleryRef.current?.click()}
              >
                <Images strokeWidth={1.75} aria-hidden="true" />
                {t("photo.choose")}
              </button>
            </>
          )}
        </div>

        {error && (
          <p className={styles.error} role="alert">
            <AlertCircle strokeWidth={1.75} aria-hidden="true" />
            {tUpload(`errors.${error}`, {
              width: MIN_WIDTH,
              height: MIN_HEIGHT,
            })}
          </p>
        )}
        {analyze.isError && (
          <p className={styles.error} role="alert">
            <AlertCircle strokeWidth={1.75} aria-hidden="true" />
            {parseApiError(analyze.error).message}
          </p>
        )}
        {!image && !error && <p className={styles.hint}>{tUpload("hint")}</p>}
      </div>

      <ul className={styles.tips}>
        <li>
          <Sun strokeWidth={1.75} aria-hidden="true" />
          <div>
            <b>{t("tips.daylightTitle")}</b>
            <span>{t("tips.daylight")}</span>
          </div>
        </li>
        <li>
          <Leaf strokeWidth={1.75} aria-hidden="true" />
          <div>
            <b>{t("tips.oneLeafTitle")}</b>
            <span>{t("tips.oneLeaf")}</span>
          </div>
        </li>
        <li>
          <Focus strokeWidth={1.75} aria-hidden="true" />
          <div>
            <b>{t("tips.sharpTitle")}</b>
            <span>{t("tips.sharp")}</span>
          </div>
        </li>
      </ul>

      <input
        ref={cameraRef}
        type="file"
        accept={ACCEPT}
        capture="environment"
        hidden
        onChange={(event) => {
          void handleFile(event.target.files?.[0]);
          event.target.value = "";
        }}
      />
      <input
        ref={galleryRef}
        type="file"
        accept={ACCEPT}
        hidden
        onChange={(event) => {
          void handleFile(event.target.files?.[0]);
          event.target.value = "";
        }}
      />
    </div>
  );
}
