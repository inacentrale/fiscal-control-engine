import type { AgentAttachedFile } from "@/api/agent/types";

export default function AgentPromptStatusBar({
  attachedFile,
  isUploading,
  isPreAnalyzing,
  isResponding,
}: {
  attachedFile: AgentAttachedFile | null;
  isUploading: boolean;
  isPreAnalyzing: boolean;
  isResponding: boolean;
}) {
  const statusLabel = getStatusLabel({
    attachedFile,
    isUploading,
    isPreAnalyzing,
    isResponding,
  });

  return (
    <div className="mt-2 flex min-h-[56px] items-center justify-between gap-4 rounded-b-[30px] rounded-t-[18px] bg-[#c0d4dd] px-4 py-3">
      <div className="flex items-center gap-2">
        <span className="rounded-full bg-[#dce5ea] px-3 py-2 text-[12px] font-semibold text-[#25313a] shadow-[inset_0_1px_0_rgba(255,255,255,0.55)]">
          Fiscal Agent
        </span>
        <span className="rounded-full bg-white/72 px-3 py-2 text-[12px] font-semibold text-[#50606b] shadow-[inset_0_1px_0_rgba(255,255,255,0.75)]">
          {statusLabel}
        </span>
      </div>

      <div className="flex min-w-0 items-center gap-3">
        <p className="hidden truncate text-[12px] font-medium text-[#6d7b86] sm:block">
          {isResponding
            ? "Preparation de la reponse agent..."
            : "En attente d'une question fiscale..."}
        </p>
        <button
          type="button"
          disabled={!isResponding}
          className="cursor-pointer rounded-full bg-[#d4dee4] px-4 py-2 text-[12px] font-semibold text-[#53616b] transition hover:bg-[#c7d3da] disabled:cursor-default disabled:opacity-55"
        >
          Stop
        </button>
      </div>
    </div>
  );
}

function getStatusLabel({
  attachedFile,
  isUploading,
  isPreAnalyzing,
  isResponding,
}: {
  attachedFile: AgentAttachedFile | null;
  isUploading: boolean;
  isPreAnalyzing: boolean;
  isResponding: boolean;
}) {
  if (isUploading) return "Upload";
  if (isPreAnalyzing) return "Pre-analyse";
  if (isResponding) return "Reponse";
  if (attachedFile) return "Pret a questionner";
  return "Pret a recevoir";
}
