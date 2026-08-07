"use client";

import { useState } from "react";

import type { AgentFileDashboard } from "@/api/agent/types";
import {
  Chart2Icon,
  DocumentTextIcon,
  SearchStatusIcon,
} from "@/public/assets/icons/AnalyticsIcons";

import AnalyticsStatGrid, { type AnalyticsStatItem } from "./AnalyticsStatGrid";
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

export function AnalyticsBusinessBalanceGrid({
  dashboard,
}: {
  dashboard: AgentFileDashboard;
}) {
  const [openNature, setOpenNature] = useState<string | null>(null);
  const balances = dashboard.business_balances_by_nature ?? [];

  if (balances.length === 0) return null;

  return (
    <section className="rounded-[22px] bg-white p-4 shadow-[0_16px_42px_rgba(64,81,92,0.07)] ring-1 ring-[#e8f0f3]">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-[15px] font-semibold text-[#102734]">
            Soldes métier par nature
          </h3>
          <p className="mt-0.5 text-[11px] font-medium text-[#8a98a2]">
            Synthèse calculée par regroupement comptable
          </p>
        </div>
        <span className="rounded-full bg-[#f5f8fa] px-2.5 py-1 text-[11px] font-semibold text-[#60737e]">
          {balances.length}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-2 md:grid-cols-3 xl:grid-cols-4">
        {balances.map((balance) => {
          const cardId = `${balance.nature}-${balance.currency}-${balance.normal_side}`;
          const isOpen = openNature === cardId;
          return (
            <div
              className="rounded-[14px] bg-[#f5f8fa] px-3 py-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.72)]"
              key={cardId}
            >
              <button
                aria-expanded={isOpen}
                className="w-full text-left"
                onClick={() => setOpenNature(isOpen ? null : cardId)}
                type="button"
              >
                <span className="flex items-start justify-between gap-2">
                  <span className="min-w-0">
                    <span className="block truncate text-[10px] font-semibold text-[#7d8d97]">
                      {natureLabel(balance.nature)}
                    </span>
                    <span className="mt-1 block truncate text-[15px] font-semibold text-[#102734]">
                      {balance.status === "calculated" &&
                      typeof balance.business_balance === "number"
                        ? formatAmount(balance.business_balance, balance.currency)
                        : "À confirmer"}
                    </span>
                  </span>
                  <span className="shrink-0 text-[13px] font-semibold text-[#60737e]">
                    {isOpen ? "−" : "+"}
                  </span>
                </span>
              </button>
              {isOpen && (
                <dl className="mt-2 space-y-1 border-t border-[#e8f0f3] pt-2 text-[10px] font-medium text-[#60737e]">
                  <InfoRow label="Devise" value={balance.currency} />
                  <InfoRow
                    label="Écritures"
                    value={formatCompactNumber(balance.entry_count)}
                  />
                  <InfoRow
                    label="Comptes"
                    value={formatCompactNumber(balance.account_count)}
                  />
                  <InfoRow
                    label="Utilisées"
                    value={formatCompactNumber(balance.used_entry_count)}
                  />
                  <InfoRow
                    label="Exclues"
                    value={formatCompactNumber(
                      balance.excluded_entry_count +
                        balance.business_excluded_entry_count
                    )}
                  />
                  <InfoRow
                    label="Débit"
                    value={formatAmount(balance.debit_total, balance.currency)}
                  />
                  <InfoRow
                    label="Crédit"
                    value={formatAmount(balance.credit_total, balance.currency)}
                  />
                  {balance.status !== "calculated" && (
                    <p className="pt-1 text-[10px] leading-4 text-[#c8563f]">
                      Nature variable ou non référencée : solde métier non
                      calculé.
                    </p>
                  )}
                </dl>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <dt>{label}</dt>
      <dd className="text-right font-semibold text-[#203743]">{value}</dd>
    </div>
  );
}

function natureLabel(nature: string): string {
  const labels: Record<string, string> = {
    resources_durables: "Ressources durables",
    fixed_assets: "Immobilisations",
    inventory: "Stocks",
    suppliers: "Fournisseurs",
    supplier_receivables: "Fournisseurs débiteurs",
    customers: "Clients",
    customer_payables: "Clients créditeurs",
    personnel: "Personnel",
    social_bodies: "Organismes sociaux",
    state_and_tax: "État / fiscalité",
    partners: "Associés / groupe",
    miscellaneous_third_parties: "Tiers divers",
    third_parties: "Tiers",
    third_party_impairment: "Dépréciations tiers",
    banks: "Banques",
    bank_overdrafts: "Concours bancaires",
    cash: "Caisse",
    cash_and_financial: "Trésorerie",
    internal_transfers: "Virements internes",
    treasury_impairment: "Risques trésorerie",
    expenses: "Charges",
    revenue: "Produits",
    unclassified: "Non classé",
  };
  return labels[nature] ?? nature.replaceAll("_", " ");
}
