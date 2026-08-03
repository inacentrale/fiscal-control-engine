import { getApiBase, joinUrl, postData } from "@/api/core/api";
import { ApiError } from "@/utils/api/errors";

import type {
  AgentRunEvent,
  AgentRunRequest,
  AgentRunResponse,
  AgentRunStreamMessage,
} from "./types";

export const runAgentPreAnalysis = (
  sessionId: string,
  fileId: string,
  sheetName: string
): Promise<AgentRunResponse> =>
  postData<AgentRunResponse>("agent/runs", {
    message: "Analyse la structure de ce Grand Livre avec l'outil analyze_ledger.",
    session_id: sessionId,
    file_id: fileId,
    allowed_tools: ["analyze_ledger"],
    requested_tool: "analyze_ledger",
    sheet_name: sheetName,
  });

export const runAgentChat = ({
  message,
  sessionId,
  fileId,
  sheetName,
}: AgentRunRequest): Promise<AgentRunResponse> =>
  postData<AgentRunResponse>("agent/runs", buildAgentRunPayload({
    message,
    sessionId,
    fileId,
    sheetName,
  }));

export const runAgentChatStream = async (
  request: AgentRunRequest,
  handlers: {
    onEvent?: (event: AgentRunEvent) => void;
    onAnswerDelta?: (chunk: string) => void;
  } = {}
): Promise<AgentRunResponse> => {
  const response = await fetch(joinUrl(getApiBase(false), "agent/runs/stream"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    credentials: "include",
    body: JSON.stringify(buildAgentRunPayload(request)),
  });

  if (!response.ok) {
    throw new ApiError(response.status, await readErrorPayload(response));
  }
  if (!response.body) {
    throw new Error("Le stream agent est indisponible.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result: AgentRunResponse | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      result = handleStreamLine(line, handlers) || result;
    }
  }

  buffer += decoder.decode();
  if (buffer.trim()) {
    result = handleStreamLine(buffer, handlers) || result;
  }

  if (!result) {
    throw new Error("La reponse finale du stream agent est manquante.");
  }

  return result;
};

const buildAgentRunPayload = ({
  message,
  sessionId,
  fileId,
  sheetName,
}: AgentRunRequest) => ({
  message,
  session_id: sessionId,
  file_id: fileId,
  allowed_tools: ["list_sheets", "get_columns", "profile_sheet", "analyze_ledger"],
  sheet_name: sheetName,
});

const handleStreamLine = (
  line: string,
  handlers: {
    onEvent?: (event: AgentRunEvent) => void;
    onAnswerDelta?: (chunk: string) => void;
  }
) => {
  const trimmedLine = line.trim();
  if (!trimmedLine) return null;

  const payload = JSON.parse(trimmedLine) as AgentRunStreamMessage;
  if (payload.type === "result") {
    return payload.data;
  }

  if (payload.data.event_type === "answer_delta") {
    handlers.onAnswerDelta?.(payload.data.message);
  } else {
    handlers.onEvent?.(payload.data);
  }

  return null;
};

const readErrorPayload = async (response: Response) => {
  try {
    return await response.json();
  } catch {
    return { error: { message: "La requete agent a echoue." } };
  }
};
