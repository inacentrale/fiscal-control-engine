import type { AgentFileDashboard } from "@/api/agent/types";

import {
  dashboardNumber,
  formatAmount,
  formatCompactNumber,
} from "./analyticsUtils";

export default function AnalyticsKpiGrid({
  dashboard,
}: {
  dashboard: AgentFileDashboard;
}) {
  const amountsByCurrency = Object.entries(
    dashboard.amount_metrics_by_currency ?? {}
  ).map(([currency, metrics]) => ({
    currency,
    value: typeof metrics.sum === "number" ? metrics.sum : 0,
  }));
  const kpis = [
    {
      label: "Lignes",
      value: formatCompactNumber(dashboardNumber(dashboard, "summary", "row_count")),
    },
    {
      label: "Colonnes",
      value: formatCompactNumber(
        dashboardNumber(dashboard, "summary", "column_count")
      ),
    },
    {
      label: "Montant",
      value:
        amountsByCurrency.length > 0
          ? amountsByCurrency
              .map(({ currency, value }) => formatAmount(value, currency))
              .join(" · ")
          : formatAmount(dashboardNumber(dashboard, "metrics", "sum")),
    },
    {
      label: "Alertes",
      value: formatCompactNumber(dashboardNumber(dashboard, "quality", "issue_count")),
    },
  ];

  return (
    <div className="grid grid-cols-4 gap-1.5">
      {kpis.map((kpi) => (
        <div
          key={kpi.label}
          className="rounded-[14px] bg-[#f5f8fa] px-2.5 py-2.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.72)]"
        >
          <p className="truncate text-[10px] font-semibold text-[#7d8d97]">
            {kpi.label}
          </p>
          <p className="mt-1 truncate text-[15px] font-semibold text-[#102734]">
            {kpi.value}
          </p>
        </div>
      ))}
    </div>
  );
}
