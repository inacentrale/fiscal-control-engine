import csv
from pathlib import Path

from app.ras_audit.account_mapping import (
    RasLedgerAccountMapping,
    load_ras_ledger_account_mappings,
)
from app.ras_audit.domain import AuditCapability, LedgerField
from app.ras_audit.normalization import (
    LedgerColumnBinding,
    LedgerNormalizationRequest,
    LedgerNormalizer,
)
from app.ras_audit.readiness import CapabilityReadinessStatus


def test_normalizes_golden_ledger_and_preserves_source_values() -> None:
    source = _fixture_path()
    with source.open(encoding="utf-8", newline="") as ledger_file:
        rows = tuple(csv.DictReader(ledger_file))

    report = LedgerNormalizer().normalize(
        LedgerNormalizationRequest(
            source_file_name=source.name,
            content_sha256="a" * 64,
            sheet_name="ledger",
            first_data_row=2,
            source_columns=tuple(rows[0]),
            rows=rows,
            bindings=_bindings(),
            known_posting_keys=frozenset({"40", "50"}),
            source_scope_complete=True,
            ras_account_mappings=_account_mappings(),
        ),
    )

    assert len(report.entries) == 26
    assert report.rejected_rows == ()
    assert report.entries[0].account_number == "632100"
    assert report.entries[0].partner_id == "SYN-TIERS-001"
    assert report.entries[0].source_fields[0].source_column == "company_code"
    assert {issue.code for issue in report.issues} == {"unknown_posting_key"}
    assert (
        report.readiness.for_capability(
            AuditCapability.COUNTERPART_RECONCILIATION,
        ).status
        is CapabilityReadinessStatus.BLOCKED
    )


def test_derives_partner_from_vendor_or_customer_without_guessing_conflicts() -> None:
    report = LedgerNormalizer().normalize(
        LedgerNormalizationRequest(
            source_file_name="partners.xlsx",
            content_sha256="c" * 64,
            sheet_name="GL",
            first_data_row=2,
            source_columns=("account", "vendor", "customer"),
            rows=(
                {"account": "61365000", "vendor": "V-001", "customer": None},
                {"account": "706000", "vendor": None, "customer": "C-001"},
                {"account": "471000", "vendor": "V-002", "customer": "C-002"},
            ),
            bindings=(
                LedgerColumnBinding(LedgerField.ACCOUNT_NUMBER, "account"),
                LedgerColumnBinding(LedgerField.VENDOR_ID, "vendor"),
                LedgerColumnBinding(LedgerField.CUSTOMER_ID, "customer"),
            ),
        )
    )

    assert [entry.partner_id for entry in report.entries] == ["V-001", "C-001", None]
    assert "conflicting_vendor_customer" in {issue.code for issue in report.issues}


def test_uses_only_an_explicit_organization_company_fallback() -> None:
    report = LedgerNormalizer().normalize(
        LedgerNormalizationRequest(
            source_file_name="company.xlsx",
            content_sha256="d" * 64,
            sheet_name="GL",
            first_data_row=2,
            source_columns=("account",),
            rows=({"account": "61365000"},),
            bindings=(
                LedgerColumnBinding(LedgerField.ACCOUNT_NUMBER, "account"),
            ),
            default_company_code=" BF-ORG ",
        )
    )

    assert report.entries[0].company_code == "BF-ORG"
    assert "company_code_from_organization_config" in {
        issue.code for issue in report.issues
    }


def test_reports_document_date_and_type_when_used_as_accounting_proxies() -> None:
    report = LedgerNormalizer().normalize(
        LedgerNormalizationRequest(
            source_file_name="proxies.xlsx",
            content_sha256="e" * 64,
            sheet_name="GL",
            first_data_row=2,
            source_columns=("Date pièce", "Type de pièce"),
            rows=({"Date pièce": "2026-01-15", "Type de pièce": "KR"},),
            bindings=(
                LedgerColumnBinding(LedgerField.POSTING_DATE, "Date pièce"),
                LedgerColumnBinding(LedgerField.JOURNAL, "Type de pièce"),
            ),
        )
    )

    assert {issue.code for issue in report.issues} == {
        "document_date_used_as_posting_date",
        "document_type_used_as_journal",
    }


def test_keeps_invalid_optional_values_as_issues_without_losing_candidate() -> None:
    report = LedgerNormalizer().normalize(
        LedgerNormalizationRequest(
            source_file_name="synthetic.xlsx",
            content_sha256="b" * 64,
            sheet_name="GL",
            first_data_row=2,
            source_columns=(
                "account",
                "label",
                "amount",
                "currency",
                "posting_date",
                "posting_key",
                "fiscal_year",
                "period",
            ),
            rows=(
                {
                    "account": "0632100",
                    "label": "Prestation a analyser",
                    "amount": "invalide",
                    "currency": " xof ",
                    "posting_date": "31/02/2025",
                    "posting_key": "XX",
                    "fiscal_year": "annee",
                    "period": "17",
                },
            ),
            bindings=_minimal_bindings(),
            known_posting_keys=frozenset({"40", "50"}),
        ),
    )

    assert len(report.entries) == 1
    entry = report.entries[0]
    assert entry.account_number == "0632100"
    assert entry.amount is None
    assert entry.posting_date is None
    assert entry.posting_key is None
    assert entry.fiscal_year is None
    assert entry.period is None
    assert {issue.code for issue in report.issues} == {
        "invalid_amount",
        "invalid_posting_date",
        "invalid_posting_key",
        "invalid_fiscal_year",
        "invalid_period",
    }


