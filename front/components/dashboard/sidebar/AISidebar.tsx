"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import {
  agentSidebarQueryKeys,
  listAgentConversations,
  listAgentFiles,
} from "@/api/agent/sidebar";
import type { AgentSidebarConversation, AgentSidebarFile } from "@/api/agent/types";
import useAgentWorkspaceStore from "@/store/agentWorkspaceStore";
import { ChevronRightIcon } from "@/public/assets/icons/AgentInputIcons";
import { SearchZoomIcon } from "@/public/assets/icons/icons";
import { AddSquareIcon, CategoryIcon } from "@/public/assets/icons/SideBarIcons";

import AISidebarConversationItem from "./AISidebarConversationItem";
import AISidebarModal, { type AISidebarModalMode } from "./AISidebarModal";
import AISidebarProfile from "./AISidebarProfile";
import type { SidebarConversation, SidebarFile } from "./aiSidebarData";

export default function AISidebar() {
  const [isRecentExpanded, setIsRecentExpanded] = useState(false);
  const [modalMode, setModalMode] = useState<AISidebarModalMode | null>(null);
  const activeRunId = useAgentWorkspaceStore((state) => state.activeRunId);
  const selectConversation = useAgentWorkspaceStore(
    (state) => state.selectConversation
  );
  const startNewChat = useAgentWorkspaceStore((state) => state.startNewChat);
  const conversationsQuery = useQuery({
    queryKey: agentSidebarQueryKeys.conversations,
    queryFn: () => listAgentConversations(20),
  });
  const filesQuery = useQuery({
    queryKey: agentSidebarQueryKeys.files,
    queryFn: () => listAgentFiles(20),
  });

  const sidebarConversations = (conversationsQuery.data?.items ?? []).map(
    (conversation) => toSidebarConversation(conversation, activeRunId)
  );
  const sidebarFiles = (filesQuery.data?.items ?? []).map(toSidebarFile);

  const visibleConversations = isRecentExpanded
    ? sidebarConversations
    : sidebarConversations.slice(0, 3);
  const hiddenCount = sidebarConversations.length - visibleConversations.length;

  return (
    <>
      <div className="flex min-h-full flex-col justify-between gap-7 text-[#102734]">
        <div className="min-h-0 space-y-7">
          <div className="space-y-1.5">
            <button
              type="button"
              onClick={startNewChat}
              className="flex h-11 w-full cursor-pointer items-center gap-3 rounded-[17px] bg-[#f5f8fa] px-3.5 text-left text-[14px] font-medium text-[#102734] shadow-[inset_0_1px_0_rgba(255,255,255,0.75)] transition hover:bg-[#edf4f7]"
            >
              <AddSquareIcon className="size-[18px] shrink-0 text-[#40515c]" />
              Nouveau chat
            </button>
            <button
              type="button"
              onClick={() => setModalMode("files")}
              className="flex h-10 w-full cursor-pointer items-center gap-3 rounded-[12px] px-3.5 text-left text-[14px] font-medium text-[#203743] transition hover:bg-[#f7f9fa]"
            >
              <CategoryIcon className="size-[18px] shrink-0 text-[#667781]" />
              Fichiers
            </button>
            <button
              type="button"
              onClick={() => setModalMode("search")}
              className="flex h-10 w-full cursor-pointer items-center gap-3 rounded-[12px] px-3.5 text-left text-[14px] font-medium text-[#203743] transition hover:bg-[#f7f9fa]"
            >
              <SearchZoomIcon className="size-[18px] shrink-0 text-[#667781]" />
              Rechercher
            </button>
          </div>

          <section className="space-y-2">
            <button
              type="button"
              onClick={() => setIsRecentExpanded((current) => !current)}
              className="flex h-8 w-full cursor-pointer items-center justify-between rounded-[10px] px-3 text-left text-[12px] font-semibold text-[#31424c] transition hover:bg-[#f7f9fa]"
            >
              <span>Récents</span>
              <ChevronRightIcon
                className={[
                  "size-3.5 text-[#8a98a2] transition-transform",
                  isRecentExpanded ? "rotate-90" : "",
                ].join(" ")}
              />
            </button>
            <div className="space-y-1">
              {conversationsQuery.isLoading &&
                Array.from({ length: 3 }).map((_, index) => (
                  <AISidebarSkeletonRow key={index} />
                ))}
              {!conversationsQuery.isLoading &&
                visibleConversations.map((conversation) => (
                  <AISidebarConversationItem
                    key={conversation.id}
                    conversation={conversation}
                    onSelect={(selectedConversation) =>
                      selectConversation({
                        runId: selectedConversation.id,
                        sessionId: selectedConversation.sessionId,
                        fileId: selectedConversation.fileId,
                      })
                    }
                  />
                ))}
              {!conversationsQuery.isLoading &&
                !conversationsQuery.isError &&
                sidebarConversations.length === 0 && (
                  <p className="px-3 py-2 text-[12px] font-medium text-[#8a98a2]">
                    Aucun échange enregistré.
                  </p>
                )}
              {conversationsQuery.isError && (
                <p className="px-3 py-2 text-[12px] text-red-600">
                  Historique indisponible.
                </p>
              )}
            </div>
            {!conversationsQuery.isLoading && !isRecentExpanded && hiddenCount > 0 && (
              <button
                type="button"
                onClick={() => setIsRecentExpanded(true)}
                className="h-8 w-full cursor-pointer rounded-[10px] px-3 text-left text-[12px] font-medium text-[#8a98a2] transition hover:bg-[#f7f9fa]"
              >
                Afficher {hiddenCount} ancien{hiddenCount > 1 ? "s" : ""}
              </button>
            )}
          </section>
        </div>

        <AISidebarProfile />
      </div>
      {modalMode && (
        <AISidebarModal
          mode={modalMode}
          conversations={sidebarConversations}
          files={sidebarFiles}
          isConversationLoading={conversationsQuery.isLoading}
          hasConversationError={conversationsQuery.isError}
          isFileLoading={filesQuery.isLoading}
          hasFileError={filesQuery.isError}
          onClose={() => setModalMode(null)}
        />
      )}
    </>
  );
}

