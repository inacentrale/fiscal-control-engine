from app.tax_declaration.partner_reconciliation import (
    PartnerMatchStatus,
    PartnerReconciler,
    PartnerReference,
)


def test_matches_exact_identifier_kind_and_value() -> None:
    matches = PartnerReconciler().reconcile(
        (_partner("line-1", "00123", "NIF", "Societe A"),),
        (_partner("invoice-1", "00123", "nif", "Autre libelle"),),
    )

    assert matches[0].status is PartnerMatchStatus.EXACT
    assert matches[0].matched_by == "identifier"
    assert matches[0].declaration_reference_ids == ("line-1",)


def test_keeps_name_only_match_potential() -> None:
    matches = PartnerReconciler().reconcile(
        (_partner("line-1", None, None, "Société Alpha SARL"),),
        (_partner("invoice-1", None, None, "Societe Alpha SARL"),),
    )

    assert matches[0].status is PartnerMatchStatus.POTENTIAL
    assert matches[0].matched_by == "name"


def test_reports_conflict_instead_of_selecting_ambiguous_name() -> None:
    matches = PartnerReconciler().reconcile(
        (
            _partner("line-1", "A", "NIF", "Homonyme"),
            _partner("line-2", "B", "NIF", "Homonyme"),
        ),
        (_partner("invoice-1", None, None, "Homonyme"),),
    )

    assert matches[0].status is PartnerMatchStatus.CONFLICT
    assert matches[0].declaration_reference_ids == ("line-1", "line-2")


def test_distinguishes_unmatched_from_unresolved() -> None:
    matches = PartnerReconciler().reconcile(
        (_partner("line-1", "A", "NIF", "Societe A"),),
        (
            _partner("invoice-1", "B", "NIF", None),
            _partner("invoice-2", None, None, None),
        ),
    )

    assert [match.status for match in matches] == [
        PartnerMatchStatus.UNMATCHED,
        PartnerMatchStatus.UNRESOLVED,
    ]


def _partner(
    reference_id: str,
    identifier: str | None,
    identifier_type: str | None,
    name: str | None,
) -> PartnerReference:
    return PartnerReference(reference_id, identifier, identifier_type, name)
