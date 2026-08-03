from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings
from app.excel_agent.excel_tools import ExcelAgentTools
from app.ledger_analysis.analysis_service import LedgerAnalysisService
from app.ledger_analysis.posting_key_rules import load_posting_key_rules
from app.ledger_analysis.schema_validator import LedgerSchemaValidationError
from app.schemas.tax_declaration import (
    CanonicalDeclarationResponse,
    CanonicalFieldResponse,
    CanonicalRecordResponse,
    SupportingEvidenceSummaryResponse,
    TaxAssuranceAssessmentResponse,
    TaxDeclarationAnalysisResponse,
    TaxDeclarationErrorDetail,
    TaxDeclarationErrorResponse,
    TaxDeclarationHistoryResponse,
    TaxDeclarationIngestionResponse,
    TaxDeclarationLedgerReconciliationResponse,
    TaxDeclarationSupportingReconciliationResponse,
    TaxDeclarationValidationResponse,
    ValidationCheckResponse,
    VatLedgerEvidenceResponse,
)
from app.tax_declaration.assurance_policy import (
    TaxAssurancePolicyError,
    load_tax_assurance_policies,
)
from app.tax_declaration.assurance_service import (
    TaxAssuranceAssessment,
    TaxAssuranceService,
)
from app.tax_declaration.domain import (
    CanonicalField,
    CanonicalTaxDeclaration,
    SourceReference,
    TaxDeclarationType,
)
from app.tax_declaration.format_detector import (
    DeclarationFormatDetector,
    DeclarationSourceReadError,
)
from app.tax_declaration.ingestion_service import (
    TaxDeclarationIngestionResult,
    TaxDeclarationIngestionService,
)
from app.tax_declaration.payroll_tax_rule_loader import (
    PayrollTaxRuleReferenceError,
    load_payroll_tax_validation_rules,
)
from app.tax_declaration.payroll_tax_validation_service import (
    PayrollTaxDeclarationValidator,
)
from app.tax_declaration.supporting_evidence import (
    PaymentEvidence,
    SupportingEvidenceExtractionError,
    SupportingEvidenceExtractor,
)
from app.tax_declaration.supporting_evidence_validation import (
    SupportingEvidenceValidator,
)
from app.tax_declaration.validation_domain import TaxDeclarationValidationReport
from app.tax_declaration.vat_historical_validation import VatHistoricalValidator
from app.tax_declaration.vat_ledger_mapping import (
    VatLedgerMappingError,
    load_vat_ledger_mappings,
)
from app.tax_declaration.vat_ledger_reconciliation import (
    VatLedgerEvidence,
    VatLedgerEvidenceBuilder,
    VatLedgerReconciler,
)
from app.tax_declaration.vat_rule_loader import (
    VatRuleReferenceError,
    load_vat_validation_rules,
)
from app.tax_declaration.vat_validation_service import VatDeclarationValidator
from app.tax_declaration.withholding_deadline_loader import (
    WithholdingDeadlineReferenceError,
    load_withholding_deadline_rules,
)
from app.tax_declaration.withholding_rule_loader import (
    WithholdingRuleReferenceError,
    load_withholding_validation_rules,
)
from app.tax_declaration.withholding_validation_service import (
    WithholdingDeclarationValidator,
)

router = APIRouter(prefix="/tax-declarations", tags=["tax-declarations"])
SettingsDependency = Annotated[Settings, Depends(get_settings)]
_UPLOAD_CHUNK_BYTES = 1024 * 1024


class TaxDeclarationUploadTooLargeError(ValueError):
    pass


