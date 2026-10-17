import { CalendarDays, ShieldCheck } from "lucide-react";
import { useFormatter, useMessages, useTranslations } from "next-intl";

import { Card, CardContent } from "@/components/ui/card";
import type { UserProfile } from "@/features/profile/types";
import { labelFor } from "@/lib/i18n/labels";

function initialsOf(fullName: string): string {
  const parts = fullName.trim().split(/\s+/);
  const first = parts[0]?.[0] ?? "";
  const last = parts.length > 1 ? parts[parts.length - 1][0] : "";
  return `${first}${last}`.toUpperCase() || "?";
}

export function ProfileHeader({ profile }: { profile: UserProfile }) {
  const t = useTranslations("profile");
  const messages = useMessages();
  const format = useFormatter();
  const memberSince = format.dateTime(new Date(profile.createdAt), "dateLong");

  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-4 text-center sm:flex-row sm:text-start">
        <div className="flex size-20 shrink-0 items-center justify-center overflow-hidden rounded-full bg-primary/10 text-2xl font-semibold text-primary">
          {profile.profileImage ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={profile.profileImage}
              alt={profile.fullName}
              className="size-full object-cover"
            />
          ) : (
            initialsOf(profile.fullName)
          )}
        </div>

        <div className="flex flex-1 flex-col gap-1.5">
          <h1 className="font-heading text-2xl font-bold text-foreground">
            {profile.fullName}
          </h1>
          <p className="text-sm text-muted-foreground">{profile.email}</p>
          <div className="mt-1 flex flex-wrap items-center justify-center gap-3 sm:justify-start">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-secondary px-2.5 py-1 text-xs font-medium text-secondary-foreground">
              <ShieldCheck className="size-3.5" />
              {labelFor(messages.common.roles, profile.role)}
            </span>
            <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
              <CalendarDays className="size-3.5" />
              {t("memberSince", { date: memberSince })}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
