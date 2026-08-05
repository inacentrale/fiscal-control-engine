import type { AgentFileDashboard } from "@/api/agent/types";
import { cn } from "@/utils/ui/styles";

import {
  dashboardNumber,
  formatAmount,
  formatCompactNumber,
} from "./analyticsUtils";

export default function AnalyticsKpiGrid({
  dashboard,
  variant = "compact",
}: {
  dashboard: AgentFileDashboard;
  variant?: "compact" | "expanded";
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
    <div
      className={cn(
        "grid grid-cols-4",
        variant === "expanded" ? "gap-3" : "gap-1.5"
      )}
    >
      {kpis.map((kpi) => (
        <div
          key={kpi.label}
          className={cn(
            "bg-[#f5f8fa] shadow-[inset_0_1px_0_rgba(255,255,255,0.72)]",
            variant === "expanded"
              ? "rounded-[22px] px-5 py-4 ring-1 ring-[#e5eef2]"
              : "rounded-[14px] px-2.5 py-2.5"
          )}
        >
          <p
            className={cn(
              "truncate font-semibold text-[#7d8d97]",
              variant === "expanded" ? "text-[12px]" : "text-[10px]"
            )}
          >
            {kpi.label}
          </p>
          <p
            className={cn(
              "truncate font-semibold text-[#102734]",
              variant === "expanded"
                ? "mt-2 text-[28px]"
                : "mt-1 text-[15px]"
            )}
          >
            {kpi.value}
          </p>
        </div>
      ))}
    </div>
  );
}