@router.post(
    "/ingest",
    response_model=TaxDeclarationIngestionResponse,
    responses={
        400: {"model": TaxDeclarationErrorResponse},
        413: {"model": TaxDeclarationErrorResponse},
    },
)
async def ingest_tax_declaration(
    settings: SettingsDependency,
    file: Annotated[UploadFile, File()],
    declaration_type: Annotated[TaxDeclarationType | None, Form()] = None,
    sheet_name: Annotated[str | None, Form()] = None,
) -> TaxDeclarationIngestionResponse | JSONResponse:
    original_file_name = Path(file.filename or "declaration.upload").name
    try:
        result = await _ingest_upload(
            file,
            settings,
            declaration_type=declaration_type,
            sheet_name=sheet_name,
            original_file_name=original_file_name,
        )
    except TaxDeclarationUploadTooLargeError:
        return _error_response(
            status.HTTP_413_CONTENT_TOO_LARGE,
            "declaration_too_large",
            "La declaration depasse la taille autorisee.",
        )
    except DeclarationSourceReadError:
        return _error_response(
            status.HTTP_400_BAD_REQUEST,
            "declaration_unreadable",
            "La declaration ne peut pas etre lue.",
        )
    finally:
        await file.close()

    return _to_response(result)


@router.post(
    "/analyze",
    response_model=TaxDeclarationAnalysisResponse,
    responses={
        400: {"model": TaxDeclarationErrorResponse},
        413: {"model": TaxDeclarationErrorResponse},
        500: {"model": TaxDeclarationErrorResponse},
    },
)
async def analyze_tax_declaration(
    settings: SettingsDependency,
    file: Annotated[UploadFile, File()],
    declaration_type: Annotated[TaxDeclarationType | None, Form()] = None,
    sheet_name: Annotated[str | None, Form()] = None,
    period_end: Annotated[date | None, Form()] = None,
    filing_date: Annotated[date | None, Form()] = None,
    tolerance: Annotated[Decimal, Form()] = Decimal("0"),
) -> TaxDeclarationAnalysisResponse | JSONResponse:
    original_file_name = Path(file.filename or "declaration.upload").name
    try:
        result = await _ingest_upload(
            file,
            settings,
            declaration_type=declaration_type,
            sheet_name=sheet_name,
            original_file_name=original_file_name,
        )
        validation = None
        if (
            result.declaration is not None
            and result.declaration_type is TaxDeclarationType.VAT
        ):
            rules = load_vat_validation_rules(
                Path(settings.vat_validation_rules_path),
            )
            validation = VatDeclarationValidator().validate(
                result.declaration,
                rules,
                period_end=period_end,
                filing_date=filing_date,
            )
        elif (
            result.declaration is not None
            and result.declaration_type is TaxDeclarationType.WITHHOLDING_TAX
        ):
            withholding_rules = load_withholding_validation_rules(
                Path(settings.withholding_validation_rules_path),
            )
            withholding_deadline_rules = load_withholding_deadline_rules(
                Path(settings.withholding_deadline_rules_path),
            )
            validation = WithholdingDeclarationValidator().validate(
                result.declaration,
                withholding_rules,
                period_end=period_end,
                filing_date=filing_date,
                deadline_rules=withholding_deadline_rules,
                tolerance=tolerance,
            )
        elif (
            result.declaration is not None
            and result.declaration_type is TaxDeclarationType.PAYROLL_TAX
        ):
            payroll_tax_rules = load_payroll_tax_validation_rules(
                Path(settings.payroll_tax_validation_rules_path),
            )
            validation = PayrollTaxDeclarationValidator().validate(
                result.declaration,
                payroll_tax_rules,
                period_end=period_end,
                filing_date=filing_date,
                tolerance=tolerance,
            )
        assurance = (
            TaxAssuranceService().assess(
                (validation,),
                load_tax_assurance_policies(
                    Path(settings.tax_assurance_policy_path),
                ),
            )
            if validation is not None
            else None
        )
    except TaxDeclarationUploadTooLargeError:
        return _error_response(
            status.HTTP_413_CONTENT_TOO_LARGE,
            "declaration_too_large",
            "La declaration depasse la taille autorisee.",
        )
    except DeclarationSourceReadError:
        return _error_response(
            status.HTTP_400_BAD_REQUEST,
            "declaration_unreadable",
            "La declaration ne peut pas etre lue.",
        )
    except VatRuleReferenceError:
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "vat_rule_reference_error",
            "Le referentiel de validation TVA est indisponible.",
        )
    except (WithholdingRuleReferenceError, WithholdingDeadlineReferenceError):
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "withholding_rule_reference_error",
            "Le referentiel de validation RAS est indisponible.",
        )
    except PayrollTaxRuleReferenceError:
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "payroll_tax_rule_reference_error",
            "Le referentiel de validation IUTS est indisponible.",
        )
    except TaxAssurancePolicyError:
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "tax_assurance_policy_error",
            "Le referentiel des niveaux d'assurance est indisponible.",
        )
    finally:
        await file.close()

    ingestion_response = _to_response(result)
    return TaxDeclarationAnalysisResponse(
        **ingestion_response.model_dump(),
        validation=(
            _validation_response(validation) if validation is not None else None
        ),
        assurance=(
            _assurance_response(assurance) if assurance is not None else None
        ),
    )


