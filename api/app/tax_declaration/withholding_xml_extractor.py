from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree

import pandas as pd

from app.tax_declaration.domain import CanonicalTaxDeclaration, SourceReference
from app.tax_declaration.withholding_tabular_extractor import (
    WithholdingTabularExtractionError,
    WithholdingTabularExtractor,
)

_FORBIDDEN_XML_MARKERS = (b"<!DOCTYPE", b"<!ENTITY")


class WithholdingXmlExtractor:
    def extract(
        self,
        source_path: Path,
        source_reference: SourceReference,
    ) -> CanonicalTaxDeclaration:
        try:
            content = source_path.read_bytes()
        except OSError as exc:
            raise WithholdingTabularExtractionError(
                "withholding XML source cannot be read",
            ) from exc
        if any(marker in content.upper() for marker in _FORBIDDEN_XML_MARKERS):
            raise WithholdingTabularExtractionError("unsafe withholding XML source")
        try:
            root = ElementTree.fromstring(content)
        except ElementTree.ParseError as exc:
            raise WithholdingTabularExtractionError(
                "invalid withholding XML source",
            ) from exc

        rows = _candidate_rows(root)
        if not rows:
            raise WithholdingTabularExtractionError(
                "withholding XML structure is unresolved",
            )
        return WithholdingTabularExtractor().extract_frame(
            pd.DataFrame(rows),
            source_reference,
        )


def _candidate_rows(root: ElementTree.Element) -> list[dict[str, str | None]]:
    rows: list[dict[str, str | None]] = []
    for element in root.iter():
        children = list(element)
        if not children or any(list(child) for child in children):
            continue
        row = {_local_name(child.tag): _text(child) for child in children}
        if len(row) >= 2:
            rows.append(row)
    return rows


def _local_name(tag: str) -> str:
    return tag.rsplit("}", maxsplit=1)[-1]


def _text(element: ElementTree.Element) -> str | None:
    text = element.text.strip() if element.text else ""
    return text or None
