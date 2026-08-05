"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import {
  agentSidebarQueryKeys,
  getAgentSessionContext,
  listAgentFiles,
} from "@/api/agent/sidebar";
import { extractRasCandidateDetectionResult } from "@/api/agent/rasCandidateDetection";
import { runRasCandidateDetection } from "@/api/agent/runAgentAnalysis";
import type {
  AgentDashboardChart,
  AgentFileDashboard,
  AgentSidebarFile,
  RasCandidateDetectionResult,
} from "@/api/agent/types";
import { Maximize24Icon } from "@/public/assets/icons/AnalyticsIcons";
import useAgentWorkspaceStore from "@/store/agentWorkspaceStore";

import AnalyticsChartCard from "./AnalyticsChartCard";
import AnalyticsKpiGrid from "./AnalyticsKpiGrid";
import AnalyticsModeSwitcher, {
  type AnalyticsMode,
} from "./AnalyticsModeSwitcher";
import AnalyticsQualityDetails from "./AnalyticsQualityDetails";
import AnalyticsReveal from "./AnalyticsReveal";
import AnalyticsViewTabs from "./AnalyticsViewTabs";
import WithholdingAnalyticsPanel, {
  WithholdingExpandedModal,
} from "./WithholdingAnalyticsPanel";
import { analyticsViews, type AnalyticsView } from "./analyticsViews";
import { compactInsight, findChart } from "./analyticsUtils";

export default function AnalyticsColumn() {
  const [activeMode, setActiveMode] = useState<AnalyticsMode>("ledger");
  const [activeView, setActiveView] = useState<AnalyticsView>("general");
  const [isExpanded, setIsExpanded] = useState(false);
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
  const rasCandidatesQuery = useQuery({
    queryKey: [
      "agent",
      "ras-candidates",
      activeSessionId,
      activeFile?.file_id,
      dashboard?.sheet_name,
    ],
    queryFn: async () => {
      const response = await runRasCandidateDetection(
        activeSessionId || "",
        activeFile?.file_id || "",
        dashboard?.sheet_name || ""
      );
      return extractRasCandidateDetectionResult(response);
    },
    enabled: Boolean(
      activeMode === "withholding" &&
        activeSessionId &&
        activeFile?.file_id &&
        dashboard?.sheet_name
    ) || Boolean(
      isExpanded &&
        activeSessionId &&
        activeFile?.file_id &&
        dashboard?.sheet_name
    ),
  });
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
      <AnalyticsReveal>
        <div className="flex items-center gap-2">
          <div className="min-w-0 flex-1">
            <AnalyticsModeSwitcher
              activeMode={activeMode}
              onChange={setActiveMode}
            />
          </div>
          <button
            aria-label="Agrandir la vue analytique"
            className="grid size-[54px] shrink-0 place-items-center rounded-[22px] bg-white text-[#40515C] shadow-[0_14px_34px_rgba(64,81,92,0.08)] ring-1 ring-[#e5eef2] transition hover:bg-[#f5f8fa] hover:text-[#102734]"
            onClick={() => setIsExpanded(true)}
            type="button"
          >
            <Maximize24Icon className="size-5" />
          </button>
        </div>
      </AnalyticsReveal>

      {activeMode === "withholding" ? (
        <WithholdingAnalyticsPanel
          state={toWithholdingState(
            rasCandidatesQuery.isLoading,
            rasCandidatesQuery.isError,
            rasCandidatesQuery.data,
            rasCandidatesQuery.error
          )}
        />
      ) : (
        <LedgerAnalyticsContent
          activeFile={activeFile}
          activeView={activeView}
          dashboard={dashboard}
          isReady={contextQuery.data?.state === "ready"}
          onViewChange={setActiveView}
          primaryChart={primaryChart}
          secondaryCharts={secondaryCharts}
        />
      )}

      {isExpanded && rasCandidatesQuery.data && (
        <ExpandedAnalyticsModalBridge
          activeMode={activeMode}
          onClose={() => setIsExpanded(false)}
          onModeChange={setActiveMode}
          result={rasCandidatesQuery.data}
        />
      )}
    </div>
  );
}

function ExpandedAnalyticsModalBridge({
  activeMode,
  onClose,
  onModeChange,
  result,
}: {
  activeMode: AnalyticsMode;
  onClose: () => void;
  onModeChange: (mode: AnalyticsMode) => void;
  result: RasCandidateDetectionResult;
}) {
  const signalItems = topEntries(result.signalCounts, 4);
  const missingFactItems = topEntries(result.missingFactCounts, 3);
  const periods = result.rasReview?.periods ?? [];
  const amount = primaryAmount(result.candidateAmountsByCurrency);
  const candidateRate =
    result.evaluatedPieceCount > 0
      ? result.candidatePieceCount / result.evaluatedPieceCount
      : 0;

  return (
    <WithholdingExpandedModal
      activeMode={activeMode}
      amount={amount}
      candidateRate={candidateRate}
      missingFactItems={missingFactItems}
      onClose={onClose}
      onModeChange={onModeChange}
      periods={periods}
      result={result}
      signalItems={signalItems}
    />
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

function LedgerAnalyticsContent({
  activeFile,
  activeView,
  dashboard,
  isReady,
  onViewChange,
  primaryChart,
  secondaryCharts,
}: {
  activeFile: AgentSidebarFile;
  activeView: AnalyticsView;
  dashboard: AgentFileDashboard;
  isReady: boolean;
  onViewChange: (view: AnalyticsView) => void;
  primaryChart: AgentDashboardChart | null;
  secondaryCharts: AgentDashboardChart[];
}) {
  return (
    <>
      <header className="space-y-1">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-[16px] font-semibold">Analyse du fichier</h2>
          <span className="rounded-full bg-[#eef6f2] px-2.5 py-1 text-[11px] font-semibold text-[#168766]">
            {isReady ? "Prêt" : "En attente"}
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
        <AnalyticsViewTabs activeView={activeView} onChange={onViewChange} />
      </AnalyticsReveal>

      <div className="space-y-3 pb-4">
        {secondaryCharts.map((chart) => (
          <AnalyticsReveal delay={0.04} key={chart.chart_id}>
            <AnalyticsChartCard chart={chart} />
          </AnalyticsReveal>
        ))}
      </div>
    </>
  );
}

function toWithholdingState(
  isLoading: boolean,
  isError: boolean,
  result: RasCandidateDetectionResult | null | undefined,
  error: Error | null
):
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "empty" }
  | { status: "ready"; result: RasCandidateDetectionResult } {
  if (isLoading) return { status: "loading" };
  if (isError) {
    return {
      status: "error",
      message:
        error?.message ||
        "La détection des candidats RAS ne peut pas être chargée.",
    };
  }
  if (!result) return { status: "empty" };
  return { status: "ready", result };
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