@router.post(
    "/analyze-history",
    response_model=TaxDeclarationHistoryResponse,
    responses={
        400: {"model": TaxDeclarationErrorResponse},
        413: {"model": TaxDeclarationErrorResponse},
        500: {"model": TaxDeclarationErrorResponse},
    },
)
async def analyze_tax_declaration_history(
    settings: SettingsDependency,
    current_file: Annotated[UploadFile, File()],
    previous_file: Annotated[UploadFile, File()],
    current_period_end: Annotated[date, Form()],
    previous_period_end: Annotated[date, Form()],
    current_sheet_name: Annotated[str | None, Form()] = None,
    previous_sheet_name: Annotated[str | None, Form()] = None,
) -> TaxDeclarationHistoryResponse | JSONResponse:
    try:
        current = await _ingest_upload(
            current_file,
            settings,
            declaration_type=TaxDeclarationType.VAT,
            sheet_name=current_sheet_name,
            original_file_name=Path(
                current_file.filename or "current-declaration.upload",
            ).name,
        )
        previous = await _ingest_upload(
            previous_file,
            settings,
            declaration_type=TaxDeclarationType.VAT,
            sheet_name=previous_sheet_name,
            original_file_name=Path(
                previous_file.filename or "previous-declaration.upload",
            ).name,
        )
        validation = None
        if current.declaration is not None and previous.declaration is not None:
            rules = load_vat_validation_rules(
                Path(settings.vat_validation_rules_path),
            )
            validation = VatHistoricalValidator().validate(
                current.declaration,
                previous.declaration,
                rules,
                current_period_end=current_period_end,
                previous_period_end=previous_period_end,
            )
    except TaxDeclarationUploadTooLargeError:
        return _error_response(
            status.HTTP_413_CONTENT_TOO_LARGE,
            "declaration_too_large",
            "Une declaration depasse la taille autorisee.",
        )
    except DeclarationSourceReadError:
        return _error_response(
            status.HTTP_400_BAD_REQUEST,
            "declaration_unreadable",
            "Une declaration ne peut pas etre lue.",
        )
    except VatRuleReferenceError:
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "vat_rule_reference_error",
            "Le referentiel de validation TVA est indisponible.",
        )
    finally:
        await current_file.close()
        await previous_file.close()

    return TaxDeclarationHistoryResponse(
        current=_to_response(current),
        previous=_to_response(previous),
        validation=(
            _validation_response(validation) if validation is not None else None
        ),
    )


