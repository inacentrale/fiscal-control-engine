import type { ReactNode } from "react";

import Topbar from "@/components/layout/topbar/Topbar";

export default function DashboardShell({ children }: { children: ReactNode }) {
  return (
    <main className="flex h-screen flex-col overflow-hidden bg-white text-gray-950">
      <Topbar />
      <section className="min-h-0 flex-1 bg-white">{children}</section>
    </main>
  );
}
