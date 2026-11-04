import { IBM_Plex_Mono } from "next/font/google";

import { ProtectedRoute } from "@/components/layout/protected-route";
import { Rail } from "@/features/dashboard/components/navigation";
import styles from "@/features/dashboard/home.module.css";

// The design system's `data` face for labels and readings; only this route uses it.
const ibmPlexMono = IBM_Plex_Mono({
  variable: "--font-ibm-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
  display: "swap",
  preload: false,
});

/** Home shell, Field Desk: a slim expandable rail instead of the app's top navbar. */
export default function HomeRouteLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute>
      <div className={`${styles.shell} ${ibmPlexMono.variable}`} data-gg-theme="field">
        <Rail />
        <main className={styles.content}>{children}</main>
      </div>
    </ProtectedRoute>
  );
}
