# Embeddings RAG

## Objectif

Les embeddings transforment les chunks en vecteurs pour permettre une recherche semantique.

Cette etape vient apres:

- sources validees;
- extraction des blocs;
- chunking;
- baseline lexicale locale.

## Etat Actuel

Le socle interne est en place sans modele externe:

- contrat `EmbeddingProvider`;
- provider deterministe pour les tests;
- `EmbeddedChunk`;
- index vectoriel local en memoire;
- recherche par similarite cosine;
- pipeline `chunks -> embeddings -> index`.

## Pourquoi un Provider Deterministe

Il permet de tester le pipeline sans:

- telecharger de modele;
- appeler une API;
- rendre les tests instables;
- exposer des donnees sensibles.

Il ne remplace pas un vrai modele d'embeddings.

## Prochain Branchement

Le premier provider reel est branche de maniere optionnelle et configurable.

Provider disponible:

- `sentence-transformers`;
- modele multilingue de baseline:
  `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`.

Le provider reel devra respecter le contrat `EmbeddingProvider`.

Configuration:

```text
RAG_EMBEDDING_PROVIDER=disabled
RAG_EMBEDDING_MODEL_NAME=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

Pour utiliser le provider reel, installer les dependances optionnelles `embeddings`, puis utiliser:

```text
RAG_EMBEDDING_PROVIDER=sentence-transformers
```

Le mode `deterministic` reste reserve aux tests et ne peut pas activer le
reranking du tool fiscal. Le mode hybride rerange uniquement des passages
ayant deja une ancre lexicale; il ne contourne donc pas un refus pour absence
de preuve textuelle.

Le resultat expose `retrieval_mode` et `retrieval_policy_version`. La baseline
actuelle utilise un reciprocal-rank fusion avec poids vectoriel double,
versionnee `tax-rag-hybrid-rerank-v1`; ce poids doit etre conserve comme non
calibre jusqu'a evaluation avec le modele reel sur tout le benchmark.

## Regles

- Pas d'appel cloud par defaut.
- Pas d'embedding de sources `draft`.
- Pas d'embedding de source contenant `A COMPLETER`.
- Garder la baseline lexicale pour comparer les resultats.
- Ne pas supprimer les refus: si aucun passage pertinent ne remonte, le systeme refuse.
- Garder `deterministic` comme provider de tests.
- Appliquer le meme perimetre de sources aux retrievers lexical et vectoriel:
  CGI et sources non legislatives validees, loi de finances 2026 uniquement.
