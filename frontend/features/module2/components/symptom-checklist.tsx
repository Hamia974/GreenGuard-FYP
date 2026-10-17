"use client";

import { useMessages, useTranslations } from "next-intl";
import { useId } from "react";

import { Checkbox } from "@/components/ui/checkbox";
import { labelFor } from "@/lib/i18n/labels";
import { cn } from "@/lib/utils";

import { NONE_VISIBLE_KEY, SYMPTOM_KEYS, defaultSymptoms, symptomImageSrc } from "../field-options";
import { OptionImage } from "./option-image";

interface SymptomChecklistProps {
  value: Record<string, boolean>;
  onChange: (next: Record<string, boolean>) => void;
  disabled?: boolean;
}

/** Multi-select symptom checklist with "None of these" mutual exclusivity,
 * enforced client-side per module2_field_options.json's mutually_exclusive_rule.
 * Each symptom shows an example photo so the farmer can compare it with their
 * own plant; the submitted keys are unchanged. */
export function SymptomChecklist({ value, onChange, disabled }: SymptomChecklistProps) {
  const t = useTranslations("soil.wizard");
  const messages = useMessages();
  const idPrefix = useId();

  const handleToggle = (key: string, checked: boolean) => {
    if (key === NONE_VISIBLE_KEY) {
      onChange(checked ? { ...defaultSymptoms(), [NONE_VISIBLE_KEY]: true } : { ...value, [NONE_VISIBLE_KEY]: false });
      return;
    }
    onChange({ ...value, [key]: checked, [NONE_VISIBLE_KEY]: checked ? false : value[NONE_VISIBLE_KEY] });
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {SYMPTOM_KEYS.filter((key) => key !== NONE_VISIBLE_KEY).map((key) => {
          const checked = !!value[key];
          const label = labelFor(messages.soil.options.symptoms, key);
          const textId = `${idPrefix}-${key}`;
          return (
            <label
              key={key}
              className={cn(
                "flex cursor-pointer flex-col gap-2 rounded-2xl border-2 p-2.5 transition-colors has-focus-visible:ring-3 has-focus-visible:ring-ring/50",
                checked ? "border-primary bg-primary/10" : "border-border bg-card hover:bg-muted",
                disabled && "pointer-events-none opacity-50"
              )}
            >
              <OptionImage src={symptomImageSrc(key)} alt={t("symptomPhotoAlt", { symptom: label })}>
                <span className="absolute top-1.5 end-1.5 flex rounded-[6px] bg-card p-1 shadow-sm">
                  <Checkbox
                    checked={checked}
                    disabled={disabled}
                    aria-labelledby={textId}
                    onCheckedChange={(next) => handleToggle(key, next === true)}
                  />
                </span>
              </OptionImage>
              <span
                id={textId}
                className={cn(
                  "text-start text-sm leading-snug font-medium",
                  checked ? "text-primary" : "text-foreground"
                )}
              >
                {label}
              </span>
            </label>
          );
        })}
      </div>

      <label className="flex cursor-pointer items-center gap-3 rounded-lg border border-dashed border-border bg-muted/40 px-3 py-2.5 text-sm font-medium text-foreground">
        <Checkbox
          checked={!!value[NONE_VISIBLE_KEY]}
          disabled={disabled}
          onCheckedChange={(checked) => handleToggle(NONE_VISIBLE_KEY, checked === true)}
        />
        {t("noneOfThese")}
      </label>
    </div>
  );
}
