import type { ReactNode } from "react";

import AppSidebar from "@/components/layout/sidebar/AppSidebar";
import Topbar from "@/components/layout/topbar/Topbar";

export default function DashboardShell({ children }: { children: ReactNode }) {
  return (
    <main className="flex h-screen flex-col overflow-hidden bg-white text-gray-950">
      <Topbar />
      <div className="flex min-h-0 flex-1">
        <AppSidebar />
        <section className="min-h-0 flex-1 bg-white">{children}</section>
      </div>
    </main>
  );
}
