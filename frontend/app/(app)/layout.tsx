import { AppNavbar } from "@/components/layout/app-navbar";
import { ProtectedRoute } from "@/components/layout/protected-route";

export default function AppRouteLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-background">
        <AppNavbar />
        <main>{children}</main>
      </div>
    </ProtectedRoute>
  );
}
