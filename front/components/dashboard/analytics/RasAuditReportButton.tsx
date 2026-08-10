"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import {
  generateRasAuditReportPreview,
  getRasAuditReportPreviewUrl,
} from "@/api/agent/rasAuditReport";
import type { AgentErrorResponse } from "@/api/agent/types";
import useAlertStore, { AlertTypeStatus } from "@/store/alertStore";
import { ApiError } from "@/utils/api/errors";

export default function RasAuditReportButton({
  sessionId,
}: {
  sessionId: string | null;
}) {
  const { setAlert } = useAlertStore();
  const router = useRouter();
  const [isGenerating, setIsGenerating] = useState(false);

  const handleClick = async () => {
    if (!sessionId || isGenerating) return;
    setIsGenerating(true);
    try {
      const preview = await generateRasAuditReportPreview(sessionId);
      router.push(
        getRasAuditReportPreviewUrl(
          preview.auditId,
          sessionId,
          preview.fileId
        )
      );
    } catch (error) {
      const message =
        error instanceof ApiError
          ? (error.data as AgentErrorResponse | undefined)?.error?.message
          : undefined;
      setAlert({
        content: message || "L’aperçu du rapport d’audit RAS est indisponible.",
        type: AlertTypeStatus.ERROR,
      });
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <button
        className="shrink-0 rounded-full bg-[#102734] px-3 py-1.5 text-[11px] font-semibold text-white transition hover:bg-[#203743] disabled:cursor-not-allowed disabled:opacity-50"
        disabled={!sessionId || isGenerating}
        onClick={handleClick}
        type="button"
      >
        {isGenerating ? "Préparation…" : "Prévisualiser le rapport"}
    </button>
  );
}
