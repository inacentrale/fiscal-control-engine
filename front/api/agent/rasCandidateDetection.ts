import type {
  AgentRunResponse,
  RasCandidateDetectionResult,
  RasReviewPeriod,
  RasReviewSummary,
} from "./types";

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
      isNumberRecord(output.missing_fact_counts) &&
      isNumberRecord(output.issue_counts) &&
      (output.ras_review === undefined ||
        parseRasReview(output.ras_review) !== null) &&
      typeof output.decision_status === "string" &&
      (output.semantic_model === null || isRecord(output.semantic_model))
  );
}

function parseRasReview(value: unknown): RasReviewSummary | null {
  if (!isRecord(value) || !Array.isArray(value.periods)) return null;

  const periods = value.periods
    .map(parseRasReviewPeriod)
    .filter((period): period is RasReviewPeriod => period !== null);

  if (periods.length !== value.periods.length) return null;

  const ordered = periods
    .sort((left, right) => periodSortValue(left.period) - periodSortValue(right.period))
    .reduce<RasReviewPeriod[]>((items, period) => {
      const previous = items.at(-1)?.cumulativeCandidateAmount ?? 0;
      items.push({
        ...period,
        cumulativeCandidateAmount: previous + period.candidateAmount,
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

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}
