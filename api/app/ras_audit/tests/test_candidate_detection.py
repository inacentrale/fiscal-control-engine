from dataclasses import replace
from decimal import Decimal
from pathlib import Path

from app.ledger_analysis.posting_key_rules import load_posting_key_rules
from app.ras_audit.account_mapping import load_ras_ledger_account_mappings
from app.ras_audit.accounting_entry import AccountingEntryReconstructor
from app.ras_audit.candidate_detection import (
    RasCandidateDetector,
    RasCandidateStatus,
)
from app.ras_audit.candidate_signals import load_ras_candidate_signals
from app.ras_audit.golden_dataset import load_golden_dataset
from app.ras_audit.semantic_classifier import (
    RasTransactionSemanticClassifier,
    load_ras_semantic_policy,
)

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = Path(__file__).parent / "fixtures"


def _detector() -> RasCandidateDetector:
    return RasCandidateDetector(
        posting_key_rules=load_posting_key_rules(
            ROOT / "docs/reference/sap-posting-key-rules.csv"
        ),
        account_mappings=load_ras_ledger_account_mappings(
            FIXTURES / "account-mapping/valid.csv"
        ),
        signals=load_ras_candidate_signals(
            ROOT / "docs/reference/ras-candidate-signals.csv"
        ),
    )


def test_detects_every_expected_golden_candidate_without_false_positive() -> None:
    dataset = load_golden_dataset(FIXTURES / "golden")
    posting_rules = load_posting_key_rules(
        ROOT / "docs/reference/sap-posting-key-rules.csv"
    )
    detected_by_scenario: dict[str, bool] = {}

    for scenario in dataset.scenarios:
        reconstruction = AccountingEntryReconstructor(posting_rules).reconstruct(
            scenario.entries
        )
        report = _detector().detect(
            ledger_entries=scenario.entries,
            reconstruction=reconstruction,
        )
        detected_by_scenario[scenario.scenario_id] = bool(report.candidates)

    assert detected_by_scenario == {
        scenario.scenario_id: scenario.expected_candidate_signal
        for scenario in dataset.scenarios
    }


def test_groups_multiline_expense_as_one_candidate_piece() -> None:
    dataset = load_golden_dataset(FIXTURES / "golden")
    scenario = next(item for item in dataset.scenarios if item.scenario_id == "SYN-004")
    posting_rules = load_posting_key_rules(
        ROOT / "docs/reference/sap-posting-key-rules.csv"
    )

    report = _detector().detect(
        ledger_entries=scenario.entries,
        reconstruction=AccountingEntryReconstructor(posting_rules).reconstruct(
            scenario.entries
        ),
    )

    assert len(report.candidates) == 1
    assert report.candidates[0].status is RasCandidateStatus.ACCOUNT_AND_TEXT
    assert report.candidates[0].amounts[0].amount == 100_000


def test_does_not_turn_a_reversal_into_a_second_candidate() -> None:
    dataset = load_golden_dataset(FIXTURES / "golden")
    scenario = next(item for item in dataset.scenarios if item.scenario_id == "SYN-005")
    posting_rules = load_posting_key_rules(
        ROOT / "docs/reference/sap-posting-key-rules.csv"
    )

    report = _detector().detect(
        ledger_entries=scenario.entries,
        reconstruction=AccountingEntryReconstructor(posting_rules).reconstruct(
            scenario.entries
        ),
    )

    assert len(report.candidates) == 1
    assert report.candidates[0].amounts[0].amount == 100_000


def test_credit_note_on_expense_account_is_not_a_text_only_candidate() -> None:
    dataset = load_golden_dataset(FIXTURES / "golden")
    scenario = next(item for item in dataset.scenarios if item.scenario_id == "SYN-002")
    entries = tuple(
        replace(
            entry,
            posting_key="50",
            label="Avoir sur prestation technique",
        )
        if entry.account_number == "632200"
        else entry
        for entry in scenario.entries
    )
    posting_rules = load_posting_key_rules(
        ROOT / "docs/reference/sap-posting-key-rules.csv"
    )

    report = _detector().detect(
        ledger_entries=entries,
        reconstruction=AccountingEntryReconstructor(posting_rules).reconstruct(entries),
    )

    assert report.candidates == ()
    assert report.excluded_piece_count == 1


def test_same_piece_credit_note_reduces_candidate_amount_per_currency() -> None:
    dataset = load_golden_dataset(FIXTURES / "golden")
    scenario = next(item for item in dataset.scenarios if item.scenario_id == "SYN-002")
    expense = next(
        entry for entry in scenario.entries if entry.account_number == "632200"
    )
    entries = scenario.entries + (
        replace(
            expense,
            line_id="credit-note-line",
            line_number="003",
            posting_key="50",
            amount=Decimal("50000"),
            label="Avoir partiel prestation technique",
        ),
    )
    posting_rules = load_posting_key_rules(
        ROOT / "docs/reference/sap-posting-key-rules.csv"
    )

    report = _detector().detect(
        ledger_entries=entries,
        reconstruction=AccountingEntryReconstructor(posting_rules).reconstruct(entries),
    )

    assert len(report.candidates) == 1
    assert report.candidates[0].amounts[0].amount == 150_000
    assert "credit-note-line" in report.candidates[0].line_ids


