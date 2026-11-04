"use client";

import { useEffect, useState } from "react";

const DURATION_MS = 1200;

/** Counts up to `target` once it is known; shows it at once under reduced motion. */
export function useCountUp(target: number | null) {
  const [value, setValue] = useState(target);

  useEffect(() => {
    if (target === null) {
      setValue(null);
      return;
    }
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setValue(target);
      return;
    }
    const startedAt = performance.now();
    let frame = requestAnimationFrame(function step(now) {
      const progress = Math.min(1, (now - startedAt) / DURATION_MS);
      setValue(Math.round(target * (1 - Math.pow(1 - progress, 3))));
      if (progress < 1) frame = requestAnimationFrame(step);
    });
    return () => cancelAnimationFrame(frame);
  }, [target]);

  return value;
}
