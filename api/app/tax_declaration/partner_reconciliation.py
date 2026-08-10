import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from app.tax_declaration.identifier_detection import (
    normalize_explicit_identifier_kind,
)


class PartnerMatchStatus(StrEnum):
    EXACT = "exact"
    POTENTIAL = "potential"
    UNMATCHED = "unmatched"
    UNRESOLVED = "unresolved"
    CONFLICT = "conflict"


@dataclass(frozen=True)
class PartnerReference:
    reference_id: str
    identifier: str | None
    identifier_type: str | None
    name: str | None


@dataclass(frozen=True)
class PartnerMatch:
    evidence_reference_id: str
    status: PartnerMatchStatus
    declaration_reference_ids: tuple[str, ...]
    matched_by: str | None


class PartnerReconciler:
    def reconcile(
        self,
        declarations: tuple[PartnerReference, ...],
        evidence: tuple[PartnerReference, ...],
    ) -> tuple[PartnerMatch, ...]:
        return tuple(_match_partner(item, declarations) for item in evidence)


def _match_partner(
    evidence: PartnerReference,
    declarations: tuple[PartnerReference, ...],
) -> PartnerMatch:
    identifier = _normalized_identifier(evidence.identifier)
    identifier_type = _normalized_kind(evidence.identifier_type)
    if identifier is not None and identifier_type is not None:
        exact = _unique_reference_ids(
            item
            for item in declarations
            if _normalized_identifier(item.identifier) == identifier
            and _normalized_kind(item.identifier_type) == identifier_type
        )
        if exact:
            return _candidate_match(
                evidence.reference_id,
                exact,
                "identifier",
                exact=True,
            )
    if identifier is not None:
        same_value = _unique_reference_ids(
            item
            for item in declarations
            if _normalized_identifier(item.identifier) == identifier
        )
        if same_value:
            return _candidate_match(
                evidence.reference_id,
                same_value,
                "identifier_without_confirmed_type",
                exact=False,
            )
    name = _normalized_name(evidence.name)
    if name is not None:
        same_name = _unique_reference_ids(
            item for item in declarations if _normalized_name(item.name) == name
        )
        if same_name:
            return _candidate_match(
                evidence.reference_id,
                same_name,
                "name",
                exact=False,
            )
    status = (
        PartnerMatchStatus.UNRESOLVED
        if identifier is None and name is None
        else PartnerMatchStatus.UNMATCHED
    )
    return PartnerMatch(evidence.reference_id, status, (), None)


def _candidate_match(
    evidence_reference_id: str,
    candidate_ids: tuple[str, ...],
    matched_by: str,
    *,
    exact: bool,
) -> PartnerMatch:
    if len(candidate_ids) > 1 and not exact:
        return PartnerMatch(
            evidence_reference_id,
            PartnerMatchStatus.CONFLICT,
            candidate_ids,
            matched_by,
        )
    return PartnerMatch(
        evidence_reference_id,
        PartnerMatchStatus.EXACT if exact else PartnerMatchStatus.POTENTIAL,
        candidate_ids,
        matched_by,
    )


def _unique_reference_ids(items: Iterable[PartnerReference]) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                item.reference_id for item in items
            },
        ),
    )


def _normalized_identifier(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().casefold()
    return normalized or None


def _normalized_kind(value: str | None) -> str | None:
    if value is None:
        return None
    return normalize_explicit_identifier_kind(value)


def _normalized_name(value: str | None) -> str | None:
    if value is None:
        return None
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    )
    normalized = re.sub(r"[^a-z0-9]+", " ", ascii_value.casefold()).strip()
    return normalized or None
