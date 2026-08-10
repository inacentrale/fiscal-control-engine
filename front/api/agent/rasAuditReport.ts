import { getApiBase, joinUrl } from "@/api/core/api";
import { ApiError } from "@/utils/api/errors";

import type { AgentRasAuditReportSummary, AgentRunResponse } from "./types";

export type RasAuditReportFormat = "csv" | "json" | "xlsx" | "pdf";

export type RasAuditReportPreviewCase = {
  period: string | null;
  document_reference: string | null;
  account_number: string | null;
  operation_nature: string;
  supplier_reference: string | null;
  status: string;
  priority: string;
  recommended_action: string;
  explanation: string;
  tax_base_amount: string | null;
  rate_percent: string | null;
  expected_amount: string | null;
  recorded_amount: string | null;
  difference: string | null;
  currency: string | null;
  missing_information: string[];
  anomalies: string[];
  legal_references: string[];
};

export type RasAuditReportPreview = {
  auditId: string;
  fileId: string;
  generatedAt: string;
  summary: {
    case_count: number;
    concluded_count: number;
    probable_count: number;
    indeterminate_count: number;
    blocked_count: number;
    error_count: number;
    anomaly_count: number;
    completeness_rate: string;
    amounts: Array<{
      currency: string;
      certainty: string;
      case_count: number;
      expected_amount: string;
      recorded_amount: string;
      difference: string;
    }>;
    top_blockers: Array<{ label: string; count: number }>;
  };
  cases: RasAuditReportPreviewCase[];
  legalReferences: string[];
};

export function extractRasAuditReportSummary(
  response: AgentRunResponse,
  sessionId?: string,
  fileId?: string
): AgentRasAuditReportSummary | null {
  const result = response.tool_results.find(
    (toolResult) =>
      toolResult.tool_name === "generate_ras_audit_report" && toolResult.ok
  );
  const output = result?.output;
  if (!isRasAuditReportOutput(output) || !sessionId || !fileId) return null;

  return {
    auditId: output.audit_id,
    reportId: output.report_id,
    caseCount: output.case_count,
    sessionId,
    fileId,
  };
}

export function getRasAuditReportDownloadUrl(
  auditId: string,
  sessionId: string,
  fileId: string,
  format: RasAuditReportFormat = "csv"
): string {
  const params = new URLSearchParams({ format, session_id: sessionId, file_id: fileId });
  const path = `agent/ras-audits/${encodeURIComponent(auditId)}/report?${params}`;
  return joinUrl(getApiBase(false), path);
}

export function getRasAuditReportPreviewUrl(
  auditId: string,
  sessionId: string,
  fileId: string
): string {
  const params = new URLSearchParams({ session_id: sessionId, file_id: fileId });
  return `/rapports/ras/${encodeURIComponent(auditId)}?${params}`;
}

/**
 * Runs a fresh RAS audit batch on the active file of a session and
 * downloads the resulting report in one call, without going through chat.
 */
export async function runAndDownloadRasAuditReport(
  sessionId: string,
  format: RasAuditReportFormat = "xlsx"
): Promise<void> {
  const path = `agent/sessions/${encodeURIComponent(sessionId)}/ras-audit-report?format=${format}`;
  const response = await fetch(joinUrl(getApiBase(false), path), {
    method: "POST",
    credentials: "include",
  });

  if (!response.ok) {
    throw new ApiError(response.status, await readErrorPayload(response));
  }

  const blob = await response.blob();
  const filename = extractFilename(response.headers.get("content-disposition"))
    ?? `rapport-audit-ras.${format}`;
  triggerBlobDownload(blob, filename);
}

export async function generateRasAuditReportPreview(
  sessionId: string
): Promise<RasAuditReportPreview> {
  const path = `agent/sessions/${encodeURIComponent(sessionId)}/ras-audit-report?format=json&preview=true`;
  const response = await fetch(joinUrl(getApiBase(false), path), {
    method: "POST",
    credentials: "include",
  });
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorPayload(response));
  }
  return parseReportPreview(response, response.headers.get("x-file-id"));
}

export async function getRasAuditReportPreview(
  auditId: string,
  sessionId: string,
  fileId: string
): Promise<RasAuditReportPreview> {
  const response = await fetch(
    `${getRasAuditReportDownloadUrl(auditId, sessionId, fileId, "json")}&preview=true`,
    { credentials: "include" }
  );
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorPayload(response));
  }
  return parseReportPreview(response, fileId);
}

async function parseReportPreview(
  response: Response,
  fileId: string | null
): Promise<RasAuditReportPreview> {
  const auditId = response.headers.get("x-audit-id");
  const payload: unknown = await response.json();
  if (!auditId || !fileId || !isReportPreviewPayload(payload)) {
    throw new ApiError(502, {
      error: { message: "L’aperçu du rapport reçu est invalide." },
    });
  }
  return {
    auditId,
    fileId,
    generatedAt: payload.generated_at,
    summary: payload.summary,
    cases: payload.cases,
    legalReferences: payload.legal_references,
  };
}

function triggerBlobDownload(blob: Blob, filename: string): void {
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
}

function extractFilename(contentDisposition: string | null): string | null {
  if (!contentDisposition) return null;
  const match = /filename="?([^";]+)"?/.exec(contentDisposition);
  return match?.[1] ?? null;
}

async function readErrorPayload(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return { error: { message: "Le rapport d'audit RAS n'a pas pu être généré." } };
  }
}

function isRasAuditReportOutput(output: Record<string, unknown> | undefined): output is {
  audit_id: string;
  report_id: string;
  case_count: number;
} {
  return Boolean(
    output &&
      typeof output.audit_id === "string" &&
      typeof output.report_id === "string" &&
      typeof output.case_count === "number" &&
      Number.isInteger(output.case_count)
  );
}

function isReportPreviewPayload(payload: unknown): payload is {
  generated_at: string;
  summary: RasAuditReportPreview["summary"];
  cases: RasAuditReportPreviewCase[];
  legal_references: string[];
} {
  if (!payload || typeof payload !== "object") return false;
  const value = payload as Record<string, unknown>;
  const summary = value.summary as Record<string, unknown> | undefined;
  return Boolean(
    typeof value.generated_at === "string" &&
      summary &&
      typeof summary.case_count === "number" &&
      typeof summary.completeness_rate === "string" &&
      Array.isArray(value.cases) &&
      Array.isArray(value.legal_references)
  );
}
