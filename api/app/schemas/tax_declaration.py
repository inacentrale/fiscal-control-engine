from typing import Any

from pydantic import BaseModel


class CanonicalFieldResponse(BaseModel):
    name: str
    source_value: Any
    normalized_value: Any
    confidence: float
    status: str
    locator: str


class CanonicalRecordResponse(BaseModel):
    record_type: str
    fields: list[CanonicalFieldResponse]


class CanonicalDeclarationResponse(BaseModel):
    schema_version: str
    declaration_type: str
    fields: list[CanonicalFieldResponse]
    records: list[CanonicalRecordResponse]


class TaxDeclarationIngestionResponse(BaseModel):
    file_name: str
    source_format: str
    format_confidence: float
    format_evidence: str
    content_sha256: str
    declaration_type: str
    status: str
    reason: str | None
    declaration: CanonicalDeclarationResponse | None


class ValidationCheckResponse(BaseModel):
    check_id: str
    layer: str
    status: str
    severity: str
    message: str
    source_url: str | None
    source_locator: str | None
    expected_value: str | None
    actual_value: str | None
    difference: str | None
    expected_date: str | None
    actual_date: str | None
    affected_lines: list[str]


class TaxDeclarationValidationResponse(BaseModel):
    overall_status: str
    checks: list[ValidationCheckResponse]


class TaxAssuranceAssessmentResponse(BaseModel):
    level: str
    policy_id: str | None
    policy_version: str | None
    description: str
    passed_layers: list[str]
    missing_layers: list[str]
    failed_layers: list[str]


class TaxDeclarationAnalysisResponse(TaxDeclarationIngestionResponse):
    validation: TaxDeclarationValidationResponse | None
    assurance: TaxAssuranceAssessmentResponse | None


class TaxDeclarationHistoryResponse(BaseModel):
    current: TaxDeclarationIngestionResponse
    previous: TaxDeclarationIngestionResponse
    validation: TaxDeclarationValidationResponse | None


class VatLedgerEvidenceResponse(BaseModel):
    declaration_type: str
    record_selector_field: str
    declaration_amount_field: str
    declaration_line: str
    currency: str
    amount: str
    entry_count: int
    used_entry_count: int
    excluded_entry_count: int
    accounts: list[str]
    mapping_ids: list[str]
    source_references: list[str]
    tolerance: str


class TaxDeclarationLedgerReconciliationResponse(BaseModel):
    declaration: TaxDeclarationIngestionResponse
    evidence: list[VatLedgerEvidenceResponse]
    validation: TaxDeclarationValidationResponse | None
    declaration_validation: TaxDeclarationValidationResponse | None = None
    assurance: TaxAssuranceAssessmentResponse | None = None


class SupportingEvidenceSummaryResponse(BaseModel):
    file_name: str
    source_format: str
    content_sha256: str
    record_count: int
    currencies: list[str]


class TaxDeclarationSupportingReconciliationResponse(BaseModel):
    declaration: TaxDeclarationIngestionResponse
    invoices: SupportingEvidenceSummaryResponse
    payments: SupportingEvidenceSummaryResponse | None
    validation: TaxDeclarationValidationResponse | None


class TaxDeclarationErrorDetail(BaseModel):
    code: str
    message: str


class TaxDeclarationErrorResponse(BaseModel):
    error: TaxDeclarationErrorDetail
