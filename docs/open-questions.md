# Points Non Clarifies

Ce document garde les questions et decisions a reprendre plus tard. Elles ne bloquent pas le socle actuel, mais elles devront etre tranchees avant de stabiliser le mapping fiscal et la future base de donnees.

## Modele de Mapping

- Faut-il conserver la source exacte du fichier importe pour chaque mapping ?
- Faut-il modeliser un resultat d'import dedie avec statistiques ?
- Quelles statistiques d'import sont obligatoires ?
  - total de lignes lues;
  - comptes valides;
  - comptes ignores;
  - doublons;
  - erreurs;
  - comptes sans libelle.
- Quel format donner aux erreurs metier structurees ?
- `confidence` doit-il rester une chaine ou devenir une enum ?

## Classification RAS

- Les categories RAS minimales sont-elles suffisantes ?
  - prestations de services residents;
  - prestations de services non-residents;
  - charges immobilieres / loyers;
  - hors perimetre;
  - a confirmer.
- Faut-il separer le statut de qualification comptable du statut fiscal ?
- Quels libelles comptables permettent une pre-classification automatique fiable ?
- Quels comptes doivent obligatoirement rester en validation metier ?

## Donnees et Stockage

- Le stockage fichier/memoire suffit-il jusqu'a la validation du POC ?
- Quel sera le schema PostgreSQL cible pour les mappings ?
- Faut-il historiser les imports successifs ?
- Faut-il conserver les lignes sources ou seulement les mappings resultants ?

## Tests

- Quels cas doivent rester unitaires uniquement ?
- Quand introduire les tests d'integration Excel reels ?
- Faut-il creer des fixtures anonymisees derivees des fichiers fournis ?
