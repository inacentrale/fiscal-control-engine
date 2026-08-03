import asyncio
from io import BytesIO
from pathlib import Path
from typing import Any

import httpx
import pandas as pd

from app.config import Settings, get_settings
from app.main import create_app


def test_ingests_unknown_extension_as_vat_csv() -> None:
    app = create_app()

    response = _post_file(
        app,
        "declaration.upload",
        b"Code;Nature;Montant\n19;TVA brute;180000\n",
        "application/octet-stream",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["file_name"] == "declaration.upload"
    assert payload["source_format"] == "csv"
    assert payload["declaration_type"] == "vat"
    assert payload["status"] == "resolved"
    assert payload["declaration"]["records"][0]["fields"][2][
        "normalized_value"
    ] == "180000"


def test_returns_unresolved_for_scan_without_ocr_guess() -> None:
    app = create_app()

    response = _post_file(
        app,
        "scan.png",
        b"\x89PNG\r\n\x1a\ncontent",
        "image/png",
    )

    assert response.status_code == 200
    assert response.json()["status"] == "unresolved"
    assert response.json()["reason"] == "structure_unresolved"


def test_ingests_withholding_declaration_from_strong_headers() -> None:
    app = create_app()

    response = _post_file(
        app,
        "ras.csv",
        b"Categorie;Base;Taux de la retenue;Montant des retenues\n"
        b"Prestations;1000000;2%;20000\n",
        "text/csv",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["declaration_type"] == "withholding_tax"
    assert payload["declaration"]["schema_version"] == "bf.withholding.v1"
    fields = {
        field["name"]: field
        for field in payload["declaration"]["records"][0]["fields"]
    }
    assert fields["tax_base"]["normalized_value"] == "1000000"
    assert fields["withheld_amount"]["normalized_value"] == "20000"


def test_analyzes_withholding_with_period_versioned_rules() -> None:
    app = create_app()
    root = Path(__file__).parents[2]

    async def override_settings() -> Settings:
        return Settings(
            withholding_validation_rules_path=str(
                root / "docs" / "reference" / "bf-withholding-validation-rules.csv",
            ),
            withholding_deadline_rules_path=str(
                root / "docs" / "reference" / "bf-withholding-deadline-rules.csv",
            ),
            tax_assurance_policy_path=str(
                root / "docs" / "reference" / "bf-tax-assurance-policy.csv",
            ),
        )

    app.dependency_overrides[get_settings] = override_settings
    response = _post_file(
        app,
        "ras.csv",
        b"Code;Regime retenue;Categorie taux;Categorie;Base;Taux;"
        b"Montant des retenues\n"
        b"01;resident;temporary_staffing_service;Mise a disposition;"
        b"1000000;2;20000\n",
        "text/csv",
        endpoint="/api/tax-declarations/analyze",
        data={"period_end": "2026-01-31", "filing_date": "2026-02-15"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["declaration_type"] == "withholding_tax"
    assert payload["validation"]["overall_status"] == "passed"
    assert payload["assurance"]["level"] == "limited"
    rate_check = next(
        check
        for check in payload["validation"]["checks"]
        if check["check_id"] == "withholding_rate_01"
    )
    assert rate_check["expected_value"] == "2"
    assert rate_check["source_locator"] == "article 15 / CGI article 207"
    deadline_check = next(
        check
        for check in payload["validation"]["checks"]
        if check["check_id"] == "withholding_deadline_resident"
    )
    assert deadline_check["status"] == "passed"
    assert deadline_check["expected_date"] == "2026-02-15"
    assert deadline_check["actual_date"] == "2026-02-15"
    assert deadline_check["source_locator"] == "article 208"


def test_analyzes_iuts_with_progressive_scale_and_deadline() -> None:
    app = create_app()
    root = Path(__file__).parents[2]

    async def override_settings() -> Settings:
        return Settings(
            payroll_tax_validation_rules_path=str(
                root / "docs" / "reference" / "bf-iuts-validation-rules.csv",
            ),
            tax_assurance_policy_path=str(
                root / "docs" / "reference" / "bf-tax-assurance-policy.csv",
            ),
        )

    app.dependency_overrides[get_settings] = override_settings
    response = _post_file(
        app,
        "iuts.csv",
        b"N ordre;Nom du salarie;Salaire brut;Base imposable;"
        b"Nombre de charges;IUTS\n"
        b"01;Salarie Test;350000;280000;2;42237\n",
        "text/csv",
        endpoint="/api/tax-declarations/analyze",
        data={"period_end": "2026-01-31", "filing_date": "2026-02-10"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["declaration_type"] == "payroll_tax"
    assert payload["declaration"]["schema_version"] == "bf.iuts.v1"
    assert payload["validation"]["overall_status"] == "passed"
    amount = next(
        check
        for check in payload["validation"]["checks"]
        if check["check_id"] == "payroll_tax_amount_01"
    )
    assert amount["expected_value"] == "42237.00"
    assert amount["actual_value"] == "42237"
    assert amount["difference"] == "0.00"
    assert amount["source_locator"] == "article 112; article 113"
    deadline = next(
        check
        for check in payload["validation"]["checks"]
        if check["check_id"] == "payroll_tax_deadline"
    )
    assert deadline["expected_date"] == "2026-02-10"
    assert deadline["actual_date"] == "2026-02-10"
    assert deadline["source_locator"] == "article 116"


def test_rejects_upload_above_configured_limit() -> None:
    app = create_app()

    async def override_settings() -> Settings:
        return Settings(agent_file_max_upload_bytes=3)

    app.dependency_overrides[get_settings] = override_settings

    response = _post_file(
        app,
        "declaration.csv",
        b"1234",
        "text/csv",
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "declaration_too_large"


def test_analyzes_vat_arithmetic_with_sourced_rules() -> None:
    app = create_app()
    rules_path = (
        Path(__file__).parents[2]
        / "docs"
        / "reference"
        / "bf-vat-validation-rules.csv"
    )
    assurance_path = (
        Path(__file__).parents[2]
        / "docs"
        / "reference"
        / "bf-tax-assurance-policy.csv"
    )

    async def override_settings() -> Settings:
        return Settings(
            vat_validation_rules_path=str(rules_path),
            tax_assurance_policy_path=str(assurance_path),
        )

    app.dependency_overrides[get_settings] = override_settings
    content = (
        "Code;Nature;Taux;Montant\n"
        + "".join(
            f"{code:02d};Ligne {code};;{code}\n" for code in range(1, 14)
        )
        + "14;Total;;91\n"
        + "15;Ligne 15;18%;15\n16;Ligne 16;10%;16\n"
        + "17;Ligne 17;;17\n18;Ligne 18;;18\n19;Total TVA;;66\n"
    ).encode()

    response = _post_file(
        app,
        "declaration.csv",
        content,
        "text/csv",
        endpoint="/api/tax-declarations/analyze",
        data={"period_end": "2024-12-31", "filing_date": "2025-01-15"},
    )

    assert response.status_code == 200
    validation = response.json()["validation"]
    assert validation["overall_status"] == "incomplete"
    arithmetic = [
        check for check in validation["checks"] if check["layer"] == "arithmetic"
    ]
    assert [check["status"] for check in arithmetic] == ["passed", "passed"]
    assert all(
        check["source_url"].startswith("https://dgi.bf/") for check in arithmetic
    )
    historical = [
        check for check in validation["checks"] if check["layer"] == "historical"
    ]
    assert historical[0]["status"] == "not_evaluated"
    assert response.json()["assurance"]["level"] == "limited"
    assert response.json()["assurance"]["missing_layers"] == [
        "historical",
        "reconciliation",
    ]


def test_analyzes_credit_history_between_two_declarations() -> None:
    app = create_app()
    rules_path = (
        Path(__file__).parents[2]
        / "docs"
        / "reference"
        / "bf-vat-validation-rules.csv"
    )

    async def override_settings() -> Settings:
        return Settings(vat_validation_rules_path=str(rules_path))

    app.dependency_overrides[get_settings] = override_settings

    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.post(
                "/api/tax-declarations/analyze-history",
                files={
                    "current_file": (
                        "current.csv",
                        b"Code;Nature;Montant\n21;Credit precedent;250\n",
                        "text/csv",
                    ),
                    "previous_file": (
                        "previous.csv",
                        b"Code;Nature;Montant\n"
                        b"vat_credit_carry_forward;Credit;250\n",
                        "text/csv",
                    ),
                },
                data={
                    "current_period_end": "2025-01-31",
                    "previous_period_end": "2024-12-31",
                },
            )

    response = asyncio.run(request())

    assert response.status_code == 200
    validation = response.json()["validation"]
    assert validation["overall_status"] == "passed"
    assert validation["checks"][1]["difference"] == "0"


def test_reconciles_vat_declaration_with_mapped_ledger_accounts() -> None:
    app = create_app()
    posting_key_path = (
        Path(__file__).parents[2]
        / "docs"
        / "reference"
        / "sap-posting-key-rules.csv"
    )

    async def override_settings() -> Settings:
        return Settings(posting_key_rules_path=str(posting_key_path))

    app.dependency_overrides[get_settings] = override_settings
    ledger_buffer = BytesIO()
    pd.DataFrame(
        {
            "Compte": [443100, 445100],
            "Texte": ["TVA collectee", "TVA deductible"],
            "Montant devise document": [180, 80],
            "Devise piece": ["XOF", "XOF"],
            "Periode comptable": [12, 12],
            "Exercice comptable": [2024, 2024],
            "Cle comptabilisation": ["50", "40"],
        },
    ).to_excel(
        ledger_buffer,
        sheet_name="Grand Livre",
        index=False,
        engine="openpyxl",
    )
    mapping = (
        b"mapping_id,version,account,declaration_line,amount_side,currency,"
        b"tolerance,valid_from,valid_to,source_reference\n"
        b"output,v1,443100,19,credit,XOF,0,2024-01-01,,config-v1\n"
        b"input,v1,445100,20,debit,XOF,0,2024-01-01,,config-v1\n"
    )

    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.post(
                "/api/tax-declarations/reconcile-ledger",
                files={
                    "declaration_file": (
                        "declaration.csv",
                        b"Code;Nature;Montant\n19;TVA brute;180\n"
                        b"20;TVA deductible;80\n",
                        "text/csv",
                    ),
                    "ledger_file": (
                        "ledger.xlsx",
                        ledger_buffer.getvalue(),
                        "application/vnd.openxmlformats-officedocument."
                        "spreadsheetml.sheet",
                    ),
                    "mapping_file": ("mapping.csv", mapping, "text/csv"),
                },
                data={
                    "declaration_period_end": "2024-12-31",
                    "declaration_currency": "XOF",
                    "ledger_sheet_name": "Grand Livre",
                },
            )

    response = asyncio.run(request())

    assert response.status_code == 200
    payload = response.json()
    assert payload["validation"]["overall_status"] == "passed"
    assert [item["amount"] for item in payload["evidence"]] == ["180.0", "80.0"]
    assert all(item["excluded_entry_count"] == 0 for item in payload["evidence"])


def test_reconciles_vat_with_invoices_and_payments() -> None:
    app = create_app()

    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.post(
                "/api/tax-declarations/reconcile-supporting-documents",
                files={
                    "declaration_file": (
                        "declaration.csv",
                        b"Code;Nature;Montant\n20;TVA deductible;180\n",
                        "text/csv",
                    ),
                    "invoices_file": (
                        "factures.csv",
                        b"Numero facture;Montant HT;Montant TVA;Montant TTC;"
                        b"Devise;Ligne declaration\n"
                        b"F-001;1000;180;1180;XOF;20\n",
                        "text/csv",
                    ),
                    "payments_file": (
                        "paiements.csv",
                        b"Numero paiement;Numero facture;Montant paiement;Devise\n"
                        b"P-001;F-001;1180;XOF\n",
                        "text/csv",
                    ),
                },
                data={"declaration_currency": "XOF", "tolerance": "0"},
            )

    response = asyncio.run(request())

    assert response.status_code == 200
    payload = response.json()
    assert payload["validation"]["overall_status"] == "passed"
    assert payload["invoices"]["record_count"] == 1
    assert payload["invoices"]["currencies"] == ["XOF"]
    assert payload["payments"]["record_count"] == 1
    assert "invoice_id" not in payload["invoices"]


def test_marks_payment_layer_incomplete_when_no_payment_file() -> None:
    app = create_app()

    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.post(
                "/api/tax-declarations/reconcile-supporting-documents",
                files={
                    "declaration_file": (
                        "declaration.csv",
                        b"Code;Nature;Montant\n20;TVA deductible;180\n",
                        "text/csv",
                    ),
                    "invoices_file": (
                        "factures.csv",
                        b"Facture;Montant HT;TVA;Total TTC;Devise;Ligne TVA\n"
                        b"F-001;1000;180;1180;XOF;20\n",
                        "text/csv",
                    ),
                },
                data={"declaration_currency": "XOF"},
            )

    response = asyncio.run(request())

    assert response.status_code == 200
    payload = response.json()
    assert payload["validation"]["overall_status"] == "incomplete"
    assert payload["payments"] is None
    payment_check = next(
        check
        for check in payload["validation"]["checks"]
        if check["layer"] == "payment_reconciliation"
    )
    assert payment_check["status"] == "not_evaluated"


def test_reconciles_xml_invoices_and_payments() -> None:
    app = create_app()

    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.post(
                "/api/tax-declarations/reconcile-supporting-documents",
                files={
                    "declaration_file": (
                        "declaration.csv",
                        b"Code;Nature;Montant\n20;TVA deductible;180\n",
                        "text/csv",
                    ),
                    "invoices_file": (
                        "factures.xml",
                        b"<Invoices><Invoice><invoice_id>F-XML-1</invoice_id>"
                        b"<net_amount>1000</net_amount><vat_amount>180</vat_amount>"
                        b"<gross_amount>1180</gross_amount><currency>XOF</currency>"
                        b"<declaration_line>20</declaration_line>"
                        b"</Invoice></Invoices>",
                        "application/xml",
                    ),
                    "payments_file": (
                        "paiements.xml",
                        b"<Payments><Payment><payment_id>P-XML-1</payment_id>"
                        b"<invoice_id>F-XML-1</invoice_id><amount>1180</amount>"
                        b"<currency>XOF</currency></Payment></Payments>",
                        "application/xml",
                    ),
                },
                data={"declaration_currency": "XOF"},
            )

    response = asyncio.run(request())

    assert response.status_code == 200
    payload = response.json()
    assert payload["validation"]["overall_status"] == "passed"
    assert payload["invoices"]["source_format"] == "xml"
    assert payload["payments"]["source_format"] == "xml"


def _post_file(
    app: Any,
    filename: str,
    content: bytes,
    content_type: str,
    endpoint: str = "/api/tax-declarations/ingest",
    data: dict[str, str] | None = None,
) -> httpx.Response:
    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.post(
                endpoint,
                files={"file": (filename, content, content_type)},
                data=data,
            )

    return asyncio.run(request())
