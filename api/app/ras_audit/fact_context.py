import base64
import csv
import hashlib
import hmac
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from app.ras_audit.rule_resolution import RasFactSource, RasLegalFact


class RasFactContextError(ValueError):
    pass


@dataclass(frozen=True)
class RasUserFactPattern:
    pattern_id: str
    version: str
    fact_name: str
    phrase: str
    normalized_value: str


@dataclass(frozen=True)
class RasExtractedFact:
    fact: RasLegalFact
    start: int
    end: int


@dataclass(frozen=True)
class RasFactExtraction:
    facts: tuple[RasExtractedFact, ...]
    conflicting_fact_names: tuple[str, ...]
    pattern_versions: tuple[str, ...]


@dataclass(frozen=True)
class RasVerifiedFactContext:
    message_sha256: str
    session_id: str | None
    file_id: str | None
    facts: tuple[RasLegalFact, ...]
    issued_at: datetime
    pattern_versions: tuple[str, ...]
    conflicting_fact_names: tuple[str, ...]


def load_ras_user_fact_patterns(path: Path) -> tuple[RasUserFactPattern, ...]:
    try:
        with path.open(encoding="utf-8", newline="") as source:
            reader = csv.DictReader(source)
            required = {
                "pattern_id",
                "version",
                "fact_name",
                "phrase",
                "normalized_value",
            }
            if set(reader.fieldnames or ()) != required:
                raise RasFactContextError("invalid RAS user fact pattern columns")
            patterns = tuple(
                RasUserFactPattern(
                    **{key: (value or "").strip() for key, value in row.items()}
                )
                for row in reader
            )
    except OSError as exc:
        raise RasFactContextError("RAS user fact patterns cannot be read") from exc
    if not patterns or any(
        not all(
            (
                item.pattern_id,
                item.version,
                item.fact_name,
                item.phrase,
                item.normalized_value,
            )
        )
        for item in patterns
    ):
        raise RasFactContextError("RAS user fact patterns are empty or incomplete")
    if len({item.pattern_id for item in patterns}) != len(patterns):
        raise RasFactContextError("duplicate RAS user fact pattern id")
    return patterns


class RasExplicitFactExtractor:
    def __init__(self, patterns: tuple[RasUserFactPattern, ...]) -> None:
        if not patterns:
            raise ValueError("RAS user fact patterns are required")
        self._patterns = patterns

    def extract(self, message: str) -> RasFactExtraction:
        matches: dict[str, list[RasExtractedFact]] = {}
        matched_versions: set[str] = set()
        for pattern in self._patterns:
            for extracted in _extract_pattern(message, pattern):
                matches.setdefault(extracted.fact.name, []).append(extracted)
                matched_versions.add(pattern.version)
        conflicts = tuple(
            sorted(
                name
                for name, items in matches.items()
                if len({item.fact.value for item in items}) > 1
            )
        )
        facts = tuple(
            sorted(
                (items[0] for name, items in matches.items() if name not in conflicts),
                key=lambda item: (item.start, item.fact.name),
            )
        )
        return RasFactExtraction(
            facts=facts,
            conflicting_fact_names=conflicts,
            pattern_versions=tuple(sorted(matched_versions)),
        )


def _extract_pattern(
    message: str,
    pattern: RasUserFactPattern,
) -> tuple[RasExtractedFact, ...]:
    if pattern.normalized_value == "$amount_with_currency":
        return _extract_amount_with_currency(message, pattern)
    if pattern.normalized_value.startswith("$iso_date_with_fact:"):
        return _extract_iso_date_with_fact(message, pattern)
    expression = re.compile(
        rf"(?<!\w){_accent_insensitive_phrase(pattern.phrase)}(?!\w)",
        flags=re.IGNORECASE,
    )
    return tuple(
        _extracted_fact(
            message=message,
            pattern=pattern,
            name=pattern.fact_name,
            value=pattern.normalized_value,
            start=found.start(),
            end=found.end(),
        )
        for found in expression.finditer(message)
    )


def _extract_amount_with_currency(
    message: str,
    pattern: RasUserFactPattern,
) -> tuple[RasExtractedFact, ...]:
    expression = re.compile(
        rf"(?<!\w){_accent_insensitive_phrase(pattern.phrase)}\s*"
        r"(?:[:=]|est de|de)?\s*"
        r"(?P<amount>(?:\d{1,3}(?:[ \u00a0\u202f]\d{3})+|\d{1,18})"
        r"(?:[,.]\d{1,6})?)\s*(?P<currency>XOF|EUR|USD)\b",
        flags=re.IGNORECASE,
    )
    extracted: list[RasExtractedFact] = []
    for found in expression.finditer(message):
        amount = re.sub(r"[ \u00a0\u202f]", "", found.group("amount")).replace(",", ".")
        extracted.extend(
            (
                _extracted_fact(
                    message=message,
                    pattern=pattern,
                    name=pattern.fact_name,
                    value=amount,
                    start=found.start(),
                    end=found.end(),
                ),
                _extracted_fact(
                    message=message,
                    pattern=pattern,
                    name="currency",
                    value=found.group("currency").upper(),
                    start=found.start(),
                    end=found.end(),
                ),
            )
        )
    return tuple(extracted)


