from datetime import datetime
from uuid import uuid4

from app.ras_audit.persistence import (
    RasAuditCaseSnapshot,
    RasAuditSnapshot,
    SqlAlchemyRasAuditRepository,
)


class RasAuditDerivationError(ValueError):
    pass


class RasAuditDerivationService:
    def __init__(self, repository: SqlAlchemyRasAuditRepository) -> None:
        self._repository = repository

    def replace_case(
        self,
        *,
        base_audit_id: str,
        source_sha256: str,
        replacement: RasAuditCaseSnapshot,
        added_reference_versions: tuple[str, ...],
        fact_context: dict[str, object],
        created_at: datetime,
    ) -> str:
        base = self._repository.get(base_audit_id.strip())
        if base is None:
            raise RasAuditDerivationError("base RAS audit was not found")
        if base.source_sha256 != source_sha256:
            raise RasAuditDerivationError("base RAS audit source hash mismatch")
        if replacement.candidate_id not in {case.candidate_id for case in base.cases}:
            raise RasAuditDerivationError(
                "candidate does not belong to the base RAS audit"
            )
        cases = tuple(
            replacement if case.candidate_id == replacement.candidate_id else case
            for case in base.cases
        )
        audit_id = uuid4().hex
        self._repository.save(
            RasAuditSnapshot(
                audit_id=audit_id,
                parent_audit_id=base.audit_id,
                session_id=base.session_id,
                file_id=base.file_id,
                source_sha256=base.source_sha256,
                status="partially_assessed_provisional",
                reference_versions=tuple(
                    sorted(set(base.reference_versions) | set(added_reference_versions))
                ),
                fact_context=fact_context,
                cases=cases,
                created_at=created_at,
            )
        )
        return audit_id
