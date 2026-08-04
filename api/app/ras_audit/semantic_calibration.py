import csv
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from app.ras_audit.semantic_classifier import (
    RasTransactionSemanticClassifier,
    SemanticClassificationStatus,
)


class SemanticCalibrationDatasetError(ValueError):
    pass


@dataclass(frozen=True)
class RasSemanticCalibrationCase:
    case_id: str
    label: str
    category: str
    expected_match: bool
    expected_signal_id: str | None


@dataclass(frozen=True)
class RasSemanticCategoryMetrics:
    category: str
    true_positives: int
    false_positives: int
    false_negatives: int
    true_negatives: int

    @property
    def precision(self) -> float:
        denominator = self.true_positives + self.false_positives
        return self.true_positives / denominator if denominator else 1.0

    @property
    def recall(self) -> float:
        denominator = self.true_positives + self.false_negatives
        return self.true_positives / denominator if denominator else 1.0


@dataclass(frozen=True)
class RasSemanticCalibrationReport:
    policy_version: str
    provider_name: str
    model_name: str
    calibration_status: str
    case_count: int
    metrics_by_category: tuple[RasSemanticCategoryMetrics, ...]

    @property
    def false_positive_count(self) -> int:
        return sum(item.false_positives for item in self.metrics_by_category)

    @property
    def false_negative_count(self) -> int:
        return sum(item.false_negatives for item in self.metrics_by_category)


def load_ras_semantic_calibration_dataset(
    path: Path,
) -> tuple[RasSemanticCalibrationCase, ...]:
    try:
        with path.open(encoding="utf-8", newline="") as source:
            reader = csv.DictReader(source)
            _validate_columns(reader.fieldnames)
            rows = tuple(reader)
    except OSError as exc:
        raise SemanticCalibrationDatasetError(
            "RAS semantic calibration dataset cannot be read"
        ) from exc
    if not rows:
        raise SemanticCalibrationDatasetError(
            "RAS semantic calibration dataset cannot be empty"
        )
    cases: list[RasSemanticCalibrationCase] = []
    seen_ids: set[str] = set()
    for row in rows:
        values = {key: (value or "").strip() for key, value in row.items()}
        case_id = values["case_id"]
        if not case_id or case_id in seen_ids:
            raise SemanticCalibrationDatasetError(
                "calibration case identifiers must be unique and non-empty"
            )
        seen_ids.add(case_id)
        expected = values["expected_match"].lower()
        if expected not in {"true", "false"}:
            raise SemanticCalibrationDatasetError("invalid expected_match value")
        expected_match = expected == "true"
        signal_id = values["expected_signal_id"] or None
        if expected_match != (signal_id is not None):
            raise SemanticCalibrationDatasetError(
                "expected matches require a signal and non-matches forbid one"
            )
        if not values["label"] or not values["category"]:
            raise SemanticCalibrationDatasetError(
                "calibration label and category are required"
            )
        cases.append(
            RasSemanticCalibrationCase(
                case_id=case_id,
                label=values["label"],
                category=values["category"],
                expected_match=expected_match,
                expected_signal_id=signal_id,
            )
        )
    return tuple(cases)


def evaluate_ras_semantic_classifier(
    classifier: RasTransactionSemanticClassifier,
    cases: Sequence[RasSemanticCalibrationCase],
) -> RasSemanticCalibrationReport:
    if not cases:
        raise ValueError("semantic calibration cases are required")
    classification = classifier.classify(tuple(case.label for case in cases))
    counts: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0, 0])
    for case, result in zip(cases, classification.results, strict=True):
        predicted_match = result.status is SemanticClassificationStatus.MATCH
        correct_signal = result.signal_id == case.expected_signal_id
        if case.expected_match and predicted_match and correct_signal:
            counts[case.category][0] += 1
        elif not case.expected_match and predicted_match:
            counts[case.category][1] += 1
        elif case.expected_match:
            counts[case.category][2] += 1
        else:
            counts[case.category][3] += 1
    metrics = tuple(
        RasSemanticCategoryMetrics(category, *values)
        for category, values in sorted(counts.items())
    )
    return RasSemanticCalibrationReport(
        policy_version=classification.policy_version,
        provider_name=classification.provider_name,
        model_name=classification.model_name,
        calibration_status=classification.calibration_status,
        case_count=len(cases),
        metrics_by_category=metrics,
    )


def _validate_columns(fieldnames: Sequence[str] | None) -> None:
    required = {
        "case_id",
        "label",
        "category",
        "expected_match",
        "expected_signal_id",
    }
    missing = required - set(fieldnames or ())
    if missing:
        raise SemanticCalibrationDatasetError(
            f"missing semantic calibration columns: {', '.join(sorted(missing))}"
        )