def _extract_iso_date_with_fact(
    message: str,
    pattern: RasUserFactPattern,
) -> tuple[RasExtractedFact, ...]:
    try:
        _, companion_name, companion_value = pattern.normalized_value.split(":", 2)
    except ValueError as exc:
        raise RasFactContextError("invalid dated RAS fact pattern") from exc
    expression = re.compile(
        rf"(?<!\w){_accent_insensitive_phrase(pattern.phrase)}\s*"
        r"(?P<date>\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})(?!\d)",
        flags=re.IGNORECASE,
    )
    extracted: list[RasExtractedFact] = []
    for found in expression.finditer(message):
        raw_date = found.group("date")
        normalized_date = (
            raw_date
            if "-" in raw_date
            else f"{raw_date[6:10]}-{raw_date[3:5]}-{raw_date[0:2]}"
        )
        try:
            date.fromisoformat(normalized_date)
        except ValueError:
            continue
        extracted.extend(
            (
                _extracted_fact(
                    message=message,
                    pattern=pattern,
                    name=pattern.fact_name,
                    value=normalized_date,
                    start=found.start(),
                    end=found.end(),
                ),
                _extracted_fact(
                    message=message,
                    pattern=pattern,
                    name=companion_name,
                    value=companion_value,
                    start=found.start(),
                    end=found.end(),
                ),
            )
        )
    return tuple(extracted)


def _accent_insensitive_phrase(phrase: str) -> str:
    equivalents = {
        "a": "aàâä",
        "à": "aàâä",
        "â": "aàâä",
        "ä": "aàâä",
        "c": "cç",
        "ç": "cç",
        "e": "eéèêë",
        "é": "eéèêë",
        "è": "eéèêë",
        "ê": "eéèêë",
        "ë": "eéèêë",
        "i": "iîï",
        "î": "iîï",
        "ï": "iîï",
        "o": "oôö",
        "ô": "oôö",
        "ö": "oôö",
        "u": "uùûü",
        "ù": "uùûü",
        "û": "uùûü",
        "ü": "uùûü",
    }
    return "".join(
        f"[{equivalents[character.lower()]}]"
        if character.lower() in equivalents
        else re.escape(character)
        for character in phrase
    )


def _extracted_fact(
    *,
    message: str,
    pattern: RasUserFactPattern,
    name: str,
    value: str,
    start: int,
    end: int,
) -> RasExtractedFact:
    evidence = (
        f"user_message:{_sha256(message)}:chars:{start}-{end}:"
        f"pattern:{pattern.pattern_id}"
    )
    return RasExtractedFact(
        fact=RasLegalFact(
            name=name,
            value=value,
            source=RasFactSource.USER,
            evidence_reference=evidence,
        ),
        start=start,
        end=end,
    )


class RasFactContextAttestor:
    def __init__(
        self,
        signing_key: str,
        *,
        max_age: timedelta = timedelta(minutes=15),
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        if len(signing_key.encode("utf-8")) < 32:
            raise ValueError(
                "RAS fact context signing key must contain at least 32 bytes"
            )
        self._key = signing_key.encode("utf-8")
        self._max_age = max_age
        self._now = now

    def issue(
        self,
        *,
        message: str,
        extraction: RasFactExtraction,
        session_id: str | None,
        file_id: str | None,
    ) -> str:
        issued_at = self._now().astimezone(UTC)
        payload = {
            "v": 1,
            "message_sha256": _sha256(message),
            "session_id": session_id,
            "file_id": file_id,
            "issued_at": issued_at.isoformat(),
            "pattern_versions": list(extraction.pattern_versions),
            "conflicting_fact_names": list(extraction.conflicting_fact_names),
            "facts": [
                {
                    "name": item.fact.name,
                    "value": item.fact.value,
                    "evidence_reference": item.fact.evidence_reference,
                }
                for item in extraction.facts
            ],
        }
        serialized = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        encoded = _encode(serialized)
        signature = _encode(hmac.digest(self._key, encoded.encode("ascii"), "sha256"))
        return f"{encoded}.{signature}"

    def verify(self, token: str) -> RasVerifiedFactContext:
        try:
            encoded, supplied_signature = token.split(".", maxsplit=1)
            expected_signature = _encode(
                hmac.digest(self._key, encoded.encode("ascii"), "sha256")
            )
            if not hmac.compare_digest(supplied_signature, expected_signature):
                raise RasFactContextError("invalid RAS fact context signature")
            payload = json.loads(_decode(encoded))
            if payload.get("v") != 1:
                raise RasFactContextError("unsupported RAS fact context version")
            issued_at = datetime.fromisoformat(payload["issued_at"]).astimezone(UTC)
            age = self._now().astimezone(UTC) - issued_at
            if age < timedelta(0) or age > self._max_age:
                raise RasFactContextError("expired RAS fact context")
            facts = tuple(
                RasLegalFact(
                    name=item["name"],
                    value=item["value"],
                    source=RasFactSource.USER,
                    evidence_reference=item["evidence_reference"],
                )
                for item in payload["facts"]
            )
            return RasVerifiedFactContext(
                message_sha256=payload["message_sha256"],
                session_id=payload.get("session_id"),
                file_id=payload.get("file_id"),
                facts=facts,
                issued_at=issued_at,
                pattern_versions=tuple(payload["pattern_versions"]),
                conflicting_fact_names=tuple(payload["conflicting_fact_names"]),
            )
        except RasFactContextError:
            raise
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise RasFactContextError("malformed RAS fact context") from exc


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode(value: str) -> str:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding).decode("utf-8")
