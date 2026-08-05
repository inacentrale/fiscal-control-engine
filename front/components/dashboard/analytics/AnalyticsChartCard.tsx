"use client";

import type { AgentDashboardChart } from "@/api/agent/types";
import { cn } from "@/utils/ui/styles";
import { motion } from "framer-motion";
import {
  Area,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Line,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  chartColors,
  chartPoints,
  chartTotal,
  formatCompactNumber,
  formatAmount,
} from "./analyticsUtils";

type TooltipPayload = Array<{
  name?: string;
  value?: number;
  payload?: { label?: string; currency?: string | null };
}>;

export default function AnalyticsChartCard({
  chart,
  featured = false,
}: {
  chart: AgentDashboardChart;
  featured?: boolean;
}) {
  const isEmpty = chart.values.length === 0 || chartTotal(chart) === 0;

  return (
    <section
      className={cn(
        "bg-white shadow-[0_16px_42px_rgba(64,81,92,0.07)] ring-1 ring-[#e8f0f3]",
        featured
          ? "rounded-[22px] p-[18px]"
          : "rounded-[18px] p-4"
      )}
    >
      <div className="flex min-w-0 items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate text-[14px] font-semibold text-[#102734]">
            {chart.title}
          </h3>
          <p className="mt-0.5 text-[11px] font-medium text-[#8a98a2]">
            {metricLabel(chart.metric)}
          </p>
        </div>
        <span className="shrink-0 rounded-full bg-[#f5f8fa] px-2.5 py-1 text-[11px] font-semibold text-[#60737e]">
          {formatChartTotal(chart)}
        </span>
      </div>

      {isEmpty ? (
        <div className="mt-4 flex h-[140px] items-center justify-center rounded-[14px] bg-[#f8fafb] px-4 text-center text-[12px] font-medium text-[#8a98a2]">
          Aucune donnée exploitable.
        </div>
      ) : featured ? (
        <FiscalHeroBars chart={chart} />
      ) : chart.kind === "composed" ? (
        <FiscalComposedChart chart={chart} />
      ) : chart.kind === "line" ? (
        <FiscalLineChart chart={chart} />
      ) : chart.kind === "doughnut" ? (
        <FiscalDonutChart chart={chart} />
      ) : chart.kind === "horizontal_bar" ? (
        <FiscalHorizontalBars chart={chart} />
      ) : (
        <FiscalBarChart chart={chart} featured={featured} />
      )}
    </section>
  );
}

