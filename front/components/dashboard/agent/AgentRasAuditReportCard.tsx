import type { AgentRasAuditReportSummary } from "@/api/agent/types";
import { getRasAuditReportDownloadUrl } from "@/api/agent/rasAuditReport";

export default function AgentRasAuditReportCard({
  report,
}: {
  report: AgentRasAuditReportSummary;
}) {
  return (
    <section className="overflow-hidden rounded-xl border border-[#dfe7eb] bg-white">
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
        <div>
          <h3 className="font-semibold text-[#203743]">Rapport d’audit RAS</h3>
          <p className="text-sm text-[#607783]">
            {report.caseCount.toLocaleString("fr-FR")} candidat
            {report.caseCount > 1 ? "s" : ""} · audit {report.auditId}
          </p>
        </div>
        <div className="flex shrink-0 gap-2">
          <a
            className="rounded-lg bg-[#102734] px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-[#203743]"
            download
            href={getRasAuditReportDownloadUrl(report.auditId, "csv")}
          >
            Télécharger (CSV)
          </a>
          <a
            className="rounded-lg border border-[#dfe7eb] px-3 py-1.5 text-xs font-semibold text-[#43606d] transition hover:bg-[#f7f9fa]"
            download
            href={getRasAuditReportDownloadUrl(report.auditId, "json")}
          >
            Télécharger (JSON)
          </a>
        </div>
      </div>
    </section>
  );
}
