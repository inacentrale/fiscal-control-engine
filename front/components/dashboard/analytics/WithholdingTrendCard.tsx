"use client";

import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { RasReviewPeriod } from "@/api/agent/types";

import { formatAmount, formatCompactNumber } from "./analyticsUtils";

type TrendPoint = RasReviewPeriod & {
  candidateRatePercent: number;
  shortPeriod: string;
};

type TooltipPayload = Array<{
  value?: number;
  payload?: TrendPoint;
}>;

export default function WithholdingTrendCard({
  periods,
}: {
  periods: RasReviewPeriod[];
}) {
  const data = periods.map((period) => ({
    ...period,
    candidateRatePercent: Math.round(period.candidateRate * 1000) / 10,
    shortPeriod: periodLabel(period.period),
  }));
  const currency = data.find((item) => item.currency)?.currency ?? null;
  const last = data.at(-1);

  if (data.length === 0) {
    return (
      <section className="rounded-[18px] bg-white p-4 shadow-[0_16px_42px_rgba(64,81,92,0.07)] ring-1 ring-[#e8f0f3]">
        <h3 className="text-[14px] font-semibold text-[#102734]">
          Tendances RAS
        </h3>
        <p className="mt-3 rounded-[14px] bg-[#f7fafb] px-3 py-3 text-[12px] font-medium leading-5 text-[#8a98a2]">
          Les périodes RAS ne sont pas encore disponibles dans la réponse API.
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-[22px] bg-white p-4 shadow-[0_16px_42px_rgba(64,81,92,0.07)] ring-1 ring-[#e8f0f3]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-[14px] font-semibold text-[#102734]">
            RAS par période
          </h3>
          <p className="mt-0.5 text-[11px] font-medium text-[#8a98a2]">
            Évaluées, candidats et taux
          </p>
        </div>
        <span className="rounded-full bg-[#f5f8fa] px-2.5 py-1 text-[11px] font-semibold text-[#60737e]">
          {data.length} période(s)
        </span>
      </div>

      <div className="mt-4 h-[176px] w-full outline-none [&_.recharts-wrapper]:outline-none [&_svg]:outline-none">
        <ResponsiveContainer height="100%" width="100%">
          <ComposedChart data={data} margin={{ top: 12, right: 0, bottom: 2, left: -26 }}>
            <CartesianGrid stroke="#EAF1F4" strokeDasharray="5 8" vertical={false} />
            <XAxis
              axisLine={false}
              dataKey="shortPeriod"
              interval="preserveStartEnd"
              tick={{ fill: "#9aa8b0", fontSize: 9, fontWeight: 700 }}
              tickLine={false}
              tickMargin={8}
            />
            <YAxis
              axisLine={false}
              tick={{ fill: "#9aa8b0", fontSize: 9, fontWeight: 700 }}
              tickFormatter={(value) => formatCompactNumber(Number(value))}
              tickLine={false}
              width={36}
              yAxisId="count"
            />
            <YAxis domain={[0, 100]} hide orientation="right" yAxisId="rate" />
            <Tooltip
              content={<TrendTooltip currency={currency} />}
              cursor={{ fill: "rgba(127,166,183,0.10)" }}
            />
            <Bar
              animationDuration={850}
              dataKey="evaluatedEntryCount"
              fill="#D9E3E8"
              maxBarSize={14}
              name="Évaluées"
              radius={[6, 6, 0, 0]}
              yAxisId="count"
            />
            <Bar
              animationDuration={850}
              dataKey="candidateEntryCount"
              fill="#40515C"
              maxBarSize={14}
              name="Candidats"
              radius={[6, 6, 0, 0]}
              yAxisId="count"
            />
            <Line
              animationDuration={850}
              dataKey="candidateRatePercent"
              dot={false}
              name="Taux"
              stroke="#12A17D"
              strokeLinecap="round"
              strokeWidth={3}
              type="monotone"
              yAxisId="rate"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2">
        <PeriodStat
          label="Montant"
          value={last ? formatAmount(last.candidateAmount, currency) : "-"}
        />
        <PeriodStat
          label="Cumul"
          value={
            last ? formatAmount(last.cumulativeCandidateAmount, currency) : "-"
          }
        />
      </div>
    </section>
  );
}

function PeriodStat({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-[14px] bg-[#f7fafb] px-3 py-2.5">
      <p className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[#8a98a2]">
        {label}
      </p>
      <p className="mt-1 truncate text-[14px] font-semibold text-[#102734]">
        {value}
      </p>
    </div>
  );
}

function TrendTooltip({
  active,
  currency,
  payload,
}: {
  active?: boolean;
  currency: string | null;
  payload?: TooltipPayload;
}) {
  if (!active || !payload?.length) return null;
  const point = payload[0]?.payload;
  if (!point) return null;

  return (
    <div className="rounded-[14px] bg-[#102734] px-3 py-2 text-white shadow-[0_14px_34px_rgba(16,39,52,0.22)]">
      <p className="text-[11px] font-medium text-white/70">
        Période P{point.period}
      </p>
      <p className="mt-1 text-[13px] font-semibold">
        Évaluées: {formatCompactNumber(point.evaluatedEntryCount)}
      </p>
      <p className="mt-1 text-[13px] font-semibold">
        Candidats: {formatCompactNumber(point.candidateEntryCount)}
      </p>
      <p className="mt-1 text-[13px] font-semibold">
        Taux: {point.candidateRatePercent}%
      </p>
      <p className="mt-1 text-[13px] font-semibold">
        Montant: {formatAmount(point.candidateAmount, currency)}
      </p>
    </div>
  );
}

function periodLabel(period: string): string {
  const numeric = Number(period);
  if (Number.isFinite(numeric) && numeric >= 1 && numeric <= 16) {
    return `P${numeric}`;
  }
  return period.length > 4 ? period.slice(0, 4) : period;
}
