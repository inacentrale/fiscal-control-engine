import type { AgentConversationMessage } from "@/api/agent/types";

import AgentFileCard from "./AgentFileCard";

type AgentUserMessageProps = {
  message: Extract<AgentConversationMessage, { role: "user" }>;
};

export default function AgentUserMessage({ message }: AgentUserMessageProps) {
  return (
    <div className="flex flex-col items-end gap-2">
      {message.attachedFile && <AgentFileCard attachedFile={message.attachedFile} />}
      <div className="max-w-[86%] rounded-2xl bg-[#edf4f7] px-4 py-3 text-[14px] font-medium leading-6 text-[#102734]">
        {message.content}
      </div>
    </div>
  );
}
