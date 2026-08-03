import csv
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path


class ArticleVerificationStatus(StrEnum):
    CONFIRMED = "confirmed"
    REVIEW_REQUIRED = "review_required"
    SOURCE_MISSING = "source_missing"
    CONFLICT = "conflict"


@dataclass(frozen=True)
class TaxArticleApplicability:
    matrix_id: str
    tax_scope: str
    cgi_article: str
    rule_subject: str
    valid_from: date
    valid_to: date
    legal_source_id: str
    legal_locator: str
    verification_status: ArticleVerificationStatus
    gap_reason: str

    def __post_init__(self) -> None:
        required = (
            self.matrix_id,
            self.tax_scope,
            self.cgi_article,
            self.rule_subject,
            self.legal_source_id,
            self.legal_locator,
        )
        if any(not value.strip() for value in required):
            raise ValueError("article applicability fields are required")
        if self.valid_to < self.valid_from:
            raise ValueError("article applicability period is invalid")
        if (
            self.verification_status is not ArticleVerificationStatus.CONFIRMED
            and not self.gap_reason.strip()
        ):
            raise ValueError("unconfirmed article applicability requires a gap reason")


def load_tax_article_applicability(
    source_path: Path,
) -> tuple[TaxArticleApplicability, ...]:
    with source_path.open(encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        required = {
            "matrix_id",
            "tax_scope",
            "cgi_article",
            "rule_subject",
            "valid_from",
            "valid_to",
            "legal_source_id",
            "legal_locator",
            "verification_status",
            "gap_reason",
        }
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError("invalid article applicability columns")
        entries = tuple(_entry(row) for row in reader)
    if len({entry.matrix_id for entry in entries}) != len(entries):
        raise ValueError("matrix_id values must be unique")
    _validate_non_overlapping(entries)
    return entries


def _entry(row: dict[str, str | None]) -> TaxArticleApplicability:
    values = {key: (value or "").strip() for key, value in row.items()}
    try:
        return TaxArticleApplicability(
            matrix_id=values["matrix_id"],
            tax_scope=values["tax_scope"],
            cgi_article=values["cgi_article"],
            rule_subject=values["rule_subject"],
            valid_from=date.fromisoformat(values["valid_from"]),
            valid_to=date.fromisoformat(values["valid_to"]),
            legal_source_id=values["legal_source_id"],
            legal_locator=values["legal_locator"],
            verification_status=ArticleVerificationStatus(
                values["verification_status"],
            ),
            gap_reason=values["gap_reason"],
        )
    except (KeyError, ValueError) as exc:
        raise ValueError("invalid article applicability row") from exc


def _validate_non_overlapping(
    entries: tuple[TaxArticleApplicability, ...],
) -> None:
    grouped: dict[tuple[str, str], list[TaxArticleApplicability]] = {}
    for entry in entries:
        grouped.setdefault((entry.tax_scope, entry.cgi_article), []).append(entry)
    for key, rows in grouped.items():
        ordered = sorted(rows, key=lambda item: item.valid_from)
        if any(
            current.valid_from <= previous.valid_to
            for previous, current in zip(ordered, ordered[1:], strict=False)
        ):
            raise ValueError(f"overlapping article applicability periods for {key}")
