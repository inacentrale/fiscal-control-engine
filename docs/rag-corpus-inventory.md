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

- 6 blocs de procedure interne (dont `PROC-001-S6`, exclusion hors perimetre RAS,
  ajoute pour couvrir RAG-Q015 et RAG-Q016 sans dependre d'une source fiscale
  externe);
- 16 sources fiscales `validation_status: validated` (RAS residents,
  RAS non-residents, loyers, CGI TVA/IUTS/IS, quatre imprimes et trois lois
  de finances et trois instructions administratives), exportees vers
  `docs/reference/rag-source-corpus.generated.csv` (37 blocs);
- 16 questions d'evaluation pretes;
- 9 questions encore en attente, dont 2 (RAG-Q007, RAG-Q013) qui
  necessitent une doctrine/commentaire fiscal redigeable seulement par un
  expert-comptable ou fiscaliste, et 7 (RAG-Q001, Q002, Q004, Q006, Q008,
  Q012, Q014) dont la source existe et est validee mais dont le retrieval
  lexical ne classe pas encore le bon passage de facon fiable (voir
  limite ci-dessous).

**Decision du 2026-08-03**: les sources fiscales ont ete passees
`validation_status: validated` par auto-validation du porteur du projet
(pas par un expert-comptable/fiscaliste, indisponible pour le moment) —
voir `docs/open-questions.md` pour le detail de cette decision et le
risque assume.

**Limite de retrieval decouverte en verifiant les questions**: le
`LexicalRetriever` compare des mots exacts sans racinisation. Sur des
paires d'articles tres proches en vocabulaire (residents/non-residents,
par exemple), des mots comme `resident` (article 206, verbe) et
`residentes` (article 210, adjectif) ne matchent pas entre eux, ce qui
peut faire remonter le mauvais article. Un filtre de mots vides francais a
ete ajoute a `LexicalRetriever` (`api/app/rag_source/lexical_retriever.py`)
et ameliore les choses, mais ne resout pas cette classe de probleme: une
vraie solution demande une racinisation ou une recherche semantique. Le
service `FiscalVectorRetriever` branche maintenant les embeddings sur le
chargement Markdown multi-sources, l'index et la vectorisation de la requete;
le fournisseur `sentence-transformers` reste configurable au deploiement.

Le validateur local detecte 16 fichiers source fiscaux, tous indexables
(`validation_status: validated`, aucun placeholder restant).

**Perimetre actif decide le 2026-08-04**: les anciennes lois de finances
restent archivees dans le corpus pour la tracabilite, mais les retrievers
lexical et vectoriel n'indexent comme loi que la loi de finances 2026. Les
sources non legislatives, notamment le CGI, restent actives. Une loi 2026 ne
doit jamais etre appliquee retroactivement a une periode anterieure.

Le chargement Markdown vers blocs RAG est documente dans `docs/source-corpus/markdown-loading.md`.

L'export Markdown vers CSV est documente dans `docs/source-corpus/export.md`.
