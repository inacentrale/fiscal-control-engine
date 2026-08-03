from pathlib import Path

import pytest

from app.rag_source.domain import RagSourceType, RagTextBlockType
from app.rag_source.markdown_source_loader import load_markdown_source_blocks


def test_load_markdown_source_blocks_from_validated_source(tmp_path: Path) -> None:
    source_path = tmp_path / "validated-source.md"
    source_path.write_text(_validated_source_markdown(), encoding="utf-8")

    blocks = load_markdown_source_blocks(source_path)

    assert len(blocks) == 2
    assert blocks[0].metadata.domain == "fiscal"
    assert blocks[0].metadata.country == "BF"
    assert blocks[0].metadata.source_type is RagSourceType.TAX_CODE
    assert blocks[0].metadata.themes == ("RAS", "loyers")
    assert blocks[0].block.block_type is RagTextBlockType.ARTICLE
    assert blocks[0].block.reference == "ART-001"
    assert blocks[0].block.heading == "RAS"
    assert blocks[0].block.text == "Texte valide sur la retenue."
    assert blocks[1].block.reference == "ART-002"


def test_load_markdown_source_blocks_rejects_non_indexable_source(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "draft-source.md"
    source_path.write_text(
        _validated_source_markdown(validation_status="draft"),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="source is not indexable"):
        load_markdown_source_blocks(source_path)


def test_load_markdown_source_blocks_rejects_block_without_text(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "bad-block.md"
    source_path.write_text(
        _validated_source_markdown(block_text=""),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="block text"):
        load_markdown_source_blocks(source_path)


def _validated_source_markdown(
    validation_status: str = "validated",
    block_text: str = "Texte valide sur la retenue.",
) -> str:
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
{block_text}
```

### Bloc 2

- `block_reference`: `ART-002`
- `block_type`: `section`
- `theme`: `loyers`

```text
Texte valide sur les loyers.
```
"""
