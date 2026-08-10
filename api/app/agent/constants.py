BLOCKED_TAX_DECISION_ANSWER = (
    "La reponse du modele a ete bloquee: seule une explication appuyee "
    "sur les controles deterministes est autorisee."
)

OVERSIZED_MODEL_ANSWER = "La reponse du modele est trop longue pour etre retournee."

AGENT_RUN_TIMEOUT_ANSWER = "L'execution agent a depasse le temps autorise."

RAS_CATEGORY_BUSINESS_LABELS = {
    "resident_services": "Prestations de services à des résidents",
    "non_resident_services": "Prestations versées à des non-résidents",
    "real_estate_charges": "Loyers et charges immobilières",
    "out_of_scope": "Opérations sans indice direct de RAS",
    "to_confirm": "Nature fiscale à confirmer",
}

RAS_CANDIDATE_STATUS_LABELS = {
    "candidate_text_only": "Libellé uniquement",
    "candidate_account_only": "Compte uniquement",
    "candidate_account_and_text": "Compte et libellé concordants",
    "candidate_indeterminate": "Candidature à confirmer",
}

RAS_CERTAINTY_LABELS = {
    "high": "Élevée",
    "medium": "Moyenne",
    "low": "Faible",
    "indeterminate": "Indéterminée",
}

FORBIDDEN_TAX_DECISION_MARKERS = (
    "soumisras",
    "categorieras",
    "taux ras",
    "decision fiscale",
)
