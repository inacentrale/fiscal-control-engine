from app.account_mapping.domain import (
    AccountMapping,
    ClassificationStatus,
    RasCategory,
)
from app.account_mapping.repository import InMemoryAccountMappingRepository


def test_repository_saves_and_lists_mappings() -> None:
    repository = InMemoryAccountMappingRepository()
    mapping = AccountMapping(
        account_number="62210000",
        label="HONORAIRES",
        ras_category=RasCategory.RESIDENT_SERVICES,
        classification_status=ClassificationStatus.CLASSIFIED,
        confidence="medium",
        justification="Libelle compatible avec des prestations de services.",
        action_required="Verifier IFU et seuil facture.",
    )

    repository.save_all([mapping])

    assert repository.list_all() == [mapping]


def test_repository_replaces_existing_mappings_by_account_number() -> None:
    repository = InMemoryAccountMappingRepository()
    original = AccountMapping(
        account_number="62210000",
        label="HONORAIRES",
        ras_category=RasCategory.TO_CONFIRM,
        classification_status=ClassificationStatus.TO_CONFIRM,
        confidence="low",
        justification="Compte a qualifier par le metier avant controle RAS.",
        action_required="Confirmer la categorie fiscale applicable.",
    )
    replacement = AccountMapping(
        account_number="62210000",
        label="HONORAIRES CONSEIL",
        ras_category=RasCategory.RESIDENT_SERVICES,
        classification_status=ClassificationStatus.CLASSIFIED,
        confidence="medium",
        justification="Libelle compatible avec des prestations de services.",
        action_required="Verifier IFU et seuil facture.",
    )

    repository.save_all([original])
    repository.save_all([replacement])

    assert repository.list_all() == [replacement]


def test_repository_lists_mappings_sorted_by_account_number() -> None:
    repository = InMemoryAccountMappingRepository()
    mapping_706 = AccountMapping(
        account_number="706000",
        label="VENTES SERVICES",
        ras_category=RasCategory.OUT_OF_SCOPE,
        classification_status=ClassificationStatus.CLASSIFIED,
        confidence="medium",
        justification="Compte hors perimetre achats.",
        action_required="Aucune action.",
    )
    mapping_604 = AccountMapping(
        account_number="604000",
        label="ACHATS PRESTATIONS",
        ras_category=RasCategory.RESIDENT_SERVICES,
        classification_status=ClassificationStatus.CLASSIFIED,
        confidence="medium",
        justification="Libelle compatible avec des prestations de services.",
        action_required="Verifier IFU et seuil facture.",
    )

    repository.save_all([mapping_706, mapping_604])

    assert repository.list_all() == [mapping_604, mapping_706]
