import type { AgentRunResponse, LedgerQueryResult } from "./types";

export const LEDGER_COLUMN_LABELS: Record<string, string> = {
  account: "Compte",
  amount: "Montant",
  posting_key: "Clé comptable",
  currency: "Devise",
  period: "Période",
  fiscal_year: "Exercice",
  document_type: "Type de document",
  tax_code: "Code fiscal",
  vendor: "Fournisseur",
  customer: "Client",
};

const EMPTY_VALUES = new Set(["", "sans valeur"]);

export function extractLedgerQueryResult(
  response: AgentRunResponse
): LedgerQueryResult | null {
  const result = response.tool_results.find(
    (toolResult) =>
      toolResult.tool_name === "query_ledger_entries" && toolResult.ok
  );
  const output = result?.output;
  if (!isLedgerQueryOutput(output)) return null;

  return {
    sheetName: output.sheet_name,
    totalMatches: output.total_matches,
    page: output.page,
    pageSize: output.page_size,
    filters: output.filters,
    returnedColumns: output.returned_columns,
    entries: output.entries,
    signConvention: output.sign_convention,
  };
}

export function getVisibleLedgerColumns(result: LedgerQueryResult): string[] {
  return result.returnedColumns.filter((column) => {
    if (
      column === "account" &&
      typeof result.filters.account === "string"
    ) {
      return false;
    }
    return result.entries.some((entry) => !isEmptyLedgerValue(entry[column]));
  });
}

export function getEmptyLedgerColumns(result: LedgerQueryResult): string[] {
  return result.returnedColumns.filter(
    (column) =>
      column !== "account" &&
      result.entries.every((entry) => isEmptyLedgerValue(entry[column]))
  );
}

export function formatLedgerValue(column: string, value: unknown): string {
  if (isEmptyLedgerValue(value)) return "—";

  if (column === "amount") {
    const amount =
      typeof value === "number"
        ? value
        : Number(String(value).replace(",", "."));
    if (Number.isFinite(amount)) {
      return new Intl.NumberFormat("fr-FR", {
        maximumFractionDigits: 2,
      }).format(amount);
    }
  }

  if (column === "period") {
    return String(value).padStart(2, "0");
  }

  return String(value);
}

export function getLedgerPageCount(result: LedgerQueryResult): number {
  return Math.max(1, Math.ceil(result.totalMatches / result.pageSize));
}

function isEmptyLedgerValue(value: unknown): boolean {
  return (
    value === null ||
    value === undefined ||
    EMPTY_VALUES.has(String(value).trim().toLocaleLowerCase("fr"))
  );
}

function isLedgerQueryOutput(
  output: Record<string, unknown> | undefined
): output is {
  sheet_name: string;
  total_matches: number;
  page: number;
  page_size: number;
  filters: Record<string, unknown>;
  returned_columns: string[];
  entries: Array<Record<string, unknown>>;
  sign_convention: string | null;
} {
  return Boolean(
    output &&
      typeof output.sheet_name === "string" &&
      typeof output.total_matches === "number" &&
      Number.isInteger(output.total_matches) &&
      typeof output.page === "number" &&
      Number.isInteger(output.page) &&
      typeof output.page_size === "number" &&
      Number.isInteger(output.page_size) &&
      output.page_size > 0 &&
      isRecord(output.filters) &&
      Array.isArray(output.returned_columns) &&
      output.returned_columns.every((column) => typeof column === "string") &&
      Array.isArray(output.entries) &&
      output.entries.every(isRecord) &&
      (output.sign_convention === null ||
        typeof output.sign_convention === "string")
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}
