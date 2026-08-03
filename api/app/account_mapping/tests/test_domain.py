import pytest

from app.account_mapping.domain import (
    AccountMapping,
    ClassificationStatus,
    GeneralLedgerAccount,
    MissingAccountLabelError,
    PlanAccount,
    RasCategory,
    build_account_mapping,
)


def test_build_account_mapping_with_plan_label() -> None:
    mapping = build_account_mapping(
        ledger_account=GeneralLedgerAccount(number="62210000"),
        plan_labels={"62210000": "HONORAIRES"},
    )

    assert mapping == AccountMapping(
        account_number="62210000",
        label="HONORAIRES",
        ras_category=RasCategory.TO_CONFIRM,
        classification_status=ClassificationStatus.TO_CONFIRM,
        confidence="low",
        justification="Compte a qualifier par le metier avant controle RAS.",
        action_required="Confirmer la categorie fiscale applicable.",
    )


def test_build_account_mapping_reports_missing_plan_label() -> None:
    mapping = build_account_mapping(
        ledger_account=GeneralLedgerAccount(number="44910002"),
        plan_labels={},
    )

    assert mapping.account_number == "44910002"
    assert mapping.label == ""
    assert mapping.classification_status is ClassificationStatus.MISSING_LABEL
    assert mapping.ras_category is RasCategory.TO_CONFIRM
    assert mapping.confidence == "none"
    assert mapping.action_required == "Renseigner le libelle du compte."


def test_general_ledger_account_rejects_blank_number() -> None:
    with pytest.raises(ValueError, match="account number"):
        GeneralLedgerAccount(number=" ")


def test_plan_account_rejects_blank_label() -> None:
    with pytest.raises(MissingAccountLabelError, match="account label"):
        PlanAccount(number="62210000", label=" ")


def test_plan_account_strips_number_and_label() -> None:
    account = PlanAccount(number=" 62210000 ", label=" HONORAIRES ")

    assert account == PlanAccount(number="62210000", label="HONORAIRES")


def test_account_mapping_requires_label_when_status_is_not_missing() -> None:
    with pytest.raises(MissingAccountLabelError):
        AccountMapping(
            account_number="62210000",
            label="",
            ras_category=RasCategory.TO_CONFIRM,
            classification_status=ClassificationStatus.TO_CONFIRM,
            confidence="low",
            justification="Compte a qualifier par le metier avant controle RAS.",
            action_required="Confirmer la categorie fiscale applicable.",
        )
