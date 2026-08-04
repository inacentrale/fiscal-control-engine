from datetime import date
from decimal import Decimal

import pytest

from app.ras_audit.domain import (
    AuditEvidence,
    AuditEvidenceKind,
    CanonicalLedgerEntry,
    LedgerSourceReference,
    RasAuditFinding,
    RasAuditStatus,
    SourceFieldValue,
)


def test_canonical_ledger_entry_normalizes_identifiers_without_losing_source() -> None:
    entry = CanonicalLedgerEntry(
        line_id="  Sheet1:12 ",
        source=LedgerSourceReference(
            file_name=" GL.xlsx ",
            content_sha256="a" * 64,
            sheet_name=" Sheet1 ",
            row_number=12,
        ),
        company_code=" BF01 ",
        fiscal_year=2025,
        period=3,
        journal=" ACH ",
        document_number=" 000042 ",
        line_number=" 001 ",
        posting_date=date(2025, 3, 20),
        account_number=" 632100 ",
        partner_id=" 000078 ",
        label=" Honoraires conseil ",
        posting_key=" 40 ",
        amount=Decimal("125000.00"),
        currency=" xof ",
        source_fields=(
            SourceFieldValue("Compte", " 632100 "),
            SourceFieldValue("Fournisseur", "000078"),
        ),
    )

    assert entry.line_id == "Sheet1:12"
    assert entry.document_number == "000042"
    assert entry.partner_id == "000078"
    assert entry.currency == "XOF"
    assert entry.source_fields[0].source_value == " 632100 "


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("amount", Decimal("NaN"), "amount must be finite"),
        ("period", 0, "period must be between 1 and 16"),
        ("posting_key", "4", "posting key must contain two digits"),
    ],
)
def test_canonical_ledger_entry_rejects_invalid_normalized_values(
    field: str,
    value: object,
    message: str,
) -> None:
    values: dict[str, object] = {
        "line_id": "Sheet1:12",
        "source": _source(),
        "period": 3,
        "posting_key": "40",
        "amount": Decimal("100"),
    }
    values[field] = value

    with pytest.raises(ValueError, match=message):
        CanonicalLedgerEntry(**values)  # type: ignore[arg-type]


def test_firm_missing_ras_finding_requires_complete_basis_and_evidence() -> None:
    evidence = _complete_evidence()
    finding = RasAuditFinding(
        candidate_id="candidate-42",
        status=RasAuditStatus.RAS_NOT_FOUND_IN_LEDGER,
        evidence=evidence,
        basis_is_complete=True,
        expected_amount=Decimal("5000"),
        recorded_amount=Decimal("0"),
        currency="XOF",
    )

    assert finding.difference == Decimal("5000")

    with pytest.raises(ValueError, match="firm status requires a complete basis"):
        RasAuditFinding(
            candidate_id="candidate-42",
            status=RasAuditStatus.RAS_NOT_FOUND_IN_LEDGER,
            evidence=evidence,
            basis_is_complete=False,
        )


def test_amount_comparison_requires_one_currency_and_both_amounts() -> None:
    with pytest.raises(ValueError, match="amount comparison requires"):
        RasAuditFinding(
            candidate_id="candidate-42",
            status=RasAuditStatus.RAS_AMOUNT_MISMATCH,
            evidence=_complete_evidence(),
            basis_is_complete=True,
            expected_amount=Decimal("5000"),
        )


def test_firm_status_requires_the_expected_evidence_kinds() -> None:
    with pytest.raises(ValueError, match=r"missing required evidence: .*legal_rule"):
        RasAuditFinding(
            candidate_id="candidate-42",
            status=RasAuditStatus.RAS_NOT_FOUND_IN_LEDGER,
            evidence=(
                AuditEvidence(
                    evidence_id="piece-42",
                    kind=AuditEvidenceKind.ACCOUNTING_ENTRY,
                    description="Piece comptable reconstruite",
                ),
            ),
            basis_is_complete=True,
            expected_amount=Decimal("5000"),
            recorded_amount=Decimal("0"),
            currency="XOF",
        )


def test_indeterminate_status_requires_named_missing_facts() -> None:
    with pytest.raises(ValueError, match="indeterminate status requires missing facts"):
        RasAuditFinding(
            candidate_id="candidate-42",
            status=RasAuditStatus.INDETERMINATE,
            evidence=(
                AuditEvidence(
                    evidence_id="missing-42",
                    kind=AuditEvidenceKind.MISSING_FACT,
                    description="Residence fiscale absente",
                ),
            ),
            basis_is_complete=False,
        )


def _source() -> LedgerSourceReference:
    return LedgerSourceReference(
        file_name="GL.xlsx",
        content_sha256="a" * 64,
        sheet_name="Sheet1",
        row_number=12,
    )


def _complete_evidence() -> tuple[AuditEvidence, ...]:
    return (
        AuditEvidence(
            evidence_id="piece-42",
            kind=AuditEvidenceKind.ACCOUNTING_ENTRY,
            description="Piece comptable reconstruite sans contrepartie RAS",
            ledger_line_ids=("Sheet1:12", "Sheet1:13"),
        ),
        AuditEvidence(
            evidence_id="rule-42",
            kind=AuditEvidenceKind.LEGAL_RULE,
            description="Regle juridique applicable",
        ),
        AuditEvidence(
            evidence_id="calculation-42",
            kind=AuditEvidenceKind.CALCULATION,
            description="Calcul deterministe",
        ),
        AuditEvidence(
            evidence_id="scope-42",
            kind=AuditEvidenceKind.SCOPE_COMPLETENESS,
            description="Perimetre du GL confirme complet",
        ),
    )
