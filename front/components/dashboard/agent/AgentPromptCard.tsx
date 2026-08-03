"use client";

import { useState, type RefObject } from "react";

import type { AgentAttachedFile } from "@/api/agent/types";
import { PlusIcon } from "@/public/assets/icons/icons";
import {
  ArrowUpIcon,
  GlobalIcon,
  ScannerIcon,
  SlidersIcon,
} from "@/public/assets/icons/AgentInputIcons";
import {
  AGENT_UPLOAD_ACCEPTED_EXTENSIONS,
  useAgentFileUpload,
} from "@/hooks/useAgentFileUpload";
import { formatFileSize } from "@/utils/ui/files";

import AgentConversation from "./AgentConversation";
import AgentFileSummary from "./AgentFileSummary";
import AgentPromptStatusBar from "./AgentPromptStatusBar";
import AgentToolbarButton from "./AgentToolbarButton";

const placeholder =
  "Demandez a l'agent d'analyser un compte, une ecriture ou une retenue a la source...";

export default function AgentPromptCard({
  scrollContainerRef,
}: {
  scrollContainerRef?: RefObject<HTMLElement | null>;
}) {
  const [prompt, setPrompt] = useState("");
  const {
    attachedFile,
    pendingFile,
    isUploading,
    isPreAnalyzing,
    isResponding,
    isRestoring,
    uploadError,
    preAnalysisError,
    messages,
    addFile,
    removeFile,
    submitPrompt,
  } = useAgentFileUpload();

  const canSubmit =
    Boolean(prompt.trim()) &&
    !isUploading &&
    !isPreAnalyzing &&
    !isRestoring &&
    !isResponding;
  const hasWorkspaceContent =
    Boolean(attachedFile) ||
    Boolean(pendingFile) ||
    Boolean(uploadError) ||
    Boolean(preAnalysisError) ||
    messages.length > 0 ||
    isUploading ||
    isPreAnalyzing ||
    isRestoring ||
    isResponding;

  const handleSubmit = () => {
    if (!canSubmit) return;
    submitPrompt(prompt);
    setPrompt("");
  };

  return (
    <div
      className={`flex min-h-full w-full max-w-[640px] flex-col gap-6 ${
        hasWorkspaceContent ? "justify-between" : "justify-center"
      }`}
    >
      <AgentConversation
        messages={messages}
        scrollContainerRef={scrollContainerRef}
      />
      <div
        className={`z-10 bg-white pb-0 pt-4 ${
          hasWorkspaceContent ? "sticky bottom-0 mt-auto" : ""
        }`}
      >
        <AgentPromptShell>
          <AgentPromptInput
            attachedFile={attachedFile}
            pendingFile={pendingFile}
            isUploading={isUploading}
            isPreAnalyzing={isPreAnalyzing}
            isRestoring={isRestoring}
            uploadError={uploadError}
            preAnalysisError={preAnalysisError}
            prompt={prompt}
            canSubmit={canSubmit}
            onPromptChange={setPrompt}
            onAddFile={addFile}
            onRemoveFile={removeFile}
            onSubmit={handleSubmit}
          />
          <AgentPromptStatusBar
            attachedFile={attachedFile}
            isUploading={isUploading}
            isPreAnalyzing={isPreAnalyzing}
            isResponding={isResponding}
          />
        </AgentPromptShell>
      </div>
    </div>
  );
}

function AgentPromptShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="overflow-hidden rounded-[40px] border-[6px] border-[#deebf1] bg-[#deebf1] shadow-[0_24px_54px_rgba(86,105,118,0.12)]">
      {children}
    </div>
  );
}

