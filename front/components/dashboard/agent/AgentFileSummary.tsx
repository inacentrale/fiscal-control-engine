import type { AgentAttachedFile } from "@/api/agent/types";
import AgentFileCard from "./AgentFileCard";

export default function AgentFileSummary({
  attachedFile,
  onRemoveFile,
}: {
  attachedFile: AgentAttachedFile;
  onRemoveFile: () => void;
}) {
  return (
    <div className="mb-3">
      <AgentFileCard attachedFile={attachedFile} onRemoveFile={onRemoveFile} />
    </div>
  );
}
