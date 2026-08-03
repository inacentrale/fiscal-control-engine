"use client";

import { useState } from "react";

import type { TaxDeclarationType } from "@/api/taxDeclarations/types";
import type { AnalyzeTaxDeclarationHistoryParams } from "@/api/taxDeclarations/analyzeTaxDeclarationHistory";
import Button from "@/components/base/button/Button";

export default function DeclarationHistoryForm({
  declarationType,
  onAnalyze,
  isAnalyzing,
  errorMessage,
}: {
  declarationType: TaxDeclarationType;
  onAnalyze: (params: AnalyzeTaxDeclarationHistoryParams) => void;
  isAnalyzing: boolean;
  errorMessage: string | null;
}) {
  const [currentFile, setCurrentFile] = useState<File | null>(null);
  const [previousFile, setPreviousFile] = useState<File | null>(null);
  const [currentPeriodEnd, setCurrentPeriodEnd] = useState("");
  const [previousPeriodEnd, setPreviousPeriodEnd] = useState("");
  const [tolerance, setTolerance] = useState("0");

  const canSubmit =
    Boolean(currentFile) &&
    Boolean(previousFile) &&
    Boolean(currentPeriodEnd) &&
    Boolean(previousPeriodEnd);

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!currentFile || !previousFile || !currentPeriodEnd || !previousPeriodEnd) return;
    onAnalyze({
      currentFile,
      previousFile,
      declarationType,
      currentPeriodEnd,
      previousPeriodEnd,
      tolerance: tolerance || undefined,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <FileField
          label="Exercice courant"
          onChange={setCurrentFile}
        />
        <FileField
          label="Exercice précédent"
          onChange={setPreviousFile}
        />
      </div>

      <div className="grid grid-cols-3 gap-3">
        <DateField
          label="Fin d'exercice courant"
          value={currentPeriodEnd}
          onChange={setCurrentPeriodEnd}
        />
        <DateField
          label="Fin d'exercice précédent"
          value={previousPeriodEnd}
          onChange={setPreviousPeriodEnd}
        />
        <div>
          <label className="mb-[1px] block text-[14px] font-medium text-[#102734]">
            Tolérance
          </label>
          <input
            type="number"
            min="0"
            step="1"
            value={tolerance}
            onChange={(event) => setTolerance(event.target.value)}
            className="h-11 w-full rounded-[12px] border border-[#e5edf1] bg-white px-3.5 text-[14px] text-[#102734] outline-none focus:border-[#3664ff]"
          />
        </div>
      </div>

      {errorMessage && (
        <p className="rounded-[10px] bg-[#fff1ed] px-3 py-2 text-[12px] font-medium text-[#c8563f]">
          {errorMessage}
        </p>
      )}

      <Button
        type="submit"
        disabled={!canSubmit || isAnalyzing}
        isLoading={isAnalyzing}
        className="h-11 rounded-[12px] bg-[#3664ff] px-5 text-[14px] font-semibold text-white disabled:opacity-50"
      >
        Comparer les deux exercices
      </Button>
    </form>
  );
}

function FileField({
  label,
  onChange,
}: {
  label: string;
  onChange: (file: File | null) => void;
}) {
  return (
    <div>
      <label className="mb-[1px] block text-[14px] font-medium text-[#102734]">
        {label}
      </label>
      <input
        type="file"
        accept=".csv,.xlsx,.xls,.xml,.pdf,.png,.jpg,.jpeg"
        onChange={(event) => onChange(event.target.files?.[0] ?? null)}
        className="block w-full text-[13px] text-[#40515c] file:mr-3 file:rounded-[10px] file:border-0 file:bg-[#f2f6f8] file:px-3 file:py-2 file:text-[12px] file:font-semibold file:text-[#203743]"
      />
    </div>
  );
}

function DateField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div>
      <label className="mb-[1px] block text-[14px] font-medium text-[#102734]">
        {label}
      </label>
      <input
        type="date"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-11 w-full rounded-[12px] border border-[#e5edf1] bg-white px-3.5 text-[14px] text-[#102734] outline-none focus:border-[#3664ff]"
      />
    </div>
  );
}
