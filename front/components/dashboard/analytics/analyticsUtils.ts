import type { AgentDashboardChart, AgentFileDashboard } from "@/api/agent/types";

export const chartColors = [
  "#40515C",
  "#7FA6B7",
  "#E36F55",
  "#12A17D",
  "#D7A44A",
  "#8B98A3",
];

export type ChartPoint = {
  label: string;
  shortLabel: string;
  value: number;
  fill: string;
  currency: string | null;
};

export function chartPoints(chart: AgentDashboardChart, limit = 8): ChartPoint[] {
  const currencies = Array.isArray(chart.metadata.currencies)
    ? chart.metadata.currencies
    : [];
  const commonCurrency =
    typeof chart.metadata.currency === "string" ? chart.metadata.currency : null;
  return chart.labels.slice(0, limit).map((label, index) => ({
    label,
    shortLabel: shortLabel(label),
    value: Number(chart.values[index] ?? 0),
    fill: chartColors[index % chartColors.length],
    currency:
      typeof currencies[index] === "string" ? currencies[index] : commonCurrency,
  }));
}

export function chartTotal(chart: AgentDashboardChart): number {
  return chart.values.reduce((sum, value) => sum + Number(value || 0), 0);
}

export function chartLeader(chart: AgentDashboardChart): ChartPoint | null {
  const points = chartPoints(chart, chart.labels.length);
  return points.reduce<ChartPoint | null>((leader, point) => {
    if (!leader || point.value > leader.value) return point;
    return leader;
  }, null);
}

export function dashboardNumber(
  dashboard: AgentFileDashboard,
  source: "summary" | "metrics" | "quality",
  key: string
): number {
  const value = dashboard[source][key];
  return typeof value === "number" ? value : 0;
}

export function formatCompactNumber(value: number): string {
  return new Intl.NumberFormat("fr-FR", {
    notation: Math.abs(value) >= 100_000 ? "compact" : "standard",
    maximumFractionDigits: Math.abs(value) >= 100_000 ? 1 : 0,
  }).format(value);
}

export function formatAmount(value: number, currency?: string | null): string {
  const formatted = new Intl.NumberFormat("fr-FR", {
    notation: Math.abs(value) >= 100_000 ? "compact" : "standard",
    maximumFractionDigits: Math.abs(value) >= 100_000 ? 1 : 0,
  }).format(value);
  return currency ? `${formatted} ${currency}` : formatted;
}

export function compactInsight(chart: AgentDashboardChart): string {
  const leader = chartLeader(chart);
  if (!leader) return "Les données sont disponibles pour exploration.";
  if (chart.metric === "amount_sum") {
    return `${leader.label} concentre la valeur la plus élevée: ${formatAmount(
      leader.value,
      leader.currency
    )}.`;
  }
  if (chart.metric === "entry_count") {
    return `${leader.label} porte le plus grand volume: ${formatCompactNumber(
      leader.value
    )} écritures.`;
  }
  return `${leader.label} ressort comme premier signal.`;
}

export function findChart(
  dashboard: AgentFileDashboard,
  chartId: string
): AgentDashboardChart | null {
  return dashboard.charts.find((chart) => chart.chart_id === chartId) ?? null;
}

function shortLabel(label: string): string {
  return label.length > 10 ? `${label.slice(0, 9)}...` : label;
}
