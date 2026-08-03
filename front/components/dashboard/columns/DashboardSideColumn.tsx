import AISidebar from "@/components/dashboard/sidebar/AISidebar";
import AnalyticsColumn from "@/components/dashboard/analytics/AnalyticsColumn";

type DashboardSideColumnProps = {
  side: "left" | "right";
};

export default function DashboardSideColumn({
  side,
}: DashboardSideColumnProps) {
  return (
    <aside
      className={[
        "custom-scrollbar min-h-0 overflow-y-auto bg-white px-6 py-6",
        side === "left"
          ? "border-b border-black/[0.06] lg:border-b-0 lg:border-r"
          : "border-t border-black/[0.06] lg:border-l lg:border-t-0",
      ].join(" ")}
    >
      {side === "left" && <AISidebar />}
      {side === "right" && <AnalyticsColumn />}
    </aside>
  );
}
