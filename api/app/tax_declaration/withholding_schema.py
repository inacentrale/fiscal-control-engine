from dataclasses import dataclass

from app.tax_declaration.domain import TaxDeclarationType

WITHHOLDING_SCHEMA_VERSION = "bf.withholding.v1"
WITHHOLDING_OFFICIAL_FORM_URLS = (
    "https://dgi.bf/wp-content/uploads/2023/10/"
    "DECLARATION-DE-RETENUE-A-LA-SOURCE-SUR-LES-SOMMES-VERSEES-AUX-"
    "PRESTATAIRES-ETABLIS-AU-BURKINA-FASO.pdf",
    "https://dgi.bf/wp-content/uploads/2023/10/"
    "DECLARATION-DE-RETENUE-A-LA-SOURCE-SUR-LES-SOMMES-VERSEES-AUX-"
    "PERSONNES-PRESTATAIRES-NAYANT-PAS-DINSTALLATION-AU-BURKINA-FASO.pdf",
    "https://dgi.bf/wp-content/uploads/2023/10/declaration-rslib-new-2024.pdf",
)


@dataclass(frozen=True)
class CanonicalWithholdingSchema:
    version: str
    declaration_type: TaxDeclarationType
    jurisdiction: str
    official_source_urls: tuple[str, ...]
    declaration_fields: tuple[str, ...]
    record_fields: tuple[str, ...]


BURKINA_FASO_WITHHOLDING_SCHEMA = CanonicalWithholdingSchema(
    version=WITHHOLDING_SCHEMA_VERSION,
    declaration_type=TaxDeclarationType.WITHHOLDING_TAX,
    jurisdiction="BF",
    official_source_urls=WITHHOLDING_OFFICIAL_FORM_URLS,
    declaration_fields=(
        "period",
        "taxpayer_identifiers",
        "taxpayer_name",
        "activity",
        "address",
        "withholding_regime",
    ),
    record_fields=(
        "line_code",
        "withholding_regime",
        "rate_category",
        "withholding_category",
        "payment_amount",
        "tax_base",
        "tax_rate",
        "withheld_amount",
    ),
)
