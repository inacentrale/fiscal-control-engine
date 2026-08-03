import { describe, expect, it } from "vitest";

import type { AgentRunResponse } from "./types";
import {
  extractLedgerQueryResult,
  formatLedgerValue,
  getEmptyLedgerColumns,
  getLedgerPageCount,
  getVisibleLedgerColumns,
} from "./ledgerQueryResult";

describe("ledgerQueryResult", () => {
  it("extracts and validates a successful ledger query", () => {
    const result = extractLedgerQueryResult(buildResponse());

    expect(result).not.toBeNull();
    expect(result?.totalMatches).toBe(203);
    expect(result?.entries).toHaveLength(2);
    expect(getLedgerPageCount(result!)).toBe(11);
  });

  it("hides the filtered account and columns empty on the current page", () => {
    const result = extractLedgerQueryResult(buildResponse())!;

    expect(getVisibleLedgerColumns(result)).toEqual([
      "amount",
      "currency",
      "period",
      "fiscal_year",
      "document_type",
    ]);
    expect(getEmptyLedgerColumns(result)).toEqual([
      "tax_code",
      "vendor",
      "customer",
    ]);
  });

  it("formats amounts, periods and empty values for display", () => {
    expect(formatLedgerValue("amount", "16250")).toBe("16 250");
    expect(formatLedgerValue("period", "3")).toBe("03");
    expect(formatLedgerValue("vendor", "Sans valeur")).toBe("—");
  });

  it("rejects malformed external tool output", () => {
    const response = buildResponse();
    response.tool_results[0].output.page_size = 0;

    expect(extractLedgerQueryResult(response)).toBeNull();
  });
});

function buildResponse(): AgentRunResponse {
  return {
    answer: "Résumé généré.",
    provider_name: "openai-compatible",
    model_name: "gpt-5-mini",
    execution_events: [],
    tool_results: [
      {
        tool_name: "query_ledger_entries",
        ok: true,
        error_code: null,
        error_message: null,
        output: {
          sheet_name: "Grand Livre",
          total_matches: 203,
          page: 1,
          page_size: 20,
          filters: { account: "44585100" },
          returned_columns: [
            "account",
            "amount",
            "currency",
            "period",
            "fiscal_year",
            "document_type",
            "tax_code",
            "vendor",
            "customer",
          ],
          entries: [
            {
              account: "44585100",
              amount: "16250",
              currency: "XOF",
              period: "3",
              fiscal_year: "2024",
              document_type: "KR",
              tax_code: "Sans valeur",
              vendor: "Sans valeur",
              customer: "Sans valeur",
            },
            {
              account: "44585100",
              amount: "21250",
              currency: "XOF",
              period: "2",
              fiscal_year: "2025",
              document_type: "KR",
              tax_code: "Sans valeur",
              vendor: "Sans valeur",
              customer: "Sans valeur",
            },
          ],
          sign_convention: "debit_positive_credit_negative",
        },
      },
    ],
  };
}
