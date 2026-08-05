"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import type { RasCandidateDetectionResult } from "@/api/agent/types";

import { chartColors, formatAmount, formatCompactNumber } from "./analyticsUtils";

type TooltipPayload = Array<{
  name?: string;
  value?: number;
  payload?: { label?: string };
}>;

export default function WithholdingDonutSummary({
  result,
}: {
  result: RasCandidateDetectionResult;
}) {
  const candidateRate =
    result.evaluatedPieceCount > 0
      ? result.candidatePieceCount / result.evaluatedPieceCount
      : 0;
  const statusData = Object.entries(result.statusCounts)
    .filter(([, value]) => value > 0)
    .sort(([, left], [, right]) => right - left)
    .map(([label, value]) => ({ label, name: rasStatusLabel(label), value }));
  const amount = primaryAmount(result.candidateAmountsByCurrency);

  return (
    <section className="rounded-[22px] bg-white p-4 shadow-[0_16px_42px_rgba(64,81,92,0.07)] ring-1 ring-[#e8f0f3]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-[14px] font-semibold text-[#102734]">
            Synthèse candidats
          </h3>
          <p className="mt-0.5 text-[11px] font-medium text-[#8a98a2]">
            Revue uniquement
          </p>
        </div>
        <span className="rounded-full bg-[#edf5f8] px-2.5 py-1 text-[11px] font-semibold text-[#40515C]">
          {Math.round(candidateRate * 1000) / 10}%
        </span>
      </div>

      <div className="mt-4 grid grid-cols-[142px_minmax(0,1fr)] items-center gap-3">
        <div className="relative h-[142px]">
          <ResponsiveContainer height="100%" width="100%">
            <PieChart>
              <Tooltip content={<DonutTooltip />} />
              <Pie
                animationDuration={900}
                cornerRadius={10}
                data={statusData}
                dataKey="value"
                innerRadius={44}
                outerRadius={64}
                paddingAngle={3}
                stroke="none"
              >
                {statusData.map((item, index) => (
                  <Cell
                    fill={chartColors[index % chartColors.length]}
                    key={item.label}
                  />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
            <strong className="text-[22px] font-semibold leading-none text-[#102734]">
              {formatCompactNumber(result.candidatePieceCount)}
            </strong>
            <span className="mt-1 text-[10px] font-semibold text-[#8a98a2]">
              candidats
            </span>
          </div>
        </div>

        <div className="min-w-0 space-y-3">
          <div>
            <p className="text-[11px] font-semibold text-[#8a98a2]">
              Montant candidat
            </p>
            <p className="mt-1 truncate text-[18px] font-semibold text-[#102734]">
              {amount
                ? formatAmount(amount.value, amount.currency)
                : "Non disponible"}
            </p>
          </div>
          <div className="space-y-2">
            {statusData.slice(0, 3).map((item, index) => (
              <div
                className="flex min-w-0 items-center justify-between gap-2"
                key={item.label}
              >
                <span className="flex min-w-0 items-center gap-2">
                  <span
                    className="size-2 shrink-0 rounded-full"
                    style={{
                      backgroundColor: chartColors[index % chartColors.length],
                    }}
                  />
                  <span className="truncate text-[11px] font-semibold text-[#60737e]">
                    {item.name}
                  </span>
                </span>
                <span className="shrink-0 text-[11px] font-semibold text-[#102734]">
                  {formatCompactNumber(item.value)}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function DonutTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: TooltipPayload;
}) {
  if (!active || !payload?.length) return null;
  const item = payload[0];

  return (
    <div className="rounded-[14px] bg-[#102734] px-3 py-2 text-white shadow-[0_14px_34px_rgba(16,39,52,0.22)]">
      <p className="max-w-[180px] truncate text-[11px] font-medium text-white/70">
        {item.payload?.label || item.name}
      </p>
      <p className="mt-0.5 text-[14px] font-semibold">
        {formatCompactNumber(Number(item.value ?? 0))}
      </p>
    </div>
  );
}

function primaryAmount(record: Record<string, string>) {
  const [currency, rawValue] = Object.entries(record)[0] ?? [];
  const value = Number(rawValue);
  if (!currency || !Number.isFinite(value)) return null;
  return { currency, value };
}

function rasStatusLabel(value: string): string {
  const labels: Record<string, string> = {
    candidate_account_and_text: "Compte + libellé",
    candidate_account_only: "Compte seul",
    candidate_text_only: "Libellé seul",
    candidate_indeterminate: "Indéterminé",
  };
  return labels[value] ?? value.replaceAll("_", " ");
}
