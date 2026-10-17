import { useFormatter, useMessages, useTranslations } from "next-intl";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmailVerificationStatus } from "@/features/profile/components/email-verification-status";
import type { UserProfile } from "@/features/profile/types";
import { labelFor } from "@/lib/i18n/labels";

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between border-b border-border py-2.5 text-sm last:border-b-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium text-foreground">{value}</span>
    </div>
  );
}

/**
 * Read-only account details per UI_SPECIFICATION.md section 16.7. Only
 * fields the backend actually tracks and returns are shown -- "Last Login"
 * is omitted since no login-signal wiring populates it. Email verification
 * status is backed by the /auth/verify-email/ flow (docs/AUTHENTICATION.md).
 */
export function AccountInformationCard({ profile }: { profile: UserProfile }) {
  const t = useTranslations("profile.accountInfo");
  const messages = useMessages();
  const format = useFormatter();
  const memberSince = format.dateTime(new Date(profile.createdAt), "dateLong");

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">{t("title")}</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col">
        <InfoRow label={t("email")} value={profile.email} />
        <div className="flex items-center justify-between gap-4 border-b border-border py-2.5 text-sm">
          <span className="text-muted-foreground">{t("emailVerification")}</span>
          <EmailVerificationStatus isVerified={profile.isVerified} />
        </div>
        <InfoRow label={t("accountType")} value={labelFor(messages.common.roles, profile.role)} />
        <InfoRow label={t("memberSince")} value={memberSince} />
        <InfoRow label={t("accountId")} value={profile.userId} />
      </CardContent>
    </Card>
  );
}
