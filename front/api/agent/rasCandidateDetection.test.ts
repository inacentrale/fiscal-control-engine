import { describe, expect, it } from "vitest";

import type { AgentRunResponse } from "./types";
import {
  extractRasCandidateDetectionResult,
  formatRasAmount,
} from "./rasCandidateDetection";

describe("rasCandidateDetection", () => {
  it("extracts a successful RAS candidate detection result", () => {
    const result = extractRasCandidateDetectionResult(buildResponse());

    expect(result?.candidatePieceCount).toBe(611);
    expect(result?.statusCounts.candidate_account_and_text).toBe(59);
    expect(result?.candidateAmountsByCurrency.XOF).toBe("100000");
    expect(result?.rasReview?.periods).toEqual([
      {
        period: "1",
        evaluatedEntryCount: 30,
        candidateEntryCount: 12,
        candidateAmount: 30000,
        cumulativeCandidateAmount: 30000,
        candidateRate: 0.4,
        currency: "XOF",
      },
      {
        period: "2",
        evaluatedEntryCount: 40,
        candidateEntryCount: 18,
        candidateAmount: 70000,
        cumulativeCandidateAmount: 100000,
        candidateRate: 0.45,
        currency: "XOF",
      },
    ]);
  });

  it("rejects malformed tool output", () => {
    const response = buildResponse();
    response.tool_results[0].output.candidate_piece_count = "611";

    expect(extractRasCandidateDetectionResult(response)).toBeNull();
  });

  it("formats RAS amounts by currency", () => {
    expect(formatRasAmount("100000", "XOF")).toBe("100\u00A0k XOF");
  });
});

function buildResponse(): AgentRunResponse {
  return {
    answer: "Candidats détectés.",
    provider_name: "internal",
    model_name: "controlled-response",
    execution_events: [],
    tool_results: [
      {
        tool_name: "detect_ras_candidates",
        ok: true,
        error_code: null,
        error_message: null,
        output: {
          sheet_name: "Sheet1",
          row_count: 2500,
          evaluated_piece_count: 900,
          candidate_piece_count: 611,
          excluded_piece_count: 4,
          rejected_row_count: 0,
          status_counts: {
            candidate_account_and_text: 59,
            candidate_account_only: 540,
            candidate_text_only: 12,
          },
          signal_counts: { services: 82 },
          operation_hint_counts: { service_fees: 90 },
          candidate_amounts_by_currency: { XOF: "100000" },
          missing_fact_counts: { posting_key_side: 3 },
          issue_counts: {},
          ras_review: {
            periods: [
              {
                period: "2",
                evaluated_entry_count: 40,
                candidate_entry_count: 18,
                candidate_amount: "70000",
                candidate_rate: 0.45,
                currency: "XOF",
              },
              {
                period: "1",
                evaluated_entry_count: 30,
                candidate_entry_count: 12,
                candidate_amount: 30000,
                candidate_rate: 0.4,
                currency: "XOF",
              },
            ],
          },
          decision_status: "review_only_no_tax_conclusion",
          semantic_model: null,
        },
      },
    ],
  };
}
