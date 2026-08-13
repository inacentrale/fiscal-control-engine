"use client";

import { useRouter } from "next/navigation";

import { getRasAuditReportPreviewUrl } from "@/api/agent/rasAuditReport";
import type { AgentRasAuditReportSummary } from "@/api/agent/types";

export default function AgentRasAuditReportCard({
  report,
}: {
  report: AgentRasAuditReportSummary;
}) {
  const router = useRouter();

  return (
    <section className="overflow-hidden rounded-xl border border-[#dfe7eb] bg-white">
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
        <div>
          <h3 className="font-semibold text-[#203743]">Rapport d’audit RAS</h3>
          <p className="text-sm text-[#607783]">
            {report.caseCount.toLocaleString("fr-FR")} dossier
            {report.caseCount > 1 ? "s" : ""} analysé
            {report.caseCount > 1 ? "s" : ""}
          </p>
        </div>
        <button
          className="rounded-lg bg-[#C20831] px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-[#9E0627] disabled:opacity-50"
          onClick={() =>
            router.push(
              getRasAuditReportPreviewUrl(
                report.auditId,
                report.sessionId,
                report.fileId
              )
            )
          }
          type="button"
        >
          Ouvrir l’aperçu du rapport
        </button>
      </div>
    </section>
  );
}
