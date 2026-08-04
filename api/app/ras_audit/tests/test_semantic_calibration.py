from pathlib import Path

import pytest

from app.ras_audit.candidate_signals import load_ras_candidate_signals
from app.ras_audit.semantic_calibration import (
    SemanticCalibrationDatasetError,
    evaluate_ras_semantic_classifier,
    load_ras_semantic_calibration_dataset,
)
from app.ras_audit.semantic_classifier import (
    RasTransactionSemanticClassifier,
    load_ras_semantic_policy,
)

ROOT = Path(__file__).resolve().parents[4]


class CalibrationEmbeddingProvider:
    _INDEX = {
        "honoraires": 0,
        "prestation": 1,
        "assistance": 2,
        "consultation": 3,
        "etude": 4,
        "service": 5,
        "loyer": 6,
        "redevance": 7,
    }
    _PARAPHRASE_INDEX = {
        "appui expert ponctuel": 2,
        "avis professionnel specialise": 3,
        "mission d analyse sectorielle": 4,
        "mise a disposition de bureaux": 6,
        "droit d utilisation d une marque": 7,
    }

    def embed_text(self, text: str) -> tuple[float, ...]:
        return self.embed_texts((text,))[0]

    def embed_texts(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        return tuple(self._vector(text) for text in texts)

    def _vector(self, text: str) -> tuple[float, ...]:
        normalized = text.lower()
        index = self._INDEX.get(normalized, self._PARAPHRASE_INDEX.get(normalized, 8))
        return tuple(1.0 if position == index else 0.0 for position in range(9))


def _classifier() -> RasTransactionSemanticClassifier:
    return RasTransactionSemanticClassifier(
        embedding_provider=CalibrationEmbeddingProvider(),
        provider_name="semantic-test",
        model_name="calibration-test-v1",
        signals=load_ras_candidate_signals(
            ROOT / "docs/reference/ras-candidate-signals.csv"
        ),
        policy=load_ras_semantic_policy(
            ROOT / "docs/reference/ras-semantic-classification-policy.csv"
        ),
    )


def test_evaluates_false_positives_and_negatives_by_category() -> None:
    cases = load_ras_semantic_calibration_dataset(
        ROOT / "docs/reference/ras-semantic-calibration-dataset.csv"
    )

    report = evaluate_ras_semantic_classifier(_classifier(), cases)

    assert report.case_count == 8
    assert report.false_positive_count == 0
    assert report.false_negative_count == 0
    assert report.calibration_status == "baseline_unvalidated"
    assert all(metric.precision == 1.0 for metric in report.metrics_by_category)
    assert all(metric.recall == 1.0 for metric in report.metrics_by_category)


def test_rejects_inconsistent_expected_signal(tmp_path: Path) -> None:
    path = tmp_path / "calibration.csv"
    path.write_text(
        "case_id,label,category,expected_match,expected_signal_id\n"
        "CAL-001,Carburant,control,false,SIG-RAS-001\n",
        encoding="utf-8",
    )

    with pytest.raises(SemanticCalibrationDatasetError, match="forbid"):
        load_ras_semantic_calibration_dataset(path)
