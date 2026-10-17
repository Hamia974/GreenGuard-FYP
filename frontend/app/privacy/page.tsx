import type { Metadata } from "next";
import { getFormatter, getTranslations } from "next-intl/server";

import { LegalPageLayout } from "@/components/legal-page-layout";
import { LEGAL_LAST_UPDATED, LEGAL_SECTION_IDS } from "@/lib/legal";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("metadata");
  return { title: t("privacyTitle") };
}

export default async function PrivacyPage() {
  const t = await getTranslations("legal.privacy");
  const format = await getFormatter();

  return (
    <LegalPageLayout title={t("title")} lastUpdated={format.dateTime(LEGAL_LAST_UPDATED, "dateLong")}>
      {LEGAL_SECTION_IDS.map((id) => (
        <section key={id}>
          <h2>{t(`sections.${id}.title`)}</h2>
          <p>{t(`sections.${id}.body`)}</p>
        </section>
      ))}
    </LegalPageLayout>
  );
}
