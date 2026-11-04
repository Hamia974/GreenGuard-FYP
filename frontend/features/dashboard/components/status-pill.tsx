"use client";

import { Eye, Leaf, TriangleAlert } from "lucide-react";
import { useTranslations } from "next-intl";

import { cn } from "@/lib/utils";

import styles from "../home.module.css";
import type { Status } from "../lib/home-status";

const ICONS = { healthy: Leaf, watch: Eye, risk: TriangleAlert, critical: TriangleAlert } as const;
const CLASSES = {
  healthy: styles.pillHealthy,
  watch: styles.pillWatch,
  risk: styles.pillRisk,
  critical: styles.pillCritical,
} as const;

interface StatusPillProps {
  status: Status;
  /** Replaces the status word, for example a risk level ("High"); the colour and icon still follow the status. */
  label?: string;
  className?: string;
}

/** Flat status pill: always a colour, an icon and a word, never colour alone. */
export function StatusPill({ status, label, className }: StatusPillProps) {
  const t = useTranslations("dashboard.status");
  const Icon = ICONS[status];
  return (
    <span className={cn(styles.pill, CLASSES[status], className)}>
      <Icon strokeWidth={1.75} aria-hidden="true" />
      {label ?? t(status)}
    </span>
  );
}
