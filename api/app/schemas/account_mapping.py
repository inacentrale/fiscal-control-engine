from pydantic import BaseModel


class AccountMappingResponse(BaseModel):
    account_number: str
    label: str
    ras_category: str
    classification_status: str
    confidence: str
    justification: str
    action_required: str


class AccountMappingListResponse(BaseModel):
    items: list[AccountMappingResponse]
    total: int


class AccountMappingImportResponse(AccountMappingListResponse):
    imported_ledger_accounts: int
    imported_plan_accounts: int
    missing_label_count: int


class AccountMappingErrorDetail(BaseModel):
    code: str
    message: str


class AccountMappingErrorResponse(BaseModel):
    error: AccountMappingErrorDetail
