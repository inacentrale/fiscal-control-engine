from pathlib import Path

import pytest

from app.ras_audit.golden_dataset import (
    GoldenDatasetError,
    GoldenExpectedCounterpart,
    QualityGateDirection,
    load_golden_dataset,
    load_quality_gates,
)


def test_loads_anonymized_golden_dataset_with_required_coverage() -> None:
    dataset = load_golden_dataset(_fixtures_path())

    assert len(dataset.scenarios) == 8
    assert dataset.coverage_tags == frozenset(
        {
            "adjustment",
            "candidate",
            "multicurrency",
            "multiline",
            "non_candidate",
            "ras_counterpart_absent",
            "ras_counterpart_present",
            "reversal",
            "unknown_posting_key",
        },
    )
    assert all(
        scenario.scenario_id.startswith("SYN-") for scenario in dataset.scenarios
    )
    assert all(
        line.partner_id is None or line.partner_id.startswith("SYN-TIERS-")
        for scenario in dataset.scenarios
        for line in scenario.entries
    )


def test_golden_dataset_keeps_legal_outcomes_unresolved() -> None:
    dataset = load_golden_dataset(_fixtures_path())

    assert all(scenario.legal_rule_id is None for scenario in dataset.scenarios)
    assert {
        scenario.expected_counterpart for scenario in dataset.scenarios
    } >= {
        GoldenExpectedCounterpart.PRESENT,
        GoldenExpectedCounterpart.ABSENT,
        GoldenExpectedCounterpart.NOT_APPLICABLE,
        GoldenExpectedCounterpart.INDETERMINATE,
    }


def test_loads_strict_backend_quality_gates() -> None:
    gates = load_quality_gates(_fixtures_path() / "quality-gates.csv")

    by_name = {gate.metric_name: gate for gate in gates}
    assert by_name["candidate_recall"].direction is QualityGateDirection.MINIMUM
    assert by_name["candidate_recall"].threshold == 1
    assert by_name["firm_alert_precision"].threshold == 1
    assert by_name["indeterminate_explanation_rate"].threshold == 1
    assert by_name["calculation_absolute_error"].direction is (
        QualityGateDirection.MAXIMUM
    )
    assert by_name["calculation_absolute_error"].threshold == 0


def test_rejects_expectation_without_ledger_scenario() -> None:
    with pytest.raises(GoldenDatasetError, match="has no ledger entries"):
        load_golden_dataset(_invalid_fixtures_path() / "orphan")


def test_rejects_duplicate_ledger_line_id() -> None:
    with pytest.raises(GoldenDatasetError, match="duplicate ledger line id"):
        load_golden_dataset(_invalid_fixtures_path() / "duplicate-line")


def _fixtures_path() -> Path:
    return Path(__file__).parent / "fixtures" / "golden"


def _invalid_fixtures_path() -> Path:
    return Path(__file__).parent / "fixtures" / "invalid-golden"
