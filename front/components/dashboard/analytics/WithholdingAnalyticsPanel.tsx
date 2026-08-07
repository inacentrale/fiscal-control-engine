"use client";
import { useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type {
  AgentDashboardChart,
  AgentFileDashboard,
  RasCandidateDetectionResult,
  RasCandidateReviewCase,
  RasReviewPeriod,
} from "@/api/agent/types";
import { ModalTitle } from "@/components/base/modal";
import {
  Chart2Icon,
  DocumentTextIcon,
  MoneyTickIcon,
  PercentageSquareIcon,
  SearchStatusIcon,
} from "@/public/assets/icons/AnalyticsIcons";

import AnalyticsReveal from "./AnalyticsReveal";
import AnalyticsChartCard from "./AnalyticsChartCard";
import AnalyticsKpiGrid from "./AnalyticsKpiGrid";
import AnalyticsQualityDetails from "./AnalyticsQualityDetails";
import AnalyticsStatGrid, { type AnalyticsStatItem } from "./AnalyticsStatGrid";
import AnalyticsViewTabs from "./AnalyticsViewTabs";
import {
  chartColors,
  findChart,
  formatAmount,
  formatCompactNumber,
} from "./analyticsUtils";
import RasAuditReportButton from "./RasAuditReportButton";
import WithholdingDonutSummary from "./WithholdingDonutSummary";
import WithholdingTrendCard from "./WithholdingTrendCard";
import AnalyticsModeSwitcher, { type AnalyticsMode } from "./AnalyticsModeSwitcher";
import type { AnalyticsView } from "./analyticsViews";

type WithholdingQueryState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "empty" }
  | { status: "ready"; result: RasCandidateDetectionResult };

export default function WithholdingAnalyticsPanel({
  sessionId = null,
  state,
}: {
  sessionId?: string | null;
  state: WithholdingQueryState;
}) {
  return (
    <>
      <header className="space-y-1">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-[16px] font-semibold">Contrôle RAS</h2>
          {state.status === "ready" && (
            <span className="rounded-full bg-[#fff4ed] px-2.5 py-1 text-[11px] font-semibold text-[#c8563f]">
              Revue
            </span>
          )}
        </div>
        {state.status === "ready" && (
          <p className="truncate text-[12px] font-medium text-[#7d8d97]">
            {state.result.sheetName} · aucune décision fiscale automatique
          </p>
        )}
        <div className="pt-1">
          <RasAuditReportButton sessionId={sessionId} />
        </div>
      </header>

      {state.status === "loading" && <WithholdingSkeleton />}
      {state.status === "error" && (
        <WithholdingState
          title="Contrôle RAS indisponible"
          text={state.message}
        />
      )}
      {state.status === "empty" && (
        <WithholdingState
          title="Aucun signal RAS"
          text="Le fichier actif ne retourne pas encore de synthèse RAS exploitable."
        />
      )}
      {state.status === "ready" && <WithholdingReadyBody result={state.result} />}
    </>
  );
}

function WithholdingReadyBody({ result }: { result: RasCandidateDetectionResult }) {
  const signalItems = topEntries(result.signalCounts, 4);
  const missingFactItems = topEntries(result.missingFactCounts, 3);
  const periods = (result.rasReview?.periods ?? []).filter(
    (period) => period.currency === "XOF"
  );
  const amount = primaryAmount(result.candidateAmountsByCurrency);
  const candidateRate =
    result.evaluatedPieceCount > 0
      ? result.candidatePieceCount / result.evaluatedPieceCount
      : 0;

  return (
    <>
      <AnalyticsReveal>
        <AnalyticsStatGrid
          items={rasCompactStats({ amount, candidateRate, result })}
          variant="compact"
        />
      </AnalyticsReveal>

      <AnalyticsReveal delay={0.02}>
        <WithholdingDonutSummary result={result} />
      </AnalyticsReveal>

      {periods.length > 0 && (
        <AnalyticsReveal delay={0.04}>
          <WithholdingTrendCard periods={periods} />
        </AnalyticsReveal>
      )}

      <AnalyticsReveal delay={0.06}>
        <RasBreakdownCard
          emptyText="Aucun signal textuel dominant."
          items={signalItems}
          title="Signaux principaux"
          valueLabel={`${signalItems.length} signal(s)`}
        />
      </AnalyticsReveal>

      {missingFactItems.length > 0 && (
        <AnalyticsReveal delay={0.08}>
          <RasBreakdownCard
            items={missingFactItems}
            tone="warning"
            title="Faits manquants"
            valueLabel={`${missingFactItems.length} point(s)`}
          />
        </AnalyticsReveal>
      )}
    </>
  );
}

