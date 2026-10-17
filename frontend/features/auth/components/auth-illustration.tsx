"use client";

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";

const nodes = [
  { cx: 120, cy: 90, r: 5, delay: 0 },
  { cx: 210, cy: 60, r: 4, delay: 0.4 },
  { cx: 260, cy: 150, r: 6, delay: 0.8 },
  { cx: 90, cy: 200, r: 4, delay: 1.2 },
  { cx: 190, cy: 230, r: 5, delay: 1.6 },
];

/**
 * Abstract "AI-monitored agriculture" motif: a leaf silhouette overlaid with
 * a sensor/network graph, per UI_SPECIFICATION.md 10.4 (no stock/cartoon art).
 */
export function AuthIllustration() {
  const t = useTranslations("auth");

  return (
    <div className="relative flex h-full w-full items-center justify-center overflow-hidden">
      <div
        aria-hidden
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(60% 60% at 30% 20%, color-mix(in oklch, var(--primary-100), transparent 30%), transparent), radial-gradient(50% 50% at 80% 80%, color-mix(in oklch, var(--primary-200), transparent 40%), transparent)",
        }}
      />

      <motion.svg
        viewBox="0 0 320 320"
        className="relative w-full max-w-md"
        role="img"
        aria-label={t("illustrationLabel")}
        animate={{ y: [0, -10, 0] }}
        transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
      >
        <defs>
          <linearGradient id="leafGradient" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="var(--primary-400)" />
            <stop offset="100%" stopColor="var(--primary-800)" />
          </linearGradient>
        </defs>

        <path
          d="M160 40C220 40 270 90 270 160C270 220 220 270 160 280C150 210 100 190 60 190C60 100 100 40 160 40Z"
          fill="url(#leafGradient)"
          opacity={0.16}
        />
        <path
          d="M160 60C165 130 190 190 250 210"
          stroke="var(--primary-700)"
          strokeWidth={2}
          strokeLinecap="round"
          fill="none"
          opacity={0.35}
        />

        {nodes.map((node, index) => {
          const target = nodes[(index + 1) % nodes.length];
          return (
            <line
              key={`edge-${index}`}
              x1={node.cx}
              y1={node.cy}
              x2={target.cx}
              y2={target.cy}
              stroke="var(--primary-500)"
              strokeWidth={1}
              opacity={0.3}
            />
          );
        })}

        {nodes.map((node, index) => (
          <motion.circle
            key={`node-${index}`}
            cx={node.cx}
            cy={node.cy}
            r={node.r}
            fill="var(--primary-600)"
            animate={{ opacity: [0.4, 1, 0.4] }}
            transition={{
              duration: 3,
              repeat: Infinity,
              delay: node.delay,
              ease: "easeInOut",
            }}
          />
        ))}
      </motion.svg>
    </div>
  );
}
