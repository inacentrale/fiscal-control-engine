# Recherche Locale RAG

## Objectif

La premiere recherche locale est lexicale, sans embeddings, sans base vectorielle et sans LLM.

Elle sert a valider le flux:

```text
corpus CSV valide
  -> blocs structures
  -> chunks
  -> recherche par recouvrement de termes
  -> chunks candidats
```

## Role

Cette recherche n'est pas la solution finale.

Elle sert de baseline simple pour:

- verifier que les chunks sont citables;
- tester les questions deja pretes;
- comparer plus tard les embeddings et l'index vectoriel;
- refuser quand aucun passage ne correspond.

## Regles

- Recherche generique, non limitee a la fiscalite.
- Pas d'appel LLM.
- Pas d'embeddings.
- Pas d'index externe.
- Retour uniquement de chunks existants.
- Score simple par termes communs.

## Suite

Les embeddings ne doivent etre ajoutes qu'apres comparaison avec cette baseline.
