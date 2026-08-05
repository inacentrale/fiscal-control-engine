from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.ledger_analysis.posting_key_rules import PostingKeyRule
from app.ras_audit.account_mapping import (
    RasLedgerAccountMapping,
    RasLedgerAccountRole,
    best_account_mapping,
)
from app.ras_audit.accounting_entry import AccountingEntryReconstructionReport
from app.ras_audit.candidate_signals import (
    CandidateSignalStrength,
    CandidateSignalType,
    RasCandidateSignal,
    matching_candidate_signals,
)
from app.ras_audit.domain import CanonicalLedgerEntry
from app.ras_audit.semantic_classifier import (
    RasSemanticClassification,
    RasTransactionSemanticClassifier,
    SemanticClassificationStatus,
)


class RasCandidateStatus(StrEnum):
    ACCOUNT_AND_TEXT = "candidate_account_and_text"
    ACCOUNT_ONLY = "candidate_account_only"
    TEXT_ONLY = "candidate_text_only"
    INDETERMINATE = "candidate_indeterminate"


@dataclass(frozen=True)
class RasCandidateAmount:
    currency: str
    amount: Decimal


@dataclass(frozen=True)
class RasCandidateAssessment:
    candidate_id: str
    accounting_entry_id: str
    status: RasCandidateStatus
    line_ids: tuple[str, ...]
    signal_ids: tuple[str, ...]
    operation_hints: tuple[str, ...]
    account_mapping_ids: tuple[str, ...]
    amounts: tuple[RasCandidateAmount, ...]
    missing_facts: tuple[str, ...]
    exclusion_signal_ids: tuple[str, ...]
    semantic_similarity: float | None = None


@dataclass(frozen=True)
class RasCandidateDetectionReport:
    candidates: tuple[RasCandidateAssessment, ...]
    evaluated_piece_count: int
    excluded_piece_count: int
    semantic_provider_name: str | None = None
    semantic_model_name: str | None = None
    semantic_policy_version: str | None = None
    semantic_calibration_status: str | None = None


@dataclass(frozen=True)
class RasCandidateDetectionToolReport:
    sheet_name: str
    source_row_count: int
    filtered_row_count: int
    filters: dict[str, object]
    rejected_row_count: int
    normalization_issue_codes: tuple[str, ...]
    ledger_entries: tuple[CanonicalLedgerEntry, ...]
    reconstruction: AccountingEntryReconstructionReport
    report: RasCandidateDetectionReport


def candidate_requires_category_split(candidate: RasCandidateAssessment) -> bool:
    return len(candidate.operation_hints) > 1


