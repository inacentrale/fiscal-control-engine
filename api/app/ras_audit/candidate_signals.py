import csv
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path
from unicodedata import normalize


class CandidateSignalType(StrEnum):
    POSITIVE = "positive"
    EXCLUSION = "exclusion"


class CandidateSignalStrength(StrEnum):
    STRONG = "strong"
    SUPPORTING = "supporting"


class CandidateSignalError(ValueError):
    pass


@dataclass(frozen=True)
class RasCandidateSignal:
    signal_id: str
    version: str
    signal_type: CandidateSignalType
    phrase: str
    normalized_phrase: str
    strength: CandidateSignalStrength
    operation_hint: str
    valid_from: date | None
    valid_to: date | None
    source_kind: str
    source_reference: str
    review_only: bool

    def is_applicable(self, posting_date: date | None) -> bool:
        if posting_date is None:
            return self.valid_from is None and self.valid_to is None
        return not (
            (self.valid_from is not None and posting_date < self.valid_from)
            or (self.valid_to is not None and posting_date > self.valid_to)
        )


def load_ras_candidate_signals(path: Path) -> tuple[RasCandidateSignal, ...]:
    try:
        with path.open(encoding="utf-8", newline="") as source:
            reader = csv.DictReader(source)
            _validate_columns(reader.fieldnames)
            signals = tuple(
                _parse_signal(row, row_number)
                for row_number, row in enumerate(reader, start=2)
            )
    except OSError as exc:
        raise CandidateSignalError("RAS candidate signals cannot be read") from exc
    if not signals:
        raise CandidateSignalError("RAS candidate signal reference is empty")
    if len({signal.signal_id for signal in signals}) != len(signals):
        raise CandidateSignalError("duplicate RAS candidate signal id")
    return signals


def matching_candidate_signals(
    signals: tuple[RasCandidateSignal, ...],
    label: str | None,
    *,
    posting_date: date | None,
) -> tuple[RasCandidateSignal, ...]:
    searchable = normalize_search_text(label or "")
    if not searchable:
        return ()
    return tuple(
        signal
        for signal in signals
        if signal.is_applicable(posting_date)
        and _contains_phrase(searchable, signal.normalized_phrase)
    )


def normalize_search_text(value: str) -> str:
    ascii_value = normalize("NFKD", value).encode("ascii", "ignore").decode()
    words = "".join(
        character if character.isalnum() else " "
        for character in ascii_value.lower()
    )
    return " ".join(words.split())


def _contains_phrase(value: str, phrase: str) -> bool:
    words = value.split()
    phrase_words = phrase.split()
    width = len(phrase_words)
    return any(
        all(
            actual == expected or actual == f"{expected}s"
            for actual, expected in zip(
                words[index : index + width], phrase_words, strict=True
            )
        )
        for index in range(len(words) - width + 1)
    )


def _validate_columns(fieldnames: Sequence[str] | None) -> None:
    missing = _required_columns() - set(fieldnames or ())
    if missing:
        raise CandidateSignalError(
            f"missing candidate signal columns: {', '.join(sorted(missing))}"
        )


def _parse_signal(
    row: dict[str, str | None],
    row_number: int,
) -> RasCandidateSignal:
    values = {key: (value or "").strip() for key, value in row.items()}
    for field in _required_columns() - {"valid_from", "valid_to"}:
        if not values[field]:
            raise CandidateSignalError(
                f"incomplete candidate signal at row {row_number}"
            )
    try:
        signal_type = CandidateSignalType(values["signal_type"])
        strength = CandidateSignalStrength(values["strength"])
        valid_from = _optional_date(values["valid_from"])
        valid_to = _optional_date(values["valid_to"])
    except ValueError as exc:
        raise CandidateSignalError(
            f"invalid candidate signal value at row {row_number}"
        ) from exc
    if valid_from and valid_to and valid_to < valid_from:
        raise CandidateSignalError(
            f"invalid candidate signal validity at row {row_number}"
        )
    if values["decision_effect"] != "review_only":
        raise CandidateSignalError(
            f"candidate signal must be review_only at row {row_number}"
        )
    phrase = normalize_search_text(values["phrase"])
    if not phrase:
        raise CandidateSignalError(f"empty candidate phrase at row {row_number}")
    return RasCandidateSignal(
        signal_id=values["signal_id"],
        version=values["version"],
        signal_type=signal_type,
        phrase=values["phrase"],
        normalized_phrase=phrase,
        strength=strength,
        operation_hint=values["operation_hint"],
        valid_from=valid_from,
        valid_to=valid_to,
        source_kind=values["source_kind"],
        source_reference=values["source_reference"],
        review_only=True,
    )


def _optional_date(value: str) -> date | None:
    return date.fromisoformat(value) if value else None


def _required_columns() -> set[str]:
    return {
        "signal_id",
        "version",
        "signal_type",
        "phrase",
        "strength",
        "operation_hint",
        "valid_from",
        "valid_to",
        "source_kind",
        "source_reference",
        "decision_effect",
    }
