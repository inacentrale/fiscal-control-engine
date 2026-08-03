# Inventaire Corpus RAG

## Decision

Le RAG doit indexer des sources metier validees.

La fiscalite est le premier domaine, pas une limite d'architecture.

Les fichiers GL anonymises peuvent servir aux tests comptables et aux exemples d'anomalies, mais ils ne sont pas des sources fiscales citables.

## Fichiers Disponibles

| Fichier | Statut anonymisation | Role possible | Eligible RAG maintenant |
| --- | --- | --- | --- |
| `docs/GL_anonymise.xlsx` | Anonymise | Donnees comptables de test | Non |
| `docs/GL_anonymise (1).xlsx` | Anonymise | Donnees comptables de test | Non |
| `docs/GL_anonymise_2500.xlsx` | Anonymise | Donnees comptables de test elargi | Non |
| `docs/donnees_test_multisheet.xlsx` | Jeu de test | Donnees applicatives de demonstration | Non |
| `docs/CDC_Agent_IA_Revue_Fiscale_SAHEL .md` | Cahier des charges projet | Gouvernance, architecture, limites | Partiel, non fiscal |
| `docs/reference/rag-mini-corpus.csv` | Procedure interne projet | Refus, citations, confidentialite, escalade | Oui, non fiscal |
| `docs/source-corpus/` | Espace de depot des sources validees | Sources fiscalite, procedures, conformite, finance | Selon statut |

## Sources Manquantes

Pour associer les questions RAG a des chunks attendus, il manque au moins un petit corpus anonymise ou public contenant:

- extraits CGI Burkina Faso;
- doctrine ou commentaire fiscal valide;
- procedure interne anonymisee;
- referentiel de taux ou seuils versionne, si utilise plus tard.

## Regle de Travail

Ne pas utiliser le Grand Livre comme source RAG.

Le GL sert a detecter une anomalie. La source RAG sert a expliquer l'anomalie detectee.

## Iteration Actuelle

Un mini corpus de procedure interne est disponible pour tester les refus, citations, confidentialite et escalade metier.

Les questions de recherche fondees sur CGI ou doctrine restent en attente de sources fiscales anonymisees et validees.

Etat actuel:

- 5 blocs de procedure interne;
- 12 questions d'evaluation pretes;
- 13 questions encore en attente de source fiscale.

Les squelettes fiscaux a completer sont dans `docs/source-corpus/fiscal/`.

Le validateur local detecte actuellement 3 fichiers source, tous non indexables tant qu'ils contiennent `A COMPLETER` et `validation_status: draft`.

Le chargement Markdown vers blocs RAG est documente dans `docs/source-corpus/markdown-loading.md`.

L'export Markdown vers CSV est documente dans `docs/source-corpus/export.md`.
