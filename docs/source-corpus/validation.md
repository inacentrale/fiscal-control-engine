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
- une source fiscale expose `applicable_from` et `applicable_to`, meme si
  une borne reste vide parce qu'elle n'est pas encore confirmee.

## Fichiers Ignores au Scan

- `README.md`
- `source-template.md`
- `validation.md`
- `markdown-loading.md`
- `export.md`

## Etat Actuel

Seize sources fiscales sont remplies avec des extraits ou syntheses
controles du Code general des impots, de lois de finances ou d'imprimes
officiels DGI et sont desormais indexables,
`validation_status: validated`:

- `fiscal/bf-ras-non-residents.md` (articles 210-214, 107)
- `fiscal/bf-ras-residents.md` (articles 206-209)
- `fiscal/bf-loyers.md` (articles 120-128, 215-219)
- `fiscal/bf-tva-cgi.md` (articles 317 et 334)
- `fiscal/bf-iuts-cgi.md` (articles 112, 113 et 116)
- `fiscal/bf-is-cgi.md` (articles 87 a 95)
- `fiscal/bf-tva-official-form.md` (lignes 01 a 27 et synthese)
- `fiscal/bf-iuts-official-form.md` (synthese et etat annexe)
- `fiscal/bf-is-official-form.md` (identification, exercice, regime et CGA)
- `fiscal/bf-is-installments-official-form.md` (structure des acomptes)
- `fiscal/bf-finance-law-2024-ras.md` (articles 16 et 18)
- `fiscal/bf-finance-law-2025-ras.md` (articles 20 et 23)
- `fiscal/bf-finance-law-2026-ras.md` (articles 15 et 16)
- `fiscal/bf-tva-base-administrative-instruction.md` (contexte d'assiette)
- `fiscal/bf-tva-exemptions-administrative-instruction.md` (base legale)
- `fiscal/bf-iuts-domicile-administrative-instruction.md` (domicile fiscal)

Les anciens blocs RAS ont ete extraits directement du PDF officiel; les
nouveaux blocs sont des syntheses controlees sur les pages officielles
indiquees et rapprochees des referentiels deterministes. Le statut
`validated` a ete obtenu par
**auto-validation du porteur du projet** (`validated_by` le mentionne
explicitement), pas par une relecture d'expert-comptable ou fiscaliste —
voir `docs/open-questions.md` pour le detail de cette decision. Une
relecture professionnelle reste a faire des que possible; si elle revele
une erreur, ces fichiers et l'export genere devront etre corriges.
