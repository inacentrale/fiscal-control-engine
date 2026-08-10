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
        snapshot = RasAuditSnapshot(
            audit_id=uuid4().hex,
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
        equivalent = self._repository.find_equivalent(snapshot)
        if equivalent is not None:
            return equivalent.audit_id
        self._repository.save(snapshot)
        return snapshot.audit_id

    def merge_candidate_derivations(
        self,
        *,
        base_audit_id: str,
        candidate_results: dict[str, str],
        created_at: datetime,
    ) -> str:
        base = self._repository.get(base_audit_id.strip())
        if base is None:
            raise RasAuditDerivationError("base RAS audit was not found")
        base_candidates = {case.candidate_id for case in base.cases}
        if not candidate_results or not set(candidate_results) <= base_candidates:
            raise RasAuditDerivationError("invalid RAS candidate derivation set")
        replacements: dict[str, RasAuditCaseSnapshot] = {}
        candidate_contexts: dict[str, object] = {}
        reference_versions = set(base.reference_versions)
        for candidate_id, derived_audit_id in candidate_results.items():
            derived = self._repository.get(derived_audit_id)
            if (
                derived is None
                or derived.parent_audit_id != base.audit_id
                or derived.source_sha256 != base.source_sha256
                or derived.session_id != base.session_id
                or derived.file_id != base.file_id
            ):
                raise RasAuditDerivationError("incompatible RAS candidate derivation")
            replacement = next(
                (case for case in derived.cases if case.candidate_id == candidate_id),
                None,
            )
            if replacement is None:
                raise RasAuditDerivationError("derived RAS candidate was not found")
            replacements[candidate_id] = replacement
            candidate_contexts[candidate_id] = derived.fact_context
            reference_versions.update(derived.reference_versions)
        merged = RasAuditSnapshot(
            audit_id=uuid4().hex,
            parent_audit_id=base.audit_id,
            session_id=base.session_id,
            file_id=base.file_id,
            source_sha256=base.source_sha256,
            status="partially_assessed_provisional",
            reference_versions=tuple(sorted(reference_versions)),
            fact_context={"candidate_contexts": candidate_contexts},
            cases=tuple(
                replacements.get(case.candidate_id, case) for case in base.cases
            ),
            created_at=created_at,
        )
        equivalent = self._repository.find_equivalent(merged)
        if equivalent is not None:
            return equivalent.audit_id
        self._repository.save(merged)
        return merged.audit_id
