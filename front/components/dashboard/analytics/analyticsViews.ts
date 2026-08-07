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
      "cumulative_resources_by_period",
      "cumulative_uses_by_period",
      "resources_by_document_type",
      "uses_by_document_type",
    ],
  },
  {
    id: "periodes",
    label: "Périodes",
    chartIds: [
      "debit_credit_by_period",
      "cumulative_resources_by_period",
      "cumulative_uses_by_period",
      "entries_by_period",
      "resources_by_fiscal_year",
      "uses_by_fiscal_year",
      "entries_by_fiscal_year",
    ],
  },
  {
    id: "tva",
    label: "TVA",
    chartIds: [
      "resources_by_tax_code",
      "uses_by_tax_code",
      "entries_by_posting_key",
      "tax_candidates_by_amount",
    ],
  },
  {
    id: "qualite",
    label: "Qualité",
    chartIds: ["data_quality_by_severity"],
  },
];