@router.post(
    "/reconcile-ledger",
    response_model=TaxDeclarationLedgerReconciliationResponse,
    responses={
        400: {"model": TaxDeclarationErrorResponse},
        413: {"model": TaxDeclarationErrorResponse},
    },
)
async def reconcile_tax_declaration_ledger(
    settings: SettingsDependency,
    declaration_file: Annotated[UploadFile, File()],
    ledger_file: Annotated[UploadFile, File()],
    mapping_file: Annotated[UploadFile, File()],
    declaration_period_end: Annotated[date, Form()],
    declaration_currency: Annotated[str, Form()],
    ledger_sheet_name: Annotated[str, Form()],
    declaration_sheet_name: Annotated[str | None, Form()] = None,
) -> TaxDeclarationLedgerReconciliationResponse | JSONResponse:
    uploads = (declaration_file, ledger_file, mapping_file)
    try:
        with TemporaryDirectory(prefix="tax-ledger-reconciliation-") as directory:
            root = Path(directory)
            declaration_path = root / "declaration.upload"
            ledger_suffix = Path(ledger_file.filename or "ledger.xlsx").suffix
            ledger_path = root / f"ledger{ledger_suffix}"
            mapping_path = root / "mapping.csv"
            for upload, destination in zip(
                uploads,
                (declaration_path, ledger_path, mapping_path),
                strict=True,
            ):
                await _save_upload(
                    upload,
                    destination,
                    max_size_bytes=settings.agent_file_max_upload_bytes,
                )
            declaration_result = TaxDeclarationIngestionService().ingest(
                declaration_path,
                content_type=declaration_file.content_type,
                expected_type=TaxDeclarationType.VAT,
                sheet_name=declaration_sheet_name,
                file_name=Path(
                    declaration_file.filename or "declaration.upload",
                ).name,
            )
            mappings = load_vat_ledger_mappings(mapping_path)
            calculator = LedgerAnalysisService(
                excel_tools=ExcelAgentTools(allowed_root=root),
                posting_key_rules=load_posting_key_rules(
                    Path(settings.posting_key_rules_path),
                ),
            )
            evidence = VatLedgerEvidenceBuilder().build(
                calculator,
                ledger_path,
                ledger_sheet_name,
                mappings,
                period_end=declaration_period_end,
            )
            validation = (
                VatLedgerReconciler().reconcile(
                    declaration_result.declaration,
                    evidence,
                    declaration_currency=declaration_currency,
                )
                if declaration_result.declaration is not None
                else None
            )
    except TaxDeclarationUploadTooLargeError:
        return _error_response(
            status.HTTP_413_CONTENT_TOO_LARGE,
            "declaration_too_large",
            "Un fichier depasse la taille autorisee.",
        )
    except (
        DeclarationSourceReadError,
        LedgerSchemaValidationError,
        VatLedgerMappingError,
        ValueError,
    ):
        return _error_response(
            status.HTTP_400_BAD_REQUEST,
            "vat_ledger_reconciliation_error",
            "Le rapprochement TVA avec le Grand Livre a echoue.",
        )
    finally:
        for upload in uploads:
            await upload.close()

    return TaxDeclarationLedgerReconciliationResponse(
        declaration=_to_response(declaration_result),
        evidence=[_evidence_response(item) for item in evidence],
        validation=(
            _validation_response(validation) if validation is not None else None
        ),
    )


