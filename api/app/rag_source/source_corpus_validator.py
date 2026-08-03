import re
from dataclasses import dataclass
from pathlib import Path

PLACEHOLDER_MARKER = "A COMPLETER"
VALIDATED_STATUS = "validated"
REQUIRED_METADATA_FIELDS = {
    "domain",
    "source_type",
    "title",
    "version",
    "language",
    "origin",
    "themes",
    "validation_status",
    "validated_by",
    "validated_at",
}
METADATA_PATTERN = re.compile(r"^- `(?P<key>[^`]+)`: `(?P<value>[^`]*)`$", re.MULTILINE)
IGNORED_SOURCE_FILENAMES = {
    "README.md",
    "export.md",
    "markdown-loading.md",
    "source-template.md",
    "validation.md",
}


@dataclass(frozen=True)
class SourceCorpusIssue:
    code: str
    message: str


@dataclass(frozen=True)
class SourceCorpusValidationReport:
    source_path: Path
    is_indexable: bool
    issues: tuple[SourceCorpusIssue, ...]
    metadata: dict[str, str]


def validate_source_corpus_file(source_path: Path) -> SourceCorpusValidationReport:
    content = source_path.read_text(encoding="utf-8")
    metadata = _extract_metadata(content)
    issues = _collect_issues(content=content, metadata=metadata)

    return SourceCorpusValidationReport(
        source_path=source_path,
        is_indexable=not issues,
        issues=tuple(issues),
        metadata=metadata,
    )


def find_source_corpus_files(root_path: Path) -> tuple[Path, ...]:
    return tuple(
        sorted(
            path
            for path in root_path.rglob("*.md")
            if path.name not in IGNORED_SOURCE_FILENAMES
        )
    )


def _extract_metadata(content: str) -> dict[str, str]:
    return {
        match.group("key").strip(): match.group("value").strip()
        for match in METADATA_PATTERN.finditer(content)
    }


def _collect_issues(
    content: str,
    metadata: dict[str, str],
) -> list[SourceCorpusIssue]:
    issues: list[SourceCorpusIssue] = []
    missing_fields = sorted(REQUIRED_METADATA_FIELDS - set(metadata))
    if missing_fields:
        issues.append(
            SourceCorpusIssue(
                code="missing_metadata",
                message=f"missing metadata fields: {', '.join(missing_fields)}",
            )
        )

    if PLACEHOLDER_MARKER in content:
        issues.append(
            SourceCorpusIssue(
                code="placeholder_found",
                message="source still contains placeholders",
            )
        )

    validation_status = metadata.get("validation_status")
    if validation_status != VALIDATED_STATUS:
        issues.append(
            SourceCorpusIssue(
                code="source_not_validated",
                message="source must be explicitly validated before indexing",
            )
        )

    return issues
