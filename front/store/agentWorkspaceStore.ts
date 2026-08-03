import { create } from "zustand";

type AgentWorkspaceSelection = {
  activeRunId: string | null;
  activeSessionId: string | null;
  activeFileId: string | null;
  resetVersion: number;
  selectConversation: (selection: {
    runId: string;
    sessionId: string | null;
    fileId: string | null;
  }) => void;
  selectFile: (selection: { sessionId: string; fileId: string }) => void;
  startNewChat: () => void;
};

const useAgentWorkspaceStore = create<AgentWorkspaceSelection>((set) => ({
  activeRunId: null,
  activeSessionId: null,
  activeFileId: null,
  resetVersion: 0,
  selectConversation: ({ runId, sessionId, fileId }) =>
    set({
      activeRunId: runId,
      activeSessionId: sessionId,
      activeFileId: fileId,
    }),
  selectFile: ({ sessionId, fileId }) =>
    set({
      activeRunId: null,
      activeSessionId: sessionId,
      activeFileId: fileId,
      resetVersion: Date.now(),
    }),
  startNewChat: () =>
    set((state) => ({
      activeRunId: null,
      activeSessionId: null,
      activeFileId: null,
      resetVersion: state.resetVersion + 1,
    })),
}));

export default useAgentWorkspaceStore;
