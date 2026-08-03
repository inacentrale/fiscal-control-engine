# Validation des Sources RAG

## Objectif

Une source ne peut etre chunkée puis indexee que si elle est complete et explicitement validee.

## Conditions

Une source Markdown est indexable uniquement si:

- toutes les metadonnees obligatoires sont presentes;
- `validation_status` vaut `validated`;
- aucun placeholder `A COMPLETER` n'est present;
- le contenu ne contient pas de donnees client ou de ligne complete de GL;
- la source est versionnee et citable.

## Fichiers Ignores au Scan

- `README.md`
- `source-template.md`
- `validation.md`
- `markdown-loading.md`
- `export.md`

## Etat Actuel

Les trois squelettes fiscaux sont detectes mais non indexables:

- `fiscal/bf-ras-non-residents.md`
- `fiscal/bf-ras-residents.md`
- `fiscal/bf-loyers.md`

Ils doivent etre remplis avec du contenu fiscal valide avant usage.
