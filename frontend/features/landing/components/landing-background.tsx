"use client";

import { useLocale } from "next-intl";
import { useEffect, useRef, useState } from "react";

import { getDirection, type Locale } from "@/lib/i18n/config";

const VIDEO_SRC = "/videos/landing-hero.mp4";
const POSTER_SRC = "/videos/landing-hero-poster.jpg";
const CROSSFADE_SECONDS = 0.9;
const STILL_FRAME_SECONDS = 2;

interface NetworkConnection {
  saveData?: boolean;
  effectiveType?: string;
}

/** Skips the video and 3D layer when the visitor is saving data or on a slow network. */
function isConstrainedConnection() {
  const { connection } = navigator as Navigator & { connection?: NetworkConnection };
  return Boolean(connection?.saveData || /(^|-)(2g|3g)$/.test(connection?.effectiveType ?? ""));
}

/**
 * The hero's living background: the drone video graded to sunset, with the
 * decorative 3D network, crop-row grid and scan line on top. Falls back to the poster on slow connections,
 * and to a still frame when the visitor prefers reduced motion.
 */
export function LandingBackground() {
  const locale = useLocale();
  // The network sits opposite the text, so it switches sides in right-to-left.
  const networkSide = getDirection(locale as Locale) === "rtl" ? -1 : 1;
  const containerRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const firstVideoRef = useRef<HTMLVideoElement>(null);
  const secondVideoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [showVideo, setShowVideo] = useState(false);

  useEffect(() => {
    if (!isConstrainedConnection()) setShowVideo(true);
  }, []);

  useEffect(() => {
    const first = firstVideoRef.current;
    const second = secondVideoRef.current;
    if (!showVideo || !first || !second) return;

    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      const showStill = () => {
        first.currentTime = STILL_FRAME_SECONDS;
      };
      first.addEventListener("loadedmetadata", showStill, { once: true });
      if (first.readyState >= 1) showStill();
      return () => first.removeEventListener("loadedmetadata", showStill);
    }

    let current = first;
    let next = second;
    let isSwapping = false;
    let frame = 0;
    let swapTimer: number | undefined;

    second.style.opacity = "0";
    first.play().catch(() => {});

    // Two stacked videos crossfade at the end of the clip, hiding the loop point.
    const watchForLoop = () => {
      frame = requestAnimationFrame(watchForLoop);
      const { duration, currentTime } = current;
      if (!duration || isSwapping || currentTime <= duration - CROSSFADE_SECONDS) return;

      isSwapping = true;
      const outgoing = current;
      next.currentTime = 0;
      next.play().catch(() => {});
      next.style.opacity = "1";
      outgoing.style.opacity = "0";
      current = next;
      next = outgoing;
      swapTimer = window.setTimeout(() => {
        outgoing.pause();
        isSwapping = false;
      }, CROSSFADE_SECONDS * 1000 + 50);
    };
    frame = requestAnimationFrame(watchForLoop);

    return () => {
      cancelAnimationFrame(frame);
      window.clearTimeout(swapTimer);
      first.pause();
      second.pause();
    };
  }, [showVideo]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!showVideo || !canvas || !container) return;
  
    const animate = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let cancelled = false;
    let stopScene: (() => void) | undefined;
  
    // Loaded only here, so Three.js never reaches any other page's bundle.
    import("@/features/landing/lib/network-scene")
      .then(({ startNetworkScene }) => {
        if (cancelled) return;
        stopScene = startNetworkScene({
          canvas,
          container,
          animate,
          networkSide,
          onPointerFrame: (x, y) => {
            if (stageRef.current) {
              stageRef.current.style.transform = `scale(1.1) translate(${x * -1.1}%, ${y * -0.7}%)`;
            }
          },
        });
      })
      .catch(() => {
        // Without WebGL the video and sunset still work, so the 3D layer is simply left out.
        canvas.style.display = "none";
      });
  
    return () => {
      cancelled = true;
      stopScene?.();
    };
  }, [showVideo, networkSide]);

  return (
    <div ref={containerRef} className="landing-background" aria-hidden="true">
      <div
        ref={stageRef}
        className="landing-stage"
        style={{ backgroundImage: `url(${POSTER_SRC})` }}
      >
        {showVideo && (
          <>
            <video ref={firstVideoRef} src={VIDEO_SRC} muted playsInline preload="auto" />
            <video ref={secondVideoRef} src={VIDEO_SRC} muted playsInline preload="auto" />
          </>
        )}
      </div>
      <div className="landing-sky" />
      <div className="landing-sun" />
      {showVideo && <canvas ref={canvasRef} className="landing-canvas" />}
      <div className="landing-veil" />
    </div>
  );
}
