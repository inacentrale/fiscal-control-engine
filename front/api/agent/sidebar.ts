import { getData } from "@/api/core/api";

import type {
  AgentSessionContextResponse,
  AgentConversationDetailResponse,
  AgentSidebarConversationListResponse,
  AgentSidebarFileListResponse,
} from "./types";

export const agentSidebarQueryKeys = {
  conversations: ["agent", "conversations"] as const,
  files: ["agent", "files"] as const,
  sessionContext: (sessionId: string) => ["agent", "sessions", sessionId, "context"],
};

export const listAgentConversations = (
  limit = 20,
  search?: string
): Promise<AgentSidebarConversationListResponse> =>
  getData<AgentSidebarConversationListResponse>("agent/conversations", {
    limit: String(limit),
    ...(search ? { search } : {}),
  });

export const listAgentFiles = (
  limit = 20,
  search?: string
): Promise<AgentSidebarFileListResponse> =>
  getData<AgentSidebarFileListResponse>("agent/files", {
    limit: String(limit),
    ...(search ? { search } : {}),
  });

export const getAgentSessionContext = (
  sessionId: string
): Promise<AgentSessionContextResponse> =>
  getData<AgentSessionContextResponse>(`agent/sessions/${sessionId}/context`);

export const getAgentConversation = (
  runId: string
): Promise<AgentConversationDetailResponse> =>
  getData<AgentConversationDetailResponse>(`agent/conversations/${runId}`);
