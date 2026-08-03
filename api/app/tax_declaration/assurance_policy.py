import csv
from dataclasses import dataclass
from pathlib import Path

from app.tax_declaration.domain import TaxDeclarationType
from app.tax_declaration.validation_domain import ValidationLayer


@dataclass(frozen=True)
class TaxAssurancePolicy:
    policy_id: str
    version: str
    level: str
    rank: int
    required_layers: tuple[ValidationLayer, ...]
    description: str
    declaration_type: TaxDeclarationType


class TaxAssurancePolicyError(ValueError):
    pass


_REQUIRED_COLUMNS = {
    "policy_id",
    "version",
    "level",
    "rank",
    "required_layers",
    "description",
    "declaration_type",
}


def load_tax_assurance_policies(
    source_path: Path,
    *,
    declaration_type: TaxDeclarationType,
) -> tuple[TaxAssurancePolicy, ...]:
    try:
        with source_path.open(encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            if reader.fieldnames is None or not _REQUIRED_COLUMNS.issubset(
                reader.fieldnames,
            ):
                raise TaxAssurancePolicyError("invalid assurance policy columns")
            policies = tuple(
                policy
                for row in reader
                if (policy := _parse_policy(row)).declaration_type
                is declaration_type
            )
    except OSError as exc:
        raise TaxAssurancePolicyError("assurance policy cannot be read") from exc
    if not policies:
        raise TaxAssurancePolicyError("assurance policy is empty")
    if len({policy.policy_id for policy in policies}) != len(policies):
        raise TaxAssurancePolicyError("duplicate assurance policy id")
    if len({policy.rank for policy in policies}) != len(policies):
        raise TaxAssurancePolicyError("duplicate assurance policy rank")
    return tuple(sorted(policies, key=lambda policy: policy.rank))


def _parse_policy(row: dict[str, str | None]) -> TaxAssurancePolicy:
    values = {key: (value or "").strip() for key, value in row.items()}
    if any(not values[column] for column in _REQUIRED_COLUMNS):
        raise TaxAssurancePolicyError("assurance policy has an empty value")
    try:
        rank = int(values["rank"])
        declaration_type = TaxDeclarationType(values["declaration_type"])
        layers = tuple(
            ValidationLayer(layer.strip())
            for layer in values["required_layers"].split("|")
            if layer.strip()
        )
    except ValueError as exc:
        raise TaxAssurancePolicyError("invalid assurance policy value") from exc
    if rank < 1 or not layers:
        raise TaxAssurancePolicyError("invalid assurance policy rank or layers")
    return TaxAssurancePolicy(
        policy_id=values["policy_id"],
        version=values["version"],
        level=values["level"],
        rank=rank,
        required_layers=layers,
        description=values["description"],
        declaration_type=declaration_type,
    )
