from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd

from app.excel_agent.excel_tools import ExcelAgentTools
from app.ledger_analysis.analysis_service import LedgerAnalysisService
from app.ledger_analysis.posting_key_rules import PostingKeyRule
from app.tax_declaration.corporate_income_tax_tabular_extractor import (
    CorporateIncomeTaxTabularExtractor,
)
from app.tax_declaration.domain import (
    CanonicalTaxDeclaration,
    DeclarationSourceFormat,
    SourceReference,
    TaxDeclarationType,
)
from app.tax_declaration.payroll_tax_tabular_extractor import (
    PayrollTaxTabularExtractor,
)
from app.tax_declaration.validation_domain import (
    OverallValidationStatus,
    TaxDeclarationValidationReport,
)
from app.tax_declaration.vat_ledger_mapping import (
    LedgerAmountSide,
    VatLedgerAccountMapping,
)
from app.tax_declaration.vat_ledger_reconciliation import (
    VatLedgerEvidenceBuilder,
    VatLedgerReconciler,
)
from app.tax_declaration.vat_tabular_extractor import VatTabularExtractor
from app.tax_declaration.withholding_tabular_extractor import (
    WithholdingTabularExtractor,
)


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


def test_reconciles_withholding_amount_using_explicit_record_fields(
    tmp_path: Path,
) -> None:
    ledger = _write_ledger(tmp_path, posting_keys=("50", "40"))
    service = LedgerAnalysisService(
        excel_tools=ExcelAgentTools(allowed_root=tmp_path),
        posting_key_rules=_posting_rules(),
    )
    mapping = VatLedgerAccountMapping(
        mapping_id="ras-payable",
        version="v1",
        account="443100",
        declaration_line="01",
        amount_side=LedgerAmountSide.CREDIT,
        currency="XOF",
        tolerance=Decimal("0"),
        valid_from=date(2024, 1, 1),
        valid_to=None,
        source_reference="organization-config-ras-v1",
        declaration_type=TaxDeclarationType.WITHHOLDING_TAX,
        record_selector_field="line_code",
        declaration_amount_field="withheld_amount",
    )
    evidence = VatLedgerEvidenceBuilder().build(
        service,
        ledger,
        "Grand Livre",
        (mapping,),
        period_end=date(2024, 12, 31),
    )
    declaration_path = tmp_path / "ras.csv"
    declaration_path.write_text(
        "N;Categorie;Taux;Montant des retenues\n"
        "01;Prestations;2%;180\n",
        encoding="utf-8",
    )
    declaration = WithholdingTabularExtractor().extract(
        declaration_path,
        SourceReference(
            file_name=declaration_path.name,
            source_format=DeclarationSourceFormat.CSV,
            content_type="text/csv",
            content_sha256="b" * 64,
        ),
    )

    report = VatLedgerReconciler().reconcile(
        declaration,
        evidence,
        declaration_currency="XOF",
    )

    assert report.overall_status is OverallValidationStatus.PASSED
    assert evidence[0].declaration_type is TaxDeclarationType.WITHHOLDING_TAX
    assert evidence[0].declaration_amount_field == "withheld_amount"


def test_reconciles_payroll_tax_amount_using_line_number(tmp_path: Path) -> None:
    declaration_path = tmp_path / "iuts.csv"
    declaration_path.write_text(
        "N ordre;Noms et prenoms des salaries;Salaires bruts;"
        "Bases imposables;Nombre de charge;IUTS du\n"
        "01;Salarie Test;350000;280000;2;42237\n",
        encoding="utf-8",
    )
    declaration = PayrollTaxTabularExtractor().extract(
        declaration_path,
        _source_reference(declaration_path, "c"),
    )

    report = _reconcile_single_account(
        tmp_path,
        declaration,
        account="447200",
        amount=Decimal("42237"),
        declaration_type=TaxDeclarationType.PAYROLL_TAX,
        selector_field="line_number",
        selector_value="01",
        amount_field="iuts_amount",
    )

    assert report.overall_status is OverallValidationStatus.PASSED


def test_reconciles_corporate_tax_due_using_company_identifier(
    tmp_path: Path,
) -> None:
    declaration_path = tmp_path / "is.csv"
    declaration_path.write_text(
        "IFU;Raison sociale;Regime;Benefice imposable;IS calcule;"
        "IMFPIC;IS a payer\n"
        "0123456789;Societe Test;Reel Normal;10000000;2750000;;2750000\n",
        encoding="utf-8",
    )
    declaration = CorporateIncomeTaxTabularExtractor().extract(
        declaration_path,
        _source_reference(declaration_path, "d"),
    )

    report = _reconcile_single_account(
        tmp_path,
        declaration,
        account="441000",
        amount=Decimal("2750000"),
        declaration_type=TaxDeclarationType.CORPORATE_INCOME_TAX,
        selector_field="company_identifier",
        selector_value="0123456789",
        amount_field="corporate_tax_due",
    )

    assert report.overall_status is OverallValidationStatus.PASSED


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


def _source_reference(path: Path, digest_character: str) -> SourceReference:
    return SourceReference(
        file_name=path.name,
        source_format=DeclarationSourceFormat.CSV,
        content_type="text/csv",
        content_sha256=digest_character * 64,
    )


def _reconcile_single_account(
    tmp_path: Path,
    declaration: CanonicalTaxDeclaration,
    *,
    account: str,
    amount: Decimal,
    declaration_type: TaxDeclarationType,
    selector_field: str,
    selector_value: str,
    amount_field: str,
) -> TaxDeclarationValidationReport:
    ledger = tmp_path / f"ledger-{declaration_type.value}.xlsx"
    pd.DataFrame(
        {
            "Compte": [account],
            "Texte": [declaration_type.value],
            "Montant devise document": [amount],
            "Devise piece": ["XOF"],
            "Periode comptable": [12],
            "Exercice comptable": [2024],
            "Cle comptabilisation": ["50"],
        },
    ).to_excel(ledger, sheet_name="Grand Livre", index=False, engine="openpyxl")
    service = LedgerAnalysisService(
        excel_tools=ExcelAgentTools(allowed_root=tmp_path),
        posting_key_rules=_posting_rules(),
    )
    evidence = VatLedgerEvidenceBuilder().build(
        service,
        ledger,
        "Grand Livre",
        (
            VatLedgerAccountMapping(
                mapping_id=f"{declaration_type.value}-payable",
                version="v1",
                account=account,
                declaration_line=selector_value,
                amount_side=LedgerAmountSide.CREDIT,
                currency="XOF",
                tolerance=Decimal("0"),
                valid_from=date(2024, 1, 1),
                valid_to=None,
                source_reference="organization-config-v1",
                declaration_type=declaration_type,
                record_selector_field=selector_field,
                declaration_amount_field=amount_field,
            ),
        ),
        period_end=date(2024, 12, 31),
    )
    return VatLedgerReconciler().reconcile(
        declaration,
        evidence,
        declaration_currency="XOF",
    )
