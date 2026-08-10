import type {
  AgentRunResponse,
  RasCandidateDetectionResult,
  RasCandidateReviewCase,
  RasReviewPeriod,
  RasReviewSummary,
} from "./types";

export function isLabelDetectedReviewCase(
  reviewCase: RasCandidateReviewCase
): boolean {
  return (
    reviewCase.detectionStatus === "candidate_text_only" ||
    reviewCase.missingFacts.includes("strong_semantic_signal")
  );
}

export function extractRasCandidateDetectionResult(
  response: AgentRunResponse
): RasCandidateDetectionResult | null {
  const result = response.tool_results.find(
    (toolResult) =>
      toolResult.tool_name === "detect_ras_candidates" && toolResult.ok
  );
  const output = result?.output;
  if (!isRasCandidateOutput(output)) return null;

  return {
    sheetName: output.sheet_name,
    rowCount: output.row_count,
    evaluatedPieceCount: output.evaluated_piece_count,
    candidatePieceCount: output.candidate_piece_count,
    excludedPieceCount: output.excluded_piece_count,
    rejectedRowCount: output.rejected_row_count,
    statusCounts: output.status_counts,
    signalCounts: output.signal_counts,
    operationHintCounts: output.operation_hint_counts,
    candidateAmountsByCurrency: output.candidate_amounts_by_currency,
    candidateAccounts: output.candidate_accounts.map((account) => ({
      accountNumber: account.account_number,
      candidatePieceCount: account.candidate_piece_count,
      amountsByCurrency: account.amounts_by_currency,
      statusCounts: account.status_counts,
      signalCounts: account.signal_counts,
    })),
    reviewCases: output.review_cases.map((reviewCase) => ({
      candidateId: reviewCase.candidate_id,
      priority: reviewCase.priority,
      documentNumber: reviewCase.document_number,
      postingDate: reviewCase.posting_date,
      fiscalYear: reviewCase.fiscal_year,
      period: reviewCase.period,
      accountNumbers: reviewCase.account_numbers,
      label: reviewCase.label,
      amountsByCurrency: reviewCase.amounts_by_currency,
      detectionStatus: reviewCase.detection_status,
      signalIds: reviewCase.signal_ids,
      operationHints: reviewCase.operation_hints,
      counterpartStatus: reviewCase.counterpart_status,
      recordedRasAmountsByCurrency:
        reviewCase.recorded_ras_amounts_by_currency,
      missingFacts: reviewCase.missing_facts,
      issues: reviewCase.issues,
      recommendedAction: reviewCase.recommended_action,
    })),
    sourceScopeComplete: output.source_scope_complete,
    sourceScopeBlockers: output.source_scope_blockers,
    missingFactCounts: output.missing_fact_counts,
    issueCounts: output.issue_counts,
    rasReview: parseRasReview(output.ras_review),
    decisionStatus: output.decision_status,
    semanticModel: output.semantic_model,
  };
}

export function formatRasAmount(value: string, currency: string): string {
  const amount = Number(value);
  const formatted = Number.isFinite(amount)
    ? new Intl.NumberFormat("fr-FR", {
        notation: Math.abs(amount) >= 100_000 ? "compact" : "standard",
        maximumFractionDigits: Math.abs(amount) >= 100_000 ? 1 : 0,
      }).format(amount)
    : value;
  return `${formatted} ${currency}`;
}

function isRasCandidateOutput(
  output: Record<string, unknown> | undefined
): output is {
  sheet_name: string;
  row_count: number;
  evaluated_piece_count: number;
  candidate_piece_count: number;
  excluded_piece_count: number;
  rejected_row_count: number;
  status_counts: Record<string, number>;
  signal_counts: Record<string, number>;
  operation_hint_counts: Record<string, number>;
  candidate_amounts_by_currency: Record<string, string>;
  candidate_accounts: Array<{
    account_number: string;
    candidate_piece_count: number;
    amounts_by_currency: Record<string, string>;
    status_counts: Record<string, number>;
    signal_counts: Record<string, number>;
  }>;
  review_cases: RasCandidateReviewCaseOutput[];
  source_scope_complete: boolean;
  source_scope_blockers: string[];
  missing_fact_counts: Record<string, number>;
  issue_counts: Record<string, number>;
  ras_review?: unknown;
  decision_status: string;
  semantic_model: Record<string, unknown> | null;
} {
  return Boolean(
    output &&
      typeof output.sheet_name === "string" &&
      isInteger(output.row_count) &&
      isInteger(output.evaluated_piece_count) &&
      isInteger(output.candidate_piece_count) &&
      isInteger(output.excluded_piece_count) &&
      isInteger(output.rejected_row_count) &&
      isNumberRecord(output.status_counts) &&
      isNumberRecord(output.signal_counts) &&
      isNumberRecord(output.operation_hint_counts) &&
      isStringRecord(output.candidate_amounts_by_currency) &&
      isCandidateAccountArray(output.candidate_accounts) &&
      isCandidateReviewCaseArray(output.review_cases) &&
      typeof output.source_scope_complete === "boolean" &&
      isStringArray(output.source_scope_blockers) &&
      isNumberRecord(output.missing_fact_counts) &&
      isNumberRecord(output.issue_counts) &&
      (output.ras_review === undefined ||
        parseRasReview(output.ras_review) !== null) &&
      typeof output.decision_status === "string" &&
      (output.semantic_model === null || isRecord(output.semantic_model))
  );
}

