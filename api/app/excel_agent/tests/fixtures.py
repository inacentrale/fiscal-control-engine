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
