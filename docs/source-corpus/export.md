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

Export reel:

- 3 sources scannees;
- 0 source exportee;
- 0 bloc exporte;
- 3 sources bloquees.

C'est attendu tant que les squelettes fiscaux ne sont pas remplis et valides.
