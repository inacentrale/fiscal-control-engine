---
name: global-rules
description: Regles globales du projet Bank Files Harmonizer.
trigger: always_on
---

# Regles Globales

## Principes

- Preferer des changements petits, explicites et reviewables.
- Optimiser pour la clarte, la stabilite et la reproductibilite.
- KISS et YAGNI: pas de fonctionnalite, configuration ou abstraction speculative.
- Fail fast: valider les entrees et echouer explicitement en cas d'etat invalide.
- Les effets de bord doivent etre visibles et isoles.

## Vocabulaire Canonique

- `GrandLivre`
- `Compte`
- `PlanComptable`
- `LibelleCompte`
- `AccountMapping`
- `CategorieRas`
- `RegleFiscale`
- `ControleFiscal`
- `Anomalie`
- `Justification`
- `Rapport`

## Donnees et Confidentialite

- Les fichiers comptables et fiscaux sont sensibles.
- Ne jamais logguer de fichier complet, de donnees personnelles, de secret ou de contenu fiscal sensible.
- Les exemples de tests doivent etre minimaux, anonymises et limites au comportement a verifier.

## Documentation et Taches

- Les intentions et decisions durables vont dans `docs/`.
- Les skills projet vont dans `docs/skills/`.
- Les taches concretes et l'avancement vont dans les todos de domaine: `api/todo.md` et `front/todo.md`.
- Ne pas creer de fichier todo dans `docs/`.
