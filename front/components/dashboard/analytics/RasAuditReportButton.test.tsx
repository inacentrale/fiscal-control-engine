// @vitest-environment jsdom

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import RasAuditReportButton from "./RasAuditReportButton";

const generatePreview = vi.fn().mockResolvedValue({
  auditId: "audit-1",
  fileId: "file-1",
  generatedAt: "2026-08-10T10:00:00+00:00",
  summary: {
    case_count: 2,
    concluded_count: 1,
    probable_count: 0,
    indeterminate_count: 1,
    blocked_count: 1,
    error_count: 0,
    anomaly_count: 1,
    completeness_rate: "0.5",
    amounts: [],
    top_blockers: [],
  },
  cases: [
    {
      period: "2026-P01",
      document_reference: "PIECE-ABC",
      account_number: "61365000",
      operation_nature: "Honoraires",
      supplier_reference: "Tiers-ABC",
      status: "Données manquantes",
      priority: "Moyenne",
      recommended_action: "Compléter les informations manquantes",
      explanation: "Des faits sont absents.",
      tax_base_amount: null,
      rate_percent: null,
      expected_amount: null,
      recorded_amount: null,
      difference: null,
      currency: "XOF",
      missing_information: ["Statut IFU"],
      anomalies: [],
      legal_references: [],
    },
  ],
  legalReferences: [],
});
const push = vi.fn();

vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

vi.mock("@/api/agent/rasAuditReport", () => ({
  generateRasAuditReportPreview: (...args: unknown[]) => generatePreview(...args),
  getRasAuditReportDownloadUrl: (
    _auditId: string,
    _sessionId: string,
    _fileId: string,
    format: string
  ) => `/report.${format}`,
  getRasAuditReportPreviewUrl: () => "/rapports/ras/audit-1?session_id=session-1&file_id=file-1",
}));

describe("RasAuditReportButton", () => {
  it("opens the dedicated preview page after generating the report", async () => {
    render(<RasAuditReportButton sessionId="session-1" />);

    fireEvent.click(screen.getByRole("button", { name: "Prévisualiser le rapport" }));

    await waitFor(() =>
      expect(push).toHaveBeenCalledWith(
        "/rapports/ras/audit-1?session_id=session-1&file_id=file-1"
      )
    );
    expect(generatePreview).toHaveBeenCalledWith("session-1");
  });
});
