from pathlib import Path

import pytest

from app.account_mapping.classifier import AccountMappingClassifier
from app.account_mapping.domain import (
    ClassificationStatus,
    GeneralLedgerAccount,
    RasCategory,
)
from app.account_mapping.rule_loader import load_classification_rules

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def build_classifier() -> AccountMappingClassifier:
    return AccountMappingClassifier(
        rules=load_classification_rules(FIXTURES_DIR / "ras_classification_rules.csv"),
    )


@pytest.mark.parametrize(
    ("label", "expected_category"),
    [
        ("HONORAIRES CONSEIL", RasCategory.RESIDENT_SERVICES),
        ("FRAIS D'ASSISTANCE TECHNIQUE", RasCategory.RESIDENT_SERVICES),
        ("LOYERS BUREAUX", RasCategory.REAL_ESTATE_CHARGES),
        ("REDEVANCES VERSEES A L ETRANGER", RasCategory.NON_RESIDENT_SERVICES),
        ("FRAIS DE SIEGE NON RESIDENT", RasCategory.NON_RESIDENT_SERVICES),
    ],
)
def test_classifier_classifies_obvious_ras_labels(
    label: str,
    expected_category: RasCategory,
) -> None:
    classifier = build_classifier()

    mapping = classifier.classify(
        ledger_account=GeneralLedgerAccount(number="62210000"),
        label=label,
    )

    assert mapping.ras_category is expected_category
    assert mapping.classification_status is ClassificationStatus.CLASSIFIED
    assert mapping.confidence == "medium"
    assert mapping.justification
    assert mapping.action_required


@pytest.mark.parametrize(
    "label",
    [
        "MATERIEL DE BUREAU",
        "COMPTE BANCAIRE",
        "PRETS AU PERSONNEL",
    ],
)
def test_classifier_marks_obvious_non_ras_labels_out_of_scope(label: str) -> None:
    classifier = build_classifier()

    mapping = classifier.classify(
        ledger_account=GeneralLedgerAccount(number="23520001"),
        label=label,
    )

    assert mapping.ras_category is RasCategory.OUT_OF_SCOPE
    assert mapping.classification_status is ClassificationStatus.CLASSIFIED
    assert mapping.confidence == "medium"


def test_classifier_keeps_ambiguous_label_to_confirm() -> None:
    classifier = build_classifier()

    mapping = classifier.classify(
        ledger_account=GeneralLedgerAccount(number="62290000"),
        label="CHARGES DIVERSES",
    )

    assert mapping.ras_category is RasCategory.TO_CONFIRM
    assert mapping.classification_status is ClassificationStatus.TO_CONFIRM
    assert mapping.confidence == "low"
    assert mapping.action_required == "Confirmer la categorie fiscale applicable."


def test_classifier_reports_missing_label() -> None:
    classifier = build_classifier()

    mapping = classifier.classify(
        ledger_account=GeneralLedgerAccount(number="44910002"),
        label="",
    )

    assert mapping.ras_category is RasCategory.TO_CONFIRM
    assert mapping.classification_status is ClassificationStatus.MISSING_LABEL
    assert mapping.confidence == "none"
