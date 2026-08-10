import type { SidebarConversation } from "./aiSidebarData";
import { TrashIcon } from "@/public/assets/icons/icons";

export default function AISidebarConversationItem({
  conversation,
  onSelect,
  onDelete,
  isDeleting = false,
}: {
  conversation: SidebarConversation;
  onSelect: (conversation: SidebarConversation) => void;
  onDelete: (conversation: SidebarConversation) => void;
  isDeleting?: boolean;
}) {
  return (
    <div
      className={[
        "group flex w-full items-center gap-1 rounded-[12px] pr-1 transition",
        conversation.isActive
          ? "bg-[#f7f9fa] text-[#102734]"
          : "text-[#31424c] hover:bg-[#f7f9fa]",
      ].join(" ")}
    >
      <button
        type="button"
        onClick={() => onSelect(conversation)}
        className="flex min-w-0 flex-1 cursor-pointer items-center justify-between gap-3 px-3 py-2.5 text-left"
      >
        <span className="min-w-0">
        <span className="block truncate text-[13px] font-medium">
          {conversation.title}
        </span>
        <span className="mt-0.5 block truncate text-[11px] font-medium text-[#8a98a2]">
          {conversation.status}
        </span>
      </span>
      <span className="shrink-0 text-[11px] font-medium text-[#8a98a2]">
        {conversation.updatedAt}
      </span>
      </button>
      <button
        type="button"
        aria-label={`Supprimer la discussion ${conversation.title}`}
        title="Supprimer la discussion"
        disabled={isDeleting}
        onClick={() => onDelete(conversation)}
        className="flex size-8 shrink-0 cursor-pointer items-center justify-center rounded-lg text-[#8a98a2] opacity-70 transition hover:bg-red-50 hover:text-red-600 focus-visible:opacity-100 disabled:cursor-wait disabled:opacity-40 group-hover:opacity-100"
      >
        <TrashIcon className="size-4" />
      </button>
    </div>
  );
}
