from pathlib import Path

import pandas as pd


def write_minified_grand_livre(directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    workbook_path = directory / "grand_livre_minifie.xlsx"
    ledger = pd.DataFrame(
        {
            "Compte": ["601000", "604000", "706000", "44910002"],
            "Date comptable": pd.to_datetime(
                ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"],
            ),
            "Libelle": [
                "Achat fournitures",
                "Achat prestations",
                "Vente services",
                "Compte a analyser",
            ],
            "Debit": [1200.0, 700.0, None, 100.0],
            "Credit": [None, None, 1500.0, None],
        },
    )
    with pd.ExcelWriter(workbook_path, engine="openpyxl") as writer:
        ledger.to_excel(writer, sheet_name="Grand Livre", index=False)
    return workbook_path


def write_ras_audit_grand_livre(directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    workbook_path = directory / "ras_audit_gl.xlsx"
    ledger = pd.DataFrame(
        {
            "Societe": ["SYN-CO", "SYN-CO", "SYN-CO"],
            "Exercice": [2025, 2025, 2025],
            "Periode": [1, 1, 1],
            "Journal": ["ACH", "ACH", "ACH"],
            "Numero piece": ["000042", "000042", "000042"],
            "Numero ligne": ["001", "002", "003"],
            "Date comptable": pd.to_datetime(["2025-01-10"] * 3),
            "Compte": ["0632100", "0401100", "0447100"],
            "Tiers": ["SYN-TIERS-001"] * 3,
            "Libelle": [
                "Honoraires synthetiques",
                "Dette synthetique",
                "Retenue synthetique",
            ],
            "Cle de comptabilisation": ["40", "50", "50"],
            "Montant devise document": [100000, 95000, 5000],
            "Devise du document": ["XOF", "XOF", "XOF"],
        },
    )
    with pd.ExcelWriter(workbook_path, engine="openpyxl") as writer:
        ledger.to_excel(writer, sheet_name="GL", index=False)
    return workbook_path


def write_large_ras_audit_grand_livre(
    directory: Path,
    *,
    candidate_count: int = 600,
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    workbook_path = directory / "ras_audit_gl_large.xlsx"
    rows: list[dict[str, object]] = []
    for candidate_index in range(candidate_count):
        document_number = f"{candidate_index + 1:06d}"
        for line_number, account, posting_key, amount, label in (
            ("001", "0632100", "40", 100_000, "Honoraires synthetiques"),
            ("002", "0401100", "50", 95_000, "Dette synthetique"),
            ("003", "0447100", "50", 5_000, "Retenue synthetique"),
        ):
            rows.append(
                {
                    "Societe": "SYN-CO",
                    "Exercice": 2025,
                    "Periode": 1,
                    "Journal": "ACH",
                    "Numero piece": document_number,
                    "Numero ligne": line_number,
                    "Date comptable": pd.Timestamp("2025-01-10"),
                    "Compte": account,
                    "Tiers": f"SYN-TIERS-{candidate_index + 1:06d}",
                    "Libelle": label,
                    "Cle de comptabilisation": posting_key,
                    "Montant devise document": amount,
                    "Devise du document": "XOF",
                }
            )
    with pd.ExcelWriter(workbook_path, engine="openpyxl") as writer:
        pd.DataFrame(rows).to_excel(writer, sheet_name="GL", index=False)
    return workbook_path
