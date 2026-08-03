"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import {
  agentSidebarQueryKeys,
  getAgentSessionContext,
  listAgentFiles,
} from "@/api/agent/sidebar";
import type { AgentDashboardChart } from "@/api/agent/types";
import useAgentWorkspaceStore from "@/store/agentWorkspaceStore";

import AnalyticsChartCard from "./AnalyticsChartCard";
import AnalyticsKpiGrid from "./AnalyticsKpiGrid";
import AnalyticsQualityDetails from "./AnalyticsQualityDetails";
import AnalyticsReveal from "./AnalyticsReveal";
import AnalyticsViewTabs from "./AnalyticsViewTabs";
import { analyticsViews, type AnalyticsView } from "./analyticsViews";
import { compactInsight, findChart } from "./analyticsUtils";

export default function AnalyticsColumn() {
  const [activeView, setActiveView] = useState<AnalyticsView>("general");
  const filesQuery = useQuery({
    queryKey: agentSidebarQueryKeys.files,
    queryFn: () => listAgentFiles(20),
  });
  const selectedSessionId = useAgentWorkspaceStore(
    (state) => state.activeSessionId
  );
  const activeSessionId =
    selectedSessionId ?? filesQuery.data?.items[0]?.session_id;
  const contextQuery = useQuery({
    queryKey: activeSessionId
      ? agentSidebarQueryKeys.sessionContext(activeSessionId)
      : ["agent", "sessions", "empty", "context"],
    queryFn: () => getAgentSessionContext(activeSessionId || ""),
    enabled: Boolean(activeSessionId),
  });

  const dashboard = contextQuery.data?.dashboard ?? null;
  const activeFile = contextQuery.data?.active_file ?? filesQuery.data?.items[0] ?? null;
  const primaryChart = dashboard ? findChart(dashboard, "top_accounts_by_amount") : null;
  const activeViewConfig =
    analyticsViews.find((view) => view.id === activeView) ?? analyticsViews[0];
  const secondaryCharts = useMemo(
    () =>
      dashboard
        ? activeViewConfig.chartIds
            .map((chartId) => findChart(dashboard, chartId))
            .filter((chart): chart is AgentDashboardChart => Boolean(chart))
        : [],
    [activeViewConfig.chartIds, dashboard]
  );

  if (filesQuery.isLoading || contextQuery.isLoading) {
    return <AnalyticsSkeleton />;
  }

  if (filesQuery.isError || contextQuery.isError) {
    return <AnalyticsState title="Analyse indisponible" text="Les données du fichier actif ne peuvent pas être chargées." />;
  }

  if (!activeFile || !dashboard) {
    return <AnalyticsState title="Aucun fichier actif" text="Ajoutez un fichier Excel pour afficher les analyses." />;
  }

  return (
    <div className="flex min-h-full flex-col gap-4 text-[#102734]">
      <header className="space-y-1">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-[16px] font-semibold">Analyse du fichier</h2>
          <span className="rounded-full bg-[#eef6f2] px-2.5 py-1 text-[11px] font-semibold text-[#168766]">
            {contextQuery.data?.state === "ready" ? "Prêt" : "En attente"}
          </span>
        </div>
        <p className="truncate text-[12px] font-medium text-[#7d8d97]">
          {activeFile.original_filename} · {dashboard.sheet_name}
        </p>
      </header>

      <AnalyticsReveal>
        <AnalyticsKpiGrid dashboard={dashboard} />
      </AnalyticsReveal>

      <AnalyticsReveal delay={0.02}>
        <AnalyticsQualityDetails dashboard={dashboard} />
      </AnalyticsReveal>

      {primaryChart && (
        <AnalyticsReveal delay={0.04}>
          <div className="space-y-2">
            <p className="mb-3 text-[12px] font-medium leading-5 text-[#60737e]">
              {compactInsight(primaryChart)}
            </p>
            <AnalyticsChartCard chart={primaryChart} featured />
          </div>
        </AnalyticsReveal>
      )}

      <AnalyticsReveal delay={0.08}>
        <AnalyticsViewTabs activeView={activeView} onChange={setActiveView} />
      </AnalyticsReveal>

      <div className="space-y-3 pb-4">
        {secondaryCharts.map((chart) => (
          <AnalyticsReveal delay={0.04} key={chart.chart_id}>
            <AnalyticsChartCard chart={chart} />
          </AnalyticsReveal>
        ))}
      </div>
    </div>
  );
}

function AnalyticsSkeleton() {
  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <div className="h-4 w-36 animate-pulse rounded-full bg-[#edf4f7]" />
        <div className="h-3 w-48 animate-pulse rounded-full bg-[#f5f8fa]" />
      </div>
      <div className="grid grid-cols-2 gap-2">
        {Array.from({ length: 4 }).map((_, index) => (
          <div
            className="h-[74px] animate-pulse rounded-[16px] bg-[#f5f8fa]"
            key={index}
          />
        ))}
      </div>
      <div className="h-[260px] animate-pulse rounded-[18px] bg-[#f5f8fa]" />
      <div className="h-[210px] animate-pulse rounded-[18px] bg-[#f5f8fa]" />
    </div>
  );
}

function AnalyticsState({ title, text }: { title: string; text: string }) {
  return (
    <div className="flex min-h-full items-center justify-center">
      <div className="rounded-[18px] bg-[#f5f8fa] px-5 py-6 text-center shadow-[inset_0_1px_0_rgba(255,255,255,0.72)]">
        <h2 className="text-[15px] font-semibold text-[#102734]">{title}</h2>
        <p className="mt-2 text-[12px] font-medium leading-5 text-[#7d8d97]">
          {text}
        </p>
      </div>
    </div>
  );
}
