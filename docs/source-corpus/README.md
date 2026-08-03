# Corpus Source RAG

Ce dossier contient les sources metier validees avant transformation en chunks RAG.

Le RAG est generique. La fiscalite est le premier domaine, mais le meme cadre peut accueillir des sources de conformite, finance, procedures ou autres domaines.

## Organisation

- `fiscal/`: textes fiscaux, doctrine, referentiels de taux et seuils.
- `procedures/`: procedures internes validees.
- `compliance/`: politiques, controles et regles de conformite.
- `finance/`: sources finance ou controle de gestion.
- `source-template.md`: modele de source a copier avant ajout d'un document.

## Regles

- Ne pas ajouter de contenu fiscal non valide.
- Ne pas ajouter de donnees client ou lignes completes de GL.
- Garder une version, une source et des themes clairs.
- Un document utilisateur reste non indexable tant qu'il n'est pas valide.
- Les fichiers de ce dossier sont des sources; les CSV de `docs/reference/` sont des artefacts exploitables par le code.
