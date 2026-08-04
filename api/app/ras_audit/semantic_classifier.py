import csv
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from math import isfinite, sqrt
from pathlib import Path

from app.rag_source.embedding_provider import EmbeddingProvider
from app.ras_audit.candidate_signals import (
    CandidateSignalType,
    RasCandidateSignal,
    normalize_search_text,
)


class SemanticPolicyError(ValueError):
    pass


class SemanticClassificationStatus(StrEnum):
    MATCH = "semantic_match_for_review"
    AMBIGUOUS = "semantic_ambiguous"
    NO_MATCH = "semantic_no_match"
    MISSING_LABEL = "semantic_missing_label"


@dataclass(frozen=True)
class RasSemanticPolicy:
    version: str
    minimum_similarity: float
    minimum_margin: float
    maximum_label_characters: int
    calibration_status: str
    decision_effect: str


@dataclass(frozen=True)
class RasSemanticClassification:
    status: SemanticClassificationStatus
    signal_id: str | None
    operation_hint: str | None
    similarity: float | None
    runner_up_similarity: float | None
    missing_facts: tuple[str, ...]


@dataclass(frozen=True)
class RasSemanticClassificationReport:
    policy_version: str
    provider_name: str
    model_name: str
    calibration_status: str
    results: tuple[RasSemanticClassification, ...]


@dataclass(frozen=True)
class RasSemanticClassificationToolReport:
    sheet_name: str
    source_row_count: int
    rejected_row_count: int
    report: RasSemanticClassificationReport


class RasTransactionSemanticClassifier:
    def __init__(
        self,
        *,
        embedding_provider: EmbeddingProvider,
        provider_name: str,
        model_name: str,
        signals: tuple[RasCandidateSignal, ...],
        policy: RasSemanticPolicy,
    ) -> None:
        references = tuple(
            signal
            for signal in signals
            if signal.signal_type is CandidateSignalType.POSITIVE
        )
        if not references:
            raise ValueError("positive RAS semantic references are required")
        if provider_name.strip().lower() == "deterministic":
            raise ValueError("deterministic hash embeddings are not semantic")
        self._provider = embedding_provider
        self._provider_name = provider_name.strip()
        self._model_name = model_name.strip()
        self._references = references
        self._policy = policy
        self._reference_vectors = self._provider.embed_texts(
            tuple(signal.phrase for signal in references)
        )
        _validate_vectors(self._reference_vectors, expected_count=len(references))

    def classify(
        self,
        labels: tuple[str | None, ...],
    ) -> RasSemanticClassificationReport:
        normalized_labels = tuple(
            normalize_search_text(label or "")[: self._policy.maximum_label_characters]
            for label in labels
        )
        present_labels = tuple(label for label in normalized_labels if label)
        embedded = self._provider.embed_texts(present_labels) if present_labels else ()
        _validate_vectors(embedded, expected_count=len(present_labels))
        vector_iterator = iter(embedded)
        results = tuple(
            self._classify_vector(next(vector_iterator))
            if label
            else RasSemanticClassification(
                status=SemanticClassificationStatus.MISSING_LABEL,
                signal_id=None,
                operation_hint=None,
                similarity=None,
                runner_up_similarity=None,
                missing_facts=("label",),
            )
            for label in normalized_labels
        )
        return RasSemanticClassificationReport(
            policy_version=self._policy.version,
            provider_name=self._provider_name,
            model_name=self._model_name,
            calibration_status=self._policy.calibration_status,
            results=results,
        )

    def _classify_vector(
        self,
        vector: tuple[float, ...],
    ) -> RasSemanticClassification:
        ranked = sorted(
            (
                (_cosine_similarity(vector, reference_vector), signal)
                for signal, reference_vector in zip(
                    self._references,
                    self._reference_vectors,
                    strict=True,
                )
            ),
            key=lambda item: (-item[0], item[1].signal_id),
        )
        best_score, best_signal = ranked[0]
        runner_up = ranked[1][0] if len(ranked) > 1 else 0.0
        if best_score < self._policy.minimum_similarity:
            return RasSemanticClassification(
                status=SemanticClassificationStatus.NO_MATCH,
                signal_id=None,
                operation_hint=None,
                similarity=best_score,
                runner_up_similarity=runner_up,
                missing_facts=("semantic_match",),
            )
        if best_score - runner_up < self._policy.minimum_margin:
            return RasSemanticClassification(
                status=SemanticClassificationStatus.AMBIGUOUS,
                signal_id=best_signal.signal_id,
                operation_hint=best_signal.operation_hint,
                similarity=best_score,
                runner_up_similarity=runner_up,
                missing_facts=("semantic_disambiguation",),
            )
        return RasSemanticClassification(
            status=SemanticClassificationStatus.MATCH,
            signal_id=best_signal.signal_id,
            operation_hint=best_signal.operation_hint,
            similarity=best_score,
            runner_up_similarity=runner_up,
            missing_facts=(),
        )


