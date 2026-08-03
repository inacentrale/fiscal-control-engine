import csv
from pathlib import Path

from app.rag_source.markdown_corpus_exporter import export_markdown_sources_to_csv


def test_export_markdown_sources_to_csv_exports_only_validated_sources(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "source-corpus"
    fiscal_dir = source_root / "fiscal"
    fiscal_dir.mkdir(parents=True)
    (source_root / "README.md").write_text("# Readme\n", encoding="utf-8")
    (fiscal_dir / "validated.md").write_text(
        _source_markdown(validation_status="validated"),
        encoding="utf-8",
    )
    (fiscal_dir / "draft.md").write_text(
        _source_markdown(validation_status="draft"),
        encoding="utf-8",
    )
    output_path = tmp_path / "rag-corpus.csv"

    summary = export_markdown_sources_to_csv(
        source_root=source_root,
        output_path=output_path,
    )

    assert summary.scanned_sources == 2
    assert summary.exported_sources == 1
    assert summary.exported_blocks == 2
    assert summary.blocked_sources == 1

    with output_path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    assert [row["block_reference"] for row in rows] == ["ART-001", "ART-002"]
    assert rows[0]["source_id"] == "Code fiscal valide"
    assert rows[0]["source_type"] == "tax_code"
    assert rows[0]["title"] == "Code fiscal valide"
    assert rows[0]["version"] == "2026"
    assert rows[0]["theme"] == "RAS"
    assert rows[0]["text"] == "Texte valide sur la retenue."


def test_export_markdown_sources_to_csv_writes_header_when_no_source_is_indexable(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "source-corpus"
    source_root.mkdir()
    (source_root / "draft.md").write_text(
        _source_markdown(validation_status="draft"),
        encoding="utf-8",
    )
    output_path = tmp_path / "rag-corpus.csv"

    summary = export_markdown_sources_to_csv(
        source_root=source_root,
        output_path=output_path,
    )

    assert summary.scanned_sources == 1
    assert summary.exported_sources == 0
    assert summary.exported_blocks == 0
    assert summary.blocked_sources == 1

    with output_path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    assert rows == []


def _source_markdown(validation_status: str) -> str:
    return f"""
# Source

## Metadonnees

- `domain`: `fiscal`
- `country`: `BF`
- `source_type`: `tax_code`
- `title`: `Code fiscal valide`
- `version`: `2026`
- `language`: `fr`
- `origin`: `anonymized_reference`
- `themes`: `RAS; loyers`
- `validation_status`: `{validation_status}`
- `validated_by`: `metier`
- `validated_at`: `2026-07-28`

## Blocs

### Bloc 1

- `block_reference`: `ART-001`
- `block_type`: `article`
- `theme`: `RAS`

```text
Texte valide sur la retenue.
```

### Bloc 2

- `block_reference`: `ART-002`
- `block_type`: `section`
- `theme`: `loyers`

```text
Texte valide sur les loyers.
```
"""
