export type AnalyticsView = "general" | "periodes" | "tva" | "tiers" | "qualite";

export const analyticsViews: Array<{
  id: AnalyticsView;
  label: string;
  chartIds: string[];
}> = [
  {
    id: "general",
    label: "Vue",
    chartIds: [
      "amount_by_account_class",
      "debit_credit_by_account_class",
      "debit_credit_by_period",
    ],
  },
  {
    id: "qualite",
    label: "Qualité",
    chartIds: ["data_quality_by_severity"],
  },
];