function AgentPromptInput({
  attachedFile,
  pendingFile,
  isUploading,
  isPreAnalyzing,
  isRestoring,
  uploadError,
  preAnalysisError,
  prompt,
  canSubmit,
  onPromptChange,
  onAddFile,
  onRemoveFile,
  onSubmit,
}: {
  attachedFile: AgentAttachedFile | null;
  pendingFile: { filename: string; sizeBytes: number } | null;
  isUploading: boolean;
  isPreAnalyzing: boolean;
  isRestoring: boolean;
  uploadError: string | null;
  preAnalysisError: string | null;
  prompt: string;
  canSubmit: boolean;
  onPromptChange: (value: string) => void;
  onAddFile: (file: File) => void;
  onRemoveFile: () => void;
  onSubmit: () => void;
}) {
  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (file) {
      onAddFile(file);
    }
  };

  return (
    <div className="rounded-b-[18px] rounded-t-[25px] bg-white px-5 pb-4 pt-5">
      <label className="block">
        <span className="sr-only">Prompt Fiscal Agent</span>
        <textarea
          rows={2}
          value={prompt}
          placeholder={placeholder}
          onChange={(event) => onPromptChange(event.target.value)}
          className="block min-h-[60px] w-full resize-none bg-transparent text-[16px] leading-6 text-black outline-none placeholder:text-black/45"
        />
      </label>

      {isUploading && (
        <div className="mb-3 flex flex-wrap items-center gap-2 rounded-2xl bg-[#edf4f7] px-3 py-2 text-[13px] font-medium text-[#31424c]">
          <span className="size-3 animate-spin rounded-full border-2 border-[#31424c]/25 border-t-[#31424c]" />
          <span>Envoi du fichier Excel vers l&apos;API</span>
          {pendingFile && (
            <span className="text-[#667781]">
              {pendingFile.filename} · {formatFileSize(pendingFile.sizeBytes)}
            </span>
          )}
        </div>
      )}

      {!isUploading && isPreAnalyzing && (
        <div className="mb-3 flex w-fit items-center gap-2 rounded-full bg-[#edf4f7] px-3 py-2 text-[13px] font-medium text-[#31424c]">
          <span className="size-3 animate-spin rounded-full border-2 border-[#31424c]/25 border-t-[#31424c]" />
          Pre-analyse deterministe du Grand Livre…
        </div>
      )}

      {isRestoring && (
        <div className="mb-3 flex w-fit items-center gap-2 rounded-full bg-[#edf4f7] px-3 py-2 text-[13px] font-medium text-[#31424c]">
          <span className="size-3 animate-spin rounded-full border-2 border-[#31424c]/25 border-t-[#31424c]" />
          Restauration de la discussion…
        </div>
      )}

      {!isUploading && !isPreAnalyzing && uploadError && (
        <div className="mb-3 rounded-xl bg-red-50 px-3 py-2 text-[13px] font-medium text-red-700">
          {uploadError}
        </div>
      )}

      {!isUploading && attachedFile && (
        <AgentFileSummary attachedFile={attachedFile} onRemoveFile={onRemoveFile} />
      )}

      {!isPreAnalyzing && preAnalysisError && (
        <div className="mb-3 rounded-xl bg-amber-50 px-3 py-2 text-[13px] font-medium text-amber-800">
          {preAnalysisError}
        </div>
      )}

      <div className="mt-3 flex items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <div className="relative size-8">
            <AgentToolbarButton
              label="Ajouter"
              variant="primary"
              disabled={isUploading}
            >
              <PlusIcon className="size-[17px]" />
            </AgentToolbarButton>
            <input
              type="file"
              aria-label="Ajouter un fichier Excel"
              accept={AGENT_UPLOAD_ACCEPTED_EXTENSIONS.join(",")}
              disabled={isUploading}
              onChange={handleFileChange}
              className="absolute inset-0 size-full cursor-pointer opacity-0 disabled:cursor-default"
            />
          </div>
          <AgentToolbarButton label="Connecteurs">
            <GlobalIcon className="size-[18px]" />
          </AgentToolbarButton>
          <AgentToolbarButton label="Selectionner un contexte">
            <ScannerIcon className="size-[18px]" />
          </AgentToolbarButton>
          <AgentToolbarButton label="Reglages">
            <SlidersIcon className="size-[18px]" />
          </AgentToolbarButton>
        </div>

        <button
          type="button"
          aria-label="Envoyer"
          disabled={!canSubmit}
          onClick={onSubmit}
          className="flex size-[46px] shrink-0 cursor-pointer items-center justify-center rounded-full bg-[#40515c] text-white shadow-[0_14px_28px_rgba(64,81,92,0.20)] transition hover:bg-[#34434c] disabled:cursor-default disabled:bg-[#9bacb5] disabled:shadow-none"
        >
          <ArrowUpIcon className="size-[20px]" />
        </button>
      </div>
    </div>
  );
}
