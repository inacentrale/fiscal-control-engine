import AgentColumn from "@/components/dashboard/agent/AgentColumn";
import DashboardSideColumn from "@/components/dashboard/columns/DashboardSideColumn";

export default function DashboardColumns() {
  return (
    <div className="grid h-full min-h-0 grid-cols-1 border-t border-black/[0.06] lg:grid-cols-[22%_50%_28%]">
      <DashboardSideColumn side="left" />
      <AgentColumn />
      <DashboardSideColumn side="right" />
    </div>
  );
}
