import csv
from pathlib import Path

import pytest

from app.ras_audit.legal_rules import (
    RasCalculationMethod,
    RasLegalRuleError,
    RasLegalRuleStatus,
    load_ras_legal_rules,
)

ROOT = Path(__file__).resolve().parents[4]
MATRIX = ROOT / "docs/reference/bf-ras-legal-rules.csv"


def test_loads_source_verified_matrix_and_preserves_blocked_gaps() -> None:
    rules = load_ras_legal_rules(MATRIX, repository_root=ROOT)

    assert len(rules) == 27
    assert sum(rule.is_active for rule in rules) == 15
    assert sum(not rule.is_active for rule in rules) == 12
    assert {rule.regime for rule in rules} == {
        "resident",
        "nonresident",
        "rent",
        "non_determined",
    }
    blocked = tuple(
        rule
        for rule in rules
        if rule.status is RasLegalRuleStatus.BLOCKED_MISSING_SCOPE_SOURCE
    )
    assert all(
        rule.calculation_method is RasCalculationMethod.UNRESOLVED
        for rule in blocked
    )
    assert all(
        any(fact.endswith("source_confirmation") for fact in rule.required_facts)
        for rule in blocked
    )


def test_resident_rule_has_distinct_scope_and_rate_evidence() -> None:
    rules = load_ras_legal_rules(MATRIX, repository_root=ROOT)
    rule = next(item for item in rules if item.rule_id == "resident_standard_2026")

    assert rule.scope_source_locator == "article 206"
    assert rule.rate_source_locator == "article 15 modifiant article 207"
    assert rule.scope_source_sha256 != rule.rate_source_sha256
    assert rule.source_assurance == (
        "auto_validated_official_extract_no_external_fiscal_review"
    )


def test_loader_rejects_a_changed_source_hash(tmp_path: Path) -> None:
    rows = _matrix_rows()
    rows[0]["scope_source_sha256"] = "0" * 64
    matrix = _write_matrix(tmp_path, rows)

    with pytest.raises(RasLegalRuleError, match="scope source hash mismatch"):
        load_ras_legal_rules(matrix, repository_root=ROOT)


def test_loader_rejects_overlapping_active_rules(tmp_path: Path) -> None:
    rows = _matrix_rows()
    duplicate = dict(rows[0])
    duplicate["rule_id"] = "overlapping-copy"
    rows.append(duplicate)
    matrix = _write_matrix(tmp_path, rows)

    with pytest.raises(RasLegalRuleError, match="overlapping active"):
        load_ras_legal_rules(matrix, repository_root=ROOT)


def test_loader_rejects_activating_an_unresolved_rule(tmp_path: Path) -> None:
    rows = _matrix_rows()
    blocked = next(
        row
        for row in rows
        if row["activation_status"] == "blocked_missing_scope_source"
    )
    blocked["activation_status"] = "active_provisional"
    matrix = _write_matrix(tmp_path, rows)

    with pytest.raises(RasLegalRuleError, match="cannot be unresolved"):
        load_ras_legal_rules(matrix, repository_root=ROOT)


def _matrix_rows() -> list[dict[str, str]]:
    with MATRIX.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def _write_matrix(tmp_path: Path, rows: list[dict[str, str]]) -> Path:
    path = tmp_path / "rules.csv"
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path
