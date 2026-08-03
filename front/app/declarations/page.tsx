"use client";

import { useState } from "react";

import DashboardShell from "@/components/layout/DashboardShell";
import DeclarationTypeSelect from "@/components/declarations/DeclarationTypeSelect";
import DeclarationUploadForm from "@/components/declarations/DeclarationUploadForm";
import DeclarationHistoryForm from "@/components/declarations/DeclarationHistoryForm";
import DeclarationFieldsTable from "@/components/declarations/DeclarationFieldsTable";
import ValidationReportPanel from "@/components/declarations/ValidationReportPanel";
import AssuranceBadge from "@/components/declarations/AssuranceBadge";
import {
  TAX_DECLARATION_TYPES_WITH_HISTORY,
  type TaxDeclarationType,
} from "@/api/taxDeclarations/types";
import { useAnalyzeTaxDeclaration } from "@/hooks/useAnalyzeTaxDeclaration";
import { useAnalyzeTaxDeclarationHistory } from "@/hooks/useAnalyzeTaxDeclarationHistory";

type Tab = "analyze" | "history";

export default function DeclarationsPage() {
  const [declarationType, setDeclarationType] =
    useState<TaxDeclarationType>("corporate_income_tax");
  const [activeTab, setActiveTab] = useState<Tab>("analyze");
  const supportsHistory =
    TAX_DECLARATION_TYPES_WITH_HISTORY.includes(declarationType);

  const {
    analyze,
    result: analysisResult,
    isAnalyzing,
    errorMessage: analyzeError,
  } = useAnalyzeTaxDeclaration();
  const {
    analyzeHistory,
    result: historyResult,
    isAnalyzing: isAnalyzingHistory,
    errorMessage: historyError,
  } = useAnalyzeTaxDeclarationHistory();

  const handleTypeChange = (type: TaxDeclarationType) => {
    setDeclarationType(type);
    if (!TAX_DECLARATION_TYPES_WITH_HISTORY.includes(type)) {
      setActiveTab("analyze");
    }
  };

  return (
    <DashboardShell>
      <div className="mx-auto h-full max-w-[860px] overflow-y-auto px-6 py-8">
        <header className="mb-6">
          <h1 className="text-[22px] font-bold text-[#102734]">
            Gestion des déclarations
          </h1>
          <p className="mt-1 text-[13px] font-medium text-[#8a98a2]">
            Analysez une déclaration TVA, RAS, IUTS ou IS et consultez son
            rapport de contrôle déterministe.
          </p>
        </header>

        <div className="rounded-[18px] bg-white p-5 shadow-[0_16px_42px_rgba(64,81,92,0.07)] ring-1 ring-[#e8f0f3]">
          <DeclarationTypeSelect
            value={declarationType}
            onChange={handleTypeChange}
          />

          <div className="mb-4 flex gap-1 rounded-[12px] bg-[#f2f6f8] p-1">
            <TabButton
              label="Analyser"
              isActive={activeTab === "analyze"}
              onClick={() => setActiveTab("analyze")}
            />
            <TabButton
              label="Historique (2 exercices)"
              isActive={activeTab === "history"}
              onClick={() => setActiveTab("history")}
              disabled={!supportsHistory}
              disabledHint="Non disponible pour ce type de déclaration"
            />
          </div>

          {activeTab === "analyze" && (
            <DeclarationUploadForm
              declarationType={declarationType}
              onAnalyze={analyze}
              isAnalyzing={isAnalyzing}
              errorMessage={analyzeError}
            />
          )}

          {activeTab === "history" && supportsHistory && (
            <DeclarationHistoryForm
              declarationType={declarationType}
              onAnalyze={analyzeHistory}
              isAnalyzing={isAnalyzingHistory}
              errorMessage={historyError}
            />
          )}
        </div>

        {activeTab === "analyze" && analysisResult && (
          <div className="mt-6 space-y-5">
            <IngestionSummary
              fileName={analysisResult.file_name}
              sourceFormat={analysisResult.source_format}
              formatConfidence={analysisResult.format_confidence}
              status={analysisResult.status}
              reason={analysisResult.reason}
            />
            {analysisResult.declaration && (
              <DeclarationFieldsTable declaration={analysisResult.declaration} />
            )}
            {analysisResult.assurance && (
              <AssuranceBadge assurance={analysisResult.assurance} />
            )}
            {analysisResult.validation && (
              <ValidationReportPanel
                overallStatus={analysisResult.validation.overall_status}
                checks={analysisResult.validation.checks}
              />
            )}
          </div>
        )}

        {activeTab === "history" && historyResult && (
          <div className="mt-6 space-y-5">
            <div className="grid grid-cols-2 gap-4">
              <IngestionSummary
                title="Exercice courant"
                fileName={historyResult.current.file_name}
                sourceFormat={historyResult.current.source_format}
                formatConfidence={historyResult.current.format_confidence}
                status={historyResult.current.status}
                reason={historyResult.current.reason}
              />
              <IngestionSummary
                title="Exercice précédent"
                fileName={historyResult.previous.file_name}
                sourceFormat={historyResult.previous.source_format}
                formatConfidence={historyResult.previous.format_confidence}
                status={historyResult.previous.status}
                reason={historyResult.previous.reason}
              />
            </div>
            {historyResult.validation ? (
              <ValidationReportPanel
                overallStatus={historyResult.validation.overall_status}
                checks={historyResult.validation.checks}
              />
            ) : (
              <p className="rounded-[14px] bg-[#f7fafb] px-4 py-3 text-[13px] font-medium text-[#60737e]">
                Aucun contrôle historique disponible pour ce type de
                déclaration.
              </p>
            )}
          </div>
        )}
      </div>
    </DashboardShell>
  );
}

function TabButton({
  label,
  isActive,
  onClick,
  disabled,
  disabledHint,
}: {
  label: string;
  isActive: boolean;
  onClick: () => void;
  disabled?: boolean;
  disabledHint?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={disabled ? disabledHint : undefined}
      className={[
        "h-9 flex-1 rounded-[10px] text-[13px] font-semibold transition",
        disabled
          ? "cursor-not-allowed text-[#b7c1c7]"
          : isActive
            ? "bg-white text-[#3664ff] shadow-[0_1px_2px_rgba(16,39,52,0.08)]"
            : "text-[#60737e] hover:text-[#203743]",
      ].join(" ")}
    >
      {label}
    </button>
  );
}

function IngestionSummary({
  title = "Fichier analysé",
  fileName,
  sourceFormat,
  formatConfidence,
  status,
  reason,
}: {
  title?: string;
  fileName: string;
  sourceFormat: string;
  formatConfidence: number;
  status: string;
  reason: string | null;
}) {
  return (
    <section className="rounded-[14px] border border-[#edf3f6] bg-white p-3.5">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-[#8a98a2]">
        {title}
      </p>
      <p className="mt-1 text-[13px] font-semibold text-[#102734]">
        {fileName}
      </p>
      <p className="mt-1 text-[11px] font-medium text-[#8a98a2]">
        Format {sourceFormat} · confiance{" "}
        {Math.round(formatConfidence * 100)}% · statut {status}
      </p>
      {reason && (
        <p className="mt-1 text-[11px] font-medium text-[#c8563f]">{reason}</p>
      )}
    </section>
  );
}
