from pathlib import Path

import pytest

from app.ras_audit.candidate_signals import (
    CandidateSignalError,
    CandidateSignalType,
    load_ras_candidate_signals,
    matching_candidate_signals,
)

ROOT = Path(__file__).resolve().parents[4]
SIGNALS_PATH = ROOT / "docs/reference/ras-candidate-signals.csv"


def test_loads_review_only_versioned_candidate_signals() -> None:
    signals = load_ras_candidate_signals(SIGNALS_PATH)

    assert signals
    assert all(signal.version == "1.0.0" for signal in signals)
    assert all(signal.review_only for signal in signals)
    assert {signal.signal_type for signal in signals} == {
        CandidateSignalType.POSITIVE,
        CandidateSignalType.EXCLUSION,
    }


def test_matching_is_accent_insensitive_and_word_bounded() -> None:
    signals = load_ras_candidate_signals(SIGNALS_PATH)

    matches = matching_candidate_signals(
        signals,
        "Étude et prestations spécialisées",
        posting_date=None,
    )
    assert {match.signal_id for match in matches} == {
        "SIG-RAS-002",
        "SIG-RAS-005",
    }
    assert not matching_candidate_signals(
        signals,
        "desservice interne",
        posting_date=None,
    )


def test_loader_rejects_a_signal_that_claims_a_tax_decision(
    tmp_path: Path,
) -> None:
    source = tmp_path / "signals.csv"
    source.write_text(
        "signal_id,version,signal_type,phrase,strength,operation_hint,"
        "valid_from,valid_to,source_kind,source_reference,decision_effect\n"
        "S1,1,positive,service,strong,service,,,internal,test,subject_to_ras\n",
        encoding="utf-8",
    )

    with pytest.raises(CandidateSignalError, match="review_only"):
        load_ras_candidate_signals(source)
