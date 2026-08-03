from dataclasses import dataclass
from unicodedata import normalize

from app.account_mapping.constants import (
    LOW_CONFIDENCE,
    MISSING_LABEL_ACTION,
    MISSING_LABEL_CONFIDENCE,
    MISSING_LABEL_JUSTIFICATION,
    TO_CONFIRM_ACTION,
    TO_CONFIRM_JUSTIFICATION,
)
from app.account_mapping.domain import (
    AccountMapping,
    ClassificationStatus,
    GeneralLedgerAccount,
    RasCategory,
)


@dataclass(frozen=True)
class ClassificationRule:
    category: RasCategory
    keywords: tuple[str, ...]
    confidence: str
    justification: str
    action_required: str


class AccountMappingClassifier:
    def __init__(self, rules: tuple[ClassificationRule, ...]) -> None:
        self._rules = rules

    def classify(
        self,
        ledger_account: GeneralLedgerAccount,
        label: str,
    ) -> AccountMapping:
        normalized_label = label.strip()
        if not normalized_label:
            return AccountMapping(
                account_number=ledger_account.number,
                label="",
                ras_category=RasCategory.TO_CONFIRM,
                classification_status=ClassificationStatus.MISSING_LABEL,
                confidence=MISSING_LABEL_CONFIDENCE,
                justification=MISSING_LABEL_JUSTIFICATION,
                action_required=MISSING_LABEL_ACTION,
            )

        searchable_label = _normalize_for_search(normalized_label)
        for rule in self._rules:
            if _contains_any(searchable_label, rule.keywords):
                return AccountMapping(
                    account_number=ledger_account.number,
                    label=normalized_label,
                    ras_category=rule.category,
                    classification_status=ClassificationStatus.CLASSIFIED,
                    confidence=rule.confidence,
                    justification=rule.justification,
                    action_required=rule.action_required,
                )

        return AccountMapping(
            account_number=ledger_account.number,
            label=normalized_label,
            ras_category=RasCategory.TO_CONFIRM,
            classification_status=ClassificationStatus.TO_CONFIRM,
            confidence=LOW_CONFIDENCE,
            justification=TO_CONFIRM_JUSTIFICATION,
            action_required=TO_CONFIRM_ACTION,
        )


def _normalize_for_search(value: str) -> str:
    without_accents = normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return " ".join(without_accents.lower().split())


def _contains_any(value: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in value for keyword in keywords)
