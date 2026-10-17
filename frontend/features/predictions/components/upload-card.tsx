"use client";

import { AlertCircle, ImageUp, UploadCloud } from "lucide-react";
import { useTranslations } from "next-intl";
import { useCallback, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

// Mirrors backend/predictions/validators.py exactly (ALLOWED_IMAGE_EXTENSIONS,
// MAX_IMAGE_SIZE_BYTES, MIN_IMAGE_WIDTH/HEIGHT) so obviously-invalid uploads
// are rejected client-side before hitting the network, per
// UI_SPECIFICATION.md 11.6 "Image Validation". The backend remains the
// source of truth and re-validates independently.
const ALLOWED_EXTENSIONS = ["jpg", "jpeg", "png"];
const MAX_SIZE_BYTES = 10 * 1024 * 1024;
const MIN_WIDTH = 224;
const MIN_HEIGHT = 224;

function extensionOf(filename: string): string {
  return filename.includes(".") ? filename.split(".").pop()!.toLowerCase() : "";
}

function readImageDimensions(file: File): Promise<{ width: number; height: number }> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      URL.revokeObjectURL(url);
      resolve({ width: img.naturalWidth, height: img.naturalHeight });
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("invalid-image"));
    };
    img.src = url;
  });
}

/** Keys under upload.errors in messages/<locale>/upload.json. */
type UploadError = "unsupportedFormat" | "tooLarge" | "resolutionTooLow" | "invalidImage";

async function validateImage(file: File): Promise<UploadError | null> {
  if (!ALLOWED_EXTENSIONS.includes(extensionOf(file.name))) {
    return "unsupportedFormat";
  }
  if (file.size > MAX_SIZE_BYTES) {
    return "tooLarge";
  }
  try {
    const { width, height } = await readImageDimensions(file);
    if (width < MIN_WIDTH || height < MIN_HEIGHT) {
      return "resolutionTooLow";
    }
  } catch {
    return "invalidImage";
  }
  return null;
}

interface UploadCardProps {
  onImageReady: (file: File, previewUrl: string) => void;
}

export function UploadCard({ onImageReady }: UploadCardProps) {
  const t = useTranslations("upload");
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<UploadError | null>(null);

  const handleFile = useCallback(
    async (file: File) => {
      setError(null);
      const validationError = await validateImage(file);
      if (validationError) {
        setError(validationError);
        return;
      }
      onImageReady(file, URL.createObjectURL(file));
    },
    [onImageReady]
  );

  return (
    <div
      onDragOver={(event) => {
        event.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(event) => {
        event.preventDefault();
        setIsDragging(false);
        const file = event.dataTransfer.files?.[0];
        if (file) void handleFile(file);
      }}
      className={cn(
        "flex flex-col items-center gap-4 rounded-2xl border-2 border-dashed border-border bg-card px-6 py-14 text-center transition-colors",
        isDragging && "border-primary bg-primary/5"
      )}
    >
      <div className="flex size-16 items-center justify-center rounded-full bg-primary/10 text-primary">
        <UploadCloud className="size-8" />
      </div>
      <div>
        <p className="font-heading text-lg font-semibold text-foreground">{t("title")}</p>
        <p className="mt-1 text-sm text-muted-foreground">{t("description")}</p>
      </div>
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/jpg,image/png"
        className="hidden"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) void handleFile(file);
          event.target.value = "";
        }}
      />
      <Button type="button" onClick={() => inputRef.current?.click()}>
        <ImageUp className="size-4" />
        {t("browse")}
      </Button>
      <p className="text-xs text-muted-foreground">{t("hint")}</p>
      {error && (
        <p className="flex items-center gap-1.5 text-sm font-medium text-destructive">
          <AlertCircle className="size-3.5" />
          {t(`errors.${error}`, { width: MIN_WIDTH, height: MIN_HEIGHT })}
        </p>
      )}
    </div>
  );
}
