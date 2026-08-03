from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.tax_declaration.document_text_extractor import DocumentTextExtractionError
from app.tax_declaration.domain import (
    CanonicalTaxDeclaration,
    DeclarationSourceFormat,
    ResolutionStatus,
    SourceReference,
    TaxDeclarationType,
)
from app.tax_declaration.format_detector import (
    DeclarationFormatDetection,
    DeclarationFormatDetector,
)
from app.tax_declaration.payroll_tax_tabular_extractor import (
    PayrollTaxTabularExtractionError,
    PayrollTaxTabularExtractor,
)
from app.tax_declaration.payroll_tax_text_extractor import (
    PayrollTaxDocumentExtractor,
)
from app.tax_declaration.payroll_tax_xml_extractor import PayrollTaxXmlExtractor
from app.tax_declaration.vat_tabular_extractor import (
    VatTabularExtractionError,
    VatTabularExtractor,
)
from app.tax_declaration.vat_text_extractor import VatDocumentExtractor
from app.tax_declaration.vat_xml_extractor import VatXmlExtractor
from app.tax_declaration.withholding_tabular_extractor import (
    WithholdingTabularExtractionError,
    WithholdingTabularExtractor,
)
from app.tax_declaration.withholding_text_extractor import (
    WithholdingDocumentExtractor,
)
from app.tax_declaration.withholding_xml_extractor import WithholdingXmlExtractor


@dataclass(frozen=True)
class TaxDeclarationIngestionResult:
    detection: DeclarationFormatDetection
    declaration_type: TaxDeclarationType
    status: ResolutionStatus
    reason: str | None
    declaration: CanonicalTaxDeclaration | None


