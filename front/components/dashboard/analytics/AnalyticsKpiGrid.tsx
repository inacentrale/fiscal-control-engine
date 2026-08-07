"use client";

import type { AgentFileDashboard } from "@/api/agent/types";
import {
  Chart2Icon,
  DocumentTextIcon,
  SearchStatusIcon,
} from "@/public/assets/icons/AnalyticsIcons";

import AnalyticsStatGrid, { type AnalyticsStatItem } from "./AnalyticsStatGrid";
import { dashboardNumber, formatCompactNumber } from "./analyticsUtils";

export default function AnalyticsKpiGrid({
  dashboard,
  variant = "compact",
}: {
  dashboard: AgentFileDashboard;
  variant?: "compact" | "expanded";
}) {
  const rowCount = dashboardNumber(dashboard, "summary", "row_count");
  const columnCount = dashboardNumber(dashboard, "summary", "column_count");
  const usedEntryCount = dashboardNumber(
    dashboard,
    "summary",
    "used_entry_count"
  );
  const currencyCount = dashboardNumber(dashboard, "summary", "currency_count");
  const issueCount = dashboardNumber(dashboard, "quality", "issue_count");
  const kpis = [
    {
      label: "Lignes",
      value: formatCompactNumber(rowCount),
    },
    {
      label: "Colonnes",
      value: formatCompactNumber(columnCount),
    },
    {
      label: "Alertes",
      value: formatCompactNumber(issueCount),
    },
  ];

  if (variant === "compact") {
    return <AnalyticsStatGrid items={toCompactStats(kpis)} variant="compact" />;
  }

  const ledgerStats: AnalyticsStatItem[] = [
    {
      accent: "#40515C",
      detail: "Volume importé du fichier",
      icon: <DocumentTextIcon className="size-5" />,
      label: "Lignes",
      muted: true,
      progress: 1,
      value: formatCompactNumber(rowCount),
    },
    {
      accent: "#7FA6B7",
      detail: `${formatCompactNumber(columnCount)} colonnes détectées`,
      icon: <Chart2Icon className="size-5" />,
      label: "Structure",
      progress: 1,
      value: formatCompactNumber(usedEntryCount || rowCount),
    },
    {
      accent: "#8B98A3",
      detail: "Devises présentes dans le fichier",
      icon: <Chart2Icon className="size-5" />,
      label: "Devises",
      progress: currencyCount > 0 ? 1 : 0,
      value: formatCompactNumber(currencyCount),
    },
    {
      accent: "#E36F55",
      detail: "Points qualité détectés",
      icon: <SearchStatusIcon className="size-5" />,
      label: "Qualité",
      progress: rowCount > 0 ? Math.min(issueCount / rowCount, 1) : 0,
      value: formatCompactNumber(issueCount),
    },
  ];

  return <AnalyticsStatGrid items={ledgerStats} />;
}

const neutral = "#40515C";

function toCompactStats(
  kpis: Array<{ label: string; value: string }>
): AnalyticsStatItem[] {
  return kpis.map((kpi) => ({
    accent: neutral,
    detail: "",
    icon: null,
    label: kpi.label,
    value: kpi.value,
  }));
}