@router.post(
    "/reconcile-supporting-documents",
    response_model=TaxDeclarationSupportingReconciliationResponse,
    responses={
        400: {"model": TaxDeclarationErrorResponse},
        413: {"model": TaxDeclarationErrorResponse},
    },
)
async def reconcile_tax_declaration_supporting_documents(
    settings: SettingsDependency,
    declaration_file: Annotated[UploadFile, File()],
    invoices_file: Annotated[UploadFile, File()],
    declaration_currency: Annotated[str, Form()],
    tolerance: Annotated[Decimal, Form()] = Decimal("0"),
    payments_file: Annotated[UploadFile | None, File()] = None,
    declaration_sheet_name: Annotated[str | None, Form()] = None,
    invoices_sheet_name: Annotated[str | None, Form()] = None,
    payments_sheet_name: Annotated[str | None, Form()] = None,
) -> TaxDeclarationSupportingReconciliationResponse | JSONResponse:
    uploads = tuple(
        upload
        for upload in (declaration_file, invoices_file, payments_file)
        if upload is not None
    )
    try:
        with TemporaryDirectory(prefix="tax-supporting-reconciliation-") as directory:
            root = Path(directory)
            declaration_path = root / "declaration.upload"
            invoices_path = root / "invoices.upload"
            await _save_upload(
                declaration_file,
                declaration_path,
                max_size_bytes=settings.agent_file_max_upload_bytes,
            )
            await _save_upload(
                invoices_file,
                invoices_path,
                max_size_bytes=settings.agent_file_max_upload_bytes,
            )
            payments_path = root / "payments.upload"
            if payments_file is not None:
                await _save_upload(
                    payments_file,
                    payments_path,
                    max_size_bytes=settings.agent_file_max_upload_bytes,
                )

            declaration_result = TaxDeclarationIngestionService().ingest(
                declaration_path,
                content_type=declaration_file.content_type,
                expected_type=TaxDeclarationType.VAT,
                sheet_name=declaration_sheet_name,
                file_name=Path(
                    declaration_file.filename or "declaration.upload",
                ).name,
            )
            detector = DeclarationFormatDetector()
            invoices_reference = detector.detect(
                invoices_path,
                content_type=invoices_file.content_type,
                file_name=invoices_file.filename or "invoices.upload",
            ).source_reference
            extractor = SupportingEvidenceExtractor()
            invoices = extractor.extract_invoices(
                invoices_path,
                invoices_reference,
                sheet_name=invoices_sheet_name,
            )
            payments_reference: SourceReference | None = None
            payments: tuple[PaymentEvidence, ...] = ()
            if payments_file is not None:
                payments_reference = detector.detect(
                    payments_path,
                    content_type=payments_file.content_type,
                    file_name=payments_file.filename or "payments.upload",
                ).source_reference
                payments = extractor.extract_payments(
                    payments_path,
                    payments_reference,
                    sheet_name=payments_sheet_name,
                )
            validation = (
                SupportingEvidenceValidator().validate(
                    declaration_result.declaration,
                    invoices,
                    payments,
                    declaration_currency=declaration_currency,
                    tolerance=tolerance,
                )
                if declaration_result.declaration is not None
                else None
            )
    except TaxDeclarationUploadTooLargeError:
        return _error_response(
            status.HTTP_413_CONTENT_TOO_LARGE,
            "supporting_document_too_large",
            "Un fichier depasse la taille autorisee.",
        )
    except (
        DeclarationSourceReadError,
        SupportingEvidenceExtractionError,
        ValueError,
    ):
        return _error_response(
            status.HTTP_400_BAD_REQUEST,
            "supporting_document_reconciliation_error",
            "Le rapprochement TVA avec les pieces justificatives a echoue.",
        )
    finally:
        for upload in uploads:
            await upload.close()

    return TaxDeclarationSupportingReconciliationResponse(
        declaration=_to_response(declaration_result),
        invoices=_supporting_summary_response(
            invoices_reference,
            len(invoices),
            {invoice.currency for invoice in invoices if invoice.currency},
        ),
        payments=(
            _supporting_summary_response(
                payments_reference,
                len(payments),
                {payment.currency for payment in payments if payment.currency},
            )
            if payments_reference is not None
            else None
        ),
        validation=(
            _validation_response(validation) if validation is not None else None
        ),
    )


async def _ingest_upload(
    file: UploadFile,
    settings: Settings,
    *,
    declaration_type: TaxDeclarationType | None,
    sheet_name: str | None,
    original_file_name: str,
) -> TaxDeclarationIngestionResult:
    with TemporaryDirectory(prefix="tax-declaration-") as directory:
        source_path = Path(directory) / "source.upload"
        await _save_upload(
            file,
            source_path,
            max_size_bytes=settings.agent_file_max_upload_bytes,
        )
        return TaxDeclarationIngestionService().ingest(
            source_path,
            content_type=file.content_type,
            expected_type=declaration_type,
            sheet_name=sheet_name,
            file_name=original_file_name,
        )


async def _save_upload(
    upload: UploadFile,
    destination: Path,
    *,
    max_size_bytes: int,
) -> None:
    total_size = 0
    with destination.open("wb") as target:
        while chunk := await upload.read(_UPLOAD_CHUNK_BYTES):
            total_size += len(chunk)
            if total_size > max_size_bytes:
                raise TaxDeclarationUploadTooLargeError
            target.write(chunk)