class TaxDeclarationIngestionService:
    def __init__(self) -> None:
        self._format_detector = DeclarationFormatDetector()
        self._vat_tabular_extractor = VatTabularExtractor()
        self._vat_xml_extractor = VatXmlExtractor()
        self._vat_document_extractor = VatDocumentExtractor()
        self._withholding_tabular_extractor = WithholdingTabularExtractor()
        self._withholding_xml_extractor = WithholdingXmlExtractor()
        self._withholding_document_extractor = WithholdingDocumentExtractor()
        self._payroll_tax_tabular_extractor = PayrollTaxTabularExtractor()
        self._payroll_tax_xml_extractor = PayrollTaxXmlExtractor()
        self._payroll_tax_document_extractor = PayrollTaxDocumentExtractor()

    def ingest(
        self,
        source_path: Path,
        *,
        content_type: str | None = None,
        expected_type: TaxDeclarationType | None = None,
        sheet_name: str | None = None,
        file_name: str | None = None,
    ) -> TaxDeclarationIngestionResult:
        detection = self._format_detector.detect(
            source_path,
            content_type=content_type,
            file_name=file_name,
        )
        if expected_type not in (
            None,
            TaxDeclarationType.VAT,
            TaxDeclarationType.WITHHOLDING_TAX,
            TaxDeclarationType.PAYROLL_TAX,
        ):
            return _unresolved(detection, expected_type, "extractor_not_available")

        source_format = detection.source_reference.source_format
        try:
            if source_format in {
                DeclarationSourceFormat.CSV,
                DeclarationSourceFormat.EXCEL,
            }:
                is_payroll_tax = (
                    expected_type is TaxDeclarationType.PAYROLL_TAX
                    or (
                        expected_type is None
                        and self._payroll_tax_tabular_extractor.is_candidate(
                            source_path,
                            detection.source_reference,
                            sheet_name=sheet_name,
                        )
                    )
                )
                is_withholding = (
                    not is_payroll_tax
                    and (
                        expected_type is TaxDeclarationType.WITHHOLDING_TAX
                    or (
                        expected_type is None
                        and self._withholding_tabular_extractor.is_candidate(
                            source_path,
                            detection.source_reference,
                            sheet_name=sheet_name,
                        )
                    )
                    )
                )
                if is_payroll_tax:
                    declaration = self._payroll_tax_tabular_extractor.extract(
                        source_path,
                        detection.source_reference,
                        sheet_name=sheet_name,
                    )
                elif is_withholding:
                    declaration = self._withholding_tabular_extractor.extract(
                        source_path,
                        detection.source_reference,
                        sheet_name=sheet_name,
                    )
                else:
                    declaration = self._vat_tabular_extractor.extract(
                        source_path,
                        detection.source_reference,
                        sheet_name=sheet_name,
                    )
            elif source_format is DeclarationSourceFormat.XML:
                declaration = self._extract_xml(
                    source_path,
                    detection.source_reference,
                    expected_type,
                )
            elif source_format is DeclarationSourceFormat.PDF:
                declaration = self._extract_document(
                    source_path,
                    detection.source_reference,
                    expected_type,
                    is_pdf=True,
                )
            elif source_format is DeclarationSourceFormat.IMAGE:
                declaration = self._extract_document(
                    source_path,
                    detection.source_reference,
                    expected_type,
                    is_pdf=False,
                )
            else:
                return _unresolved(detection, expected_type, "extractor_not_available")
        except (
            VatTabularExtractionError,
            WithholdingTabularExtractionError,
            PayrollTaxTabularExtractionError,
            DocumentTextExtractionError,
        ):
            return _unresolved(detection, expected_type, "structure_unresolved")

        return TaxDeclarationIngestionResult(
            detection=detection,
            declaration_type=declaration.declaration_type,
            status=ResolutionStatus.RESOLVED,
            reason=None,
            declaration=declaration,
        )

    def _extract_xml(
        self,
        source_path: Path,
        source_reference: SourceReference,
        expected_type: TaxDeclarationType | None,
    ) -> CanonicalTaxDeclaration:
        if expected_type is TaxDeclarationType.VAT:
            return self._vat_xml_extractor.extract(source_path, source_reference)
        if expected_type is TaxDeclarationType.PAYROLL_TAX:
            return self._payroll_tax_xml_extractor.extract(
                source_path,
                source_reference,
            )
        if expected_type is TaxDeclarationType.WITHHOLDING_TAX:
            return self._withholding_xml_extractor.extract(
                source_path,
                source_reference,
            )
        try:
            return self._payroll_tax_xml_extractor.extract(
                source_path,
                source_reference,
            )
        except PayrollTaxTabularExtractionError:
            pass
        try:
            return self._withholding_xml_extractor.extract(
                source_path,
                source_reference,
            )
        except WithholdingTabularExtractionError:
            return self._vat_xml_extractor.extract(source_path, source_reference)

    def _extract_document(
        self,
        source_path: Path,
        source_reference: SourceReference,
        expected_type: TaxDeclarationType | None,
        *,
        is_pdf: bool,
    ) -> CanonicalTaxDeclaration:
        if expected_type is TaxDeclarationType.VAT:
            if is_pdf:
                return self._vat_document_extractor.extract_pdf(
                    source_path,
                    source_reference,
                )
            return self._vat_document_extractor.extract_image(
                source_path,
                source_reference,
            )
        if expected_type is TaxDeclarationType.PAYROLL_TAX:
            if is_pdf:
                return self._payroll_tax_document_extractor.extract_pdf(
                    source_path,
                    source_reference,
                )
            return self._payroll_tax_document_extractor.extract_image(
                source_path,
                source_reference,
            )
        if expected_type is TaxDeclarationType.WITHHOLDING_TAX:
            if is_pdf:
                return self._withholding_document_extractor.extract_pdf(
                    source_path,
                    source_reference,
                )
            return self._withholding_document_extractor.extract_image(
                source_path,
                source_reference,
            )
        try:
            if is_pdf:
                return self._payroll_tax_document_extractor.extract_pdf(
                    source_path,
                    source_reference,
                )
            return self._payroll_tax_document_extractor.extract_image(
                source_path,
                source_reference,
            )
        except (PayrollTaxTabularExtractionError, DocumentTextExtractionError):
            pass
        try:
            if is_pdf:
                return self._withholding_document_extractor.extract_pdf(
                    source_path,
                    source_reference,
                )
            return self._withholding_document_extractor.extract_image(
                source_path,
                source_reference,
            )
        except (WithholdingTabularExtractionError, DocumentTextExtractionError):
            pass
        if is_pdf:
            return self._vat_document_extractor.extract_pdf(
                source_path,
                source_reference,
            )
        return self._vat_document_extractor.extract_image(
            source_path,
            source_reference,
        )


def _unresolved(
    detection: DeclarationFormatDetection,
    expected_type: TaxDeclarationType | None,
    reason: str,
) -> TaxDeclarationIngestionResult:
    return TaxDeclarationIngestionResult(
        detection=detection,
        declaration_type=expected_type or TaxDeclarationType.UNRESOLVED,
        status=ResolutionStatus.UNRESOLVED,
        reason=reason,
        declaration=None,
    )