def test_unknown_account_requires_text_evidence_and_stays_text_only() -> None:
    dataset = load_golden_dataset(FIXTURES / "golden")
    scenario = next(item for item in dataset.scenarios if item.scenario_id == "SYN-002")
    entries_without_signal = tuple(
        replace(entry, account_number="999999", label="Achat de carburant")
        if entry.account_number == "632200"
        else entry
        for entry in scenario.entries
    )
    entries_with_signal = tuple(
        replace(entry, account_number="999999")
        if entry.account_number == "632200"
        else entry
        for entry in scenario.entries
    )
    posting_rules = load_posting_key_rules(
        ROOT / "docs/reference/sap-posting-key-rules.csv"
    )

    without_signal = _detector().detect(
        ledger_entries=entries_without_signal,
        reconstruction=AccountingEntryReconstructor(posting_rules).reconstruct(
            entries_without_signal
        ),
    )
    with_signal = _detector().detect(
        ledger_entries=entries_with_signal,
        reconstruction=AccountingEntryReconstructor(posting_rules).reconstruct(
            entries_with_signal
        ),
    )

    assert without_signal.candidates == ()
    assert with_signal.candidates[0].status is RasCandidateStatus.TEXT_ONLY
    assert with_signal.candidates[0].account_mapping_ids == ()


def test_unknown_posting_key_remains_candidate_but_is_indeterminate() -> None:
    dataset = load_golden_dataset(FIXTURES / "golden")
    scenario = next(item for item in dataset.scenarios if item.scenario_id == "SYN-008")
    posting_rules = load_posting_key_rules(
        ROOT / "docs/reference/sap-posting-key-rules.csv"
    )

    report = _detector().detect(
        ledger_entries=scenario.entries,
        reconstruction=AccountingEntryReconstructor(posting_rules).reconstruct(
            scenario.entries
        ),
    )

    assert report.candidates[0].status is RasCandidateStatus.ACCOUNT_AND_TEXT
    assert report.candidates[0].missing_facts == ("posting_key_side",)
    assert report.candidates[0].amounts == ()


class HybridSemanticTestProvider:
    def embed_text(self, text: str) -> tuple[float, ...]:
        return self.embed_texts((text,))[0]

    def embed_texts(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        vectors = []
        references = (
            "honoraires",
            "prestation",
            "assistance",
            "consultation",
            "etude",
            "service",
            "loyer",
            "redevance",
        )
        for text in texts:
            normalized = text.lower()
            index = 2 if "appui expert" in normalized else 8
            if normalized in references:
                index = references.index(normalized)
            vectors.append(
                tuple(1.0 if position == index else 0.0 for position in range(9))
            )
        return tuple(vectors)


def test_hybrid_detector_adds_semantic_paraphrase_as_review_candidate() -> None:
    dataset = load_golden_dataset(FIXTURES / "golden")
    scenario = next(item for item in dataset.scenarios if item.scenario_id == "SYN-002")
    entries = tuple(
        replace(entry, account_number="621100", label="Appui expert ponctuel")
        if index == 0
        else entry
        for index, entry in enumerate(scenario.entries)
    )
    posting_rules = load_posting_key_rules(
        ROOT / "docs/reference/sap-posting-key-rules.csv"
    )
    classifier = RasTransactionSemanticClassifier(
        embedding_provider=HybridSemanticTestProvider(),
        provider_name="semantic-test",
        model_name="synthetic-model-v1",
        signals=load_ras_candidate_signals(
            ROOT / "docs/reference/ras-candidate-signals.csv"
        ),
        policy=load_ras_semantic_policy(
            ROOT / "docs/reference/ras-semantic-classification-policy.csv"
        ),
    )
    detector = RasCandidateDetector(
        posting_key_rules=posting_rules,
        account_mappings=load_ras_ledger_account_mappings(
            FIXTURES / "account-mapping/valid.csv"
        ),
        signals=load_ras_candidate_signals(
            ROOT / "docs/reference/ras-candidate-signals.csv"
        ),
        semantic_classifier=classifier,
    )

    report = detector.detect(
        ledger_entries=entries,
        reconstruction=AccountingEntryReconstructor(posting_rules).reconstruct(entries),
    )

    assert report.candidates[0].status is RasCandidateStatus.TEXT_ONLY
    assert report.candidates[0].signal_ids == ("SIG-RAS-003",)
    assert report.candidates[0].semantic_similarity == 1.0
    assert report.semantic_model_name == "synthetic-model-v1"