def _to_response(
    result: TaxDeclarationIngestionResult,
) -> TaxDeclarationIngestionResponse:
    reference = result.detection.source_reference
    return TaxDeclarationIngestionResponse(
        file_name=reference.file_name,
        source_format=reference.source_format.value,
        format_confidence=result.detection.confidence,
        format_evidence=result.detection.evidence,
        content_sha256=reference.content_sha256,
        declaration_type=result.declaration_type.value,
        status=result.status.value,
        reason=result.reason,
        declaration=(
            _declaration_response(result.declaration)
            if result.declaration is not None
            else None
        ),
    )


def _declaration_response(
    declaration: CanonicalTaxDeclaration,
) -> CanonicalDeclarationResponse:
    return CanonicalDeclarationResponse(
        schema_version=declaration.schema_version,
        declaration_type=declaration.declaration_type.value,
        fields=[_field_response(field) for field in declaration.fields],
        records=[
            CanonicalRecordResponse(
                record_type=record.record_type,
                fields=[_field_response(field) for field in record.fields],
            )
            for record in declaration.records
        ],
    )


def _field_response(field: CanonicalField) -> CanonicalFieldResponse:
    return CanonicalFieldResponse(
        name=field.name,
        source_value=_json_value(field.source_value),
        normalized_value=_json_value(field.normalized_value),
        confidence=field.confidence,
        status=field.status.value,
        locator=field.provenance.locator,
    )


def _validation_response(
    report: TaxDeclarationValidationReport,
) -> TaxDeclarationValidationResponse:
    return TaxDeclarationValidationResponse(
        overall_status=report.overall_status.value,
        checks=[
            ValidationCheckResponse(
                check_id=check.check_id,
                layer=check.layer.value,
                status=check.status.value,
                severity=check.severity.value,
                message=check.message,
                source_url=check.source_url,
                source_locator=check.source_locator,
                expected_value=_decimal_text(check.expected_value),
                actual_value=_decimal_text(check.actual_value),
                difference=_decimal_text(check.difference),
                expected_date=(
                    check.expected_date.isoformat()
                    if check.expected_date is not None
                    else None
                ),
                actual_date=(
                    check.actual_date.isoformat()
                    if check.actual_date is not None
                    else None
                ),
                affected_lines=list(check.affected_lines),
            )
            for check in report.checks
        ],
    )


def _assurance_response(
    assessment: TaxAssuranceAssessment,
) -> TaxAssuranceAssessmentResponse:
    return TaxAssuranceAssessmentResponse(
        level=assessment.level,
        policy_id=assessment.policy_id,
        policy_version=assessment.policy_version,
        description=assessment.description,
        passed_layers=[layer.value for layer in assessment.passed_layers],
        missing_layers=[layer.value for layer in assessment.missing_layers],
        failed_layers=[layer.value for layer in assessment.failed_layers],
    )


def _decimal_text(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def _evidence_response(evidence: VatLedgerEvidence) -> VatLedgerEvidenceResponse:
    return VatLedgerEvidenceResponse(
        declaration_line=evidence.declaration_line,
        currency=evidence.currency,
        amount=str(evidence.amount),
        entry_count=evidence.entry_count,
        used_entry_count=evidence.used_entry_count,
        excluded_entry_count=evidence.excluded_entry_count,
        accounts=list(evidence.accounts),
        mapping_ids=list(evidence.mapping_ids),
        source_references=list(evidence.source_references),
        tolerance=str(evidence.tolerance),
    )


def _supporting_summary_response(
    reference: SourceReference,
    record_count: int,
    currencies: set[str],
) -> SupportingEvidenceSummaryResponse:
    return SupportingEvidenceSummaryResponse(
        file_name=reference.file_name,
        source_format=reference.source_format.value,
        content_sha256=reference.content_sha256,
        record_count=record_count,
        currencies=sorted(currencies),
    )


def _json_value(value: Any) -> Any:
    return str(value) if isinstance(value, Decimal) else value


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    response = TaxDeclarationErrorResponse(
        error=TaxDeclarationErrorDetail(code=code, message=message),
    )
    return JSONResponse(status_code=status_code, content=response.model_dump())
