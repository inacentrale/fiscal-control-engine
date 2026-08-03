export type AnalyticsView = "general" | "periodes" | "tva" | "tiers" | "qualite";

export const analyticsViews: Array<{
  id: AnalyticsView;
  label: string;
  chartIds: string[];
}> = [
  {
    id: "general",
    label: "Vue",
    chartIds: ["amount_by_period", "data_quality_by_severity"],
  },
  {
    id: "periodes",
    label: "Périodes",
    chartIds: ["amount_by_period", "entries_by_period"],
  },
  {
    id: "tva",
    label: "TVA",
    chartIds: ["amount_by_tax_code", "tax_candidates_by_amount"],
  },
  {
    id: "tiers",
    label: "Tiers",
    chartIds: ["top_vendors_by_amount", "top_customers_by_amount"],
  },
  {
    id: "qualite",
    label: "Qualité",
    chartIds: ["data_quality_by_severity"],
  },
];
