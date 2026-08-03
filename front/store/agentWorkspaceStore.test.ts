import { beforeEach, describe, expect, it } from "vitest";

import useAgentWorkspaceStore from "./agentWorkspaceStore";

describe("agentWorkspaceStore", () => {
  beforeEach(() => {
    useAgentWorkspaceStore.setState({
      activeRunId: null,
      activeSessionId: null,
      activeFileId: null,
      resetVersion: 0,
    });
  });

  it("selects a persisted conversation", () => {
    useAgentWorkspaceStore.getState().selectConversation({
      runId: "run-1",
      sessionId: "session-1",
      fileId: "file-1",
    });

    expect(useAgentWorkspaceStore.getState()).toMatchObject({
      activeRunId: "run-1",
      activeSessionId: "session-1",
      activeFileId: "file-1",
    });
  });

  it("clears the selection for a new chat", () => {
    useAgentWorkspaceStore.getState().selectFile({
      sessionId: "session-1",
      fileId: "file-1",
    });
    useAgentWorkspaceStore.getState().startNewChat();

    expect(useAgentWorkspaceStore.getState()).toMatchObject({
      activeRunId: null,
      activeSessionId: null,
      activeFileId: null,
    });
  });
});
