"use client";

import { useState } from "react";

import type { TaxDeclarationType } from "@/api/taxDeclarations/types";
import type { AnalyzeTaxDeclarationParams } from "@/api/taxDeclarations/analyzeTaxDeclaration";
import Button from "@/components/base/button/Button";

export default function DeclarationUploadForm({
  declarationType,
  onAnalyze,
  isAnalyzing,
  errorMessage,
}: {
  declarationType: TaxDeclarationType;
  onAnalyze: (params: AnalyzeTaxDeclarationParams) => void;
  isAnalyzing: boolean;
  errorMessage: string | null;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [periodEnd, setPeriodEnd] = useState("");
  const [filingDate, setFilingDate] = useState("");
  const [tolerance, setTolerance] = useState("0");

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!file) return;
    onAnalyze({
      file,
      declarationType,
      periodEnd: periodEnd || undefined,
      filingDate: filingDate || undefined,
      tolerance: tolerance || undefined,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div>
        <label className="mb-[1px] block text-[14px] font-medium text-[#102734]">
          Fichier de déclaration
        </label>
        <input
          type="file"
          accept=".csv,.xlsx,.xls,.xml,.pdf,.png,.jpg,.jpeg"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          className="block w-full text-[13px] text-[#40515c] file:mr-3 file:rounded-[10px] file:border-0 file:bg-[#f2f6f8] file:px-3 file:py-2 file:text-[12px] file:font-semibold file:text-[#203743]"
        />
      </div>

      <div className="grid grid-cols-3 gap-3">
        <DateField
          label="Fin de période / exercice"
          value={periodEnd}
          onChange={setPeriodEnd}
        />
        <DateField
          label="Date de dépôt"
          value={filingDate}
          onChange={setFilingDate}
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
        disabled={!file || isAnalyzing}
        isLoading={isAnalyzing}
        className="h-11 rounded-[12px] bg-[#3664ff] px-5 text-[14px] font-semibold text-white disabled:opacity-50"
      >
        Analyser la déclaration
      </Button>
    </form>
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
