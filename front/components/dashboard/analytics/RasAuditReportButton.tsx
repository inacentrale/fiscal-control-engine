"use client";

import { useState } from "react";

import { runAndDownloadRasAuditReport } from "@/api/agent/rasAuditReport";
import type { AgentErrorResponse } from "@/api/agent/types";
import useAlertStore, { AlertTypeStatus } from "@/store/alertStore";
import { ApiError } from "@/utils/api/errors";

export default function RasAuditReportButton({
  sessionId,
}: {
  sessionId: string | null;
}) {
  const { setAlert } = useAlertStore();
  const [isDownloading, setIsDownloading] = useState(false);

  const handleClick = async () => {
    if (!sessionId || isDownloading) return;
    setIsDownloading(true);
    try {
      await runAndDownloadRasAuditReport(sessionId, "csv");
    } catch (error) {
      const message =
        error instanceof ApiError
          ? (error.data as AgentErrorResponse | undefined)?.error?.message
          : undefined;
      setAlert({
        content: message || "Le rapport d'audit RAS n'a pas pu être généré.",
        type: AlertTypeStatus.ERROR,
      });
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <button
      className="shrink-0 rounded-full bg-[#102734] px-3 py-1.5 text-[11px] font-semibold text-white transition hover:bg-[#203743] disabled:cursor-not-allowed disabled:opacity-50"
      disabled={!sessionId || isDownloading}
      onClick={handleClick}
      type="button"
    >
      {isDownloading ? "Génération…" : "Télécharger le rapport"}
    </button>
  );
}
