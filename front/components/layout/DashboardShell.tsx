import type { ReactNode } from "react";

export default function DashboardShell({ children }: { children: ReactNode }) {
  return (
    <main className="h-screen overflow-hidden bg-white text-gray-950">
      {children}
    </main>
  );
}
