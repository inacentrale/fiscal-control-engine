from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from app.account_mapping.domain import AccountMapping, ClassificationStatus
from app.account_mapping.import_service import AccountMappingImportService
from app.account_mapping.repository import (
    AccountMappingRepository,
    InMemoryAccountMappingRepository,
)
from app.account_mapping.rule_loader import load_classification_rules
from app.account_mapping.service import AccountMappingService
from app.config import Settings, get_settings
from app.schemas.account_mapping import (
    AccountMappingErrorDetail,
    AccountMappingErrorResponse,
    AccountMappingImportResponse,
    AccountMappingListResponse,
    AccountMappingResponse,
)

router = APIRouter(prefix="/account-mappings", tags=["account-mappings"])


class AccountMappingImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


async def get_api_settings() -> Settings:
    return get_settings()


@lru_cache
def _get_shared_repository() -> AccountMappingRepository:
    return InMemoryAccountMappingRepository()


async def get_account_mapping_repository() -> AccountMappingRepository:
    return _get_shared_repository()


AccountMappingRepositoryDependency = Annotated[
    AccountMappingRepository,
    Depends(get_account_mapping_repository),
]
SettingsDependency = Annotated[Settings, Depends(get_api_settings)]


@router.get("", response_model=AccountMappingListResponse)
async def list_account_mappings(
    repository: AccountMappingRepositoryDependency,
) -> AccountMappingListResponse:
    mappings = repository.list_all()
    return AccountMappingListResponse(
        items=[_to_response(mapping) for mapping in mappings],
        total=len(mappings),
    )


@router.post(
    "/import-from-files",
    response_model=AccountMappingImportResponse,
    responses={400: {"model": AccountMappingErrorResponse}},
)
async def import_account_mappings_from_files(
    request: AccountMappingImportRequest,
    settings: SettingsDependency,
    repository: AccountMappingRepositoryDependency,
) -> AccountMappingImportResponse | JSONResponse:
    _ = request
    try:
        import_service = AccountMappingImportService()
        ledger_accounts = import_service.read_ledger_accounts(
            Path(settings.account_mapping_ledger_accounts_path),
        )
        plan_accounts = import_service.read_plan_accounts(
            Path(settings.account_mapping_plan_accounts_path),
        )
        mapping_service = AccountMappingService(
            repository=repository,
            rules=load_classification_rules(
                Path(settings.ras_classification_rules_path),
            ),
        )
        mappings = mapping_service.build_from_accounts(
            ledger_accounts=ledger_accounts,
            plan_accounts=plan_accounts,
        )
    except (OSError, ValueError):
        return _to_error_response(
            code="account_mapping_import_error",
            message="L'import des mappings de comptes a echoue.",
        )

    return AccountMappingImportResponse(
        items=[_to_response(mapping) for mapping in mappings],
        total=len(mappings),
        imported_ledger_accounts=len(ledger_accounts),
        imported_plan_accounts=len(plan_accounts),
        missing_label_count=sum(
            1
            for mapping in mappings
            if mapping.classification_status is ClassificationStatus.MISSING_LABEL
        ),
    )


def _to_response(mapping: AccountMapping) -> AccountMappingResponse:
    return AccountMappingResponse(
        account_number=mapping.account_number,
        label=mapping.label,
        ras_category=mapping.ras_category.value,
        classification_status=mapping.classification_status.value,
        confidence=mapping.confidence,
        justification=mapping.justification,
        action_required=mapping.action_required,
    )


def _to_error_response(code: str, message: str) -> JSONResponse:
    response = AccountMappingErrorResponse(
        error=AccountMappingErrorDetail(code=code, message=message),
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=response.model_dump(),
    )
