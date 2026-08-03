from pathlib import Path

import pytest

from app.tax_declaration.domain import (
    CanonicalField,
    DeclarationSourceFormat,
    FieldProvenance,
    ResolutionStatus,
    SourceReference,
)


def test_unresolved_field_preserves_source_and_provenance() -> None:
    source = SourceReference(
        file_name="declaration.bin",
        source_format=DeclarationSourceFormat.UNKNOWN,
        content_type=None,
        content_sha256="a" * 64,
    )

    field = CanonicalField(
        name="taxpayer_identifier",
        source_value="identifiant libre",
        normalized_value=None,
        confidence=0.4,
        status=ResolutionStatus.UNRESOLVED,
        provenance=FieldProvenance(source_reference=source, locator="page:1"),
    )

    assert field.source_value == "identifiant libre"
    assert field.normalized_value is None
    assert field.provenance.locator == "page:1"


def test_resolved_field_requires_a_normalized_value() -> None:
    source = SourceReference(
        file_name=Path("declaration.csv").name,
        source_format=DeclarationSourceFormat.CSV,
        content_type="text/csv",
        content_sha256="b" * 64,
    )

    with pytest.raises(ValueError, match="normalized value"):
        CanonicalField(
            name="taxpayer_identifier",
            source_value="123",
            normalized_value=None,
            confidence=0.9,
            status=ResolutionStatus.RESOLVED,
            provenance=FieldProvenance(source_reference=source, locator="row:2"),
        )

