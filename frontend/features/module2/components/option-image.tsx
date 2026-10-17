"use client";

import { ImageOff } from "lucide-react";
import Image from "next/image";
import { type ReactNode, useState } from "react";

interface OptionImageProps {
  src: string | undefined;
  alt: string;
  /** Overlay rendered on top of the photo (e.g. a selected tick or checkbox). */
  children?: ReactNode;
}

/** Square photo frame shared by the questionnaire's visual option cards.
 * Falls back to a neutral placeholder if the file is missing, so a broken
 * asset never hides the option itself (its text label is always shown). */
export function OptionImage({ src, alt, children }: OptionImageProps) {
  const [broken, setBroken] = useState(false);

  return (
    <div className="relative aspect-square w-full overflow-hidden rounded-xl bg-muted">
      {src && !broken ? (
        <Image
          src={src}
          alt={alt}
          fill
          sizes="(min-width: 640px) 200px, 45vw"
          className="object-cover"
          onError={() => setBroken(true)}
        />
      ) : (
        <div className="flex h-full w-full items-center justify-center text-muted-foreground">
          <ImageOff className="size-6" aria-hidden="true" />
        </div>
      )}
      {children}
    </div>
  );
}
