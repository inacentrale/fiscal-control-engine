from dataclasses import dataclass

from app.tax_declaration.domain import TaxDeclarationType

PAYROLL_TAX_SCHEMA_VERSION = "bf.iuts.v1"
PAYROLL_TAX_OFFICIAL_FORM_URL = (
    "https://dgi.bf/wp-content/uploads/2023/10/"
    "DECLARATION-DE-VERSEMENT-DE-RETENUE-DE-LIMPOT-UNIQUE-SUR-LES-"
    "TRAITEMENTS-ET-SALAIRES-IUTS-ET-TAXE-PATRONAL-DAPPRENTISSAGE-TPA.pdf"
)


@dataclass(frozen=True)
class CanonicalPayrollTaxSchema:
    version: str
    declaration_type: TaxDeclarationType
    jurisdiction: str
    official_source_urls: tuple[str, ...]
    declaration_fields: tuple[str, ...]
    record_fields: tuple[str, ...]


BURKINA_FASO_PAYROLL_TAX_SCHEMA = CanonicalPayrollTaxSchema(
    version=PAYROLL_TAX_SCHEMA_VERSION,
    declaration_type=TaxDeclarationType.PAYROLL_TAX,
    jurisdiction="BF",
    official_source_urls=(PAYROLL_TAX_OFFICIAL_FORM_URL,),
    declaration_fields=(
        "period",
        "taxpayer_identifiers",
        "taxpayer_name",
        "activity",
        "address",
    ),
    record_fields=(
        "line_number",
        "employee_identifier",
        "employee_name",
        "gross_salary",
        "taxable_base",
        "dependent_count",
        "iuts_amount",
    ),
)
