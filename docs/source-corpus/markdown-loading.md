# Chargement Markdown vers RAG

## Objectif

Les sources Markdown validees dans `docs/source-corpus/` peuvent etre converties en blocs RAG exploitables.

Le loader Markdown accepte uniquement les sources indexables selon `validation.md`.

## Flux

```text
source Markdown validee
  -> validation des metadonnees
  -> extraction des blocs
  -> RagCorpusBlock
  -> chunks
  -> recherche locale ou index futur
```

## Regles

- Les sources `draft` sont refusees.
- Les sources contenant `A COMPLETER` sont refusees.
- Les sources sans metadonnees obligatoires sont refusees.
- `README.md`, `source-template.md` et `validation.md` sont ignores au scan.
- Le parsing suit le template `source-template.md`.

## Etat Actuel

Le scan local trouve 16 sources Markdown fiscales:

- 16 indexables;
- 0 bloquee;
- 37 blocs exportables.

Les sources dont la date ou le contenu normatif reste incertain ne sont
indexees que comme structure, ou restent dans l'inventaire avec un statut
explicite; elles ne deviennent pas des regles deterministes.
