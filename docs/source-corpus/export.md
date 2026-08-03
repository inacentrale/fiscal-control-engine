# Export du Corpus Markdown

## Objectif

Les sources Markdown validees dans `docs/source-corpus/` peuvent etre exportees vers un CSV exploitable par le pipeline RAG.

## Sortie

Le fichier genere est:

```text
docs/reference/rag-source-corpus.generated.csv
```

Colonnes:

- `source_id`
- `source_type`
- `title`
- `version`
- `applicable_from`
- `applicable_to`
- `source_url`
- `applicability_status`
- `block_reference`
- `block_type`
- `theme`
- `text`

## Regles

- Les sources `draft` sont ignorees.
- Les sources avec `A COMPLETER` sont ignorees.
- Les sources non indexables ne bloquent pas l'export.
- Le CSV est cree avec son en-tete meme si aucune source n'est exportee.

## Etat Actuel

Export reel (2026-08-03):

- 16 sources scannees;
- 16 sources exportees;
- 37 blocs exportes;
- 0 source bloquee.

Sortie generee: `docs/reference/rag-source-corpus.generated.csv`.

Les 16 sources ont ete passees `validation_status: validated` par
auto-validation du porteur du projet (pas par un expert-comptable ou
fiscaliste, indisponible pour le moment) — voir `docs/open-questions.md`.
Si une relecture professionnelle ulterieure corrige le contenu des
squelettes, relancer cet export pour regenerer le CSV.

Note sur le multi-sources: `RagChunker.chunk()` suppose un seul document
par appel et n'attribue le titre correct qu'a une source a la fois. Pour
chunker un CSV exporte contenant plusieurs sources distinctes (comme
celui-ci), utiliser `chunk_corpus_blocks()`
(`api/app/rag_source/chunker.py`), qui regroupe les blocs par source avant
de les chunker, plutot que d'appeler `RagChunker.chunk()` directement sur
l'ensemble.
