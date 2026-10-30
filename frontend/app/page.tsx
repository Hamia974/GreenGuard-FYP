import { Leaf } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { LanguageSwitcher } from "@/components/layout/language-switcher";
import { LandingBackground } from "@/features/landing/components/landing-background";

/** The product name reads the same in every language. */
const BRAND_NAME = "Green Guard";

export default async function Home() {
  const t = await getTranslations("home");

  return (
    <main className="landing">
      <LandingBackground />
      <LanguageSwitcher className="landing-language" />
      <section className="landing-content">
        <p className="landing-kicker">
          <Leaf aria-hidden="true" />
          {t("kicker")}
        </p>
        <h1 className="landing-title" dir="ltr">
          <Image
            className="landing-logo"
            src="/images/brand/shield.png"
            alt=""
            width={441}
            height={519}
            priority
          />
          {BRAND_NAME}
        </h1>
        <p className="landing-tagline">{t("tagline")}</p>
        <p className="landing-description">{t("description")}</p>
        <div className="landing-actions">
          <Link href="/register" className="landing-button landing-button--primary">
            {t("signUp")}
          </Link>
          <Link href="/login" className="landing-button landing-button--secondary">
            {t("logIn")}
          </Link>
        </div>
      </section>
    </main>
  );
}
