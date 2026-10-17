"use client";

import { Check } from "lucide-react";

import { cn } from "@/lib/utils";

import { OptionImage } from "./option-image";

export interface Option {
  value: string;
  label: string;
  hint?: string;
  /** Path under /public (e.g. "/images/crops/wheat.jpg") for a real photo
   * that helps a low-literacy farmer identify this option by sight instead
   * of relying on the English label alone. When any option in a grid has
   * one, the whole grid renders in visual (photo-first) mode. */
  imageSrc?: string;
}

interface OptionGridProps {
  options: Option[];
  value: string | undefined;
  onChange: (value: string) => void;
  columns?: string;
  disabled?: boolean;
}

/** Single-select grid of pictorial-style buttons, per Module2_Frontend_Form_Spec.md's
 * recommendation to avoid plain text dropdowns for questionnaire fields. */
export function OptionGrid({
  options,
  value,
  onChange,
  columns = "sm:grid-cols-2",
  disabled,
}: OptionGridProps) {
  const visual = options.some((option) => option.imageSrc);

  if (visual) {
    return (
      <div className={cn("grid grid-cols-2 gap-3", columns)}>
        {options.map((option) => {
          const selected = option.value === value;
          return (
            <button
              key={option.value}
              type="button"
              disabled={disabled}
              onClick={() => onChange(option.value)}
              aria-pressed={selected}
              className={cn(
                "flex flex-col items-center gap-2 rounded-2xl border-2 p-2.5 text-center transition-colors",
                selected
                  ? "border-primary bg-primary/10"
                  : "border-border bg-card hover:bg-muted",
                disabled && "pointer-events-none opacity-50"
              )}
            >
              <OptionImage src={option.imageSrc} alt={option.label}>
                {selected && (
                  <div className="absolute top-1.5 end-1.5 flex size-6 items-center justify-center rounded-full bg-primary text-primary-foreground">
                    <Check className="size-4" />
                  </div>
                )}
              </OptionImage>
              <span
                className={cn(
                  "text-sm font-semibold",
                  selected ? "text-primary" : "text-foreground"
                )}
              >
                {option.label}
              </span>
              {option.hint && (
                <span className="text-xs font-normal text-muted-foreground">{option.hint}</span>
              )}
            </button>
          );
        })}
      </div>
    );
  }

  return (
    <div className={cn("grid grid-cols-1 gap-2", columns)}>
      {options.map((option) => {
        const selected = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            disabled={disabled}
            onClick={() => onChange(option.value)}
            aria-pressed={selected}
            className={cn(
              "flex items-center justify-between gap-2 rounded-xl border px-4 py-3 text-start text-sm font-medium transition-colors",
              selected
                ? "border-primary bg-primary/10 text-primary"
                : "border-border bg-card text-foreground hover:bg-muted",
              disabled && "pointer-events-none opacity-50"
            )}
          >
            <span>
              {option.label}
              {option.hint && (
                <span className="mt-0.5 block text-xs font-normal text-muted-foreground">
                  {option.hint}
                </span>
              )}
            </span>
            {selected && <Check className="size-4 shrink-0" />}
          </button>
        );
      })}
    </div>
  );
}
