from pathlib import Path

import pytest

from app.ras_audit.candidate_signals import load_ras_candidate_signals
from app.ras_audit.semantic_classifier import (
    RasTransactionSemanticClassifier,
    SemanticClassificationStatus,
    SemanticPolicyError,
    load_ras_semantic_policy,
)

ROOT = Path(__file__).resolve().parents[4]


class SemanticTestEmbeddingProvider:
    _REFERENCE_INDEX = {
        "honoraires": 0,
        "prestation": 1,
        "assistance": 2,
        "consultation": 3,
        "etude": 4,
        "service": 5,
        "loyer": 6,
        "redevance": 7,
    }

    def embed_text(self, text: str) -> tuple[float, ...]:
        return self.embed_texts((text,))[0]

    def embed_texts(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        return tuple(self._vector(text) for text in texts)

    def _vector(self, text: str) -> tuple[float, ...]:
        normalized = text.lower()
        if "appui expert" in normalized:
            index = 2
        elif "avis professionnel ambigu" in normalized:
            return (0.74, 0, 0, 0.6726, 0, 0, 0, 0, 0)
        elif normalized in self._REFERENCE_INDEX:
            index = self._REFERENCE_INDEX[normalized]
        else:
            index = 8
        return tuple(1.0 if position == index else 0.0 for position in range(9))


def _classifier() -> RasTransactionSemanticClassifier:
    return RasTransactionSemanticClassifier(
        embedding_provider=SemanticTestEmbeddingProvider(),
        provider_name="semantic-test",
        model_name="synthetic-model-v1",
        signals=load_ras_candidate_signals(
            ROOT / "docs/reference/ras-candidate-signals.csv"
        ),
        policy=load_ras_semantic_policy(
            ROOT / "docs/reference/ras-semantic-classification-policy.csv"
        ),
    )


def test_classifies_semantic_paraphrase_for_review_with_model_trace() -> None:
    report = _classifier().classify(("Appui expert ponctuel",))

    result = report.results[0]
    assert result.status is SemanticClassificationStatus.MATCH
    assert result.signal_id == "SIG-RAS-003"
    assert result.operation_hint == "assistance_service"
    assert result.similarity == pytest.approx(1.0)
    assert report.policy_version == "1.0.0"
    assert report.model_name == "synthetic-model-v1"
    assert report.calibration_status == "baseline_unvalidated"


def test_keeps_close_semantic_matches_ambiguous() -> None:
    result = _classifier().classify(("Avis professionnel ambigu",)).results[0]

    assert result.status is SemanticClassificationStatus.AMBIGUOUS
    assert result.missing_facts == ("semantic_disambiguation",)


def test_returns_no_match_and_missing_label_without_guessing() -> None:
    results = _classifier().classify(("Approvisionnement carburant", None)).results

    assert results[0].status is SemanticClassificationStatus.NO_MATCH
    assert results[0].signal_id is None
    assert results[1].status is SemanticClassificationStatus.MISSING_LABEL
    assert results[1].missing_facts == ("label",)


def test_rejects_hash_embeddings_as_semantic_classifier() -> None:
    with pytest.raises(ValueError, match="not semantic"):
        RasTransactionSemanticClassifier(
            embedding_provider=SemanticTestEmbeddingProvider(),
            provider_name="deterministic",
            model_name="hash",
            signals=load_ras_candidate_signals(
                ROOT / "docs/reference/ras-candidate-signals.csv"
            ),
            policy=load_ras_semantic_policy(
                ROOT / "docs/reference/ras-semantic-classification-policy.csv"
            ),
        )


def test_policy_rejects_a_tax_decision_effect(tmp_path: Path) -> None:
    policy_path = tmp_path / "policy.csv"
    policy_path.write_text(
        "version,minimum_similarity,minimum_margin,maximum_label_characters,"
        "calibration_status,decision_effect\n"
        "1,0.7,0.1,100,validated,subject_to_ras\n",
        encoding="utf-8",
    )

    with pytest.raises(SemanticPolicyError, match="review_only"):
        load_ras_semantic_policy(policy_path)
