import type { AgentAttachedFile } from "@/api/agent/types";
import { CloseIcon } from "@/public/assets/icons/icons";
import { DocumentTextIcon } from "@/public/assets/icons/AgentInputIcons";
import { formatFileSize } from "@/utils/ui/files";

export default function AgentFileCard({
  attachedFile,
  onRemoveFile,
}: {
  attachedFile: AgentAttachedFile;
  onRemoveFile?: () => void;
}) {
  const fileMeta = `${formatFileSize(attachedFile.sizeBytes)} · ${
    attachedFile.sheetNames.length
  } feuille(s)`;
  const content = (
    <>
      <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-white text-[#40515c] shadow-[inset_0_0_0_1px_rgba(64,81,92,0.08)]">
        <DocumentTextIcon className="size-5" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-[13px] font-semibold text-[#102734]">
          {attachedFile.filename}
        </span>
        <span className="mt-0.5 block text-[12px] font-medium text-[#667781]">
          Excel · {fileMeta}
        </span>
      </span>
      {attachedFile.previewUrl && (
        <span className="shrink-0 rounded-full bg-white px-3 py-1.5 text-[12px] font-semibold text-[#40515c]">
          Ouvrir
        </span>
      )}
    </>
  );

  return (
    <div className="flex max-w-[360px] items-center gap-2 rounded-2xl bg-[#edf4f7] p-2 text-[#31424c]">
      {attachedFile.previewUrl ? (
        <a
          href={attachedFile.previewUrl}
          target="_blank"
          rel="noreferrer"
          title={`Ouvrir ${attachedFile.filename}`}
          className="flex min-w-0 flex-1 cursor-pointer items-center gap-3"
        >
          {content}
        </a>
      ) : (
        <div className="flex min-w-0 flex-1 items-center gap-3">{content}</div>
      )}
      {onRemoveFile && (
        <button
          type="button"
          aria-label="Retirer le fichier"
          onClick={onRemoveFile}
          className="flex size-7 shrink-0 cursor-pointer items-center justify-center rounded-full text-[#31424c]/60 transition hover:bg-black/[0.06] hover:text-[#31424c]"
        >
          <CloseIcon className="size-3" />
        </button>
      )}
    </div>
  );
}
