from pathlib import Path

import pytest

from app.tax_declaration.assurance_policy import (
    TaxAssurancePolicyError,
    load_tax_assurance_policies,
)
from app.tax_declaration.domain import TaxDeclarationType
from app.tax_declaration.validation_domain import ValidationLayer


def test_loads_ordered_versioned_assurance_policy(tmp_path: Path) -> None:
    source = _write_policy(
        tmp_path,
        "high,v1,high,2,structure|reconciliation,High,vat\n"
        "limited,v1,limited,1,structure,Limited,vat\n"
        "payroll-limited,v1,limited,1,structure,Limited,payroll_tax\n",
    )

    policies = load_tax_assurance_policies(
        source,
        declaration_type=TaxDeclarationType.VAT,
    )

    assert [policy.level for policy in policies] == ["limited", "high"]
    assert policies[1].required_layers == (
        ValidationLayer.STRUCTURE,
        ValidationLayer.RECONCILIATION,
    )


def test_rejects_unknown_assurance_layer(tmp_path: Path) -> None:
    source = _write_policy(
        tmp_path,
        "limited,v1,limited,1,unknown,Limited,vat\n",
    )

    with pytest.raises(TaxAssurancePolicyError, match="invalid"):
        load_tax_assurance_policies(
            source,
            declaration_type=TaxDeclarationType.VAT,
        )


def _write_policy(tmp_path: Path, rows: str) -> Path:
    source = tmp_path / "policy.csv"
    source.write_text(
        "policy_id,version,level,rank,required_layers,description,"
        "declaration_type\n" + rows,
        encoding="utf-8",
    )
    return source