class RasCandidateDetector:
    def __init__(
        self,
        *,
        posting_key_rules: tuple[PostingKeyRule, ...],
        account_mappings: tuple[RasLedgerAccountMapping, ...],
        signals: tuple[RasCandidateSignal, ...],
        semantic_classifier: RasTransactionSemanticClassifier | None = None,
    ) -> None:
        self._posting_sides = {
            rule.posting_key: rule.side for rule in posting_key_rules
        }
        self._account_mappings = account_mappings
        self._signals = signals
        self._semantic_classifier = semantic_classifier

    def detect(
        self,
        *,
        ledger_entries: tuple[CanonicalLedgerEntry, ...],
        reconstruction: AccountingEntryReconstructionReport,
    ) -> RasCandidateDetectionReport:
        lines_by_id = {line.line_id: line for line in ledger_entries}
        piece_lines = tuple(
            tuple(
                lines_by_id[line_id]
                for line_id in accounting_entry.line_ids
                if line_id in lines_by_id
            )
            for accounting_entry in reconstruction.entries
        )
        semantic_report = (
            self._semantic_classifier.classify(
                tuple(_piece_label(lines) for lines in piece_lines)
            )
            if self._semantic_classifier is not None
            else None
        )
        candidates: list[RasCandidateAssessment] = []
        excluded_count = 0
        for index, (accounting_entry, lines) in enumerate(
            zip(reconstruction.entries, piece_lines, strict=True)
        ):
            assessment, excluded = self._assess_piece(
                accounting_entry.entry_id,
                lines,
                (
                    semantic_report.results[index]
                    if semantic_report is not None
                    else None
                ),
            )
            if assessment is not None:
                candidates.append(assessment)
            elif excluded:
                excluded_count += 1
        return RasCandidateDetectionReport(
            candidates=tuple(candidates),
            evaluated_piece_count=len(reconstruction.entries),
            excluded_piece_count=excluded_count,
            semantic_provider_name=(
                semantic_report.provider_name if semantic_report else None
            ),
            semantic_model_name=(
                semantic_report.model_name if semantic_report else None
            ),
            semantic_policy_version=(
                semantic_report.policy_version if semantic_report else None
            ),
            semantic_calibration_status=(
                semantic_report.calibration_status if semantic_report else None
            ),
        )

    def _assess_piece(
        self,
        accounting_entry_id: str,
        lines: tuple[CanonicalLedgerEntry, ...],
        semantic: RasSemanticClassification | None,
    ) -> tuple[RasCandidateAssessment | None, bool]:
        account_lines: list[tuple[CanonicalLedgerEntry, RasLedgerAccountMapping]] = []
        reverse_account_lines: list[
            tuple[CanonicalLedgerEntry, RasLedgerAccountMapping]
        ] = []
        unknown_side_lines: list[
            tuple[CanonicalLedgerEntry, RasLedgerAccountMapping]
        ] = []
        positive_signals: dict[str, RasCandidateSignal] = {}
        exclusion_signals: dict[str, RasCandidateSignal] = {}

        for line in lines:
            signals = matching_candidate_signals(
                self._signals,
                line.label,
                posting_date=line.posting_date,
            )
            for signal in signals:
                target = (
                    positive_signals
                    if signal.signal_type is CandidateSignalType.POSITIVE
                    else exclusion_signals
                )
                target[signal.signal_id] = signal
            mapping = self._expense_mapping(line)
            if mapping is None:
                continue
            side = self._posting_sides.get(line.posting_key or "")
            if side is None:
                unknown_side_lines.append((line, mapping))
            elif side == mapping.normal_side.value:
                account_lines.append((line, mapping))
            else:
                reverse_account_lines.append((line, mapping))

        # A credit-side movement on an expense account is an avoir/reversal signal,
        # not a new expense candidate. Text alone must not turn it back into one.
        if reverse_account_lines and not account_lines and not unknown_side_lines:
            return None, True

        has_account_evidence = bool(account_lines or unknown_side_lines)
        semantic_is_match = (
            semantic is not None
            and semantic.status is SemanticClassificationStatus.MATCH
        )
        semantic_is_ambiguous = (
            semantic is not None
            and semantic.status is SemanticClassificationStatus.AMBIGUOUS
        )
        has_text_evidence = bool(positive_signals) or semantic_is_match
        if not has_account_evidence and not has_text_evidence:
            if exclusion_signals:
                return None, True
            if semantic_is_ambiguous:
                assert semantic is not None
                return self._semantic_only_ambiguous(
                    accounting_entry_id,
                    lines,
                    semantic,
                    exclusion_signals,
                ), False
            return None, bool(exclusion_signals)
        # An exclusion phrase can suppress text-only noise, never configured
        # account evidence. The result remains a review candidate, not a tax decision.
        if exclusion_signals and not has_account_evidence:
            return None, True

        missing_facts: list[str] = []
        if unknown_side_lines:
            missing_facts.append("posting_key_side")
        if semantic_is_ambiguous:
            missing_facts.append("semantic_disambiguation")
        if has_account_evidence and has_text_evidence:
            status = RasCandidateStatus.ACCOUNT_AND_TEXT
        elif has_account_evidence and unknown_side_lines and not account_lines:
            status = RasCandidateStatus.INDETERMINATE
        elif has_account_evidence:
            status = RasCandidateStatus.ACCOUNT_ONLY
        else:
            status = RasCandidateStatus.TEXT_ONLY
        if positive_signals and not any(
            signal.strength is CandidateSignalStrength.STRONG
            for signal in positive_signals.values()
        ):
            missing_facts.append("strong_semantic_signal")

        evidence_lines = tuple(dict.fromkeys(
            [
                line.line_id
                for line, _ in (
                    account_lines + reverse_account_lines + unknown_side_lines
                )
            ]
            + [
                line.line_id
                for line in lines
                if matching_candidate_signals(
                    tuple(positive_signals.values()),
                    line.label,
                    posting_date=line.posting_date,
                )
            ]
        ))
        mappings = tuple(dict.fromkeys(
            mapping.mapping_id
            for _, mapping in (
                account_lines + reverse_account_lines + unknown_side_lines
            )
        ))
        semantic_signal_ids = (
            (semantic.signal_id,)
            if semantic_is_match and semantic is not None and semantic.signal_id
            else ()
        )
        semantic_hints = (
            (semantic.operation_hint,)
            if semantic_is_match and semantic is not None and semantic.operation_hint
            else ()
        )
        return RasCandidateAssessment(
            candidate_id=accounting_entry_id,
            accounting_entry_id=accounting_entry_id,
            status=status,
            line_ids=evidence_lines,
            signal_ids=tuple(sorted(set(positive_signals) | set(semantic_signal_ids))),
            operation_hints=tuple(
                sorted(
                    {signal.operation_hint for signal in positive_signals.values()}
                    | set(semantic_hints)
                )
            ),
            account_mapping_ids=mappings,
            amounts=_amounts(account_lines, reverse_account_lines),
            missing_facts=tuple(missing_facts),
            exclusion_signal_ids=tuple(sorted(exclusion_signals)),
            semantic_similarity=(semantic.similarity if semantic else None),
        ), False

    def _semantic_only_ambiguous(
        self,
        accounting_entry_id: str,
        lines: tuple[CanonicalLedgerEntry, ...],
        semantic: RasSemanticClassification,
        exclusions: dict[str, RasCandidateSignal],
    ) -> RasCandidateAssessment:
        return RasCandidateAssessment(
            candidate_id=accounting_entry_id,
            accounting_entry_id=accounting_entry_id,
            status=RasCandidateStatus.INDETERMINATE,
            line_ids=tuple(line.line_id for line in lines if line.label),
            signal_ids=((semantic.signal_id,) if semantic.signal_id else ()),
            operation_hints=(
                (semantic.operation_hint,) if semantic.operation_hint else ()
            ),
            account_mapping_ids=(),
            amounts=(),
            missing_facts=("semantic_disambiguation",),
            exclusion_signal_ids=tuple(sorted(exclusions)),
            semantic_similarity=semantic.similarity,
        )

    def _expense_mapping(
        self,
        line: CanonicalLedgerEntry,
    ) -> RasLedgerAccountMapping | None:
        if line.account_number is None or line.posting_date is None:
            return None
        return best_account_mapping(
            self._account_mappings,
            line.account_number,
            role=RasLedgerAccountRole.EXPENSE_CANDIDATE,
            posting_date=line.posting_date,
            company_code=line.company_code,
        )


def _amounts(
    normal_lines: list[tuple[CanonicalLedgerEntry, RasLedgerAccountMapping]],
    reverse_lines: list[tuple[CanonicalLedgerEntry, RasLedgerAccountMapping]],
) -> tuple[RasCandidateAmount, ...]:
    totals: dict[str, Decimal] = {}
    for line, _ in normal_lines:
        if line.amount is not None and line.currency is not None:
            totals[line.currency] = totals.get(line.currency, Decimal("0")) + abs(
                line.amount
            )
    for line, _ in reverse_lines:
        if line.amount is not None and line.currency is not None:
            totals[line.currency] = totals.get(line.currency, Decimal("0")) - abs(
                line.amount
            )
    return tuple(
        RasCandidateAmount(currency=currency, amount=amount)
        for currency, amount in sorted(totals.items())
    )


def _piece_label(lines: tuple[CanonicalLedgerEntry, ...]) -> str | None:
    labels = tuple(dict.fromkeys(line.label for line in lines if line.label))
    return " | ".join(labels) if labels else None
