from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.ras_audit.fact_context import (
    RasExplicitFactExtractor,
    RasFactContextAttestor,
    RasFactContextError,
    load_ras_user_fact_patterns,
)

PATTERNS = Path("../docs/reference/ras-user-fact-patterns.csv")
NOW = datetime(2026, 8, 4, 12, tzinfo=UTC)


def test_extracts_only_explicit_facts_with_message_evidence() -> None:
    extractor = RasExplicitFactExtractor(load_ras_user_fact_patterns(PATTERNS))

    result = extractor.extract(
        "Le prestataire non résident ne dispose pas d'établissement stable."
    )

    assert {item.fact.name: item.fact.value for item in result.facts} == {
        "residence_status": "nonresident",
        "stable_establishment_status": "false",
    }
    assert all("user_message:" in item.fact.evidence_reference for item in result.facts)


def test_conflicting_explicit_values_are_not_attested() -> None:
    extractor = RasExplicitFactExtractor(load_ras_user_fact_patterns(PATTERNS))

    result = extractor.extract(
        "Le prestataire résident puis le prestataire non résident."
    )

    assert "residence_status" in result.conflicting_fact_names
    assert all(item.fact.name != "residence_status" for item in result.facts)


def test_extracts_explicit_tax_base_and_currency_without_float_conversion() -> None:
    extractor = RasExplicitFactExtractor(load_ras_user_fact_patterns(PATTERNS))

    result = extractor.extract("L'assiette fiscale est de 100 000,50 XOF.")

    assert {item.fact.name: item.fact.value for item in result.facts} == {
        "tax_base_amount": "100000.50",
        "currency": "XOF",
    }


def test_extracts_sourced_payment_event_date_without_llm_inference() -> None:
    extractor = RasExplicitFactExtractor(load_ras_user_fact_patterns(PATTERNS))

    result = extractor.extract("Le paiement effectu\u00e9 le 10/01/2025.")

    assert {item.fact.name: item.fact.value for item in result.facts} == {
        "payment_date": "2025-01-10",
        "payment_status": "paid",
    }

    without_accents = extractor.extract("Le paiement effectue le 2025-01-10.")
    assert {item.fact.name: item.fact.value for item in without_accents.facts} == {
        "payment_date": "2025-01-10",
        "payment_status": "paid",
    }


def test_invalid_payment_date_is_not_attested() -> None:
    extractor = RasExplicitFactExtractor(load_ras_user_fact_patterns(PATTERNS))

    result = extractor.extract("Le paiement effectu\u00e9 le 31/02/2025.")

    assert result.facts == ()


def test_signed_context_round_trip_and_tamper_rejection() -> None:
    extractor = RasExplicitFactExtractor(load_ras_user_fact_patterns(PATTERNS))
    extraction = extractor.extract("Il s'agit d'une prestation de services.")
    attestor = RasFactContextAttestor("k" * 32, now=lambda: NOW)

    token = attestor.issue(
        message="Il s'agit d'une prestation de services.",
        extraction=extraction,
        session_id="session-1",
        file_id="file-1",
    )
    verified = attestor.verify(token)

    assert verified.session_id == "session-1"
    assert [(fact.name, fact.value) for fact in verified.facts] == [
        ("operation_type", "service_any")
    ]
    with pytest.raises(RasFactContextError, match="signature"):
        attestor.verify(token[:-1] + ("A" if token[-1] != "A" else "B"))


def test_expired_context_is_rejected() -> None:
    extractor = RasExplicitFactExtractor(load_ras_user_fact_patterns(PATTERNS))
    extraction = extractor.extract("Prestation de services")
    issued = RasFactContextAttestor("k" * 32, now=lambda: NOW).issue(
        message="Prestation de services",
        extraction=extraction,
        session_id=None,
        file_id=None,
    )
    verifier = RasFactContextAttestor(
        "k" * 32,
        max_age=timedelta(minutes=15),
        now=lambda: NOW + timedelta(minutes=16),
    )

    with pytest.raises(RasFactContextError, match="expired"):
        verifier.verify(issued)