function AISidebarSkeletonRow() {
  return (
    <div className="rounded-[12px] px-3 py-2.5">
      <div className="h-3.5 w-3/4 animate-pulse rounded-full bg-[#edf4f7]" />
      <div className="mt-2 h-2.5 w-1/2 animate-pulse rounded-full bg-[#f5f8fa]" />
    </div>
  );
}

function toSidebarConversation(
  conversation: AgentSidebarConversation,
  activeRunId: string | null
): SidebarConversation {
  return {
    id: conversation.run_id,
    title: conversation.title,
    status: conversation.status,
    updatedAt: formatRelativeDate(conversation.created_at),
    sessionId: conversation.session_id,
    fileId: conversation.file_id,
    isActive: conversation.run_id === activeRunId,
  };
}

function toSidebarFile(file: AgentSidebarFile): SidebarFile {
  const sheetCount = file.sheet_names.length;
  const fileSize = file.file_size_bytes ? formatCompactFileSize(file.file_size_bytes) : null;
  return {
    id: file.file_id,
    sessionId: file.session_id,
    filename: file.original_filename,
    meta: [
      fileSize,
      sheetCount > 0 ? `${sheetCount} feuille${sheetCount > 1 ? "s" : ""}` : null,
    ]
      .filter(Boolean)
      .join(" · "),
  };
}

function formatRelativeDate(value: string): string {
  const timestamp = new Date(value).getTime();
  if (Number.isNaN(timestamp)) return "";
  const diffSeconds = Math.max(0, Math.round((Date.now() - timestamp) / 1000));
  if (diffSeconds < 60) return "Maintenant";
  const diffMinutes = Math.round(diffSeconds / 60);
  if (diffMinutes < 60) return `${diffMinutes} min`;
  const diffHours = Math.round(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours} h`;
  const diffDays = Math.round(diffHours / 24);
  if (diffDays < 7) return `${diffDays} j`;
  return new Intl.DateTimeFormat("fr-FR", {
    day: "2-digit",
    month: "short",
  }).format(new Date(value));
}

function formatCompactFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} Ko`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
}