function FiscalHeroBars({ chart }: { chart: AgentDashboardChart }) {
  const data = chartPoints(chart, 6);
  const max = Math.max(...data.map((item) => item.value), 1);

  return (
    <div className="mt-5 space-y-3.5">
      {data.map((item, index) => {
        const percent = Math.max(8, Math.round((item.value / max) * 100));

        return (
          <div
            className="grid grid-cols-[72px_minmax(0,1fr)_58px] items-center gap-2"
            key={item.label}
          >
            <span className="truncate text-[11px] font-semibold text-[#60737e]">
              {item.label}
            </span>
            <div className="h-8 overflow-hidden rounded-full bg-[#eef4f7]">
              <motion.div
                className="h-full rounded-full"
                initial={{ width: 0 }}
                style={{ backgroundColor: chartColors[index % chartColors.length] }}
                transition={{
                  duration: 0.68,
                  delay: index * 0.06,
                  ease: [0.22, 1, 0.36, 1],
                }}
                viewport={{ once: true }}
                whileInView={{ width: `${percent}%` }}
              />
            </div>
            <span className="text-right text-[11px] font-semibold text-[#102734]">
              {formatChartValue(chart, item.value, item.currency)}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function FiscalComposedChart({ chart }: { chart: AgentDashboardChart }) {
  const colors = ["#40515C", "#7FA6B7", "#E36F55"];
  const currency =
    typeof chart.metadata.currency === "string" ? chart.metadata.currency : null;
  const data = chart.labels.map((label, index) => ({
    label,
    shortLabel: label.length > 10 ? `${label.slice(0, 9)}...` : label,
    debit: Number(chart.series[0]?.values[index] ?? 0),
    credit: Number(chart.series[1]?.values[index] ?? 0),
    balance: Number(chart.series[2]?.values[index] ?? chart.values[index] ?? 0),
    currency,
  }));

  return (
    <div className="mt-4 h-[170px] w-full outline-none [&_.recharts-wrapper]:outline-none [&_svg]:outline-none">
      <ResponsiveContainer height="100%" width="100%">
        <ComposedChart data={data} margin={{ top: 12, right: 8, bottom: 2, left: -24 }}>
          <CartesianGrid stroke="#EDF3F6" strokeDasharray="6 9" vertical={false} />
          <XAxis
            axisLine={false}
            dataKey="shortLabel"
            interval="preserveStartEnd"
            tick={{ fill: "#8b9aa3", fontSize: 9, fontWeight: 600 }}
            tickLine={false}
            tickMargin={10}
          />
          <YAxis
            axisLine={false}
            tick={{ fill: "#9aa8b0", fontSize: 9, fontWeight: 600 }}
            tickFormatter={(value) => formatCompactNumber(Number(value))}
            tickLine={false}
            width={42}
          />
          <Tooltip content={<ComposedTooltip currency={currency} />} cursor={{ fill: "rgba(127,166,183,0.10)" }} />
          <Bar dataKey="debit" fill={colors[0]} maxBarSize={16} name="Débit" radius={[6, 6, 0, 0]} />
          <Bar dataKey="credit" fill={colors[1]} maxBarSize={16} name="Crédit" radius={[6, 6, 0, 0]} />
          <Line
            dataKey="balance"
            dot={{ fill: "#FFFFFF", r: 3, stroke: colors[2], strokeWidth: 2 }}
            name="Solde"
            stroke={colors[2]}
            strokeLinecap="round"
            strokeWidth={3}
            type="monotone"
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

function FiscalBarChart({
  chart,
  featured,
}: {
  chart: AgentDashboardChart;
  featured: boolean;
}) {
  const data = chartPoints(chart, featured ? 8 : 6);

  return (
    <div
      className={cn(
        "mt-4 w-full outline-none [&_.recharts-wrapper]:outline-none [&_svg]:outline-none",
        featured ? "h-[190px]" : "h-[142px]"
      )}
    >
      <ResponsiveContainer height="100%" width="100%">
        <BarChart data={data} margin={{ top: 12, right: 6, bottom: 10, left: -24 }}>
          <CartesianGrid stroke="#EDF3F6" strokeDasharray="6 9" vertical={false} />
          <XAxis
            axisLine={false}
            dataKey="shortLabel"
            interval={0}
            tick={{ fill: "#8b9aa3", fontSize: 9, fontWeight: 600 }}
            tickLine={false}
            tickMargin={10}
          />
          <YAxis
            allowDecimals={false}
            axisLine={false}
            tick={{ fill: "#9aa8b0", fontSize: 9, fontWeight: 600 }}
            tickFormatter={(value) => formatCompactNumber(Number(value))}
            tickLine={false}
            width={42}
          />
          <Tooltip content={<ChartTooltip metric={chart.metric} />} cursor={{ fill: "rgba(127,166,183,0.10)" }} />
          <Bar
            animationDuration={850}
            dataKey="value"
            maxBarSize={24}
            radius={[8, 8, 8, 8]}
          >
            {data.map((entry) => (
              <Cell fill={entry.fill} key={entry.label} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function FiscalLineChart({ chart }: { chart: AgentDashboardChart }) {
  const data = chartPoints(chart, 12);
  const gradientId = `analytics-line-${chart.chart_id}`;

  return (
    <div className="mt-4 h-[150px] w-full outline-none [&_.recharts-wrapper]:outline-none [&_svg]:outline-none">
      <ResponsiveContainer height="100%" width="100%">
        <ComposedChart data={data} margin={{ top: 12, right: 10, bottom: 2, left: -24 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="#7FA6B7" stopOpacity={0.24} />
              <stop offset="100%" stopColor="#7FA6B7" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#EDF3F6" strokeDasharray="6 9" vertical={false} />
          <XAxis
            axisLine={false}
            dataKey="shortLabel"
            interval="preserveStartEnd"
            tick={{ fill: "#8b9aa3", fontSize: 9, fontWeight: 600 }}
            tickLine={false}
            tickMargin={10}
          />
          <YAxis
            allowDecimals={false}
            axisLine={false}
            tick={{ fill: "#9aa8b0", fontSize: 9, fontWeight: 600 }}
            tickFormatter={(value) => formatCompactNumber(Number(value))}
            tickLine={false}
            width={42}
          />
          <Tooltip content={<ChartTooltip metric={chart.metric} />} cursor={{ stroke: "#7FA6B7", strokeDasharray: "4 8" }} />
          <Area
            animationBegin={70}
            animationDuration={900}
            dataKey="value"
            fill={`url(#${gradientId})`}
            stroke="none"
            type="monotone"
          />
          <Line
            animationDuration={900}
            dataKey="value"
            dot={{ fill: "#FFFFFF", r: 3, stroke: "#7FA6B7", strokeWidth: 2 }}
            stroke="#7FA6B7"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={3}
            type="monotone"
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

function FiscalDonutChart({ chart }: { chart: AgentDashboardChart }) {
  const data = chartPoints(chart, 5).map((point) => ({
    name: point.label,
    value: point.value,
    currency: point.currency,
  }));

  return (
    <div className="mt-4 grid items-center gap-3 sm:grid-cols-[118px_minmax(0,1fr)]">
      <div className="relative h-[118px]">
        <ResponsiveContainer height="100%" width="100%">
          <PieChart>
            <Tooltip content={<ChartTooltip metric={chart.metric} />} />
            <Pie
              animationDuration={850}
              cornerRadius={8}
              data={data}
              dataKey="value"
              innerRadius={34}
              outerRadius={52}
              paddingAngle={3}
            >
              {data.map((item, index) => (
                <Cell fill={chartColors[index % chartColors.length]} key={item.name} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-[9px] font-semibold text-[#9aa8b0]">Total</span>
          <strong className="text-[16px] font-semibold text-[#102734]">
            {formatChartTotal(chart)}
          </strong>
        </div>
      </div>
      <div className="min-w-0 space-y-2">
        {data.map((item, index) => (
          <div className="flex min-w-0 items-center justify-between gap-2" key={item.name}>
            <span className="flex min-w-0 items-center gap-2">
              <span
                className="size-2 shrink-0 rounded-full"
                style={{ backgroundColor: chartColors[index % chartColors.length] }}
              />
              <span className="truncate text-[11px] font-semibold text-[#60737e]">
                {item.name}
              </span>
            </span>
            <span className="shrink-0 text-[11px] font-semibold text-[#102734]">
              {formatChartValue(chart, item.value, item.currency)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function FiscalHorizontalBars({ chart }: { chart: AgentDashboardChart }) {
  const data = chartPoints(chart, 7);
  const max = Math.max(...data.map((item) => item.value), 1);

  return (
    <div className="mt-4 space-y-3">
      {data.map((item, index) => {
        const percent = Math.max(6, Math.round((item.value / max) * 100));

        return (
          <div className="space-y-1.5" key={item.label}>
            <div className="flex min-w-0 items-center justify-between gap-2">
              <span className="min-w-0 truncate text-[12px] font-semibold text-[#344854]">
                {item.label}
              </span>
              <span className="shrink-0 text-[12px] font-semibold text-[#102734]">
              {formatChartValue(chart, item.value, item.currency)}
              </span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-[#eef4f7]">
              <motion.div
                className="h-full rounded-full"
                initial={{ width: 0 }}
                style={{ backgroundColor: item.fill }}
                transition={{
                  duration: 0.58,
                  delay: index * 0.05,
                  ease: [0.22, 1, 0.36, 1],
                }}
                viewport={{ once: true }}
                whileInView={{ width: `${percent}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function ComposedTooltip({
  active,
  currency,
  payload,
}: {
  active?: boolean;
  currency: string | null;
  payload?: TooltipPayload;
}) {
  if (!active || !payload?.length) return null;
  const title = payload[0]?.payload?.label;

  return (
    <div className="rounded-[14px] bg-[#102734] px-3 py-2 text-white shadow-[0_14px_34px_rgba(16,39,52,0.22)]">
      <p className="text-[11px] font-medium text-white/70">{title}</p>
      {payload.map((item) => (
        <p className="mt-0.5 text-[13px] font-semibold" key={item.name}>
          {item.name}: {formatAmount(Number(item.value ?? 0), currency)}
        </p>
      ))}
    </div>
  );
}

function ChartTooltip({
  active,
  payload,
  label,
  metric,
}: {
  active?: boolean;
  payload?: TooltipPayload;
  label?: string;
  metric: string;
}) {
  if (!active || !payload?.length) return null;
  const item = payload[0];
  const title = item?.payload?.label || item?.name || label;

  return (
    <div className="rounded-[14px] bg-[#102734] px-3 py-2 text-white shadow-[0_14px_34px_rgba(16,39,52,0.22)]">
      <p className="max-w-[180px] truncate text-[11px] font-medium text-white/70">
        {title}
      </p>
      <p className="mt-0.5 text-[14px] font-semibold">
        {metric === "amount_sum"
          ? formatAmount(
              Number(item?.value ?? 0),
              item?.payload?.currency ?? null
            )
          : formatCompactNumber(Number(item?.value ?? 0))}
      </p>
    </div>
  );
}

function metricLabel(metric: string): string {
  if (metric === "amount_sum") return "Montants";
  if (metric === "entry_count") return "Écritures";
  if (metric === "issue_count") return "Qualité";
  return metric;
}

function formatChartValue(
  chart: AgentDashboardChart,
  value: number,
  currency: string | null
): string {
  return chart.metric === "amount_sum"
    ? formatAmount(value, currency)
    : formatCompactNumber(value);
}

function formatChartTotal(chart: AgentDashboardChart): string {
  if (chart.metric !== "amount_sum") return formatCompactNumber(chartTotal(chart));
  const currencies = Array.isArray(chart.metadata.currencies)
    ? chart.metadata.currencies.filter(
        (value): value is string => typeof value === "string"
      )
    : [];
  const uniqueCurrencies = [...new Set(currencies)];
  if (uniqueCurrencies.length > 1) return "Multi-devises";
  return formatAmount(chartTotal(chart), uniqueCurrencies[0] ?? null);
}
