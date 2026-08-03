from pathlib import Path

from app.rag_source.source_corpus_validator import (
    find_source_corpus_files,
    validate_source_corpus_file,
)


def test_validated_source_without_placeholders_is_indexable(tmp_path: Path) -> None:
    source_path = tmp_path / "validated-source.md"
    source_path.write_text(
        _source_markdown(validation_status="validated"),
        encoding="utf-8",
    )

    report = validate_source_corpus_file(source_path)

    assert report.is_indexable is True
    assert report.issues == ()


def test_draft_source_is_not_indexable(tmp_path: Path) -> None:
    source_path = tmp_path / "draft-source.md"
    source_path.write_text(
        _source_markdown(validation_status="draft"),
        encoding="utf-8",
    )

    report = validate_source_corpus_file(source_path)

    assert report.is_indexable is False
    assert any(issue.code == "source_not_validated" for issue in report.issues)


def test_source_with_placeholder_is_not_indexable(tmp_path: Path) -> None:
    source_path = tmp_path / "placeholder-source.md"
    source_path.write_text(
        _source_markdown(validation_status="validated", title="A COMPLETER"),
        encoding="utf-8",
    )

    report = validate_source_corpus_file(source_path)

    assert report.is_indexable is False
    assert any(issue.code == "placeholder_found" for issue in report.issues)


def test_source_missing_required_metadata_is_not_indexable(tmp_path: Path) -> None:
    source_path = tmp_path / "missing-metadata.md"
    source_path.write_text(
        """
# Source

## Metadonnees

- `domain`: `fiscal`
- `source_type`: `tax_code`

## Blocs

```text
Texte valide.
```
""",
        encoding="utf-8",
    )

    report = validate_source_corpus_file(source_path)

    assert report.is_indexable is False
    assert any(issue.code == "missing_metadata" for issue in report.issues)


def test_find_source_corpus_files_ignores_readme_and_templates(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Readme\n", encoding="utf-8")
    (tmp_path / "source-template.md").write_text("# Template\n", encoding="utf-8")
    (tmp_path / "validation.md").write_text("# Validation\n", encoding="utf-8")
    (tmp_path / "markdown-loading.md").write_text("# Loading\n", encoding="utf-8")
    (tmp_path / "export.md").write_text("# Export\n", encoding="utf-8")
    fiscal_dir = tmp_path / "fiscal"
    fiscal_dir.mkdir()
    expected_source = fiscal_dir / "bf-ras.md"
    expected_source.write_text(
        _source_markdown(validation_status="validated"),
        encoding="utf-8",
    )

    assert find_source_corpus_files(tmp_path) == (expected_source,)


def _source_markdown(
    validation_status: str,
    title: str = "Code fiscal valide",
) -> str:
    return f"""
# Source

## Metadonnees

- `domain`: `fiscal`
- `country`: `BF`
- `source_type`: `tax_code`
- `title`: `{title}`
- `version`: `2026`
- `language`: `fr`
- `origin`: `anonymized_reference`
- `themes`: `RAS`
- `validation_status`: `{validation_status}`
- `validated_by`: `metier`
- `validated_at`: `2026-07-28`

## Blocs

```text
Texte fiscal valide fourni par le metier.
```
"""
