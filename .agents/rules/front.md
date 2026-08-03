---
name: front-rules
description: Regles frontend futures pour l'interface de revue fiscale.
trigger: glob
globs:
  - "front/**/*"
---

# Regles Frontend

## Perimetre

- Le frontend sera defini apres le socle API.
- Interface cible: outil operationnel de revue fiscale, pas landing page marketing.
- Priorite a la lisibilite, aux tableaux, aux filtres, aux statuts et aux parcours de validation.

## Architecture

- Organiser par domaines metier: account mappings, controles fiscaux, anomalies, rapports.
- Les appels API doivent passer par une couche service typée.
- Les composants de domaine vivent dans `components/[domain]`.
- Les composants generiques vivent dans `components/ui` ou `components/base`.
- Utiliser des types explicites pour toutes les donnees venant de l'API.

## UX et Donnees

- Toujours afficher les etats de chargement, erreur, vide et succes.
- Les statuts fiscaux doivent etre scannables: badges, filtres, tri et details de justification.
- Ne pas masquer les comptes ambigus: ils doivent rester visibles comme `a confirmer`.
- Ne pas presenter une classification comme certaine si son niveau de confiance ne l'est pas.

## Tests

- Tester en priorite la logique pure: services API, formatage, filtres, validations et stores.
- Ne pas multiplier les tests de rendu UI sans valeur metier claire.
- Les parcours critiques de validation fiscale devront avoir des scenarios manuels ou E2E quand l'interface existe.
