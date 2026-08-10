// @vitest-environment jsdom

import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import RasAuditReportPreviewPage from "./RasAuditReportPreviewPage";

const getPreview = vi.fn().mockResolvedValue({
  auditId: "audit-1",
  fileId: "file-1",
  generatedAt: "2026-08-10T10:00:00+00:00",
  summary: {
    case_count: 43,
    concluded_count: 0,
    probable_count: 16,
    indeterminate_count: 27,
    blocked_count: 43,
    error_count: 0,
    anomaly_count: 43,
    completeness_rate: "0",
    amounts: [],
    top_blockers: [{ label: "Faits juridiques propres au cas", count: 43 }],
  },
  cases: [
    {
      period: "2022-P04",
      document_reference: "PIECE-ABC",
      account_number: "61312000",
      operation_nature: "Location",
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
      currency: null,
      missing_information: ["Statut IFU"],
      anomalies: [],
      legal_references: [],
    },
  ],
  legalReferences: [],
});

vi.mock("@/api/agent/rasAuditReport", () => ({
  getRasAuditReportPreview: (...args: unknown[]) => getPreview(...args),
  getRasAuditReportDownloadUrl: (
    _auditId: string,
    _sessionId: string,
    _fileId: string,
    format: string
  ) => `/report.${format}`,
}));

describe("RasAuditReportPreviewPage", () => {
  it("shows the full report preview and download formats on a dedicated page", async () => {
    render(
      <RasAuditReportPreviewPage
        auditId="audit-1"
        fileId="file-1"
        sessionId="session-1"
      />
    );

    await waitFor(() => expect(screen.getAllByText("PIECE-ABC").length).toBeGreaterThan(0));
    expect(screen.getAllByText("43", { selector: "p" }).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Location").length).toBeGreaterThan(0);
    expect(screen.getByText("Télécharger Excel").getAttribute("href")).toBe(
      "/report.xlsx"
    );
    expect(screen.getByText("Télécharger PDF").getAttribute("href")).toBe(
      "/report.pdf"
    );
    expect(screen.queryByText("Télécharger CSV")).toBeNull();
    expect(screen.queryByText("Télécharger JSON")).toBeNull();
    expect(getPreview).toHaveBeenCalledWith("audit-1", "session-1", "file-1");
  });
});