def test_rejects_structural_blank_row_with_explicit_reason() -> None:
    report = LedgerNormalizer().normalize(
        LedgerNormalizationRequest(
            source_file_name="synthetic.xlsx",
            content_sha256="c" * 64,
            sheet_name="GL",
            first_data_row=7,
            source_columns=(
                "account",
                "label",
                "amount",
                "currency",
                "posting_date",
                "posting_key",
                "fiscal_year",
                "period",
            ),
            rows=({"account": "", "label": "", "amount": ""},),
            bindings=_minimal_bindings(),
        ),
    )

    assert report.entries == ()
    assert report.rejected_rows[0].row_number == 7
    assert report.rejected_rows[0].reason_code == "structural_blank_row"


def test_rejects_non_standard_currency_code_without_losing_source_row() -> None:
    report = LedgerNormalizer().normalize(
        LedgerNormalizationRequest(
            source_file_name="synthetic.xlsx",
            content_sha256="f" * 64,
            sheet_name="GL",
            first_data_row=2,
            source_columns=tuple(
                binding.source_column for binding in _minimal_bindings()
            ),
            rows=(
                {
                    "account": "613000",
                    "label": "Prestation",
                    "amount": "1000",
                    "currency": "FCFA",
                    "posting_date": "2026-04-10",
                    "posting_key": "40",
                    "fiscal_year": "2026",
                    "period": "4",
                },
            ),
            bindings=_minimal_bindings(),
            known_posting_keys=frozenset({"40"}),
        ),
    )

    assert len(report.entries) == 1
    assert report.entries[0].currency is None
    assert {issue.code for issue in report.issues} == {"invalid_currency"}


def test_rejects_duplicate_source_binding() -> None:
    request = LedgerNormalizationRequest(
        source_file_name="synthetic.xlsx",
        content_sha256="d" * 64,
        sheet_name="GL",
        first_data_row=2,
        source_columns=("Compte",),
        rows=(),
        bindings=(
            LedgerColumnBinding(LedgerField.ACCOUNT_NUMBER, "Compte"),
            LedgerColumnBinding(LedgerField.PARTNER_ID, "Compte"),
        ),
    )

    try:
        LedgerNormalizer().normalize(request)
    except ValueError as error:
        assert str(error) == (
            "source column cannot map to multiple ledger fields: Compte"
        )
    else:
        raise AssertionError("duplicate source binding should be rejected")


def test_rejects_mapping_to_unavailable_source_column() -> None:
    request = LedgerNormalizationRequest(
        source_file_name="synthetic.xlsx",
        content_sha256="e" * 64,
        sheet_name="GL",
        first_data_row=2,
        source_columns=("Compte",),
        rows=(),
        bindings=(LedgerColumnBinding(LedgerField.LABEL, "Libelle absent"),),
    )

    try:
        LedgerNormalizer().normalize(request)
    except ValueError as error:
        assert str(error) == "mapped source column is unavailable: Libelle absent"
    else:
        raise AssertionError("unavailable source column should be rejected")


def _fixture_path() -> Path:
    return Path(__file__).parent / "fixtures" / "golden" / "ledger.csv"


def _account_mappings() -> tuple[RasLedgerAccountMapping, ...]:
    return load_ras_ledger_account_mappings(
        Path(__file__).parent / "fixtures" / "account-mapping" / "valid.csv"
    )


def _bindings() -> tuple[LedgerColumnBinding, ...]:
    return tuple(
        LedgerColumnBinding(field, field.value)
        for field in LedgerField
        if field.value
        in {
            "company_code",
            "fiscal_year",
            "period",
            "journal",
            "document_number",
            "line_number",
            "posting_date",
            "account_number",
            "partner_id",
            "label",
            "posting_key",
            "amount",
            "currency",
        }
    )


def _minimal_bindings() -> tuple[LedgerColumnBinding, ...]:
    return (
        LedgerColumnBinding(LedgerField.ACCOUNT_NUMBER, "account"),
        LedgerColumnBinding(LedgerField.LABEL, "label"),
        LedgerColumnBinding(LedgerField.AMOUNT, "amount"),
        LedgerColumnBinding(LedgerField.CURRENCY, "currency"),
        LedgerColumnBinding(LedgerField.POSTING_DATE, "posting_date"),
        LedgerColumnBinding(LedgerField.POSTING_KEY, "posting_key"),
        LedgerColumnBinding(LedgerField.FISCAL_YEAR, "fiscal_year"),
        LedgerColumnBinding(LedgerField.PERIOD, "period"),
    )
