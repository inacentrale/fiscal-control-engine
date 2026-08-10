import { afterEach, describe, expect, it, vi } from "vitest";

import { generateRasAuditReportPreview } from "./rasAuditReport";

describe("generateRasAuditReportPreview", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("returns the business preview and scoped download identifiers", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          generated_at: "2026-08-10T10:00:00+00:00",
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
          cases: [],
          legal_references: ["CGI, article 207"],
        }),
        {
          status: 200,
          headers: { "X-Audit-ID": "audit-1", "X-File-ID": "file-1" },
        }
      )
    );
    vi.stubGlobal("fetch", fetchMock);

    const preview = await generateRasAuditReportPreview("session-1");

    expect(preview.auditId).toBe("audit-1");
    expect(preview.fileId).toBe("file-1");
    expect(preview.summary.case_count).toBe(2);
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining(
        "agent/sessions/session-1/ras-audit-report?format=json&preview=true"
      ),
      expect.objectContaining({ method: "POST" })
    );
  });

  it("rejects a preview without scoped identifiers", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            generated_at: "2026-08-10T10:00:00+00:00",
            summary: { case_count: 1, completeness_rate: "0" },
            cases: [],
            legal_references: [],
          }),
          { status: 200 }
        )
      )
    );

    await expect(generateRasAuditReportPreview("session-1")).rejects.toThrow();
  });
});
