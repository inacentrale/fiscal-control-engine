REQUIRED_LEDGER_COLUMNS = (
    "Compte",
    "Date comptable",
    "Libelle",
    "Debit",
    "Credit",
)

CANONICAL_LEDGER_FIELDS = (
    "account",
    "amount",
    "currency",
    "text",
    "vendor",
    "customer",
    "tax_code",
    "period",
    "fiscal_year",
    "document_type",
    "posting_key",
)

REQUIRED_CANONICAL_LEDGER_FIELDS = (
    "account",
    "amount",
    "text",
)

LEDGER_AGGREGATION_FIELDS = (
    "account",
    "currency",
    "period",
    "document_type",
    "tax_code",
    "vendor",
    "customer",
)

LEDGER_QUERY_OUTPUT_FIELDS = (
    "account",
    "amount",
    "posting_key",
    "currency",
    "period",
    "fiscal_year",
    "document_type",
    "tax_code",
    "vendor",
    "customer",
)

LEDGER_QUALITY_CRITICAL_FIELDS = (
    "account",
    "amount",
    "text",
)

LEDGER_COUNTERPARTY_FIELDS = (
    "vendor",
    "customer",
)

LEDGER_TAX_CANDIDATE_LIMIT = 20

LEDGER_SCHEMA_MIN_CONFIDENCE = 0.65
LEDGER_SCHEMA_AMBIGUITY_MARGIN = 0.04

LEDGER_FIELD_SYNONYMS = {
    "account": (
        "compte",
        "compte general",
        "numero compte",
        "n compte",
        "nº compte",
        "gl account",
        "account",
    ),
    "amount": (
        "montant devise document",
        "montant en devise document",
        "montant en devise interne",
        "montant",
        "debit",
        "credit",
        "amount",
        "balance",
    ),
    "currency": (
        "devise piece",
        "devise de la piece",
        "devise interne",
        "devise",
        "currency",
    ),
    "text": (
        "texte",
        "libelle",
        "description",
        "designation",
        "memo",
    ),
    "vendor": (
        "fournisseur",
        "vendor",
        "supplier",
    ),
    "customer": (
        "client",
        "customer",
    ),
    "tax_code": (
        "code tva",
        "tva",
        "tax code",
        "vat code",
    ),
    "period": (
        "periode comptable",
        "periode",
        "mois",
        "period",
    ),
    "fiscal_year": (
        "exercice comptable",
        "exercice",
        "annee fiscale",
        "fiscal year",
    ),
    "document_type": (
        "type de piece",
        "type piece",
        "document type",
        "piece type",
    ),
    "posting_key": (
        "cle comptabilisation",
        "cle de comptabilisation",
        "clé de comptabilisation",
        "posting key",
        "bschl",
    ),
}
