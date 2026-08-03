from dataclasses import dataclass

from app.tax_declaration.domain import TaxDeclarationType

CORPORATE_INCOME_TAX_SCHEMA_VERSION = "bf.is.v1"
CORPORATE_INCOME_TAX_OFFICIAL_FORM_URLS = (
    "https://dgi.bf/wp-content/uploads/2023/10/"
    "DECLARATION-DES-BENEFICES-SOUMIS-A-LIMPOT-SUR-LES-SOCIETES.pdf",
    "https://dgi.bf/wp-content/uploads/2023/10/"
    "DECLARATION-DES-ACOMPTES-PROVISIONNELS-IMPOT-SUR-LES-SOCIETES-.pdf",
    "https://dgi.bf/wp-content/uploads/2023/10/"
    "BORDEREAU-AVIS-DE-VERSEMENT-MINIMUM-FORFAITAIRE-DE-PERCEPTION-"
    "ACOMPTE-BIC.pdf",
)


@dataclass(frozen=True)
class CanonicalCorporateIncomeTaxSchema:
    version: str
    declaration_type: TaxDeclarationType
    jurisdiction: str
    official_source_urls: tuple[str, ...]
    declaration_fields: tuple[str, ...]
    record_fields: tuple[str, ...]


BURKINA_FASO_CORPORATE_INCOME_TAX_SCHEMA = CanonicalCorporateIncomeTaxSchema(
    version=CORPORATE_INCOME_TAX_SCHEMA_VERSION,
    declaration_type=TaxDeclarationType.CORPORATE_INCOME_TAX,
    jurisdiction="BF",
    official_source_urls=CORPORATE_INCOME_TAX_OFFICIAL_FORM_URLS,
    declaration_fields=(
        "period",
        "taxpayer_identifiers",
        "taxpayer_name",
        "activity",
        "address",
    ),
    record_fields=(
        "company_identifier",
        "company_identifier_type",
        "company_name",
        "tax_regime",
        "taxable_profit",
        "annual_turnover_excluding_tax",
        "computed_corporate_tax",
        "minimum_tax_declared",
        "minimum_tax_treatment",
        "corporate_tax_due",
        "provisional_installments_paid",
    ),
)
