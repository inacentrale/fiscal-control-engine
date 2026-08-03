from dataclasses import dataclass
from enum import StrEnum

from app.account_mapping.constants import (
    LOW_CONFIDENCE,
    MISSING_LABEL_ACTION,
    MISSING_LABEL_CONFIDENCE,
    MISSING_LABEL_JUSTIFICATION,
    TO_CONFIRM_ACTION,
    TO_CONFIRM_JUSTIFICATION,
)


class RasCategory(StrEnum):
    NON_RESIDENT_SERVICES = "non_resident_services"
    RESIDENT_SERVICES = "resident_services"
    REAL_ESTATE_CHARGES = "real_estate_charges"
    OUT_OF_SCOPE = "out_of_scope"
    TO_CONFIRM = "to_confirm"


class ClassificationStatus(StrEnum):
    CLASSIFIED = "classified"
    TO_CONFIRM = "to_confirm"
    MISSING_LABEL = "missing_label"


class MissingAccountLabelError(ValueError):
    pass


@dataclass(frozen=True)
class GeneralLedgerAccount:
    number: str

    def __post_init__(self) -> None:
        normalized_number = self.number.strip()
        if not normalized_number:
            raise ValueError("account number is required")
        object.__setattr__(self, "number", normalized_number)


@dataclass(frozen=True)
class PlanAccount:
    number: str
    label: str

    def __post_init__(self) -> None:
        normalized_number = self.number.strip()
        normalized_label = self.label.strip()
        if not normalized_number:
            raise ValueError("account number is required")
        if not normalized_label:
            raise MissingAccountLabelError("account label is required")
        object.__setattr__(self, "number", normalized_number)
        object.__setattr__(self, "label", normalized_label)


@dataclass(frozen=True)
class AccountMapping:
    account_number: str
    label: str
    ras_category: RasCategory
    classification_status: ClassificationStatus
    confidence: str
    justification: str
    action_required: str

    def __post_init__(self) -> None:
        normalized_number = self.account_number.strip()
        normalized_label = self.label.strip()
        if not normalized_number:
            raise ValueError("account number is required")
        if (
            self.classification_status is not ClassificationStatus.MISSING_LABEL
            and not normalized_label
        ):
            raise MissingAccountLabelError("account label is required")
        object.__setattr__(self, "account_number", normalized_number)
        object.__setattr__(self, "label", normalized_label)


def build_account_mapping(
    ledger_account: GeneralLedgerAccount,
    plan_labels: dict[str, str],
) -> AccountMapping:
    label = plan_labels.get(ledger_account.number, "").strip()
    if not label:
        return AccountMapping(
            account_number=ledger_account.number,
            label="",
            ras_category=RasCategory.TO_CONFIRM,
            classification_status=ClassificationStatus.MISSING_LABEL,
            confidence=MISSING_LABEL_CONFIDENCE,
            justification=MISSING_LABEL_JUSTIFICATION,
            action_required=MISSING_LABEL_ACTION,
        )

    return AccountMapping(
        account_number=ledger_account.number,
        label=label,
        ras_category=RasCategory.TO_CONFIRM,
        classification_status=ClassificationStatus.TO_CONFIRM,
        confidence=LOW_CONFIDENCE,
        justification=TO_CONFIRM_JUSTIFICATION,
        action_required=TO_CONFIRM_ACTION,
    )
