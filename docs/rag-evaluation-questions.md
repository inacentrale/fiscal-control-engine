# Questions d'Evaluation RAG

## Objectif

Ces questions servent a verifier la qualite de la recherche RAG avant de choisir les embeddings et l'index.

Elles ne valident pas une decision fiscale. Elles verifient seulement que le systeme retrouve les bons passages sources ou refuse quand la source manque.

Le jeu exploitable par le code est dans `docs/reference/rag-evaluation-questions.csv`.

## Regles

- Chaque question doit avoir un theme attendu.
- Chaque reponse attendue doit etre une attente de recherche, pas une reponse fiscale definitive.
- Les questions sans source attendue doivent forcer un refus.
- Les questions devront etre reliees a des chunks exacts quand le corpus fiscal valide sera disponible.

## Couverture Initiale

Le premier jeu contient 25 questions:

- 5 sur les prestataires non residents;
- 5 sur les prestataires residents;
- 4 sur les loyers et charges immobilieres;
- 4 sur les exclusions ou hors perimetre;
- 4 sur les preuves, declarations et controle;
- 3 questions de refus.

## Prochaine Etape

Associer chaque question a:

- un document source valide;
- un article ou une section attendue;
- un ou plusieurs `chunk_reference` attendus.

L'etat actuel des associations est suivi dans `docs/reference/rag-question-expectations.csv`.

Les fichiers GL anonymises ne sont pas utilises comme sources RAG, car ils ne sont pas des textes fiscaux citables.

Une premiere iteration de corpus interne est disponible dans `docs/reference/rag-mini-corpus.csv`.
