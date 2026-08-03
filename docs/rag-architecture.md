# Architecture RAG

## Objectif

Le RAG sert a expliquer un resultat deja detecte par une logique deterministe ou metier.

Dans le premier perimetre, ce resultat est une anomalie fiscale. L'architecture reste generique pour pouvoir couvrir plus tard d'autres domaines documentaires.

Il ne decide jamais:

- si une ecriture est conforme;
- si un compte est soumis a RAS;
- quel taux fiscal appliquer;
- quelle anomalie retenir;
- toute decision metier qui doit rester deterministe ou humaine.

## Pipeline Cible

```text
Documents sources valides
  -> extraction texte
  -> nettoyage
  -> decoupage par structure documentaire
  -> enrichissement metadonnees
  -> index local
  -> recherche locale
  -> reranking
  -> selection 3-5 passages
  -> explication LLM avec citations
```

## Sources

Sources attendues:

- CGI par pays;
- doctrine fiscale;
- procedures internes;
- referentiels de taux et seuils;
- notes de validation metier.
- autres sources metier validees plus tard.

Le format minimal d'une source est defini dans `docs/rag-source-format.md`.

L'inventaire actuel du corpus est dans `docs/rag-corpus-inventory.md`.

Chaque source doit avoir:

- pays;
- type de document;
- titre;
- date ou version;
- article ou section;
- theme fiscal;
- chemin ou identifiant source.

## Chunking

Le decoupage doit respecter la structure fiscale:

- article;
- section;
- paragraphe;
- alinea si utile.

Eviter le decoupage uniquement par taille fixe, car il casse le contexte juridique.

La strategie initiale est definie dans `docs/rag-chunking-strategy.md`.

## Recherche

Progression prevue:

1. recherche lexicale locale simple;
2. embeddings + index local;
3. recherche hybride;
4. reranking;
5. selection stricte de 3 a 5 passages.

La baseline lexicale locale est documentee dans `docs/rag-local-retrieval.md`.

Le socle embeddings/index local est documente dans `docs/rag-embeddings.md`.

Les schemas Mermaid du flux RAG sont dans `docs/rag-flow-mermaid.md`.

## Reponse LLM

Le LLM recoit seulement:

- l'anomalie detectee par le moteur;
- les passages selectionnes;
- les metadonnees de citation;
- une consigne de non-decision.

Il doit repondre avec:

- explication courte;
- sources citees;
- incertitudes;
- recommandation de verification humaine si source insuffisante.

## Refus

Le systeme doit refuser de produire une explication forte si:

- aucun passage pertinent n'est trouve;
- les sources se contredisent;
- la question demande une decision fiscale non couverte par les regles;
- la source est absente ou non versionnee.

## Evaluation

Avant branchement LLM:

- creer un petit corpus fiscal de test;
- preparer 20 a 30 questions attendues;
- verifier retrieval, citations et refus;
- garder des tests de non-regression.

Les questions initiales sont definies dans `docs/rag-evaluation-questions.md`.

## Garde-fous

- Donnees GL jamais envoyees a une API cloud sans decision explicite.
- RAG local prioritaire.
- LLM explicatif uniquement.
- Pas de reponse sans citation.
- Pas de decision fiscale par prompt.
