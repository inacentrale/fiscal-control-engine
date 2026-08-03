from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd

from app.excel_agent.excel_tools import ExcelAgentTools
from app.ledger_analysis.analysis_service import LedgerAnalysisService
from app.ledger_analysis.posting_key_rules import PostingKeyRule
from app.tax_declaration.domain import (
    CanonicalTaxDeclaration,
    DeclarationSourceFormat,
    SourceReference,
)
from app.tax_declaration.validation_domain import OverallValidationStatus
from app.tax_declaration.vat_ledger_mapping import (
    LedgerAmountSide,
    VatLedgerAccountMapping,
)
from app.tax_declaration.vat_ledger_reconciliation import (
    VatLedgerEvidenceBuilder,
    VatLedgerReconciler,
)
from app.tax_declaration.vat_tabular_extractor import VatTabularExtractor


def test_builds_debit_credit_evidence_and_reconciles_declaration(
    tmp_path: Path,
) -> None:
    ledger = _write_ledger(tmp_path, posting_keys=("50", "40"))
    service = LedgerAnalysisService(
        excel_tools=ExcelAgentTools(allowed_root=tmp_path),
        posting_key_rules=_posting_rules(),
    )
    evidence = VatLedgerEvidenceBuilder().build(
        service,
        ledger,
        "Grand Livre",
        _mappings(),
        period_end=date(2024, 12, 31),
    )
    declaration = _declaration(tmp_path, output_vat=180, input_vat=80)

    report = VatLedgerReconciler().reconcile(
        declaration,
        evidence,
        declaration_currency="XOF",
    )

    assert report.overall_status is OverallValidationStatus.PASSED
    assert [item.amount for item in evidence] == [Decimal("180.0"), Decimal("80.0")]
    assert all(item.excluded_entry_count == 0 for item in evidence)


def test_fails_when_unknown_posting_key_excludes_ledger_entry(tmp_path: Path) -> None:
    ledger = _write_ledger(tmp_path, posting_keys=("99", "40"))
    service = LedgerAnalysisService(
        excel_tools=ExcelAgentTools(allowed_root=tmp_path),
        posting_key_rules=_posting_rules(),
    )
    evidence = VatLedgerEvidenceBuilder().build(
        service,
        ledger,
        "Grand Livre",
        _mappings(),
        period_end=date(2024, 12, 31),
    )
    declaration = _declaration(tmp_path, output_vat=180, input_vat=80)

    report = VatLedgerReconciler().reconcile(
        declaration,
        evidence,
        declaration_currency="XOF",
    )

    assert report.overall_status is OverallValidationStatus.FAILED
    assert evidence[0].excluded_entry_count == 1


def test_returns_incomplete_without_applicable_mapping(tmp_path: Path) -> None:
    declaration = _declaration(tmp_path, output_vat=0, input_vat=0)

    report = VatLedgerReconciler().reconcile(
        declaration,
        (),
        declaration_currency="XOF",
    )

    assert report.overall_status is OverallValidationStatus.INCOMPLETE


def _write_ledger(tmp_path: Path, posting_keys: tuple[str, str]) -> Path:
    path = tmp_path / "ledger.xlsx"
    pd.DataFrame(
        {
            "Compte": [443100, 445100],
            "Texte": ["TVA collectee", "TVA deductible"],
            "Montant devise document": [180.0, 80.0],
            "Devise piece": ["XOF", "XOF"],
            "Periode comptable": [12, 12],
            "Exercice comptable": [2024, 2024],
            "Cle comptabilisation": list(posting_keys),
        },
    ).to_excel(path, sheet_name="Grand Livre", index=False, engine="openpyxl")
    return path


def _declaration(
    tmp_path: Path,
    output_vat: int,
    input_vat: int,
) -> CanonicalTaxDeclaration:
    path = tmp_path / "declaration.csv"
    path.write_text(
        "Code;Nature;Montant\n"
        f"19;TVA brute;{output_vat}\n20;TVA deductible;{input_vat}\n",
        encoding="utf-8",
    )
    reference = SourceReference(
        file_name=path.name,
        source_format=DeclarationSourceFormat.CSV,
        content_type="text/csv",
        content_sha256="a" * 64,
    )
    return VatTabularExtractor().extract(path, reference)


def _mappings() -> tuple[VatLedgerAccountMapping, ...]:
    return (
        _mapping("output", "443100", "19", LedgerAmountSide.CREDIT),
        _mapping("input", "445100", "20", LedgerAmountSide.DEBIT),
    )


def _mapping(
    mapping_id: str,
    account: str,
    declaration_line: str,
    side: LedgerAmountSide,
) -> VatLedgerAccountMapping:
    return VatLedgerAccountMapping(
        mapping_id=mapping_id,
        version="v1",
        account=account,
        declaration_line=declaration_line,
        amount_side=side,
        currency="XOF",
        tolerance=Decimal("0"),
        valid_from=date(2024, 1, 1),
        valid_to=None,
        source_reference="organization-config-v1",
    )


def _posting_rules() -> tuple[PostingKeyRule, ...]:
    return (
        PostingKeyRule("40", "debit", "gl", "standard", "Debit", "test"),
        PostingKeyRule("50", "credit", "gl", "standard", "Credit", "test"),
    )