type RasCandidateReviewCaseOutput = {
  candidate_id: string;
  priority: "high" | "medium" | "low";
  document_number: string | null;
  posting_date: string | null;
  fiscal_year: number | null;
  period: number | null;
  account_numbers: string[];
  label: string | null;
  amounts_by_currency: Record<string, string>;
  detection_status: string;
  signal_ids: string[];
  operation_hints: string[];
  counterpart_status: string;
  recorded_ras_amounts_by_currency: Record<string, string>;
  missing_facts: string[];
  issues: string[];
  recommended_action: string;
};

function isCandidateReviewCaseArray(
  value: unknown
): value is RasCandidateReviewCaseOutput[] {
  return (
    Array.isArray(value) &&
    value.every(
      (item) =>
        isRecord(item) &&
        typeof item.candidate_id === "string" &&
        ["high", "medium", "low"].includes(String(item.priority)) &&
        isNullableString(item.document_number) &&
        isNullableString(item.posting_date) &&
        isNullableInteger(item.fiscal_year) &&
        isNullableInteger(item.period) &&
        isStringArray(item.account_numbers) &&
        isNullableString(item.label) &&
        isStringRecord(item.amounts_by_currency) &&
        typeof item.detection_status === "string" &&
        isStringArray(item.signal_ids) &&
        isStringArray(item.operation_hints) &&
        typeof item.counterpart_status === "string" &&
        isStringRecord(item.recorded_ras_amounts_by_currency) &&
        isStringArray(item.missing_facts) &&
        isStringArray(item.issues) &&
        typeof item.recommended_action === "string"
    )
  );
}

function isCandidateAccountArray(value: unknown): value is Array<{
  account_number: string;
  candidate_piece_count: number;
  amounts_by_currency: Record<string, string>;
  status_counts: Record<string, number>;
  signal_counts: Record<string, number>;
}> {
  return (
    Array.isArray(value) &&
    value.every(
      (item) =>
        isRecord(item) &&
        typeof item.account_number === "string" &&
        isInteger(item.candidate_piece_count) &&
        isStringRecord(item.amounts_by_currency) &&
        isNumberRecord(item.status_counts) &&
        isNumberRecord(item.signal_counts)
    )
  );
}

function parseRasReview(value: unknown): RasReviewSummary | null {
  if (!isRecord(value) || !Array.isArray(value.periods)) return null;

  const periods = value.periods
    .map(parseRasReviewPeriod)
    .filter((period): period is RasReviewPeriod => period !== null);

  if (periods.length !== value.periods.length) return null;

  const cumulativeByCurrency = new Map<string, number>();
  const ordered = periods
    .sort((left, right) => periodSortValue(left.period) - periodSortValue(right.period))
    .reduce<RasReviewPeriod[]>((items, period) => {
      const currencyKey = period.currency ?? "currency-unavailable";
      const previous = cumulativeByCurrency.get(currencyKey) ?? 0;
      const cumulativeCandidateAmount = previous + period.candidateAmount;
      cumulativeByCurrency.set(currencyKey, cumulativeCandidateAmount);
      items.push({
        ...period,
        cumulativeCandidateAmount,
      });
      return items;
    }, []);

  return { periods: ordered };
}

function parseRasReviewPeriod(value: unknown): RasReviewPeriod | null {
  if (!isRecord(value)) return null;

  const period = firstString(value, ["period", "periode", "label"]);
  const candidateEntryCount = firstNumber(value, [
    "candidate_entry_count",
    "candidateEntryCount",
    "candidate_count",
    "candidateCount",
    "entry_count",
    "entryCount",
  ]);
  const candidateAmount = firstNumber(value, [
    "candidate_amount",
    "candidateAmount",
    "amount",
    "amount_sum",
    "amountSum",
  ]);
  const evaluatedEntryCount =
    firstNumber(value, [
      "evaluated_entry_count",
      "evaluatedEntryCount",
      "evaluated_count",
      "evaluatedCount",
    ]) ?? candidateEntryCount;
  const candidateRate =
    firstNumber(value, [
      "candidate_rate",
      "candidateRate",
      "rate",
    ]) ?? 0;
  const currency = firstString(value, ["currency", "devise"]);

  if (!period || candidateEntryCount === null || candidateAmount === null) {
    return null;
  }

  return {
    period,
    evaluatedEntryCount: evaluatedEntryCount ?? candidateEntryCount,
    candidateEntryCount,
    candidateAmount,
    cumulativeCandidateAmount: candidateAmount,
    candidateRate,
    currency,
  };
}

function firstString(
  record: Record<string, unknown>,
  keys: string[]
): string | null {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "string" && value.trim()) return value.trim();
    if (typeof value === "number" && Number.isFinite(value)) return String(value);
  }
  return null;
}

function firstNumber(
  record: Record<string, unknown>,
  keys: string[]
): number | null {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "number" && Number.isFinite(value)) return value;
    if (typeof value === "string" && value.trim()) {
      const parsed = Number(value);
      if (Number.isFinite(parsed)) return parsed;
    }
  }
  return null;
}

function periodSortValue(period: string): number {
  const parsed = Number(period);
  return Number.isFinite(parsed) ? parsed : Number.MAX_SAFE_INTEGER;
}

function isInteger(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value);
}

function isNumberRecord(value: unknown): value is Record<string, number> {
  return (
    isRecord(value) &&
    Object.values(value).every((item) => typeof item === "number")
  );
}

function isStringRecord(value: unknown): value is Record<string, string> {
  return (
    isRecord(value) &&
    Object.values(value).every((item) => typeof item === "string")
  );
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function isNullableString(value: unknown): value is string | null {
  return value === null || typeof value === "string";
}

function isNullableInteger(value: unknown): value is number | null {
  return value === null || isInteger(value);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}
