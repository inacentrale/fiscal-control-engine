import DashboardShell from "@/components/layout/DashboardShell";
import DashboardColumns from "@/components/dashboard/DashboardColumns";

export default function HomePage() {
  return (
    <DashboardShell>
      <DashboardColumns />
    </DashboardShell>
  );
}
