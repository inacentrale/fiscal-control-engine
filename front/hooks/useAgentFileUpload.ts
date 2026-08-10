import { useEffect, useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { agentSidebarQueryKeys } from "@/api/agent/sidebar";
import {
  getAgentConversation,
  getAgentSessionContext,
} from "@/api/agent/sidebar";
import { uploadAgentFile } from "@/api/agent/uploadAgentFile";
import {
  isAgentStreamTimeoutError,
  runAgentChat,
  runAgentChatStream,
  runAgentPreAnalysis,
} from "@/api/agent/runAgentAnalysis";
import type {
  AgentAttachedFile,
  AgentConversationMessage,
  AgentRunEvent,
  AgentErrorResponse,
  AgentRunResponse,
  LedgerPreAnalysis,
} from "@/api/agent/types";
import { ApiError } from "@/utils/api/errors";
import useAlertStore, { AlertTypeStatus } from "@/store/alertStore";
import { extractLedgerQueryResult } from "@/api/agent/ledgerQueryResult";
import { extractRasAuditReportSummary } from "@/api/agent/rasAuditReport";
import useAgentWorkspaceStore from "@/store/agentWorkspaceStore";

export const AGENT_UPLOAD_ACCEPTED_EXTENSIONS = [".xlsx", ".xlsm"];

type ChatMutationVariables = {
  message: string;
  assistantMessageId: string;
  sessionId?: string;
  fileId?: string;
  sheetName?: string;
};

const hasAcceptedExtension = (filename: string): boolean => {
  const lowerCaseFilename = filename.toLowerCase();
  return AGENT_UPLOAD_ACCEPTED_EXTENSIONS.some((extension) =>
    lowerCaseFilename.endsWith(extension)
  );
};

export const useAgentFileUpload = () => {
  const [attachedFile, setAttachedFile] = useState<AgentAttachedFile | null>(null);
  const [activeFileContext, setActiveFileContext] =
    useState<AgentAttachedFile | null>(null);
  const [pendingFile, setPendingFile] = useState<{ filename: string; sizeBytes: number } | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [preAnalysis, setPreAnalysis] = useState<LedgerPreAnalysis | null>(null);
  const [preAnalysisError, setPreAnalysisError] = useState<string | null>(null);
  const [messages, setMessages] = useState<AgentConversationMessage[]>([]);
  const [isResponding, setIsResponding] = useState(false);
  const [isRestoring, setIsRestoring] = useState(false);
  const activePreviewUrlRef = useRef<string | null>(null);
  const previewUrlsRef = useRef<Set<string>>(new Set());
  const { setAlert } = useAlertStore();
  const queryClient = useQueryClient();
  const activeRunId = useAgentWorkspaceStore((state) => state.activeRunId);
  const activeSessionId = useAgentWorkspaceStore((state) => state.activeSessionId);
  const resetVersion = useAgentWorkspaceStore((state) => state.resetVersion);

  useEffect(() => {
    const previewUrls = previewUrlsRef.current;
    return () => {
      previewUrls.forEach((previewUrl) => {
        revokePreviewUrl(previewUrl);
      });
      previewUrls.clear();
    };
  }, []);

  useEffect(() => {
    revokeActivePreviewUrl(activePreviewUrlRef.current, previewUrlsRef.current);
    activePreviewUrlRef.current = null;
    setAttachedFile(null);
    setActiveFileContext(null);
    setPendingFile(null);
    setUploadError(null);
    setPreAnalysis(null);
    setPreAnalysisError(null);
    setMessages([]);
  }, [resetVersion]);

  useEffect(() => {
    if (!activeRunId && !activeSessionId) return;
    let cancelled = false;

    async function restoreWorkspace() {
      setIsRestoring(true);
      setPreAnalysis(null);
      setPreAnalysisError(null);
      try {
        const [conversation, context] = await Promise.all([
          activeRunId ? getAgentConversation(activeRunId) : Promise.resolve(null),
          activeSessionId
            ? getAgentSessionContext(activeSessionId)
            : Promise.resolve(null),
        ]);
        if (cancelled) return;
        setMessages(
          (conversation?.messages ?? []).map((message) =>
            message.role === "user"
              ? {
                  id: message.message_id,
                  role: "user" as const,
                  content: message.content,
                  attachedFile: null,
                }
              : {
                  id: message.message_id,
                  role: "assistant" as const,
                  content: message.content,
                  status: "done" as const,
                  hasFileContext: Boolean(context?.active_file),
                  preAnalysis: null,
                  ledgerQuery: null,
                  rasAuditReport: null,
                  executionEvents: [],
                  providerName: null,
                  modelName: null,
                }
          )
        );
        const file = context?.active_file;
        const restoredFile = file
          ? {
              sessionId: file.session_id,
              fileId: file.file_id,
              filename: file.original_filename,
              sizeBytes: file.file_size_bytes ?? 0,
              previewUrl: null,
              expiresAt: file.expires_at,
              sheetNames: file.sheet_names,
              selectedSheetName: file.sheet_names[0] ?? "",
            }
          : null;
        setAttachedFile(restoredFile);
        setActiveFileContext(restoredFile);
      } catch {
        if (!cancelled) {
          setMessages([]);
          setAlert({
            content: "La discussion sélectionnée ne peut pas être restaurée.",
            type: AlertTypeStatus.ERROR,
          });
        }
      } finally {
        if (!cancelled) setIsRestoring(false);
      }
    }

    restoreWorkspace();
    return () => {
      cancelled = true;
    };
  }, [activeRunId, activeSessionId, setAlert]);

  const preAnalysisMutation = useMutation({
    mutationFn: ({
      sessionId,
      fileId,
      sheetName,
    }: {
      sessionId: string;
      fileId: string;
      sheetName: string;
    }) => runAgentPreAnalysis(sessionId, fileId, sheetName),
    onSuccess: (response) => {
      setPreAnalysisError(null);
      setPreAnalysis(extractLedgerPreAnalysis(response));
    },
    onError: () => {
      setPreAnalysis(null);
      setPreAnalysisError("La pre-analyse deterministe a echoue.");
    },
  });

  const uploadMutation = useMutation({
    mutationFn: uploadAgentFile,
    onSuccess: (response, file) => {
      const selectedSheetName = response.sheet_names[0] || "";
      const previewUrl = createPreviewUrl(file);
      revokeActivePreviewUrl(activePreviewUrlRef.current, previewUrlsRef.current);
      if (previewUrl) {
        previewUrlsRef.current.add(previewUrl);
      }
      activePreviewUrlRef.current = previewUrl;
      setUploadError(null);
      setPendingFile(null);
      setPreAnalysis(null);
      setPreAnalysisError(null);
      const uploadedFileContext = {
        sessionId: response.session_id,
        fileId: response.file_id,
        filename: response.original_filename,
        sizeBytes: file.size,
        previewUrl,
        expiresAt: response.expires_at,
        sheetNames: response.sheet_names,
        selectedSheetName,
      };
      setAttachedFile(uploadedFileContext);
      setActiveFileContext(uploadedFileContext);
      queryClient.invalidateQueries({
        queryKey: agentSidebarQueryKeys.files,
      });
      preAnalysisMutation.mutate({
        sessionId: response.session_id,
        fileId: response.file_id,
        sheetName: selectedSheetName,
      });
    },
    onError: (error: unknown) => {
      setPendingFile(null);
      const message =
        error instanceof ApiError
          ? (error.data as AgentErrorResponse | undefined)?.error?.message
          : undefined;
      const errorMessage = message || "L'envoi du fichier a echoue.";

      setAlert({
        content: errorMessage,
        type: AlertTypeStatus.ERROR,
      });
      setUploadError(errorMessage);
    },
  });

  const addFile = (file: File) => {
    setUploadError(null);
    setPreAnalysis(null);
    setPreAnalysisError(null);
    if (!hasAcceptedExtension(file.name)) {
      const message =
        "Seuls les fichiers Excel (.xlsx, .xlsm) sont acceptes pour le moment.";
      setAlert({
        content: message,
        type: AlertTypeStatus.ERROR,
      });
      setUploadError(message);
      return;
    }

    setPendingFile({ filename: file.name, sizeBytes: file.size });
    uploadMutation.mutate(file);
  };

  const removeFile = () => {
    revokeActivePreviewUrl(activePreviewUrlRef.current, previewUrlsRef.current);
    activePreviewUrlRef.current = null;
    setAttachedFile(null);
    setActiveFileContext(null);
    setPendingFile(null);
    setUploadError(null);
    setPreAnalysis(null);
    setPreAnalysisError(null);
    preAnalysisMutation.reset();
    uploadMutation.reset();
  };

  const submitPrompt = (message: string) => {
    const trimmedMessage = message.trim();
    if (!trimmedMessage || isResponding) return;

    const userMessageId = createMessageId("user");
    const assistantMessageId = createMessageId("assistant");
    const submittedFile = attachedFile ?? activeFileContext;
    const submittedPreAnalysis = preAnalysis;

    setMessages((currentMessages) => [
      ...currentMessages,
      {
        id: userMessageId,
        role: "user",
        content: trimmedMessage,
        attachedFile: submittedFile,
      },
      {
        id: assistantMessageId,
        role: "assistant",
        content: null,
        status: "loading",
        hasFileContext: Boolean(submittedFile),
        preAnalysis: submittedPreAnalysis,
        ledgerQuery: null,
        rasAuditReport: null,
        executionEvents: [],
        providerName: null,
        modelName: null,
      },
    ]);

    if (attachedFile) {
      setAttachedFile(null);
      setPreAnalysis(null);
      setPreAnalysisError(null);
    }

    runChatWithStream({
      message: trimmedMessage,
      assistantMessageId,
      sessionId: submittedFile?.sessionId,
      fileId: submittedFile?.fileId,
      sheetName: submittedFile?.selectedSheetName,
    });
  };

  async function runChatWithStream({
    message,
    assistantMessageId,
    sessionId,
    fileId,
    sheetName,
  }: ChatMutationVariables) {
    setIsResponding(true);
    let hasStreamProgress = false;

    try {
      const response = await runAgentChatStream(
        { message, sessionId, fileId, sheetName },
        {
          onEvent: (event) => {
            hasStreamProgress = true;
            appendAssistantEvent(assistantMessageId, event);
          },
          onAnswerDelta: (chunk) => {
            hasStreamProgress = true;
            appendAssistantAnswerDelta(assistantMessageId, chunk);
          },
        }
      );
      completeAssistantMessage(assistantMessageId, response, sessionId, fileId);
      invalidateSidebarData();
    } catch (error) {
      if (!hasStreamProgress && !isAgentStreamTimeoutError(error)) {
        try {
          const fallbackResponse = await runAgentChat({
            message,
            sessionId,
            fileId,
            sheetName,
          });
          completeAssistantMessage(
            assistantMessageId,
            fallbackResponse,
            sessionId,
            fileId
          );
          invalidateSidebarData();
          return;
        } catch {
          // The message is marked as failed below.
        }
      }

      failAssistantMessage(assistantMessageId);
    } finally {
      setIsResponding(false);
    }
  }

  function appendAssistantEvent(assistantMessageId: string, event: AgentRunEvent) {
    setMessages((currentMessages) =>
      currentMessages.map((message) =>
        message.id === assistantMessageId && message.role === "assistant"
          ? {
              ...message,
              executionEvents: [...message.executionEvents, event],
            }
          : message
      )
    );
  }

  function appendAssistantAnswerDelta(
    assistantMessageId: string,
    chunk: string
  ) {
    setMessages((currentMessages) =>
      currentMessages.map((message) =>
        message.id === assistantMessageId && message.role === "assistant"
          ? {
              ...message,
              content: message.content ? `${message.content}\n\n${chunk}` : chunk,
            }
          : message
      )
    );
  }

  function completeAssistantMessage(
    assistantMessageId: string,
    response: AgentRunResponse,
    sessionId?: string,
    fileId?: string
  ) {
    setMessages((currentMessages) =>
      currentMessages.map((message) =>
        message.id === assistantMessageId && message.role === "assistant"
          ? {
              ...message,
              content: response.answer,
              status: "done",
              ledgerQuery: extractLedgerQueryResult(response),
              rasAuditReport: extractRasAuditReportSummary(
                response,
                sessionId,
                fileId
              ),
              executionEvents: response.execution_events,
              providerName: response.provider_name,
              modelName: response.model_name,
            }
          : message
      )
    );
  }

  function invalidateSidebarData() {
    queryClient.invalidateQueries({
      queryKey: agentSidebarQueryKeys.conversations,
    });
    queryClient.invalidateQueries({
      queryKey: agentSidebarQueryKeys.files,
    });
  }

  function failAssistantMessage(assistantMessageId: string) {
    setMessages((currentMessages) =>
      currentMessages.map((message) =>
        message.id === assistantMessageId && message.role === "assistant"
          ? {
              ...message,
              content: "La reponse agent a echoue. Vous pouvez reformuler ou relancer.",
              status: "error",
            }
          : message
      )
    );
  }

  return {
    attachedFile,
    pendingFile,
    isUploading: uploadMutation.isPending,
    isPreAnalyzing: preAnalysisMutation.isPending,
    isResponding,
    isRestoring,
    uploadError,
    preAnalysisError,
    messages,
    addFile,
    removeFile,
    submitPrompt,
  };
};

const createMessageId = (prefix: string) => {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `${prefix}-${crypto.randomUUID()}`;
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2)}`;
};

const createPreviewUrl = (file: File) => {
  if (typeof URL === "undefined") return null;
  return URL.createObjectURL(file);
};

const revokeActivePreviewUrl = (
  previewUrl: string | null,
  previewUrls: Set<string>
) => {
  if (!previewUrl) return;
  revokePreviewUrl(previewUrl);
  previewUrls.delete(previewUrl);
};

const revokePreviewUrl = (previewUrl: string | null) => {
  if (!previewUrl || typeof URL === "undefined") return;
  URL.revokeObjectURL(previewUrl);
};

const extractLedgerPreAnalysis = (response: AgentRunResponse): LedgerPreAnalysis | null => {
  const result = response.tool_results.find(
    (toolResult) => toolResult.tool_name === "analyze_ledger" && toolResult.ok
  );
  const output = result?.output;
  if (!isLedgerAnalysisOutput(output)) return null;

  return {
    sheetName: output.sheet_name,
    rowCount: output.row_count,
    columnCount: output.column_count,
    schema: output.schema,
    columns: output.columns,
  };
};

const isLedgerAnalysisOutput = (
  output: Record<string, unknown> | undefined
): output is {
  sheet_name: string;
  row_count: number;
  column_count: number;
  schema: LedgerPreAnalysis["schema"];
  columns: LedgerPreAnalysis["columns"];
} => {
  if (!output) return false;
  return (
    typeof output.sheet_name === "string" &&
    typeof output.row_count === "number" &&
    typeof output.column_count === "number" &&
    isLedgerSchema(output.schema) &&
    Array.isArray(output.columns)
  );
};

const isLedgerSchema = (schema: unknown): schema is LedgerPreAnalysis["schema"] => {
  if (!schema || typeof schema !== "object") return false;
  const candidate = schema as Partial<LedgerPreAnalysis["schema"]>;
  return (
    typeof candidate.is_valid === "boolean" &&
    Array.isArray(candidate.present_columns) &&
    Array.isArray(candidate.missing_required_columns) &&
    Array.isArray(candidate.optional_columns)
  );
};
