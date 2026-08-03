from app.agent_file.domain import StoredAgentFile


class AgentUploadRagIndexingPolicy:
    def can_index(self, stored_file: StoredAgentFile) -> bool:
        return (
            stored_file.validated_for_agent
            and stored_file.anonymized_for_rag
            and stored_file.rag_indexable
        )

    def rejection_reason(self, stored_file: StoredAgentFile) -> str | None:
        if self.can_index(stored_file):
            return None
        if not stored_file.validated_for_agent:
            return "upload_not_validated_for_agent"
        if not stored_file.anonymized_for_rag:
            return "upload_not_anonymized_for_rag"
        if not stored_file.rag_indexable:
            return "upload_not_marked_rag_indexable"
        return "upload_not_rag_indexable"