function RasBreakdownCard({
  emptyText = "Aucune donnée exploitable.",
  items,
  title,
  tone = "neutral",
  valueLabel,
}: {
  emptyText?: string;
  items: Array<{ label: string; value: number }>;
  title: string;
  tone?: "neutral" | "warning";
  valueLabel: string;
}) {
  const max = Math.max(...items.map((item) => item.value), 1);

  return (
    <section className="rounded-[18px] bg-white p-4 shadow-[0_16px_42px_rgba(64,81,92,0.07)] ring-1 ring-[#e8f0f3]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-[14px] font-semibold text-[#102734]">{title}</h3>
          <p className="mt-0.5 text-[11px] font-medium text-[#8a98a2]">
            Synthèse agrégée
          </p>
        </div>
        <span className="rounded-full bg-[#f5f8fa] px-2.5 py-1 text-[11px] font-semibold text-[#60737e]">
          {valueLabel}
        </span>
      </div>

      {items.length > 0 ? (
        <div className="mt-4 space-y-3">
          {items.map((item) => (
            <div className="space-y-1.5" key={item.label}>
              <div className="flex items-center justify-between gap-2">
                <span className="truncate text-[12px] font-semibold text-[#344854]">
                  {rasLabel(item.label)}
                </span>
                <span className="text-[12px] font-semibold text-[#102734]">
                  {formatCompactNumber(item.value)}
                </span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-[#eef4f7]">
                <div
                  className={[
                    "h-full rounded-full transition-all duration-700 ease-out",
                    tone === "warning" ? "bg-[#E36F55]" : "bg-[#40515C]",
                  ].join(" ")}
                  style={{
                    width: `${Math.max(
                      7,
                      Math.round((item.value / max) * 100)
                    )}%`,
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="mt-4 rounded-[14px] bg-[#f7fafb] px-3 py-3 text-[12px] font-medium text-[#8a98a2]">
          {emptyText}
        </p>
      )}
    </section>
  );
}

export function WithholdingExpandedModal({
  activeMode,
  amount,
  dashboard,
  activeView,
  candidateRate,
  missingFactItems,
  onModeChange,
  onClose,
  onViewChange,
  periods,
  primaryChart,
  result,
  secondaryCharts,
  signalItems,
  sessionId = null,
}: {
  activeMode: AnalyticsMode;
  activeView: AnalyticsView;
  amount: { currency: string; value: number } | null;
  dashboard: AgentFileDashboard;
  candidateRate: number;
  missingFactItems: Array<{ label: string; value: number }>;
  onModeChange: (mode: AnalyticsMode) => void;
  onClose: () => void;
  onViewChange: (view: AnalyticsView) => void;
  periods: RasReviewPeriod[];
  primaryChart: AgentDashboardChart | null;
  result: RasCandidateDetectionResult;
  secondaryCharts: AgentDashboardChart[];
  signalItems: Array<{ label: string; value: number }>;
  sessionId?: string | null;
}) {
  const [selectedMissingFact, setSelectedMissingFact] = useState<string | null>(
    null
  );
  const handleModalActiveChange = (isActive: boolean) => {
    if (!isActive) onClose();
  };
  const title =
    activeMode === "withholding" ? "Contrôle RAS" : "Analyse Grand Livre";

  return (
    <div className="fixed inset-0 z-50 bg-[#102734]/26 p-3 backdrop-blur-[2px] sm:p-6">
      <section className="mx-auto flex h-full max-w-[1480px] flex-col overflow-hidden rounded-[30px] bg-[#f7fafb] shadow-[0_32px_90px_rgba(16,39,52,0.24)] ring-1 ring-white/70">
        <div className="sticky top-0 z-10 bg-[#f7fafb]/92 px-5 pt-4 backdrop-blur sm:px-7">
          <ModalTitle
            className="mb-2 pb-0"
            setActive={handleModalActiveChange}
            title={
              <span className="flex min-w-0 items-center gap-4">
                <span className="shrink-0">{title}</span>
                <span className="block w-[300px] max-w-[52vw]">
                  <AnalyticsModeSwitcher
                    activeMode={activeMode}
                    compact
                    onChange={onModeChange}
                  />
                </span>
                {activeMode === "withholding" && (
                  <RasAuditReportButton sessionId={sessionId} />
                )}
              </span>
            }
            titleClass="!max-w-none !overflow-visible !text-clip !whitespace-normal text-[#102734]"
          />
        </div>

        <div className="custom-scrollbar min-h-0 flex-1 overflow-y-auto px-4 pb-5 pt-3 sm:px-7">
          {activeMode === "withholding" ? (
            <>
              <AnalyticsStatGrid
                items={rasExpandedStats({
                  amount,
                  candidateRate,
                  result,
                })}
              />

              <div className="mt-4">
                <RasCandidateAccountsTable result={result} />
              </div>

              <div className="mt-4">
                <RasReviewQueue
                  missingFactFilter={selectedMissingFact}
                  onClearMissingFactFilter={() => setSelectedMissingFact(null)}
                  result={result}
                />
              </div>

              <div
                className={[
                  "mt-4 grid gap-4",
                  periods.length > 0
                    ? "xl:grid-cols-[minmax(0,1.08fr)_minmax(420px,0.92fr)]"
                    : "xl:grid-cols-1",
                ].join(" ")}
              >
                {periods.length > 0 && <ExpandedTrendCard periods={periods} />}
                <ExpandedStatusCard result={result} />
              </div>

              {periods.length > 0 && (
                <div className="mt-4">
                  <ExpandedRasPeriodVolumeCard periods={periods} />
                </div>
              )}

              <div className="mt-4">
                <ExpandedBarCard
                  countLabel={`${signalItems.length} ${
                    signalItems.length > 1
                      ? "signaux détectés"
                      : "signal détecté"
                  }`}
                  items={signalItems}
                  subtitle="Comptages par signal déterministe"
                  title="Signaux principaux"
                />
              </div>

              <div className="mt-4 grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
                <RasMissingFactsCard
                  items={missingFactItems}
                  onSelect={(fact) => {
                    setSelectedMissingFact((current) =>
                      current === fact ? null : fact
                    );
                    setTimeout(() => {
                      document
                        .getElementById("ras-review-queue")
                        ?.scrollIntoView({ behavior: "smooth", block: "start" });
                    }, 0);
                  }}
                  selectedFact={selectedMissingFact}
                />
                <RasDataQualityCard
                  items={topEntries(result.issueCounts, 6)}
                  rowCount={result.rowCount}
                />
              </div>
            </>
          ) : (
            <ExpandedLedgerView
              activeView={activeView}
              dashboard={dashboard}
              onViewChange={onViewChange}
              primaryChart={primaryChart}
              secondaryCharts={secondaryCharts}
            />
          )}
        </div>
      </section>
    </div>
  );
}

function RasCandidateAccountsTable({
  result,
}: {
  result: RasCandidateDetectionResult;
}) {
  const accounts = result.candidateAccounts;

  return (
    <details
      className="group rounded-[24px] bg-white shadow-[0_18px_44px_rgba(64,81,92,0.07)] ring-1 ring-[#e5eef2]"
      open
    >
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-4 marker:hidden">
        <span>
          <span className="block text-[16px] font-semibold text-[#102734]">
            Comptes concernés
          </span>
          <span className="mt-1 block text-[12px] font-medium text-[#7d8d97]">
            Regroupement des pièces candidates par compte de charge
          </span>
        </span>
        <span className="flex items-center gap-2">
          <span className="rounded-full bg-[#edf5f8] px-3 py-1.5 text-[12px] font-semibold text-[#40515C]">
            {formatCompactNumber(accounts.length)} compte(s)
          </span>
          <span
            aria-hidden="true"
            className="text-[18px] font-semibold text-[#60737e] transition-transform group-open:rotate-45"
          >
            +
          </span>
        </span>
      </summary>

      {accounts.length > 0 ? (
        <div className="overflow-x-auto border-t border-[#edf2f4]">
          <table className="w-full min-w-[760px] border-collapse text-left">
            <thead className="bg-[#f7fafb] text-[11px] font-semibold uppercase tracking-[0.04em] text-[#7d8d97]">
              <tr>
                <th className="px-4 py-3">Compte</th>
                <th className="px-4 py-3 text-right">Pièces candidates</th>
                <th className="px-4 py-3 text-right">Montant candidat</th>
                <th className="px-4 py-3">Mode de détection</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#edf2f4]">
              {accounts.map((account) => (
                <tr className="text-[13px] text-[#40515C]" key={account.accountNumber}>
                  <td className="whitespace-nowrap px-4 py-3 font-semibold text-[#102734]">
                    {account.accountNumber}
                  </td>
                  <td className="px-4 py-3 text-right font-semibold">
                    {formatCompactNumber(account.candidatePieceCount)}
                  </td>
                  <td className="px-4 py-3 text-right font-semibold">
                    {formatAccountAmounts(account.amountsByCurrency)}
                  </td>
                  <td className="px-4 py-3">
                    {primaryDetectionMode(account.statusCounts)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="border-t border-[#edf2f4] px-4 py-5 text-[13px] font-medium text-[#7d8d97]">
          Aucun compte de charge identifié parmi les candidats.
        </p>
      )}
    </details>
  );
}

function RasReviewQueue({
  missingFactFilter,
  onClearMissingFactFilter,
  result,
}: {
  missingFactFilter: string | null;
  onClearMissingFactFilter: () => void;
  result: RasCandidateDetectionResult;
}) {
  const [detectionStatus, setDetectionStatus] = useState("all");
  const filteredCases = result.reviewCases.filter(
    (reviewCase) =>
      (detectionStatus === "all" ||
        reviewCase.detectionStatus === detectionStatus) &&
      (!missingFactFilter || reviewCase.missingFacts.includes(missingFactFilter))
  );

  return (
    <details
      className="group rounded-[24px] bg-white shadow-[0_18px_44px_rgba(64,81,92,0.07)] ring-1 ring-[#e5eef2]"
      id="ras-review-queue"
      open
    >
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-4 marker:hidden">
        <span>
          <span className="block text-[16px] font-semibold text-[#102734]">
            Pièces à vérifier
          </span>
          <span className="mt-1 block text-[12px] font-medium text-[#7d8d97]">
            Motif, contrepartie RAS et action attendue pour chaque candidat
          </span>
        </span>
        <span className="flex items-center gap-2">
          <span className="rounded-full bg-[#fff4ed] px-3 py-1.5 text-[12px] font-semibold text-[#c8563f]">
            {detectionStatus === "all" && !missingFactFilter
              ? `${formatCompactNumber(result.reviewCases.length)} cas`
              : `${formatCompactNumber(filteredCases.length)} / ${formatCompactNumber(result.reviewCases.length)}`}
          </span>
          <span
            aria-hidden="true"
            className="text-[18px] font-semibold text-[#60737e] transition-transform group-open:rotate-45"
          >
            +
          </span>
        </span>
      </summary>

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[#edf2f4] px-4 py-3">
        <label
          className="text-[12px] font-semibold text-[#60737e]"
          htmlFor="ras-detection-status-filter"
        >
          Filtrer la colonne « Pourquoi ? »
        </label>
        <select
          className="min-w-[220px] rounded-[12px] border border-[#dce7eb] bg-[#f7fafb] px-3 py-2 text-[12px] font-semibold text-[#40515C] outline-none transition focus:border-[#7FA6B7] focus:ring-2 focus:ring-[#7FA6B7]/20"
          id="ras-detection-status-filter"
          onChange={(event) => setDetectionStatus(event.target.value)}
          value={detectionStatus}
        >
          <option value="all">Tous les modes de détection</option>
          <option value="candidate_account_and_text">Compte + libellé</option>
          <option value="candidate_account_only">Compte seul</option>
          <option value="candidate_text_only">Libellé seul</option>
          <option value="candidate_indeterminate">Indéterminé</option>
        </select>
      </div>

      {missingFactFilter && (
        <div className="flex items-center justify-between gap-3 border-t border-[#f2e3da] bg-[#fff8f3] px-4 py-3">
          <p className="text-[12px] font-semibold text-[#9b5b42]">
            Filtre actif : {missingFactLabel(missingFactFilter)}
          </p>
          <button
            className="cursor-pointer text-[12px] font-semibold text-[#9b5b42] underline underline-offset-2"
            onClick={onClearMissingFactFilter}
            type="button"
          >
            Effacer
          </button>
        </div>
      )}

      {!result.sourceScopeComplete && (
        <p className="border-t border-[#f2e3da] bg-[#fff8f3] px-4 py-3 text-[12px] font-medium text-[#9b5b42]">
          La recherche de contrepartie est limitée par les données disponibles :
          aucune absence de RAS n’est présentée comme certaine.
        </p>
      )}

      {filteredCases.length > 0 ? (
        <div className="max-h-[560px] overflow-auto border-t border-[#edf2f4]">
          <table className="w-full min-w-[1120px] border-collapse text-left">
            <thead className="sticky top-0 z-[1] bg-[#f7fafb] text-[11px] font-semibold uppercase tracking-[0.04em] text-[#7d8d97]">
              <tr>
                <th className="px-4 py-3">Priorité</th>
                <th className="px-4 py-3">Pièce / date</th>
                <th className="px-4 py-3">Compte / libellé</th>
                <th className="px-4 py-3 text-right">Montant</th>
                <th className="px-4 py-3">Pourquoi ?</th>
                <th className="px-4 py-3">Contrepartie RAS</th>
                <th className="px-4 py-3">Action attendue</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#edf2f4]">
              {filteredCases.map((reviewCase) => (
                <RasReviewQueueRow
                  key={reviewCase.candidateId}
                  reviewCase={reviewCase}
                />
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="border-t border-[#edf2f4] px-4 py-5 text-[13px] font-medium text-[#7d8d97]">
          Aucune pièce ne correspond au mode de détection sélectionné.
        </p>
      )}
    </details>
  );
}

function RasReviewQueueRow({
  reviewCase,
}: {
  reviewCase: RasCandidateReviewCase;
}) {
  const priorityStyles = {
    high: "bg-[#fff0eb] text-[#c8563f]",
    medium: "bg-[#fff7df] text-[#9a6a13]",
    low: "bg-[#eaf8f3] text-[#168066]",
  };
  const priorityLabels = { high: "Haute", medium: "Moyenne", low: "Faible" };

  return (
    <tr className="align-top text-[12px] text-[#40515C]">
      <td className="px-4 py-3">
        <span className={`rounded-full px-2.5 py-1 font-semibold ${priorityStyles[reviewCase.priority]}`}>
          {priorityLabels[reviewCase.priority]}
        </span>
      </td>
      <td className="px-4 py-3">
        <strong className="block whitespace-nowrap text-[#102734]">
          {reviewCase.documentNumber ?? "Pièce non renseignée"}
        </strong>
        <span className="mt-1 block text-[#7d8d97]">
          {formatReviewDate(reviewCase.postingDate)}
        </span>
      </td>
      <td className="max-w-[260px] px-4 py-3">
        <strong className="block text-[#102734]">
          {reviewCase.accountNumbers.join(", ") || "Compte non identifié"}
        </strong>
        <span className="mt-1 block truncate text-[#7d8d97]" title={reviewCase.label ?? undefined}>
          {reviewCase.label ?? "Libellé non renseigné"}
        </span>
      </td>
      <td className="whitespace-nowrap px-4 py-3 text-right font-semibold text-[#102734]">
        {formatAccountAmounts(reviewCase.amountsByCurrency)}
      </td>
      <td className="px-4 py-3">
        {rasLabel(reviewCase.detectionStatus)}
      </td>
      <td className="px-4 py-3">
        {counterpartStatusLabel(reviewCase.counterpartStatus)}
      </td>
      <td className="max-w-[240px] px-4 py-3 font-semibold text-[#102734]">
        {reviewActionLabel(reviewCase.recommendedAction)}
      </td>
    </tr>
  );
}

function formatReviewDate(value: string | null): string {
  if (!value) return "Date non renseignée";
  const date = new Date(`${value}T00:00:00`);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat("fr-FR").format(date);
}

function counterpartStatusLabel(value: string): string {
  const labels: Record<string, string> = {
    found_in_same_entry: "Présente dans la même pièce",
    potential_related_entry: "Contrepartie liée à confirmer",
    not_found_in_scope: "Non trouvée dans le périmètre",
    indeterminate: "Recherche non concluante",
    not_evaluated: "Non évaluée",
  };
  return labels[value] ?? value.replaceAll("_", " ");
}

function reviewActionLabel(value: string): string {
  const labels: Record<string, string> = {
    verify_ras_booking: "Vérifier la comptabilisation de la RAS",
    confirm_related_counterpart: "Confirmer le lien avec la contrepartie trouvée",
    complete_missing_information: "Compléter les informations manquantes",
    validate_recorded_counterpart: "Valider la contrepartie comptabilisée",
  };
  return labels[value] ?? value.replaceAll("_", " ");
}

function formatAccountAmounts(amounts: Record<string, string>): string {
  const values = Object.entries(amounts).map(([currency, rawAmount]) =>
    formatAmount(Number(rawAmount), currency)
  );
  return values.length > 0 ? values.join(" · ") : "Montant indisponible";
}

function primaryDetectionMode(statuses: Record<string, number>): string {
  const [status] = Object.entries(statuses).sort(
    ([, left], [, right]) => right - left
  )[0] ?? ["candidate_indeterminate", 0];
  return rasLabel(status);
}

function ExpandedLedgerView({
  activeView,
  dashboard,
  onViewChange,
  primaryChart,
  secondaryCharts,
}: {
  activeView: AnalyticsView;
  dashboard: AgentFileDashboard;
  onViewChange: (view: AnalyticsView) => void;
  primaryChart: AgentDashboardChart | null;
  secondaryCharts: AgentDashboardChart[];
}) {
  const priorityCharts = [
    findChart(dashboard, "amount_by_account_class"),
    findChart(dashboard, "debit_credit_by_account_class"),
    findChart(dashboard, "debit_credit_by_period"),
    findChart(dashboard, "cumulative_resources_by_period"),
    findChart(dashboard, "cumulative_uses_by_period"),
  ].filter((chart): chart is AgentDashboardChart => Boolean(chart));
  const orderedCharts = [primaryChart, ...priorityCharts].filter(
    (chart): chart is AgentDashboardChart => Boolean(chart)
  );
  const displayedIds = new Set(orderedCharts.map((chart) => chart.chart_id));
  const remainingCharts = secondaryCharts.filter(
    (chart) => !displayedIds.has(chart.chart_id)
  );

  return (
    <>
      <AnalyticsKpiGrid dashboard={dashboard} variant="expanded" />
      <div className="mt-4">
        <AnalyticsQualityDetails dashboard={dashboard} defaultOpen />
      </div>
      <div className="mt-4">
        <AnalyticsViewTabs activeView={activeView} onChange={onViewChange} />
      </div>
      <div className="mt-4 grid gap-4 xl:grid-cols-2">
        {[...orderedCharts, ...remainingCharts].map((chart) => (
          <AnalyticsChartCard
            chart={chart}
            density="modal"
            featured={chart.chart_id === "top_accounts_by_amount"}
            key={chart.chart_id}
          />
        ))}
      </div>
    </>
  );
}

function rasExpandedStats({
  amount,
  candidateRate,
  result,
}: {
  amount: { currency: string; value: number } | null;
  candidateRate: number;
  result: RasCandidateDetectionResult;
}): AnalyticsStatItem[] {
  const rejectedRate =
    result.rowCount > 0 ? result.rejectedRowCount / result.rowCount : 0;
  const excludedRate =
    result.evaluatedPieceCount > 0
      ? result.excludedPieceCount / result.evaluatedPieceCount
      : 0;

  return [
    {
      accent: "#40515C",
      detail: "Pièces évaluées dans la revue",
      icon: <DocumentTextIcon className="size-5" />,
      label: "Évaluées",
      muted: true,
      progress:
        result.rowCount > 0 ? result.evaluatedPieceCount / result.rowCount : 0,
      value: formatCompactNumber(result.evaluatedPieceCount),
    },
    {
      accent: "#7FA6B7",
      detail: "Pièces candidates à examiner",
      icon: <SearchStatusIcon className="size-5" />,
      label: "Candidates",
      progress: candidateRate,
      strong: true,
      value: formatCompactNumber(result.candidatePieceCount),
    },
    {
      accent: "#12A17D",
      detail: "Part des candidats détectés",
      icon: <PercentageSquareIcon className="size-5" />,
      label: "Ratio",
      progress: candidateRate,
      value: `${Math.round(candidateRate * 1000) / 10}%`,
    },
    {
      accent: "#D7A44A",
      detail: amount ? `Montant candidat en ${amount.currency}` : "Montant candidat",
      icon: <MoneyTickIcon className="size-5" />,
      label: "Montant",
      progress: amount ? 1 : 0,
      value: amount ? formatAmount(amount.value, amount.currency) : "-",
    },
    {
      accent: "#8B98A3",
      detail: "Pièces sorties du périmètre",
      icon: <Chart2Icon className="size-5" />,
      label: "Exclues",
      muted: true,
      progress: excludedRate,
      value: formatCompactNumber(result.excludedPieceCount),
    },
    {
      accent: "#E36F55",
      detail: "Lignes rejetées par contrôle",
      icon: <SearchStatusIcon className="size-5" />,
      label: "Rejets",
      progress: rejectedRate,
      value: formatCompactNumber(result.rejectedRowCount),
    },
  ];
}

function rasCompactStats({
  amount,
  candidateRate,
  result,
}: {
  amount: { currency: string; value: number } | null;
  candidateRate: number;
  result: RasCandidateDetectionResult;
}): AnalyticsStatItem[] {
  return [
    {
      accent: "#40515C",
      detail: "",
      icon: null,
      label: "Pièces",
      value: formatCompactNumber(result.evaluatedPieceCount),
    },
    {
      accent: "#7FA6B7",
      detail: "",
      icon: null,
      label: "Candidats",
      value: formatCompactNumber(result.candidatePieceCount),
    },
    {
      accent: "#12A17D",
      detail: "",
      icon: null,
      label: "Taux",
      value: `${Math.round(candidateRate * 1000) / 10}%`,
    },
    {
      accent: "#D7A44A",
      detail: "",
      icon: null,
      label: "Montant",
      value: amount ? formatAmount(amount.value, amount.currency) : "-",
    },
  ];
}

function ExpandedRasPeriodVolumeCard({
  periods,
}: {
  periods: RasReviewPeriod[];
}) {
  const data = periods.map((period) => ({
    ...period,
    shortPeriod: `P${period.period}`,
    candidateRatePercent: Math.round(period.candidateRate * 1000) / 10,
  }));

  return (
    <section className="rounded-[24px] bg-white p-4 shadow-[0_18px_44px_rgba(64,81,92,0.07)] ring-1 ring-[#e5eef2]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-[16px] font-semibold text-[#102734]">
            Pièces RAS par période
          </h3>
          <p className="mt-1 text-[12px] font-medium text-[#7d8d97]">
            Candidats comparés au volume évalué
          </p>
        </div>
      </div>

      <div className="mt-4 h-[220px] w-full outline-none [&_.recharts-wrapper]:outline-none [&_svg]:outline-none">
        <ResponsiveContainer height="100%" width="100%">
          <BarChart data={data} margin={{ top: 12, right: 18, bottom: 4, left: -12 }}>
            <CartesianGrid stroke="#EAF1F4" strokeDasharray="6 10" vertical={false} />
            <XAxis
              axisLine={false}
              dataKey="shortPeriod"
              tick={{ fill: "#8b9aa3", fontSize: 11, fontWeight: 700 }}
              tickLine={false}
              tickMargin={12}
            />
            <YAxis
              axisLine={false}
              tick={{ fill: "#9aa8b0", fontSize: 11, fontWeight: 700 }}
              tickFormatter={(value) => formatCompactNumber(Number(value))}
              tickLine={false}
              width={56}
            />
            <Tooltip content={<ExpandedRasVolumeTooltip />} cursor={{ fill: "rgba(127,166,183,0.10)" }} />
            <Bar
              dataKey="evaluatedEntryCount"
              fill="#D9E3E8"
              maxBarSize={28}
              name="Évaluées"
              radius={[8, 8, 0, 0]}
            />
            <Bar
              dataKey="candidateEntryCount"
              fill="#40515C"
              maxBarSize={28}
              name="Candidats"
              radius={[8, 8, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

function ExpandedTrendCard({ periods }: { periods: RasReviewPeriod[] }) {
  const data = periods.map((period) => ({
    ...period,
    shortPeriod: `P${period.period}`,
  }));
  const currency = data.find((item) => item.currency)?.currency ?? null;

  return (
    <section className="rounded-[24px] bg-white p-4 shadow-[0_18px_44px_rgba(64,81,92,0.07)] ring-1 ring-[#e5eef2]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-[16px] font-semibold text-[#102734]">
            Courbes RAS
          </h3>
          <p className="mt-1 text-[12px] font-medium text-[#7d8d97]">
            Montant candidat et cumul par période
          </p>
        </div>
      </div>

      {data.length > 0 ? (
        <div className="mt-4 h-[230px] w-full outline-none [&_.recharts-wrapper]:outline-none [&_svg]:outline-none">
          <ResponsiveContainer height="100%" width="100%">
            <AreaChart data={data} margin={{ top: 18, right: 18, bottom: 4, left: -12 }}>
              <defs>
                <linearGradient id="ras-expanded-amount" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stopColor="#40515C" stopOpacity={0.24} />
                  <stop offset="100%" stopColor="#40515C" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="ras-expanded-cumulative" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stopColor="#12A17D" stopOpacity={0.14} />
                  <stop offset="100%" stopColor="#12A17D" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#EAF1F4" strokeDasharray="6 10" vertical={false} />
              <XAxis
                axisLine={false}
                dataKey="shortPeriod"
                tick={{ fill: "#8b9aa3", fontSize: 11, fontWeight: 700 }}
                tickLine={false}
                tickMargin={12}
              />
              <YAxis
                axisLine={false}
                tick={{ fill: "#9aa8b0", fontSize: 11, fontWeight: 700 }}
                tickFormatter={(value) => formatCompactNumber(Number(value))}
                tickLine={false}
                width={62}
              />
              <Tooltip
                content={<ExpandedTrendTooltip currency={currency} />}
                cursor={{ stroke: "#40515C", strokeDasharray: "4 8" }}
              />
              <Legend
                align="center"
                iconType="line"
                verticalAlign="bottom"
                wrapperStyle={{
                  color: "#60737e",
                  fontSize: 11,
                  fontWeight: 600,
                  paddingTop: 8,
                }}
              />
              <Area
                dataKey="candidateAmount"
                fill="url(#ras-expanded-amount)"
                legendType="none"
                stroke="none"
                tooltipType="none"
                type="monotone"
              />
              <Area
                dataKey="cumulativeCandidateAmount"
                fill="url(#ras-expanded-cumulative)"
                legendType="none"
                stroke="none"
                tooltipType="none"
                type="monotone"
              />
              <Line
                dataKey="candidateAmount"
                dot={{ fill: "#FFFFFF", r: 4, stroke: "#40515C", strokeWidth: 2 }}
                name="Montant candidat"
                stroke="#40515C"
                strokeWidth={3}
                type="monotone"
              />
              <Line
                dataKey="cumulativeCandidateAmount"
                dot={false}
                name="Cumul candidat"
                stroke="#12A17D"
                strokeWidth={3}
                type="monotone"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <p className="mt-5 rounded-[18px] bg-[#f7fafb] px-4 py-5 text-[13px] font-medium text-[#7d8d97]">
          Les périodes RAS ne sont pas encore disponibles.
        </p>
      )}
    </section>
  );
}

function ExpandedRasVolumeTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{
    name?: string;
    value?: number;
    payload?: { period?: string; candidateRatePercent?: number };
  }>;
}) {
  if (!active || !payload?.length) return null;
  const period = payload[0]?.payload?.period;
  const rate = payload[0]?.payload?.candidateRatePercent ?? 0;

  return (
    <div className="rounded-[16px] bg-[#102734] px-3 py-2 text-white shadow-[0_14px_34px_rgba(16,39,52,0.22)]">
      <p className="text-[11px] font-medium text-white/70">Période P{period}</p>
      {payload.map((item) => (
        <p className="mt-1 text-[13px] font-semibold" key={item.name}>
          {item.name}: {formatCompactNumber(Number(item.value ?? 0))}
        </p>
      ))}
      <p className="mt-1 text-[12px] font-semibold text-white/75">
        Taux candidat: {rate}%
      </p>
    </div>
  );
}

function ExpandedStatusCard({
  result,
}: {
  result: RasCandidateDetectionResult;
}) {
  const data = topEntries(result.statusCounts, 5).map((item) => ({
    ...item,
    name: rasLabel(item.label),
    guidance: rasStatusGuidance(item.label),
  }));

  return (
    <section className="rounded-[24px] bg-white p-4 shadow-[0_18px_44px_rgba(64,81,92,0.07)] ring-1 ring-[#e5eef2]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-[16px] font-semibold text-[#102734]">
            Statuts candidats
          </h3>
          <p className="mt-1 text-[12px] font-medium text-[#7d8d97]">
            Répartition des modes de détection
          </p>
        </div>
        <span className="rounded-full bg-[#edf5f8] px-3 py-1.5 text-[12px] font-semibold text-[#40515C]">
          {formatCompactNumber(result.candidatePieceCount)}
        </span>
      </div>

      <div className="mt-4 grid items-center gap-4 md:grid-cols-[200px_minmax(0,1fr)]">
        <div className="relative h-[200px]">
          <ResponsiveContainer height="100%" width="100%">
            <PieChart>
              <Tooltip content={<ExpandedPieTooltip />} />
              <Pie
                cornerRadius={12}
                data={data}
                dataKey="value"
                innerRadius={60}
                outerRadius={88}
                paddingAngle={3}
                stroke="none"
              >
                {data.map((item, index) => (
                  <Cell
                    fill={chartColors[index % chartColors.length]}
                    key={item.label}
                  />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
            <strong className="text-[30px] font-semibold leading-none text-[#102734]">
              {formatCompactNumber(result.candidatePieceCount)}
            </strong>
            <span className="mt-2 text-[12px] font-semibold text-[#8a98a2]">
              candidats
            </span>
          </div>
        </div>

        <div className="space-y-3">
          {data.map((item, index) => (
            <div
              className="flex items-start justify-between gap-3 rounded-[16px] bg-[#f7fafb] px-4 py-3"
              key={item.label}
            >
              <span className="flex min-w-0 items-start gap-3">
                <span
                  className="mt-1 size-3 shrink-0 rounded-full"
                  style={{ backgroundColor: chartColors[index % chartColors.length] }}
                />
                <span className="min-w-0">
                  <span className="block text-[13px] font-semibold text-[#40515C]">
                    {item.name}
                  </span>
                  <span className="mt-1 block text-[11px] font-medium leading-4 text-[#7d8d97]">
                    {item.guidance}
                  </span>
                </span>
              </span>
              <span className="shrink-0 text-[14px] font-semibold text-[#102734]">
                {formatCompactNumber(item.value)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function RasMissingFactsCard({
  items,
  onSelect,
  selectedFact,
}: {
  items: Array<{ label: string; value: number }>;
  onSelect: (fact: string) => void;
  selectedFact: string | null;
}) {
  return (
    <section className="rounded-[24px] bg-white p-4 shadow-[0_18px_44px_rgba(64,81,92,0.07)] ring-1 ring-[#e5eef2]">
      <div>
        <h3 className="text-[16px] font-semibold text-[#102734]">
          Points à confirmer
        </h3>
        <p className="mt-1 text-[12px] font-medium text-[#7d8d97]">
          Informations à contrôler avant toute conclusion
        </p>
      </div>

      {items.length > 0 ? (
        <div className="mt-4 space-y-3">
          {items.map((item) => {
            const guidance = missingFactGuidance(item.label);
            const selected = selectedFact === item.label;
            return (
              <button
                className={[
                  "w-full cursor-pointer rounded-[16px] border px-4 py-3 text-left transition",
                  selected
                    ? "border-[#E36F55] bg-[#fff8f3]"
                    : "border-transparent bg-[#f7fafb] hover:border-[#dce7eb]",
                ].join(" ")}
                key={item.label}
                onClick={() => onSelect(item.label)}
                type="button"
              >
                <span className="flex items-start justify-between gap-3">
                  <span className="min-w-0">
                    <strong className="block text-[13px] font-semibold text-[#102734]">
                      {guidance.label}
                    </strong>
                    <span className="mt-1 block text-[11px] font-medium leading-4 text-[#7d8d97]">
                      {guidance.explanation}
                    </span>
                  </span>
                  <span className="shrink-0 rounded-full bg-white px-2.5 py-1 text-[11px] font-semibold text-[#c8563f] ring-1 ring-[#f0ded6]">
                    {formatCompactNumber(item.value)} {item.value > 1 ? "pièces" : "pièce"}
                  </span>
                </span>
                <span className="mt-3 block border-t border-[#e8eef1] pt-2 text-[12px] font-semibold text-[#40515C]">
                  Action : {guidance.action}
                </span>
              </button>
            );
          })}
        </div>
      ) : (
        <p className="mt-4 rounded-[16px] bg-[#f7fafb] px-4 py-4 text-[13px] font-medium text-[#7d8d97]">
          Aucun point bloquant détecté sur les pièces candidates.
        </p>
      )}
    </section>
  );
}

function missingFactGuidance(value: string): {
  action: string;
  explanation: string;
  label: string;
} {
  const guidance: Record<
    string,
    { action: string; explanation: string; label: string }
  > = {
    strong_semantic_signal: {
      label: "Nature réelle de l’opération à confirmer",
      explanation:
        "Le libellé contient seulement un indice générique ou modéré.",
      action: "vérifier la facture ou le contrat",
    },
    posting_key_side: {
      label: "Sens comptable à confirmer",
      explanation:
        "La clé de comptabilisation ne permet pas d’établir le sens de la ligne.",
      action: "contrôler la clé de comptabilisation",
    },
    semantic_disambiguation: {
      label: "Libellé ambigu à clarifier",
      explanation:
        "La description ne permet pas d’identifier clairement l’opération.",
      action: "consulter la pièce justificative",
    },
  };
  return (
    guidance[value] ?? {
      label: missingFactLabel(value),
      explanation: "Une information nécessaire à la revue reste indisponible.",
      action: "compléter les informations de la pièce",
    }
  );
}

function missingFactLabel(value: string): string {
  return missingFactGuidanceLabel(value) ?? value.replaceAll("_", " ");
}

function missingFactGuidanceLabel(value: string): string | null {
  const labels: Record<string, string> = {
    strong_semantic_signal: "Nature réelle de l’opération à confirmer",
    posting_key_side: "Sens comptable à confirmer",
    semantic_disambiguation: "Libellé ambigu à clarifier",
  };
  return labels[value] ?? null;
}

function RasDataQualityCard({
  items,
  rowCount,
}: {
  items: Array<{ label: string; value: number }>;
  rowCount: number;
}) {
  const structuralItems = items.filter((item) =>
    isStructuralQualityIssue(item.label)
  );
  const rowItems = items.filter(
    (item) => !isStructuralQualityIssue(item.label)
  );

  return (
    <section className="rounded-[24px] bg-white p-4 shadow-[0_18px_44px_rgba(64,81,92,0.07)] ring-1 ring-[#e5eef2]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-[16px] font-semibold text-[#102734]">
            Qualité des données
          </h3>
          <p className="mt-1 text-[12px] font-medium text-[#7d8d97]">
            Fiabilité des informations utilisées par l’audit
          </p>
        </div>
        <span className="rounded-full bg-[#fff4ed] px-3 py-1.5 text-[12px] font-semibold text-[#c8563f]">
          {items.length} {items.length > 1 ? "points" : "point"}
        </span>
      </div>

      {items.length > 0 ? (
        <div className="mt-4 space-y-4">
          {structuralItems.length > 0 && (
            <QualityIssueSection
              items={structuralItems}
              rowCount={rowCount}
              title="Limites globales du fichier"
            />
          )}
          {rowItems.length > 0 && (
            <QualityIssueSection
              items={rowItems}
              rowCount={rowCount}
              title="Incohérences de lignes"
            />
          )}
        </div>
      ) : (
        <p className="mt-4 rounded-[16px] bg-[#f7fafb] px-4 py-4 text-[13px] font-medium text-[#7d8d97]">
          Aucun problème de qualité détecté dans le périmètre analysé.
        </p>
      )}
    </section>
  );
}

function QualityIssueSection({
  items,
  rowCount,
  title,
}: {
  items: Array<{ label: string; value: number }>;
  rowCount: number;
  title: string;
}) {
  return (
    <div>
      <h4 className="text-[11px] font-semibold uppercase tracking-[0.06em] text-[#8a98a2]">
        {title}
      </h4>
      <div className="mt-2 space-y-2">
        {items.map((item) => {
          const guidance = qualityIssueGuidance(item.label);
          const affectsWholeFile =
            isStructuralQualityIssue(item.label) && item.value >= rowCount;
          return (
            <div
              className="rounded-[16px] bg-[#f7fafb] px-4 py-3"
              key={item.label}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <strong className="block text-[13px] font-semibold text-[#102734]">
                    {guidance.label}
                  </strong>
                  <p className="mt-1 text-[11px] font-medium leading-4 text-[#7d8d97]">
                    {guidance.explanation}
                  </p>
                </div>
                <span className="shrink-0 rounded-full bg-white px-2.5 py-1 text-[11px] font-semibold text-[#c8563f] ring-1 ring-[#f0ded6]">
                  {affectsWholeFile
                    ? "Tout le fichier"
                    : `${formatCompactNumber(item.value)} ${
                        item.value > 1 ? "lignes" : "ligne"
                      }`}
                </span>
              </div>
              <p className="mt-3 border-t border-[#e8eef1] pt-2 text-[12px] font-semibold text-[#40515C]">
                Action : {guidance.action}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function isStructuralQualityIssue(value: string): boolean {
  return [
    "document_date_used_as_posting_date",
    "document_type_used_as_journal",
    "company_code_from_organization_config",
  ].includes(value);
}

function qualityIssueGuidance(value: string): {
  action: string;
  explanation: string;
  label: string;
} {
  const guidance: Record<
    string,
    { action: string; explanation: string; label: string }
  > = {
    document_date_used_as_posting_date: {
      label: "Date de pièce utilisée comme date comptable",
      explanation:
        "La date comptable n’est pas disponible et la date de pièce sert d’approximation.",
      action: "fournir la date de comptabilisation si elle existe",
    },
    document_type_used_as_journal: {
      label: "Type de pièce utilisé comme journal",
      explanation:
        "Le journal comptable n’est pas disponible et le type de pièce sert d’approximation.",
      action: "fournir le journal comptable si disponible",
    },
    company_code_from_organization_config: {
      label: "Société issue de la configuration",
      explanation:
        "Le code société n’est pas présent dans le GL et provient de la configuration.",
      action: "confirmer que le fichier concerne bien cette société",
    },
    conflicting_vendor_customer: {
      label: "Fournisseur et client contradictoires",
      explanation:
        "La ligne contient des identifiants fournisseur et client différents.",
      action: "identifier le partenaire réellement concerné",
    },
    conflicting_generic_partner: {
      label: "Partenaire générique contradictoire",
      explanation:
        "Le partenaire générique ne correspond pas au fournisseur ou au client.",
      action: "corriger ou confirmer l’identifiant du partenaire",
    },
    unknown_posting_key: {
      label: "Clé de comptabilisation inconnue",
      explanation:
        "Le sens débit ou crédit de la ligne ne peut pas être déterminé.",
      action: "renseigner ou mapper la clé de comptabilisation",
    },
    invalid_amount: {
      label: "Montant invalide",
      explanation: "Le montant de la ligne ne peut pas être interprété.",
      action: "corriger le format du montant",
    },
    invalid_currency: {
      label: "Devise invalide",
      explanation: "La devise n’est pas un code alphabétique à trois lettres.",
      action: "corriger le code devise",
    },
    invalid_posting_date: {
      label: "Date comptable invalide",
      explanation: "La date de la ligne ne peut pas être interprétée.",
      action: "corriger le format de la date",
    },
    invalid_period: {
      label: "Période invalide",
      explanation: "La période comptable est absente ou hors plage autorisée.",
      action: "corriger la période comptable",
    },
    invalid_fiscal_year: {
      label: "Exercice invalide",
      explanation: "L’exercice comptable ne peut pas être interprété.",
      action: "corriger l’exercice comptable",
    },
  };
  return (
    guidance[value] ?? {
      label: value.replaceAll("_", " "),
      explanation: "Le moteur a identifié une information non exploitable.",
      action: "contrôler les données sources concernées",
    }
  );
}

function ExpandedBarCard({
  countLabel,
  items,
  subtitle,
  title,
  tone = "neutral",
}: {
  countLabel?: string;
  items: Array<{ label: string; value: number }>;
  subtitle: string;
  title: string;
  tone?: "neutral" | "warning";
}) {
  const data = items.map((item, index) => ({
    ...item,
    name: rasLabel(item.label),
    fill:
      tone === "warning"
        ? ["#E36F55", "#D7A44A", "#7FA6B7"][index % 3]
        : chartColors[index % chartColors.length],
  }));

  return (
    <section className="rounded-[24px] bg-white p-4 shadow-[0_18px_44px_rgba(64,81,92,0.07)] ring-1 ring-[#e5eef2]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-[16px] font-semibold text-[#102734]">{title}</h3>
          <p className="mt-1 text-[12px] font-medium text-[#7d8d97]">{subtitle}</p>
        </div>
        <span className="rounded-full bg-[#f5f8fa] px-3 py-1.5 text-[12px] font-semibold text-[#60737e]">
          {countLabel ?? data.length}
        </span>
      </div>

      {data.length > 0 ? (
        <div className="mt-4 h-[210px] w-full outline-none [&_.recharts-wrapper]:outline-none [&_svg]:outline-none">
          <ResponsiveContainer height="100%" width="100%">
            <BarChart data={data} layout="vertical" margin={{ top: 6, right: 18, bottom: 4, left: 6 }}>
              <CartesianGrid horizontal={false} stroke="#EAF1F4" strokeDasharray="6 10" />
              <XAxis
                axisLine={false}
                tick={{ fill: "#9aa8b0", fontSize: 11, fontWeight: 700 }}
                tickFormatter={(value) => formatCompactNumber(Number(value))}
                tickLine={false}
                type="number"
              />
              <YAxis
                axisLine={false}
                dataKey="name"
                tick={{ fill: "#40515C", fontSize: 11, fontWeight: 700 }}
                tickLine={false}
                type="category"
                width={132}
              />
              <Tooltip content={<ExpandedBarTooltip />} cursor={{ fill: "rgba(127,166,183,0.10)" }} />
              <Bar dataKey="value" maxBarSize={18} radius={[8, 8, 8, 8]}>
                {data.map((item) => (
                  <Cell fill={item.fill} key={item.label} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <p className="mt-5 rounded-[18px] bg-[#f7fafb] px-4 py-5 text-[13px] font-medium text-[#7d8d97]">
          Aucune donnée exploitable.
        </p>
      )}
    </section>
  );
}

function ExpandedTrendTooltip({
  active,
  currency,
  payload,
}: {
  active?: boolean;
  currency: string | null;
  payload?: Array<{
    payload?: {
      period?: string;
      candidateAmount?: number;
      cumulativeCandidateAmount?: number;
    };
  }>;
}) {
  if (!active || !payload?.length) return null;
  const point = payload[0]?.payload;
  if (!point) return null;

  return (
    <div className="rounded-[16px] bg-[#102734] px-3 py-2 text-white shadow-[0_14px_34px_rgba(16,39,52,0.22)]">
      <p className="text-[11px] font-medium text-white/70">
        Période P{point.period}
      </p>
      <p className="mt-1 text-[13px] font-semibold">
        Montant candidat : {formatAmount(Number(point.candidateAmount ?? 0), currency)}
      </p>
      <p className="mt-1 text-[13px] font-semibold">
        Cumul candidat : {formatAmount(Number(point.cumulativeCandidateAmount ?? 0), currency)}
      </p>
    </div>
  );
}

function ExpandedPieTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ value?: number; payload?: { name?: string } }>;
}) {
  if (!active || !payload?.length) return null;
  const item = payload[0];

  return (
    <div className="rounded-[16px] bg-[#102734] px-3 py-2 text-white shadow-[0_14px_34px_rgba(16,39,52,0.22)]">
      <p className="max-w-[220px] truncate text-[11px] font-medium text-white/70">
        {item.payload?.name}
      </p>
      <p className="mt-1 text-[14px] font-semibold">
        {formatCompactNumber(Number(item.value ?? 0))}
      </p>
    </div>
  );
}

function ExpandedBarTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ value?: number; payload?: { name?: string } }>;
}) {
  if (!active || !payload?.length) return null;
  const item = payload[0];

  return (
    <div className="rounded-[16px] bg-[#102734] px-3 py-2 text-white shadow-[0_14px_34px_rgba(16,39,52,0.22)]">
      <p className="max-w-[220px] truncate text-[11px] font-medium text-white/70">
        {item.payload?.name}
      </p>
      <p className="mt-1 text-[14px] font-semibold">
        {formatCompactNumber(Number(item.value ?? 0))}
      </p>
    </div>
  );
}

function WithholdingSkeleton() {
  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <div className="h-4 w-32 animate-pulse rounded-full bg-[#edf4f7]" />
        <div className="h-3 w-48 animate-pulse rounded-full bg-[#f5f8fa]" />
      </div>
      <div className="grid grid-cols-4 gap-1.5">
        {Array.from({ length: 4 }).map((_, index) => (
          <div
            className="h-[62px] animate-pulse rounded-[14px] bg-[#f5f8fa]"
            key={index}
          />
        ))}
      </div>
      <div className="h-[150px] animate-pulse rounded-[18px] bg-[#f5f8fa]" />
      <div className="h-[220px] animate-pulse rounded-[18px] bg-[#f5f8fa]" />
    </div>
  );
}

function WithholdingState({ title, text }: { title: string; text: string }) {
  return (
    <AnalyticsReveal delay={0.04}>
      <section className="rounded-[22px] bg-[#f7fafb] px-4 py-5 ring-1 ring-[#e4eef3]">
        <p className="text-[15px] font-semibold text-[#102734]">{title}</p>
        <p className="mt-2 text-[12px] font-medium leading-5 text-[#60737e]">
          {text}
        </p>
      </section>
    </AnalyticsReveal>
  );
}

function topEntries(record: Record<string, number>, limit: number) {
  return Object.entries(record)
    .filter(([, value]) => value > 0)
    .sort(([, left], [, right]) => right - left)
    .slice(0, limit)
    .map(([label, value]) => ({ label, value }));
}

function primaryAmount(record: Record<string, string>) {
  const [currency, rawValue] = Object.entries(record)[0] ?? [];
  const value = Number(rawValue);
  if (!currency || !Number.isFinite(value)) return null;
  return { currency, value };
}

function rasLabel(value: string): string {
  const labels: Record<string, string> = {
    candidate_account_and_text: "Compte + libellé",
    candidate_account_only: "Compte seul",
    candidate_text_only: "Libellé seul",
    candidate_indeterminate: "Indéterminé",
    posting_key_side: "Sens comptable à confirmer",
    semantic_disambiguation: "Sémantique à confirmer",
    "SIG-RAS-001": "Honoraires",
    "SIG-RAS-002": "Prestations",
    "SIG-RAS-003": "Assistance",
    "SIG-RAS-004": "Consultations",
    "SIG-RAS-005": "Études",
    "SIG-RAS-006": "Services",
    "SIG-RAS-007": "Loyers",
    "SIG-RAS-008": "Redevances",
    "SIG-RAS-EX-001": "Virements internes exclus",
    "SIG-RAS-EX-002": "Extournes exclues",
  };
  return labels[value] ?? value.replaceAll("_", " ");
}

function rasStatusGuidance(value: string): string {
  const guidance: Record<string, string> = {
    candidate_account_and_text:
      "Deux indices indépendants concordent ; vérifier l’applicabilité fiscale.",
    candidate_account_only:
      "Contrôler la nature réelle de l’opération.",
    candidate_text_only:
      "Vérifier le classement comptable et écarter un faux positif.",
    candidate_indeterminate:
      "Compléter le sens comptable ou les données manquantes.",
  };
  return guidance[value] ?? "Examiner les éléments ayant déclenché la détection.";
}
