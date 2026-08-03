from datetime import date

import pytest

from app.rag_source.domain import (
    FiscalSourceDocument,
    FiscalSourceMetadata,
    FiscalSourceOrigin,
    FiscalSourceStatus,
    FiscalSourceType,
    RagApplicabilityStatus,
    RagSourceDocument,
    RagSourceMetadata,
    RagSourceOrigin,
    RagSourceStatus,
    RagSourceType,
)


def test_reference_source_metadata_is_normalized() -> None:
    metadata = RagSourceMetadata(
        country=" bf ",
        source_type=RagSourceType.TAX_CODE,
        title="  Code general des impots ",
        version="2025",
        language=" fr ",
        origin=RagSourceOrigin.ANONYMIZED_REFERENCE,
        source_path="docs/source/cgi-bf-2025.pdf",
        themes=(" ras ", " TVA"),
        applicable_from=date(2025, 1, 1),
        applicability_status=RagApplicabilityStatus.CONFIRMED,
    )

    assert metadata.domain == "fiscal"
    assert metadata.country == "BF"
    assert metadata.title == "Code general des impots"
    assert metadata.language == "fr"
    assert metadata.themes == ("ras", "TVA")
    assert metadata.applicable_from == date(2025, 1, 1)
    assert metadata.applicability_status is RagApplicabilityStatus.CONFIRMED


def test_metadata_rejects_an_inverted_applicability_period() -> None:
    with pytest.raises(ValueError, match="applicable_to"):
        RagSourceMetadata(
            country="BF",
            source_type=RagSourceType.TAX_CODE,
            title="Code general des impots",
            version="2025",
            language="fr",
            origin=RagSourceOrigin.ANONYMIZED_REFERENCE,
            source_path="docs/source/cgi.pdf",
            themes=("RAS",),
            applicable_from=date(2025, 1, 1),
            applicable_to=date(2024, 12, 31),
            applicability_status=RagApplicabilityStatus.CONFIRMED,
        )


def test_confirmed_applicability_requires_a_start_date() -> None:
    with pytest.raises(ValueError, match="requires applicable_from"):
        RagSourceMetadata(
            country="BF",
            source_type=RagSourceType.TAX_CODE,
            title="Code general des impots",
            version="2025",
            language="fr",
            origin=RagSourceOrigin.ANONYMIZED_REFERENCE,
            source_path="docs/source/cgi.pdf",
            themes=("RAS",),
            applicability_status=RagApplicabilityStatus.CONFIRMED,
        )


def test_non_fiscal_source_metadata_is_supported() -> None:
    metadata = RagSourceMetadata(
        domain="compliance",
        source_type=RagSourceType.INTERNAL_PROCEDURE,
        title="Politique de confidentialite",
        version="2026-07-28",
        language="fr",
        origin=RagSourceOrigin.ANONYMIZED_REFERENCE,
        source_path="docs/reference/policy.csv",
        themes=("donnees sensibles",),
    )

    assert metadata.domain == "compliance"
    assert metadata.country is None
    assert metadata.source_type is RagSourceType.INTERNAL_PROCEDURE


def test_official_fiscal_source_types_are_supported() -> None:
    assert RagSourceType.LAW.value == "law"
    assert RagSourceType.ADMINISTRATIVE_INSTRUCTION.value == (
        "administrative_instruction"
    )
    assert RagSourceType.OFFICIAL_FORM.value == "official_form"


def test_user_upload_requires_an_opaque_owner_reference() -> None:
    with pytest.raises(ValueError, match="owner_reference"):
        RagSourceMetadata(
            country="BF",
            source_type=RagSourceType.BUSINESS_NOTE,
            title="Note fiscale client",
            version="2026-07-28",
            language="fr",
            origin=RagSourceOrigin.USER_UPLOAD,
            source_path="uploads/source.pdf",
            themes=("RAS",),
        )


def test_metadata_rejects_empty_required_fields() -> None:
    with pytest.raises(ValueError, match="title"):
        RagSourceMetadata(
            country="BF",
            source_type=RagSourceType.TAX_CODE,
            title=" ",
            version="2025",
            language="fr",
            origin=RagSourceOrigin.ANONYMIZED_REFERENCE,
            source_path="docs/source/cgi.pdf",
            themes=("RAS",),
        )


def test_metadata_rejects_a_non_https_source_url() -> None:
    with pytest.raises(ValueError, match="source_url must use HTTPS"):
        RagSourceMetadata(
            country="BF",
            source_type=RagSourceType.TAX_CODE,
            title="Code general des impots",
            version="2025",
            language="fr",
            origin=RagSourceOrigin.ANONYMIZED_REFERENCE,
            source_path="docs/source/cgi.pdf",
            themes=("RAS",),
            source_url="http://example.test/cgi.pdf",
        )


def test_metadata_requires_at_least_one_theme() -> None:
    with pytest.raises(ValueError, match="themes"):
        RagSourceMetadata(
            country="BF",
            source_type=RagSourceType.TAX_CODE,
            title="Code general des impots",
            version="2025",
            language="fr",
            origin=RagSourceOrigin.ANONYMIZED_REFERENCE,
            source_path="docs/source/cgi.pdf",
            themes=(),
        )


def test_document_is_indexable_only_when_active_with_text_hash() -> None:
    metadata = RagSourceMetadata(
        country="BF",
        source_type=RagSourceType.TAX_CODE,
        title="Code general des impots",
        version="2025",
        language="fr",
        origin=RagSourceOrigin.ANONYMIZED_REFERENCE,
        source_path="docs/source/cgi.pdf",
        themes=("RAS",),
    )

    pending_document = RagSourceDocument(
        metadata=metadata,
        text_sha256="abc123",
        status=RagSourceStatus.PENDING_REVIEW,
    )
    active_document = RagSourceDocument(
        metadata=metadata,
        text_sha256="abc123",
        status=RagSourceStatus.ACTIVE,
    )

    assert pending_document.can_be_indexed is False
    assert active_document.can_be_indexed is True


def test_document_rejects_empty_text_hash() -> None:
    metadata = RagSourceMetadata(
        country="BF",
        source_type=RagSourceType.TAX_CODE,
        title="Code general des impots",
        version="2025",
        language="fr",
        origin=RagSourceOrigin.ANONYMIZED_REFERENCE,
        source_path="docs/source/cgi.pdf",
        themes=("RAS",),
    )

    with pytest.raises(ValueError, match="text_sha256"):
        RagSourceDocument(
            metadata=metadata,
            text_sha256=" ",
            status=RagSourceStatus.ACTIVE,
        )


def test_fiscal_names_are_kept_as_compatibility_aliases() -> None:
    assert FiscalSourceMetadata is RagSourceMetadata
    assert FiscalSourceDocument is RagSourceDocument
    assert FiscalSourceType is RagSourceType
    assert FiscalSourceOrigin is RagSourceOrigin
    assert FiscalSourceStatus is RagSourceStatus
