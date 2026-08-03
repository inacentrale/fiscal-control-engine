from pathlib import Path

from app.agent_file.persistent_file_store import PersistentAgentFileStore
from app.agent_file.temporary_file_store import TemporaryAgentFileStore


class AgentFileResolver:
    def __init__(
        self,
        store: TemporaryAgentFileStore | PersistentAgentFileStore,
    ) -> None:
        self._store = store

    def resolve_file_path(
        self,
        session_id: str | None,
        file_id: str | None,
        direct_file_path: str | None,
    ) -> Path | None:
        has_session_reference = bool(session_id or file_id)
        has_direct_file_path = bool(direct_file_path)

        if has_session_reference and has_direct_file_path:
            raise ValueError("choose either session file reference or direct file path")
        if has_session_reference:
            if not session_id or not file_id:
                raise ValueError("session_id and file_id are required together")
            stored_file = self._store.resolve(session_id=session_id, file_id=file_id)
            if stored_file is None:
                raise ValueError("unknown or expired agent file")
            return stored_file.path
        if direct_file_path:
            return Path(direct_file_path)
        return None
