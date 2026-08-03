import type { SidebarConversation } from "./aiSidebarData";

export default function AISidebarConversationItem({
  conversation,
  onSelect,
}: {
  conversation: SidebarConversation;
  onSelect: (conversation: SidebarConversation) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onSelect(conversation)}
      className={[
        "flex w-full cursor-pointer items-center justify-between gap-3 rounded-[12px] px-3 py-2.5 text-left transition",
        conversation.isActive
          ? "bg-[#f7f9fa] text-[#102734]"
          : "text-[#31424c] hover:bg-[#f7f9fa]",
      ].join(" ")}
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
  );
}
