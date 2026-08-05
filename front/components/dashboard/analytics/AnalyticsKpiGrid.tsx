"use client";

import { useState } from "react";

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
  const [openNature, setOpenNature] = useState<string | null>(null);
  const balancesByNature = dashboard.business_balances_by_nature ?? [];
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
      label: "Alertes",
      value: formatCompactNumber(dashboardNumber(dashboard, "quality", "issue_count")),
    },
  ];

  return (
    <div
      className={cn(
        "grid grid-cols-2 xl:grid-cols-4",
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
      {balancesByNature.map((balance) => {
        const cardId = `${balance.nature}-${balance.currency}-${balance.normal_side}`;
        const isOpen = openNature === cardId;
        return (
          <div
            className="rounded-[14px] bg-[#f5f8fa] px-2.5 py-2.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.72)]"
            key={cardId}
          >
            <button
              aria-expanded={isOpen}
              className="w-full text-left"
              onClick={() => setOpenNature(isOpen ? null : cardId)}
              type="button"
            >
              <span className="flex items-start justify-between gap-2">
                <span>
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
                <span className="text-[13px] font-semibold text-[#60737e]">
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
                    Nature variable ou non référencée : solde métier non calculé.
                  </p>
                )}
              </dl>
            )}
          </div>
        );
      })}
    </div>
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
