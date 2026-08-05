"use client";

import type { ReactNode } from "react";

import { cn } from "@/utils/ui/styles";

export type AnalyticsStatItem = {
  accent: string;
  detail: string;
  icon: ReactNode;
  label: string;
  muted?: boolean;
  progress?: number;
  strong?: boolean;
  value: string;
};

export default function AnalyticsStatGrid({
  items,
  variant = "expanded",
}: {
  items: AnalyticsStatItem[];
  variant?: "compact" | "expanded";
}) {
  if (variant === "compact") {
    return (
      <div className="grid grid-cols-4 gap-1.5">
        {items.map((item) => (
          <CompactStatCard item={item} key={item.label} />
        ))}
      </div>
    );
  }

  return (
    <div className="scrollbar-none -mx-1 flex snap-x gap-5 overflow-x-auto px-1 pb-1">
      {items.map((item) => (
        <ExpandedStatCard item={item} key={item.label} />
      ))}
    </div>
  );
}

function CompactStatCard({ item }: { item: AnalyticsStatItem }) {
  return (
    <div className="rounded-[14px] bg-[#f5f8fa] px-2.5 py-2.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.72)]">
      <p className="truncate text-[10px] font-semibold text-[#7d8d97]">
        {item.label}
      </p>
      <p className="mt-1 truncate text-[15px] font-semibold text-[#102734]">
        {item.value}
      </p>
    </div>
  );
}

function ExpandedStatCard({ item }: { item: AnalyticsStatItem }) {
  return (
    <div
      className={cn(
        "min-w-[210px] snap-start overflow-hidden rounded-[22px] bg-white px-5 py-4 shadow-[0_18px_44px_rgba(64,81,92,0.07)] ring-1 sm:min-w-[225px] xl:min-w-[238px]",
        item.strong ? "ring-[#d7e8ef]" : "ring-[#e5eef2]"
      )}
    >
      <div className="flex items-center justify-between gap-3">
        <p className="truncate text-[12px] font-semibold text-[#7d8d97]">
          {item.label}
        </p>
        <span
          className="flex size-9 shrink-0 items-center justify-center rounded-full"
          style={{ backgroundColor: `${item.accent}14`, color: item.accent }}
        >
          {item.icon}
        </span>
      </div>
      <p
        className={cn(
          "mt-2 truncate font-semibold text-[#102734]",
          item.strong ? "text-[30px]" : "text-[27px]"
        )}
      >
        {item.value}
      </p>
      <div className="mt-3 flex min-w-0 items-center gap-2">
        <span
          className="size-1.5 shrink-0 rounded-full"
          style={{ backgroundColor: item.muted ? "#8B98A3" : item.accent }}
        />
        <span className="truncate text-[11px] font-semibold text-[#8a98a2]">
          {item.detail}
        </span>
      </div>
    </div>
  );
}
