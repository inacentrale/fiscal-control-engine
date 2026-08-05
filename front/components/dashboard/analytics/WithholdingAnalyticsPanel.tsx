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
  RasCandidateDetectionResult,
  RasReviewPeriod,
} from "@/api/agent/types";
import { PageTitle } from "@/components/base/PageTitle";
import { ClosePlainIcon } from "@/public/assets/icons/AnalyticsIcons";

import AnalyticsReveal from "./AnalyticsReveal";
import {
  chartColors,
  formatAmount,
  formatCompactNumber,
} from "./analyticsUtils";
import WithholdingDonutSummary from "./WithholdingDonutSummary";
import WithholdingTrendCard from "./WithholdingTrendCard";
import AnalyticsModeSwitcher, { type AnalyticsMode } from "./AnalyticsModeSwitcher";

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
        <div className="grid grid-cols-4 gap-1.5">
          <RasKpi label="Pièces" value={result.evaluatedPieceCount} />
          <RasKpi label="Candidats" value={result.candidatePieceCount} />
          <RasKpi label="Taux" value={`${Math.round(candidateRate * 1000) / 10}%`} />
          <RasKpi
            label="Montant"
            value={amount ? formatAmount(amount.value, amount.currency) : "-"}
          />
        </div>
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

function RasKpi({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-[14px] bg-[#f5f8fa] px-2.5 py-2.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.72)]">
      <p className="truncate text-[10px] font-semibold text-[#7d8d97]">
        {label}
      </p>
      <p className="mt-1 truncate text-[15px] font-semibold text-[#102734]">
        {typeof value === "number" ? formatCompactNumber(value) : value}
      </p>
    </div>
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
  candidateRate,
  missingFactItems,
  onModeChange,
  onClose,
  periods,
  result,
  signalItems,
}: {
  activeMode: AnalyticsMode;
  amount: { currency: string; value: number } | null;
  candidateRate: number;
  missingFactItems: Array<{ label: string; value: number }>;
  onModeChange: (mode: AnalyticsMode) => void;
  onClose: () => void;
  periods: RasReviewPeriod[];
  result: RasCandidateDetectionResult;
  signalItems: Array<{ label: string; value: number }>;
}) {
  return (
    <div className="fixed inset-0 z-50 bg-[#102734]/26 p-3 backdrop-blur-[2px] sm:p-6">
      <section className="mx-auto flex h-full max-w-[1480px] flex-col overflow-hidden rounded-[30px] bg-[#f7fafb] shadow-[0_32px_90px_rgba(16,39,52,0.24)] ring-1 ring-white/70">
        <div className="sticky top-0 z-10 bg-[#f7fafb]/92 px-5 pt-5 backdrop-blur sm:px-7">
          <PageTitle
            actions={
              <div className="flex items-center gap-3">
                <div className="w-[300px] max-w-[56vw]">
                  <AnalyticsModeSwitcher
                    activeMode={activeMode}
                    onChange={onModeChange}
                  />
                </div>
                <button
                  aria-label="Réduire la vue agrandie"
                  className="cursor-pointer text-[#40515C] transition hover:text-[#102734]"
                  onClick={onClose}
                  type="button"
                >
                  <ClosePlainIcon className="size-6 rotate-45" />
                </button>
              </div>
            }
            title="Contrôle RAS"
          />
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-5 sm:px-7">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <ExpandedKpi label="Pièces évaluées" value={result.evaluatedPieceCount} />
            <ExpandedKpi label="Candidats RAS" value={result.candidatePieceCount} />
            <ExpandedKpi
              label="Taux candidat"
              value={`${Math.round(candidateRate * 1000) / 10}%`}
            />
            <ExpandedKpi
              label="Montant candidat"
              value={amount ? formatAmount(amount.value, amount.currency) : "-"}
            />
          </div>

          <div className="mt-5 grid gap-5 xl:grid-cols-[1.12fr_0.88fr]">
            <ExpandedTrendCard periods={periods} />
            <ExpandedStatusCard result={result} />
          </div>

          <div className="mt-5 grid gap-5 xl:grid-cols-2">
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

          <div className="mt-5 grid gap-5 xl:grid-cols-[0.95fr_1.05fr]">
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
        </div>
      </section>
    </div>
  );
}

function ExpandedKpi({
  label,
  value,
}: {
  label: string;
  value: number | string;
}) {
  return (
    <div className="rounded-[24px] bg-white px-5 py-4 shadow-[0_18px_44px_rgba(64,81,92,0.07)] ring-1 ring-[#e5eef2]">
      <p className="text-[12px] font-semibold text-[#7d8d97]">{label}</p>
      <p className="mt-2 truncate text-[28px] font-semibold text-[#102734]">
        {typeof value === "number" ? formatCompactNumber(value) : value}
      </p>
    </div>
  );
}

function ExpandedTrendCard({ periods }: { periods: RasReviewPeriod[] }) {
  const data = periods.map((period) => ({
    ...period,
    shortPeriod: `P${period.period}`,
  }));
  const currency = data.find((item) => item.currency)?.currency ?? null;

  return (
    <section className="rounded-[28px] bg-white p-5 shadow-[0_18px_44px_rgba(64,81,92,0.07)] ring-1 ring-[#e5eef2]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-[18px] font-semibold text-[#102734]">
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
        <div className="mt-5 h-[340px] w-full outline-none [&_.recharts-wrapper]:outline-none [&_svg]:outline-none">
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
    <section className="rounded-[28px] bg-white p-5 shadow-[0_18px_44px_rgba(64,81,92,0.07)] ring-1 ring-[#e5eef2]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-[18px] font-semibold text-[#102734]">
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

      <div className="mt-5 grid items-center gap-4 md:grid-cols-[240px_minmax(0,1fr)]">
        <div className="relative h-[240px]">
          <ResponsiveContainer height="100%" width="100%">
            <PieChart>
              <Tooltip content={<ExpandedPieTooltip />} />
              <Pie
                cornerRadius={12}
                data={data}
                dataKey="value"
                innerRadius={72}
                outerRadius={104}
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
            <strong className="text-[34px] font-semibold leading-none text-[#102734]">
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
    <section className="rounded-[28px] bg-white p-5 shadow-[0_18px_44px_rgba(64,81,92,0.07)] ring-1 ring-[#e5eef2]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-[18px] font-semibold text-[#102734]">{title}</h3>
          <p className="mt-1 text-[12px] font-medium text-[#7d8d97]">{subtitle}</p>
        </div>
        <span className="rounded-full bg-[#f5f8fa] px-3 py-1.5 text-[12px] font-semibold text-[#60737e]">
          {data.length}
        </span>
      </div>

      {data.length > 0 ? (
        <div className="mt-5 h-[260px] w-full outline-none [&_.recharts-wrapper]:outline-none [&_svg]:outline-none">
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
