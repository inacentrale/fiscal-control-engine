"use client";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
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
import AnalyticsKpiGrid, {
  AnalyticsBusinessBalanceGrid,
} from "./AnalyticsKpiGrid";
import AnalyticsQualityDetails from "./AnalyticsQualityDetails";
import AnalyticsStatGrid, { type AnalyticsStatItem } from "./AnalyticsStatGrid";
import AnalyticsViewTabs from "./AnalyticsViewTabs";
import {
  chartColors,
  findChart,
  formatAmount,
  formatCompactNumber,
} from "./analyticsUtils";
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
  state,
}: {
  state: WithholdingQueryState;
}) {
  if (state.status === "loading") return <WithholdingSkeleton />;
  if (state.status === "error") {
    return (
      <WithholdingState
        title="Contrôle RAS indisponible"
        text={state.message}
      />
    );
  }
  if (state.status === "empty") {
    return (
      <WithholdingState
        title="Aucun signal RAS"
        text="Le fichier actif ne retourne pas encore de synthèse RAS exploitable."
      />
    );
  }

  const result = state.result;
  const signalItems = topEntries(result.signalCounts, 4);
  const missingFactItems = topEntries(result.missingFactCounts, 3);
  const periods = result.rasReview?.periods ?? [];
  const amount = primaryAmount(result.candidateAmountsByCurrency);
  const candidateRate =
    result.evaluatedPieceCount > 0
      ? result.candidatePieceCount / result.evaluatedPieceCount
      : 0;

  return (
    <>
      <header className="space-y-1">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-[16px] font-semibold">Contrôle RAS</h2>
          <span className="rounded-full bg-[#fff4ed] px-2.5 py-1 text-[11px] font-semibold text-[#c8563f]">
            Revue
          </span>
        </div>
        <p className="truncate text-[12px] font-medium text-[#7d8d97]">
          {result.sheetName} · aucune décision fiscale automatique
        </p>
      </header>

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
}) {
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

              <div className="mt-4 grid gap-4 xl:grid-cols-2">
                <ExpandedBarCard
                  items={signalItems}
                  subtitle="Comptages par signal déterministe"
                  title="Signaux principaux"
                />
                <ExpandedBarCard
                  items={topEntries(result.operationHintCounts, 6)}
                  subtitle="Nature probable de l'opération"
                  title="Indices opérationnels"
                />
              </div>

              <div className="mt-4 grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
                <ExpandedBarCard
                  items={missingFactItems}
                  subtitle="Informations à confirmer avant décision"
                  title="Faits manquants"
                  tone="warning"
                />
                <ExpandedBarCard
                  items={topEntries(result.issueCounts, 6)}
                  subtitle="Points de qualité détectés"
                  title="Qualité des données"
                  tone="warning"
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
    findChart(dashboard, "cumulative_balance_by_period"),
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
      <div className="mt-4">
        <AnalyticsBusinessBalanceGrid dashboard={dashboard} />
      </div>
      <div className="mt-4">
        <AnalyticsQualityDetails dashboard={dashboard} defaultOpen />
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
      detail: "Écritures candidates à revoir",
      icon: <SearchStatusIcon className="size-5" />,
      label: "À revoir",
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
        <span className="rounded-full bg-[#edf5f8] px-3 py-1.5 text-[12px] font-semibold text-[#40515C]">
          {data.length} période(s)
        </span>
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
        <span className="rounded-full bg-[#edf5f8] px-3 py-1.5 text-[12px] font-semibold text-[#40515C]">
          {data.length} période(s)
        </span>
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
              <Area
                dataKey="candidateAmount"
                fill="url(#ras-expanded-amount)"
                stroke="none"
                type="monotone"
              />
              <Area
                dataKey="cumulativeCandidateAmount"
                fill="url(#ras-expanded-cumulative)"
                stroke="none"
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
              className="flex items-center justify-between gap-3 rounded-[16px] bg-[#f7fafb] px-4 py-3"
              key={item.label}
            >
              <span className="flex min-w-0 items-center gap-3">
                <span
                  className="size-3 shrink-0 rounded-full"
                  style={{ backgroundColor: chartColors[index % chartColors.length] }}
                />
                <span className="truncate text-[13px] font-semibold text-[#40515C]">
                  {item.name}
                </span>
              </span>
              <span className="text-[14px] font-semibold text-[#102734]">
                {formatCompactNumber(item.value)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function ExpandedBarCard({
  items,
  subtitle,
  title,
  tone = "neutral",
}: {
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
          {data.length}
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
  payload?: Array<{ name?: string; value?: number; payload?: { period?: string } }>;
}) {
  if (!active || !payload?.length) return null;

  return (
    <div className="rounded-[16px] bg-[#102734] px-3 py-2 text-white shadow-[0_14px_34px_rgba(16,39,52,0.22)]">
      <p className="text-[11px] font-medium text-white/70">
        Période P{payload[0]?.payload?.period}
      </p>
      {payload.map((item) => (
        <p className="mt-1 text-[13px] font-semibold" key={item.name}>
          {item.name}: {formatAmount(Number(item.value ?? 0), currency)}
        </p>
      ))}
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
  };
  return labels[value] ?? value.replaceAll("_", " ");
}
