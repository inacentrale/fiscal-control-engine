import { DocumentTextIcon } from "@/public/assets/icons/AgentInputIcons";

import type { SidebarFile } from "./aiSidebarData";

export default function AISidebarFileItem({
  file,
  onSelect,
}: {
  file: SidebarFile;
  onSelect: (file: SidebarFile) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onSelect(file)}
      className="group flex w-full cursor-pointer items-center gap-3 rounded-[14px] px-3 py-2.5 text-left text-[#40515c] transition hover:bg-[#f5f8fa]"
    >
      <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-[#edf4f7] text-[#40515c] transition group-hover:bg-white">
        <DocumentTextIcon className="size-4" />
      </span>
      <span className="min-w-0">
        <span className="block truncate text-[13px] font-semibold text-[#203743]">
          {file.filename}
        </span>
        <span className="mt-0.5 block text-[11px] font-medium text-[#8a98a2]">
          {file.meta}
        </span>
      </span>
    </button>
  );
}
