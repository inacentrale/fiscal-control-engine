from dataclasses import dataclass
from unicodedata import normalize

from app.excel_agent.constants import DETECTED_TYPE_NUMBER, DETECTED_TYPE_TEXT
from app.excel_agent.domain import ExcelColumnProfile
from app.ledger_analysis.constants import (
    CANONICAL_LEDGER_FIELDS,
    LEDGER_FIELD_SYNONYMS,
    LEDGER_SCHEMA_AMBIGUITY_MARGIN,
    LEDGER_SCHEMA_MIN_CONFIDENCE,
    REQUIRED_CANONICAL_LEDGER_FIELDS,
)

MAPPED_STATUS = "mapped"
TO_CONFIRM_STATUS = "a_confirmer"
MISSING_STATUS = "missing"


@dataclass(frozen=True)
class LedgerColumnMapping:
    canonical_field: str
    source_column: str | None
    confidence: float
    status: str
    reason: str


@dataclass(frozen=True)
class LedgerSchemaClassification:
    mappings: tuple[LedgerColumnMapping, ...]

    @property
    def is_usable(self) -> bool:
        return all(
            self.get_mapping(required_field).status == MAPPED_STATUS
            for required_field in REQUIRED_CANONICAL_LEDGER_FIELDS
        )

    @property
    def requires_confirmation(self) -> bool:
        return any(mapping.status == TO_CONFIRM_STATUS for mapping in self.mappings)

    def get_mapping(self, canonical_field: str) -> LedgerColumnMapping:
        for mapping in self.mappings:
            if mapping.canonical_field == canonical_field:
                return mapping
        raise KeyError(canonical_field)


class LedgerSchemaClassifier:
    def classify(
        self,
        columns: tuple[ExcelColumnProfile, ...],
    ) -> LedgerSchemaClassification:
        mappings = tuple(
            _classify_field(canonical_field, columns)
            for canonical_field in CANONICAL_LEDGER_FIELDS
        )
        return LedgerSchemaClassification(mappings=mappings)


def _classify_field(
    canonical_field: str,
    columns: tuple[ExcelColumnProfile, ...],
) -> LedgerColumnMapping:
    candidates = sorted(
        ((_score_column(canonical_field, column), column) for column in columns),
        key=lambda candidate: candidate[0],
    )
    if not candidates:
        return _missing(canonical_field)

    best_score, best_column = candidates[-1]
    second_score = candidates[-2][0] if len(candidates) > 1 else 0.0
    if best_score <= 0:
        return _missing(canonical_field)
    if best_score < LEDGER_SCHEMA_MIN_CONFIDENCE:
        return _to_confirm(canonical_field, best_column, best_score, "score faible")
    if best_score - second_score < LEDGER_SCHEMA_AMBIGUITY_MARGIN:
        return _to_confirm(canonical_field, best_column, best_score, "mapping ambigu")
    return LedgerColumnMapping(
        canonical_field=canonical_field,
        source_column=best_column.name,
        confidence=_to_confidence(best_score),
        status=MAPPED_STATUS,
        reason="nom et profil de colonne compatibles",
    )


def _score_column(canonical_field: str, column: ExcelColumnProfile) -> float:
    normalized_name = _normalize_name(column.name)
    synonyms = LEDGER_FIELD_SYNONYMS[canonical_field]
    scored_synonyms = tuple(
        (
            _name_match_score(normalized_name, synonym),
            _synonym_priority_bonus(normalized_name, synonym, index),
        )
        for index, synonym in enumerate(synonyms)
    )
    name_score, priority_bonus = max(scored_synonyms)
    if name_score < 0.3:
        return 0.0
    type_score = _type_score(canonical_field, column.detected_type)
    completeness_score = max(0.0, 1.0 - column.missing_ratio)
    position_penalty = column.position * 0.002
    score = (name_score * 0.78) + (type_score * 0.15) + (completeness_score * 0.07)
    return max(0.0, score + priority_bonus - position_penalty)


def _name_match_score(normalized_name: str, synonym: str) -> float:
    normalized_synonym = _normalize_name(synonym)
    if normalized_name == normalized_synonym:
        return 1.0
    if normalized_synonym in normalized_name:
        return 0.9
    synonym_words = set(normalized_synonym.split())
    name_words = set(normalized_name.split())
    if not synonym_words:
        return 0.0
    common_ratio = len(synonym_words & name_words) / len(synonym_words)
    return common_ratio * 0.75


def _synonym_priority_bonus(
    normalized_name: str,
    synonym: str,
    index: int,
) -> float:
    normalized_synonym = _normalize_name(synonym)
    if normalized_name != normalized_synonym:
        return 0.0
    return 0.12 / (index + 1)


def _type_score(canonical_field: str, detected_type: str) -> float:
    numeric_fields = {
        "account",
        "amount",
        "vendor",
        "customer",
        "period",
        "fiscal_year",
        "posting_key",
    }
    text_fields = {
        "currency",
        "text",
        "tax_code",
        "document_type",
    }
    if canonical_field in numeric_fields and detected_type == DETECTED_TYPE_NUMBER:
        return 1.0
    if canonical_field in text_fields and detected_type == DETECTED_TYPE_TEXT:
        return 1.0
    return 0.35


def _missing(canonical_field: str) -> LedgerColumnMapping:
    return LedgerColumnMapping(
        canonical_field=canonical_field,
        source_column=None,
        confidence=0.0,
        status=MISSING_STATUS,
        reason="aucune colonne candidate fiable",
    )


def _to_confirm(
    canonical_field: str,
    column: ExcelColumnProfile,
    confidence: float,
    reason: str,
) -> LedgerColumnMapping:
    return LedgerColumnMapping(
        canonical_field=canonical_field,
        source_column=column.name,
        confidence=_to_confidence(confidence),
        status=TO_CONFIRM_STATUS,
        reason=reason,
    )


def _normalize_name(column_name: str) -> str:
    without_accents = normalize("NFKD", column_name)
    ascii_name = without_accents.encode("ascii", "ignore").decode("ascii")
    normalized_chars = [
        character.lower() if character.isalnum() else " "
        for character in ascii_name
    ]
    return " ".join("".join(normalized_chars).split())


def _to_confidence(score: float) -> float:
    return round(min(1.0, score), 2)
