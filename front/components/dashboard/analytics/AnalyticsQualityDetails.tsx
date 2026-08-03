"use client";

import { useState } from "react";

import type {
  AgentDataQualityIssue,
  AgentFileDashboard,
} from "@/api/agent/types";

import { formatCompactNumber } from "./analyticsUtils";

export default function AnalyticsQualityDetails({
  dashboard,
}: {
  dashboard: AgentFileDashboard;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const rawIssues = dashboard.quality.issues;
  const issues = Array.isArray(rawIssues)
    ? rawIssues.filter(isQualityIssue)
    : [];
  const excludedPostingIssue = issues.find(
    (issue) => issue.issue_type === "missing_or_unknown_posting_key"
  );

  if (issues.length === 0) return null;

  return (
    <section className="overflow-hidden rounded-[18px] bg-white shadow-[0_16px_42px_rgba(64,81,92,0.07)] ring-1 ring-[#e8f0f3]">
      <button
        aria-expanded={isOpen}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
        onClick={() => setIsOpen((current) => !current)}
        type="button"
      >
        <span>
          <span className="block text-[13px] font-semibold text-[#102734]">
            Détail des alertes de qualité
          </span>
          <span className="mt-0.5 block text-[11px] font-medium text-[#8a98a2]">
            {excludedPostingIssue
              ? `${formatCompactNumber(
                  excludedPostingIssue.affected_count
                )} écriture(s) exclue(s) des calculs signés`
              : `${issues.length} problème(s) détecté(s)`}
          </span>
        </span>
        <span className="text-[16px] font-semibold text-[#60737e]">
          {isOpen ? "−" : "+"}
        </span>
      </button>

      {isOpen && (
        <div className="space-y-2 border-t border-[#edf3f6] p-3">
          {issues.map((issue, index) => (
            <article
              className="rounded-[14px] bg-[#f7fafb] p-3"
              key={`${issue.issue_type}-${issue.source_column}-${index}`}
            >
              <div className="flex items-start justify-between gap-2">
                <p className="text-[12px] font-semibold text-[#102734]">
                  {qualityIssueLabel(issue.issue_type)}
                </p>
                <span className="rounded-full bg-[#fff1ed] px-2 py-0.5 text-[10px] font-semibold text-[#c8563f]">
                  {severityLabel(issue.severity)}
                </span>
              </div>
              <p className="mt-1 text-[11px] font-medium leading-4 text-[#60737e]">
                {issue.message}
              </p>
              <p className="mt-2 text-[10px] font-medium text-[#8a98a2]">
                {formatCompactNumber(issue.affected_count)} ligne(s) · {Math.round(
                  issue.affected_ratio * 100
                )}% du fichier
                {issue.source_column ? ` · Colonne : ${issue.source_column}` : ""}
              </p>
              {issue.affected_accounts && issue.affected_accounts.length > 0 && (
                <div className="mt-3 overflow-hidden rounded-[10px] border border-[#e5edf1] bg-white">
                  <table className="w-full border-collapse text-left">
                    <thead className="bg-[#f2f6f8] text-[10px] font-semibold text-[#60737e]">
                      <tr>
                        <th className="px-2.5 py-2">Compte</th>
                        <th className="px-2.5 py-2 text-right">
                          Écritures exclues
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#edf3f6]">
                      {issue.affected_accounts.map((account) => (
                        <tr key={account.account}>
                          <td className="px-2.5 py-2 text-[11px] font-semibold text-[#203743]">
                            {account.account}
                          </td>
                          <td className="px-2.5 py-2 text-right text-[11px] font-medium text-[#60737e]">
                            {formatCompactNumber(account.affected_count)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function isQualityIssue(value: unknown): value is AgentDataQualityIssue {
  if (!value || typeof value !== "object") return false;
  const issue = value as Record<string, unknown>;
  return (
    typeof issue.issue_type === "string" &&
    typeof issue.severity === "string" &&
    typeof issue.affected_count === "number" &&
    typeof issue.affected_ratio === "number" &&
    typeof issue.message === "string"
  );
}

function qualityIssueLabel(issueType: string): string {
  const labels: Record<string, string> = {
    empty_column: "Colonne vide",
    missing_critical_value: "Valeur critique manquante",
    invalid_amount: "Montant invalide",
    multiple_currencies: "Plusieurs devises",
    missing_counterparty: "Tiers manquant",
    invalid_period: "Période comptable invalide",
    missing_or_unknown_posting_key: "Clé de comptabilisation inexploitable",
    negative_amount_without_indicator: "Montant négatif non interprétable",
  };
  return labels[issueType] ?? issueType.replaceAll("_", " ");
}

function severityLabel(severity: string): string {
  const labels: Record<string, string> = {
    error: "Erreur",
    warning: "Avertissement",
    info: "Information",
  };
  return labels[severity] ?? severity;
}
