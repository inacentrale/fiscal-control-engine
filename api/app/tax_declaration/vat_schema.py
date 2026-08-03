from dataclasses import dataclass

from app.tax_declaration.domain import TaxDeclarationType

VAT_SCHEMA_VERSION = "bf.vat.v1"
VAT_OFFICIAL_FORM_URL = (
    "https://dgi.bf/wp-content/uploads/2023/10/"
    "DECLARATION-DE-LA-TAXE-SUR-LA-VALEUR-AJOUTEE.pdf"
)


@dataclass(frozen=True)
class CanonicalDeclarationSchema:
    version: str
    declaration_type: TaxDeclarationType
    jurisdiction: str
    official_source_url: str
    declaration_fields: tuple[str, ...]
    record_fields: tuple[str, ...]


BURKINA_FASO_VAT_SCHEMA = CanonicalDeclarationSchema(
    version=VAT_SCHEMA_VERSION,
    declaration_type=TaxDeclarationType.VAT,
    jurisdiction="BF",
    official_source_url=VAT_OFFICIAL_FORM_URL,
    declaration_fields=(
        "period",
        "taxpayer_identifiers",
        "taxpayer_name",
        "activity",
        "address",
    ),
    record_fields=(
        "line_code",
        "operation_nature",
        "tax_base",
        "tax_rate",
        "tax_amount",
    ),
)

