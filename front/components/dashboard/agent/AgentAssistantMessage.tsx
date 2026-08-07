import type { AgentConversationMessage } from "@/api/agent/types";

import AgentExecutionTrace from "./AgentExecutionTrace";
import AgentLedgerEntriesTable from "./AgentLedgerEntriesTable";
import AgentMarkdownAnswer from "./AgentMarkdownAnswer";
import AgentModelMeta from "./AgentModelMeta";
import AgentRasAuditReportCard from "./AgentRasAuditReportCard";

type AgentAssistantMessageProps = {
  message: Extract<AgentConversationMessage, { role: "assistant" }>;
};

export default function AgentAssistantMessage({
  message,
}: AgentAssistantMessageProps) {
  const isLoading = message.status === "loading";
  const hasResult = Boolean(message.content || message.ledgerQuery);

  return (
    <div className="space-y-3 px-1 text-[15px] leading-7 text-[#203743]">
      {(isLoading || message.executionEvents.length > 0) && (
        <AgentExecutionTrace
          events={message.executionEvents}
          hasFile={message.hasFileContext}
          isLoading={isLoading}
        />
      )}

      {message.ledgerQuery && (
        <AgentLedgerEntriesTable result={message.ledgerQuery} />
      )}

      {message.rasAuditReport && (
        <AgentRasAuditReportCard report={message.rasAuditReport} />
      )}

      {message.content && !message.ledgerQuery && (
        <div className="group/answer">
          <AgentMarkdownAnswer
            content={message.content}
            isError={message.status === "error"}
          />
          {!isLoading && message.providerName && message.modelName && (
            <AgentModelMeta
              providerName={message.providerName}
              modelName={message.modelName}
            />
          )}
        </div>
      )}

      {message.ledgerQuery &&
        !isLoading &&
        message.providerName &&
        message.modelName && (
          <AgentModelMeta
            providerName={message.providerName}
            modelName={message.modelName}
          />
        )}

      {!isLoading && !hasResult && (
        <p className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-medium text-amber-800">
          Aucun résultat n’a été retourné. Vérifiez qu’un fichier Excel est
          attaché, puis relancez la demande.
        </p>
      )}
    </div>
  );
}
