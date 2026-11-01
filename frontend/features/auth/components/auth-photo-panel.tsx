"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef } from "react";

const PHOTOS = ["/images/crops/wheat.jpg", "/images/crops/eggplant.jpg", "/images/crops/rice.jpg"];
const SPECK_COUNT = 34;
const VERTICAL_TEAR_VIEW_BOX = "0 0 30 1000";
const HORIZONTAL_TEAR_VIEW_BOX = "0 0 1000 30";

/** Small seeded generator, so the tear and the light keep the same shape on every visit. */
function createRandom(initialSeed: number) {
  let seed = initialSeed;
  return () => {
    seed = (seed * 16807) % 2147483647;
    return (seed - 1) / 2147483646;
  };
}

/** A jagged edge along the length of the panel, closed on the form's side. */
function createTearPoints() {
  const random = createRandom(99);
  const points: [number, number][] = [];
  let along = -5;
  let across = 15;
  while (along < 1005) {
    points.push([along, across]);
    along += 12 + random() * 30;
    across = Math.max(3, Math.min(26, across + (random() - 0.5) * 16));
  }
  points.push([1005, across]);
  return points;
}

const TEAR_POINTS = createTearPoints();
const VERTICAL_TEAR = `M${TEAR_POINTS.map(([y, x]) => `${x.toFixed(1)} ${y.toFixed(1)}`).join(" L")} L34 1005 L34 -5 Z`;
const HORIZONTAL_TEAR = `M${TEAR_POINTS.map(([x, y]) => `${x.toFixed(1)} ${y.toFixed(1)}`).join(" L")} L1005 34 L-5 34 Z`;

/** Drifting specks of light. Decorative only, and left out with reduced motion. */
function useDriftingLight(canvasRef: React.RefObject<HTMLCanvasElement | null>) {
  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const random = createRandom(77);
    const specks = Array.from({ length: SPECK_COUNT }, () => ({
      x: random(),
      y: random(),
      size: 0.9 + random() * 2.4,
      speed: 0.012 + random() * 0.03,
      phase: random() * Math.PI * 2,
    }));

    const resize = () => {
      const ratio = Math.min(2, window.devicePixelRatio || 1);
      canvas.width = canvas.clientWidth * ratio;
      canvas.height = canvas.clientHeight * ratio;
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
    };
    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(canvas);
    resize();

    let frame = 0;
    const draw = (time: number) => {
      frame = requestAnimationFrame(draw);
      if (document.hidden) return;
      const { clientWidth: width, clientHeight: height } = canvas;
      context.clearRect(0, 0, width, height);
      context.fillStyle = "#ffffff";
      specks.forEach((speck) => {
        const y = (((speck.y - (time / 1000) * speck.speed) % 1) + 1) % 1;
        const x = speck.x + Math.sin(time / 1700 + speck.phase) * 0.018;
        context.globalAlpha = 0.25 + 0.45 * ((Math.sin(time / 900 + speck.phase) + 1) / 2);
        context.beginPath();
        context.arc(x * width, y * height, speck.size, 0, Math.PI * 2);
        context.fill();
      });
    };
    frame = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(frame);
      resizeObserver.disconnect();
    };
  }, [canvasRef]);
}

/** The left side of the sign-in pages: real crop photos fading into each other. */
export function AuthPhotoPanel({ headline, brandName }: { headline: string; brandName: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  useDriftingLight(canvasRef);

  return (
    <div className="auth-panel">
      <div className="auth-photos" aria-hidden="true">
        {PHOTOS.map((src, index) => (
          <Image key={src} src={src} alt="" fill sizes="(max-width: 900px) 100vw, 50vw" priority={index === 0} />
        ))}
      </div>
      <canvas ref={canvasRef} className="auth-light" aria-hidden="true" />
      <div className="auth-shade" aria-hidden="true" />
      <svg className="auth-tear auth-tear--side" viewBox={VERTICAL_TEAR_VIEW_BOX} preserveAspectRatio="none" aria-hidden="true">
        <path d={VERTICAL_TEAR} />
      </svg>
      <svg className="auth-tear auth-tear--bottom" viewBox={HORIZONTAL_TEAR_VIEW_BOX} preserveAspectRatio="none" aria-hidden="true">
        <path d={HORIZONTAL_TEAR} />
      </svg>
      <Link href="/" className="auth-brand" dir="ltr">
        <Image src="/images/brand/shield.png" alt="" width={441} height={519} />
        {brandName}
      </Link>
      <p className="auth-headline">{headline}</p>
    </div>
  );
}
