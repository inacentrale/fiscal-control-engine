from pathlib import Path

from app.config import get_settings
from app.ras_audit.legal_rules import load_ras_legal_rules
from app.ras_audit.tax_event_rules import load_ras_tax_event_rules
from app.ras_audit.theoretical_calculation import load_ras_calculation_parameters


def main() -> int:
    settings = get_settings()
    repository_root = Path(settings.ras_legal_repository_root_path)
    legal_rules = load_ras_legal_rules(
        Path(settings.ras_legal_rules_path),
        repository_root=repository_root,
    )
    tax_event_rules = load_ras_tax_event_rules(
        Path(settings.ras_tax_event_rules_path),
        repository_root=repository_root,
    )
    calculation_parameters = load_ras_calculation_parameters(
        Path(settings.ras_calculation_parameters_path),
        repository_root=repository_root,
    )
    print(
        "RAS source verification ok: "
        f"legal_rules={len(legal_rules)} "
        f"tax_event_rules={len(tax_event_rules)} "
        f"calculation_parameters={len(calculation_parameters)}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
