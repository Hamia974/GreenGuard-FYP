import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

// Points next-intl at the per-request locale/messages resolver. See docs/I18N_GUIDE.md.
const withNextIntl = createNextIntlPlugin("./lib/i18n/request.ts");

const nextConfig: NextConfig = {
  // Produces a minimal `.next/standalone` server bundle so the Docker image
  // doesn't need to ship node_modules/ or the full build cache. Has no
  // effect on `next dev` or a plain `next build` outside Docker.
  output: "standalone",
};

export default withNextIntl(nextConfig);
