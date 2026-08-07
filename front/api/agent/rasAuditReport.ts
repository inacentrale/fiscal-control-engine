import { getApiBase, joinUrl } from "@/api/core/api";
import { ApiError } from "@/utils/api/errors";

import type { AgentRasAuditReportSummary, AgentRunResponse } from "./types";

export type RasAuditReportFormat = "csv" | "json";

export function extractRasAuditReportSummary(
  response: AgentRunResponse
): AgentRasAuditReportSummary | null {
  const result = response.tool_results.find(
    (toolResult) =>
      toolResult.tool_name === "generate_ras_audit_report" && toolResult.ok
  );
  const output = result?.output;
  if (!isRasAuditReportOutput(output)) return null;

  return {
    auditId: output.audit_id,
    reportId: output.report_id,
    caseCount: output.case_count,
  };
}

export function getRasAuditReportDownloadUrl(
  auditId: string,
  format: RasAuditReportFormat = "csv"
): string {
  const path = `agent/ras-audits/${encodeURIComponent(auditId)}/report?format=${format}`;
  return joinUrl(getApiBase(false), path);
}

/**
 * Runs a fresh RAS audit batch on the active file of a session and
 * downloads the resulting report in one call, without going through chat.
 */
export async function runAndDownloadRasAuditReport(
  sessionId: string,
  format: RasAuditReportFormat = "csv"
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
