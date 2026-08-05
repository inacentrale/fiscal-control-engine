"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { RasReviewPeriod } from "@/api/agent/types";

import { formatAmount, formatCompactNumber } from "./analyticsUtils";

type TrendMetric = "candidateAmount" | "candidateEntryCount" | "cumulativeCandidateAmount";

type TrendPoint = RasReviewPeriod & {
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
    shortPeriod: periodLabel(period.period),
  }));
  const currency = data.find((item) => item.currency)?.currency ?? null;

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
            Tendances RAS
          </h3>
          <p className="mt-0.5 text-[11px] font-medium text-[#8a98a2]">
            Par période comptable
          </p>
        </div>
        <span className="rounded-full bg-[#f5f8fa] px-2.5 py-1 text-[11px] font-semibold text-[#60737e]">
          {data.length} période(s)
        </span>
      </div>

      <div className="mt-4 space-y-3">
        <MiniTrend
          color="#40515C"
          currency={currency}
          data={data}
          label="Montant candidat"
          metric="candidateAmount"
        />
        <MiniTrend
          color="#7FA6B7"
          data={data}
          label="Écritures candidates"
          metric="candidateEntryCount"
        />
        <MiniTrend
          color="#12A17D"
          currency={currency}
          data={data}
          label="Cumul candidat"
          metric="cumulativeCandidateAmount"
        />
      </div>
    </section>
  );
}

function MiniTrend({
  color,
  currency = null,
  data,
  label,
  metric,
}: {
  color: string;
  currency?: string | null;
  data: TrendPoint[];
  label: string;
  metric: TrendMetric;
}) {
  const lastValue = Number(data.at(-1)?.[metric] ?? 0);
  const gradientId = `ras-${metric}`;

  return (
    <div className="rounded-[16px] bg-[#f7fafb] px-3 py-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold text-[#60737e]">{label}</p>
          <p className="mt-0.5 text-[15px] font-semibold text-[#102734]">
            {metric === "candidateEntryCount"
              ? formatCompactNumber(lastValue)
              : formatAmount(lastValue, currency)}
          </p>
        </div>
        <span className="rounded-full bg-white px-2 py-1 text-[10px] font-semibold text-[#8a98a2] shadow-[inset_0_0_0_1px_rgba(216,229,235,0.9)]">
          P{data[0]?.period} - P{data.at(-1)?.period}
        </span>
      </div>

      <div className="mt-2 h-[78px] w-full outline-none [&_.recharts-wrapper]:outline-none [&_svg]:outline-none">
        <ResponsiveContainer height="100%" width="100%">
          <AreaChart data={data} margin={{ top: 10, right: 4, bottom: 0, left: -28 }}>
            <defs>
              <linearGradient id={gradientId} x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor={color} stopOpacity={0.2} />
                <stop offset="100%" stopColor={color} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#EAF1F4" strokeDasharray="5 8" vertical={false} />
            <XAxis
              axisLine={false}
              dataKey="shortPeriod"
              interval="preserveStartEnd"
              tick={{ fill: "#9aa8b0", fontSize: 9, fontWeight: 600 }}
              tickLine={false}
              tickMargin={6}
            />
            <YAxis
              axisLine={false}
              domain={["dataMin", "dataMax"]}
              tick={false}
              tickLine={false}
              width={28}
            />
            <Tooltip
              content={
                <TrendTooltip
                  currency={currency}
                  metric={metric}
                  title={label}
                />
              }
              cursor={{ stroke: color, strokeDasharray: "4 8" }}
            />
            <Area
              animationDuration={850}
              dataKey={metric}
              fill={`url(#${gradientId})`}
              stroke="none"
              type="monotone"
            />
            <Line
              animationDuration={850}
              dataKey={metric}
              dot={false}
              stroke={color}
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={3}
              type="monotone"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function TrendTooltip({
  active,
  currency,
  metric,
  payload,
  title,
}: {
  active?: boolean;
  currency: string | null;
  metric: TrendMetric;
  payload?: TooltipPayload;
  title: string;
}) {
  if (!active || !payload?.length) return null;
  const item = payload[0];
  const value = Number(item.value ?? 0);

  return (
    <div className="rounded-[14px] bg-[#102734] px-3 py-2 text-white shadow-[0_14px_34px_rgba(16,39,52,0.22)]">
      <p className="text-[11px] font-medium text-white/70">
        {title} · P{item.payload?.period}
      </p>
      <p className="mt-0.5 text-[14px] font-semibold">
        {metric === "candidateEntryCount"
          ? formatCompactNumber(value)
          : formatAmount(value, currency)}
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
