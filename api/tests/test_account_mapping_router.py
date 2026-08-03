import asyncio
from pathlib import Path
from typing import Any

import httpx

from app.account_mapping.domain import (
    AccountMapping,
    ClassificationStatus,
    RasCategory,
)
from app.account_mapping.repository import InMemoryAccountMappingRepository
from app.config import Settings
from app.main import create_app
from app.routers.account_mapping import get_account_mapping_repository, get_api_settings

FIXTURES_DIR = (
    Path(__file__).parents[1] / "app" / "account_mapping" / "tests" / "fixtures"
)


def test_account_mappings_endpoint_returns_empty_list() -> None:
    app = create_app()
    repository = InMemoryAccountMappingRepository()

    async def override_repository() -> InMemoryAccountMappingRepository:
        return repository

    app.dependency_overrides[get_account_mapping_repository] = override_repository

    response = _get(app, "/api/account-mappings")

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}


def test_account_mappings_endpoint_returns_stored_mappings() -> None:
    app = create_app()
    repository = InMemoryAccountMappingRepository()
    repository.save_all(
        [
            AccountMapping(
                account_number="604000",
                label="Achats de prestations",
                ras_category=RasCategory.RESIDENT_SERVICES,
                classification_status=ClassificationStatus.CLASSIFIED,
                confidence="high",
                justification="Regle deterministe de test.",
                action_required="Verifier la piece source.",
            ),
        ],
    )

    async def override_repository() -> InMemoryAccountMappingRepository:
        return repository

    app.dependency_overrides[get_account_mapping_repository] = override_repository

    response = _get(app, "/api/account-mappings")

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "account_number": "604000",
                "label": "Achats de prestations",
                "ras_category": "resident_services",
                "classification_status": "classified",
                "confidence": "high",
                "justification": "Regle deterministe de test.",
                "action_required": "Verifier la piece source.",
            },
        ],
        "total": 1,
    }


def test_account_mappings_import_endpoint_builds_from_configured_files() -> None:
    app = create_app()
    repository = InMemoryAccountMappingRepository()

    async def override_repository() -> InMemoryAccountMappingRepository:
        return repository

    async def override_settings() -> Settings:
        return Settings(
            account_mapping_ledger_accounts_path=str(
                FIXTURES_DIR / "ledger_accounts.csv",
            ),
            account_mapping_plan_accounts_path=str(FIXTURES_DIR / "plan_accounts.csv"),
            ras_classification_rules_path=str(
                FIXTURES_DIR / "ras_classification_rules.csv",
            ),
        )

    app.dependency_overrides[get_account_mapping_repository] = override_repository
    app.dependency_overrides[get_api_settings] = override_settings

    response = _post(app, "/api/account-mappings/import-from-files", json={})

    assert response.status_code == 200
    payload = response.json()
    assert payload["imported_ledger_accounts"] == 139
    assert payload["imported_plan_accounts"] == 138
    assert payload["total"] == 139
    assert payload["missing_label_count"] == 1
    assert repository.list_all()[0].account_number == "16000BSP"
    assert any(
        item["account_number"] == "44910002"
        and item["classification_status"] == "missing_label"
        for item in payload["items"]
    )


def test_account_mappings_import_endpoint_rejects_request_paths() -> None:
    response = _post(
        create_app(),
        "/api/account-mappings/import-from-files",
        json={
            "ledger_path": "/tmp/client-ledger.csv",
            "plan_path": "/tmp/client-plan.csv",
        },
    )

    assert response.status_code == 422


def test_account_mappings_import_endpoint_returns_sanitized_config_error() -> None:
    app = create_app()

    async def override_settings() -> Settings:
        return Settings(
            account_mapping_ledger_accounts_path="/secret/missing-ledger.csv",
            account_mapping_plan_accounts_path=str(FIXTURES_DIR / "plan_accounts.csv"),
            ras_classification_rules_path=str(
                FIXTURES_DIR / "ras_classification_rules.csv",
            ),
        )

    app.dependency_overrides[get_api_settings] = override_settings

    response = _post(app, "/api/account-mappings/import-from-files", json={})

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "account_mapping_import_error",
            "message": "L'import des mappings de comptes a echoue.",
        },
    }
    assert "/secret/missing-ledger.csv" not in response.text


def _get(app: Any, path: str) -> httpx.Response:
    return asyncio.run(_async_get(app, path))


def _post(app: Any, path: str, json: dict[str, object]) -> httpx.Response:
    return asyncio.run(_async_post(app, path, json))


async def _async_get(app: Any, path: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        return await client.get(path)


async def _async_post(
    app: Any,
    path: str,
    json: dict[str, object],
) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        return await client.post(path, json=json)