def load_ras_semantic_policy(path: Path) -> RasSemanticPolicy:
    try:
        with path.open(encoding="utf-8", newline="") as source:
            reader = csv.DictReader(source)
            _validate_policy_columns(reader.fieldnames)
            rows = tuple(reader)
    except OSError as exc:
        raise SemanticPolicyError("RAS semantic policy cannot be read") from exc
    if len(rows) != 1:
        raise SemanticPolicyError("RAS semantic policy must contain exactly one row")
    values = {key: (value or "").strip() for key, value in rows[0].items()}
    try:
        minimum_similarity = float(values["minimum_similarity"])
        minimum_margin = float(values["minimum_margin"])
        maximum_label_characters = int(values["maximum_label_characters"])
    except ValueError as exc:
        raise SemanticPolicyError("invalid RAS semantic policy value") from exc
    if not 0 <= minimum_similarity <= 1 or not 0 <= minimum_margin <= 1:
        raise SemanticPolicyError("semantic thresholds must be between zero and one")
    if not 1 <= maximum_label_characters <= 2_000:
        raise SemanticPolicyError("maximum label characters is invalid")
    if values["decision_effect"] != "review_only":
        raise SemanticPolicyError("semantic policy must be review_only")
    if values["calibration_status"] not in {"baseline_unvalidated", "validated"}:
        raise SemanticPolicyError("invalid semantic calibration status")
    return RasSemanticPolicy(
        version=values["version"],
        minimum_similarity=minimum_similarity,
        minimum_margin=minimum_margin,
        maximum_label_characters=maximum_label_characters,
        calibration_status=values["calibration_status"],
        decision_effect=values["decision_effect"],
    )


def _validate_policy_columns(fieldnames: Sequence[str] | None) -> None:
    required = {
        "version",
        "minimum_similarity",
        "minimum_margin",
        "maximum_label_characters",
        "calibration_status",
        "decision_effect",
    }
    missing = required - set(fieldnames or ())
    if missing:
        raise SemanticPolicyError(
            f"missing semantic policy columns: {', '.join(sorted(missing))}"
        )


def _validate_vectors(
    vectors: tuple[tuple[float, ...], ...],
    *,
    expected_count: int,
) -> None:
    if len(vectors) != expected_count:
        raise ValueError("embedding provider returned an invalid vector count")
    if not vectors:
        return
    dimension = len(vectors[0])
    if dimension < 1 or any(
        len(vector) != dimension or any(not isfinite(value) for value in vector)
        for vector in vectors
    ):
        raise ValueError("embedding provider returned invalid vectors")


def _cosine_similarity(
    left: tuple[float, ...],
    right: tuple[float, ...],
) -> float:
    if len(left) != len(right):
        raise ValueError("embedding vector dimension mismatch")
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return sum(
        left_value * right_value
        for left_value, right_value in zip(left, right, strict=True)
    ) / (left_norm * right_norm)
