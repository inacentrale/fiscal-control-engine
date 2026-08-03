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
- modele rapide de baseline: `all-MiniLM-L6-v2`;
- modele multilingue a evaluer ensuite si necessaire.

Le provider reel devra respecter le contrat `EmbeddingProvider`.

Configuration:

```text
RAG_EMBEDDING_PROVIDER=deterministic
RAG_EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
```

Pour utiliser le provider reel, installer les dependances optionnelles `embeddings`, puis utiliser:

```text
RAG_EMBEDDING_PROVIDER=sentence-transformers
```

## Regles

- Pas d'appel cloud par defaut.
- Pas d'embedding de sources `draft`.
- Pas d'embedding de source contenant `A COMPLETER`.
- Garder la baseline lexicale pour comparer les resultats.
- Ne pas supprimer les refus: si aucun passage pertinent ne remonte, le systeme refuse.
- Garder `deterministic` comme provider de tests.
