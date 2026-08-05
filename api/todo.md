# Todo API

Checklist operationnelle du chantier API. Les cases seront cochees au fur et a mesure.

## Socle Python

- [x] Mettre a jour les skills locales de standards: TDD, architecture, revue de code, revue adversariale.
- [x] Initialiser `api/` comme projet Python propre.
- [x] Ajouter la structure `app/` avec domaines, configuration et tests.
- [x] Ajouter les dependances de base: FastAPI, Pydantic, Pandas, lecteur Excel, pytest, lint/typecheck.
- [x] Ajouter un module de configuration et `api/.env.example`.
- [x] Ajouter Docker comme environnement de developpement reproductible.
- [x] Ajouter les scripts racine `package.json` pour dev, lint, typecheck et tests API.
- [x] Supprimer le `Makefile` API au profit de Docker + scripts racine.
- [x] Generer le lockfile `uv.lock` via Docker apres premier build API.

## Coeur Metier Stable

- [x] Creer les objets metier typés: compte GL, compte du plan comptable, mapping compte, statut de classification.
- [x] Creer les contrats de service independants de FastAPI et de la base.
- [x] Creer une interface de stockage `AccountMappingRepository`.
- [x] Ajouter une implementation initiale fichier ou memoire du repository.
- [x] Garder PostgreSQL comme implementation future sans changer les contrats metier.
- [x] Documenter les points non clarifies dans `docs/open-questions.md`.

## Import et Normalisation

- [x] Documenter les fichiers Excel, feuilles, colonnes et roles dans `docs/excel-sources.md`.
- [x] Documenter la vue projet dans `docs/project-overview.md`.
- [x] Encapsuler la lecture Excel/CSV dans un service d'import dedie.
- [x] Limiter Pandas a la lecture, au nettoyage et a la jointure initiale des fichiers.
- [x] Transformer les lignes importees en objets metier typés.
- [x] Preparer un jeu de donnees CSV representatif depuis les fichiers Excel.

## Domaine `account-mapping`

- [x] Creer le domaine `account_mapping`.
- [x] Creer le service de jointure comptes GL + plan comptable.
- [x] Creer le service de classification RAS preliminaire avec justification et niveau de confiance.
- [x] Isoler les constantes metier du mapping dans un module `constants.py`.
- [x] Sortir les regles et textes RAS vers `docs/reference/ras-classification-rules.csv`.
- [x] Charger le referentiel RAS via la configuration API.
- [x] Creer les schemas Pydantic et contrats de reponse explicites.

## Agent Excel / Tools

- [x] Clarifier la cible: agent LLM avec tools Excel deterministes, RAG comme module de contexte/citations.
- [x] Definir le contrat general d'un tool agent: nom, description, entree, sortie, erreurs, garde-fous.
- [x] Definir les contrats des tools Excel initiaux: `list_sheets`, `get_columns`, `profile_sheet`.
- [x] Implementer le tool interne `list_sheets` en TDD, sans route HTTP.
- [x] Implementer le tool interne `get_columns` en TDD, sans route HTTP.
- [x] Implementer le tool interne `profile_sheet` en TDD, sans route HTTP.
- [x] Ajouter un registre local de tools appelables par l'agent.
- [x] Ajouter les schemas de reponse structures des tools Excel.
- [x] Ajouter les erreurs structurees: chemin non autorise, feuille inconnue, format non supporte.
- [x] Ajouter les erreurs structurees pour fichier absent ou fichier Excel invalide/corrompu.
- [x] Limiter les sorties des tools pour ne pas exposer de lignes completes ou de donnees sensibles.
- [x] Autoriser les tools Excel sur les racines projet et stockage temporaire controlees.
- [x] Documenter le flux Agent Excel dans `docs/rag-flow-mermaid.md`.
- [x] Decider que les tools restent internes et ne sont pas exposes un par un en HTTP.
- [x] Valider les tool calls avant execution: nom connu, schema valide, fichier autorise, limites respectees.
- [x] Ajouter les tests unitaires pour tool call invalide, arguments invalides et fichier non autorise.
- [x] Ajouter un executeur interne de tools avec sorties structurees et erreurs normalisees.
- [x] Ajouter une fixture de test Grand Livre minifiee pour l'Excel analyse en premier.
- [x] Ajouter le tool interne `analyze_ledger` pour le rapport Grand Livre structure.
- [x] Autoriser `analyze_ledger` par defaut dans l'endpoint agent.

## Grand Livre Analyse

- [x] Definir les colonnes attendues du Grand Livre minifie sans regle fiscale.
- [x] Implementer le validateur de schema Grand Livre en TDD.
- [x] Detecter les colonnes presentes, manquantes et optionnelles.
- [x] Refuser le profiling metier Grand Livre si une colonne essentielle manque.
- [x] Garder cette validation independante du LLM et de FastAPI.
- [x] Produire un rapport interne Grand Livre: schema, lignes, colonnes, profils de colonnes.
- [x] Verifier que le rapport Grand Livre n'expose pas de valeurs de cellules.
- [x] Brancher le rapport Grand Livre dans un tool agent interne sans endpoint dedie.

## Tools Analytiques Grand Livre

- [x] Ajouter `classify_ledger_schema`: comprendre le sens des colonnes d'un Excel utilisateur sans dependre de leur nom exact, puis les mapper vers un schema canonique (`account`, `amount`, `currency`, `text`, `vendor`, `customer`, `tax_code`, `period`, `fiscal_year`, `document_type`) avec tests sur `docs/GL_anonymise_2500.xlsx`.
- [x] Ajouter les heuristiques de mapping colonnes: synonymes, types de valeurs, formats, exemples anonymises, score de confiance et statut `a_confirmer`.
- [x] Refuser les mappings ambigus au lieu de laisser le LLM deviner le sens d'une colonne.
- [x] Adapter `analyze_ledger` pour utiliser les roles detectes par `classify_ledger_schema` (`account`, `amount`, `text`, etc.) et analyser le Grand Livre meme si les noms de colonnes changent.
- [x] Ajouter `aggregate_ledger`: calculer les agrégats par compte, periode, type de piece, code TVA, fournisseur/client, avec tests sur totaux et comptages attendus.
- [x] Ajouter `query_ledger_entries`: filtrer les ecritures par compte, periode, montant, code TVA ou tiers, avec pagination stricte et colonnes autorisees uniquement.
- [x] Ajouter `calculate_ledger_metrics`: calculs explicites demandes par l'utilisateur (`somme`, `nombre`, `moyenne`, `min`, `max`, `top comptes`, repartitions), sans envoyer les lignes completes au LLM.
- [x] Ajouter `detect_data_quality_issues`: detecter colonnes vides, valeurs manquantes critiques, montants incoherents, devises multiples, tiers absents, dates/periodes suspectes.
- [x] Ajouter `detect_tax_candidates`: identifier les candidats TVA/RAS a partir des comptes, libelles, tiers, codes TVA et montants, sans decision fiscale finale.
- [x] Historique: ajouter un routeur deterministe de tools, ensuite remplace par le flux LLM-first.
- [x] Historique: router une demande generale du type `Explique-moi cet Excel`, ensuite remplace par selection LLM-first.
- [x] Ajouter des tests de consistance tool par tool: fixture Excel anonymisee, sortie attendue stable, absence de donnees sensibles, limites de lignes respectees.
- [x] Enrichir le dashboard Grand Livre avec les graphes API `debit_credit_by_period` et `cumulative_balance_by_period`.
- [x] Enrichir le dashboard Grand Livre avec les agrégats API par classe OHADA, devise, exercice, clé de comptabilisation et qualité par champ.
- [x] Exposer dans le résumé dashboard les KPI déterministes: écritures utilisées, débit, crédit, solde, moyenne, nombre de devises et alertes qualité.
- [x] Enrichir `detect_ras_candidates` avec `ras_review.periods`: periode, pieces evaluees, candidats, montant, devise et taux candidat.

## Orchestrateur Agent

- [x] Definir le contrat interne d'une execution agent: message utilisateur, fichier cible, contexte, tools autorises.
- [x] Implementer l'orchestrateur agent en TDD: appel modele, validation tool call, execution tool, reponse finale.
- [x] Ajouter la consigne systeme: le LLM explique, les regles deterministes decident.
- [x] Ajouter une validation de sortie pour bloquer toute decision fiscale directe du LLM.
- [x] Ajouter le garde-fou de boucle: nombre maximal de tool calls.
- [x] Ajouter le garde-fou de taille maximale de reponse.
- [x] Ajouter le garde-fou de timeout global.
- [x] Ajouter les tests unitaires de l'orchestrateur: reponse sans tool, reponse avec tool, tool refuse, fallback modele.
- [x] Definir le contrat interne `AgentRunEvent` lisible par un utilisateur non technique: `run_started`, `file_checked`, `model_requested`, `tool_requested`, `tool_started`, `tool_finished`, `fallback_used`, `answer_delta`, `answer_ready`, `run_failed`.
- [x] Collecter une trace d'execution safe dans `AgentRunResult`: etapes pedagogiques, outils utilises, resume des observations LLM, sans chain-of-thought ni donnees sensibles.
- [x] Ajouter les tests unitaires de trace agent: ordre des etapes, erreurs tool, fallback modele, timeout.
- [x] Ajouter une synthese visible des pre-traitements: fichier verifie, controles lances, outil choisi, statut de chaque etape, jamais les pensees internes du modele.
- [x] Ajouter les libelles et resumes utilisateur des tools analytiques dans les evenements de streaming.

## LLM / Modeles Externes

- [x] Definir une interface interne `ModelProvider` independante des fournisseurs externes.
- [x] Definir un contrat de requete modele: messages, tools autorises, temperature, limites tokens, timeout.
- [x] Definir un contrat de reponse modele: texte, tool calls, usage, modele utilise, raison d'arret.
- [x] Ajouter une configuration securisee des providers via variables d'environnement, sans cle dans le code.
- [x] Ajouter un registre de modeles: principal, fallback rapide, fallback local/interne.
- [x] Ajouter une factory de providers modeles avec fallback interne controle.
- [x] Ajouter les definitions de tools dans le contrat `ModelRequest` pour les LLM externes.
- [x] Ajouter un adapter `openai-compatible` derriere `ModelProvider`.
- [x] Ajouter un adapter natif `gemini` derriere `ModelProvider`.
- [x] Ajouter le support minimal des function calls Gemini pour les tools agent.
- [x] Ajouter un provider dedie `groq` via l'API compatible OpenAI.
- [x] Garder les providers inconnus explicitement refuses.
- [x] Implementer le fallback ordonne: modele principal -> modele secondaire -> reponse controlee sans LLM.
- [x] Configurer la chaine cible Gemini -> Groq -> reponse controlee interne.
- [x] Ajouter des retries bornes et un circuit breaker simple pour les appels modeles.
- [x] Ajouter l'application stricte du timeout mesure autour des appels modeles.
- [x] Journaliser uniquement les metadonnees utiles: provider, modele, duree, statut, jamais les donnees sensibles.
- [x] Configurer `LLM_OPENAI_COMPATIBLE_API_KEY` et `LLM_OPENAI_COMPATIBLE_BASE_URL` sans secret dans `.env.example`.
- [x] Configurer `LLM_GEMINI_API_KEY`, `LLM_GEMINI_BASE_URL`, `LLM_GROQ_API_KEY` et `LLM_GROQ_BASE_URL` sans secret dans `.env.example`.
- [x] Retourner `provider_name` et `model_name` dans la reponse `POST /api/agent/runs`.
- [x] Retourner une reponse agent formatee en Markdown propre: paragraphes courts, listes, tableaux simples, sections courtes.
- [x] Ajouter une consigne modele stricte de formatage Markdown et de ton clair pour un utilisateur non technique.
- [x] Normaliser les sorties de providers pour eviter les listes inline illisibles et les blocs non structures.
- [x] Ajouter un smoke check local LLM qui retourne uniquement des metadonnees.
- [x] Ajouter le script `api:smoke:llm` pour tester une cle locale non commitee.
- [ ] Reporter le test reel `openai-compatible` generique: hors perimetre immediat, on teste seulement Gemini et Groq pour l'instant.
- [x] Tester un appel reel Gemini puis Groq avec cles locales non commitees: Gemini repond en premier, Groq a ete valide comme fallback.
- [x] Ajouter des tests unitaires avec providers fake pour succes, fallback et timeout.
- [x] Ajouter des tests unitaires pour erreur provider avancee et tool call invalide.
- [x] Ajouter les tests unitaires Gemini, Groq/factory et retour du modele repondant.

## Endpoint Agent Future

- [x] Definir le contrat HTTP unique: `POST /api/agent/runs`.
- [x] Ajouter les schemas Pydantic de requete/reponse de l'endpoint agent.
- [x] Brancher l'endpoint sur l'orchestrateur agent, sans logique metier dans le router.
- [x] Retourner une reponse structuree sans exposer les tools comme endpoints separes.
- [x] Retourner des erreurs HTTP explicites sans exposer fichiers, prompts complets ou donnees sensibles.
- [x] Ajouter les tests unitaires du router agent avec orchestrateur fake.
- [x] Ajouter `execution_events` dans `AgentRunResponse`: libelles utilisateur, etapes, tools, provider, modele, statuts.
- [x] Ajouter un endpoint de streaming `POST /api/agent/runs/stream` en NDJSON pour afficher les etapes et la reponse sans attendre la fin.
- [x] Streamer les evenements safe en direct: progression, tool appele, resultat resume, provider utilise, morceaux de reponse Markdown, jamais de prompt complet ni chain-of-thought.
- [x] Ajouter les tests unitaires du flux streaming agent avec orchestrateur fake.

## Uploads et Sessions Future

- [x] Definir le stockage temporaire des fichiers uploades avec expiration.
- [x] Configurer le chemin et la duree de vie du stockage temporaire sans secret.
- [x] Associer un fichier utilisateur a une session ou execution agent.
- [x] Scanner et valider les fichiers uploades avant tout stockage/profiling.
- [x] Bloquer l'indexation RAG des uploads tant qu'ils ne sont pas valides et anonymises.
- [x] Ajouter un service interne d'upload qui retourne `session_id`/`file_id` sans chemin serveur.
- [x] Ajouter `python-multipart` aux dependances API pour supporter les uploads FastAPI.
- [x] Ajouter l'endpoint multipart `POST /api/agent/files`.
- [x] Brancher l'upload et le run agent sur le meme store temporaire en memoire.
- [x] Tester le flux HTTP complet upload Excel -> run agent sur le Grand Livre minifie.
- [x] Tester le flux HTTP upload Excel -> run agent -> tool `analyze_ledger`.

## RAG Documentaire / Sources

- [x] Definir le format documentaire dans `docs/rag-source-format.md`.
- [x] Creer les objets metier typés pour les sources fiscales RAG.
- [x] Distinguer documents anonymises et uploads utilisateur.
- [x] Bloquer l'indexation des uploads utilisateur tant qu'ils ne sont pas valides.
- [x] Definir le contrat interne de chunk fiscal sans route HTTP.
- [x] Implementer le chunking par blocs article/section/paragraphe avec fenetre de mots en secours.
- [x] Preparer 25 questions d'evaluation RAG dans `docs/reference/rag-evaluation-questions.csv`.
- [x] Inventorier les fichiers disponibles dans `docs/rag-corpus-inventory.md`.
- [x] Creer `docs/reference/rag-question-expectations.csv` avec 3 refus prets et 22 questions en attente de source.
- [x] Ajouter `docs/reference/rag-mini-corpus.csv` pour les procedures internes non fiscales.
- [x] Associer les questions internes pretes a des chunks attendus.
- [x] Valider le mini corpus: 5 blocs, 5 chunk refs, 12 attentes pretes, 13 sources fiscales manquantes.
- [x] Generaliser les objets internes RAG avec aliases de compatibilite `Fiscal...`.
- [x] Ajouter une recherche lexicale locale sans LLM ni embeddings.
- [x] Ajouter un loader CSV generique pour mini corpus RAG.
- [x] Valider le flux local corpus -> chunks -> recherche.
- [x] Creer `docs/source-corpus/` avec templates generiques et squelettes fiscaux.
- [x] Ajouter un validateur local des sources Markdown: draft, placeholders et metadonnees manquantes.
- [x] Verifier que les 3 squelettes fiscaux sont detectes et non indexables.
- [x] Ajouter un loader Markdown qui transforme une source validee en blocs RAG.
- [x] Verifier le scan reel: 3 sources Markdown, 0 indexable, 3 bloquees.
- [x] Ajouter l'export Markdown valide vers `docs/reference/rag-source-corpus.generated.csv`.
- [x] Verifier l'export reel: 3 sources scannees, 0 source exportee, 0 bloc exporte, 3 sources bloquees.
- [x] Definir les contrats internes embeddings/index vectoriel sans modele externe.
- [x] Ajouter un index vectoriel local en memoire pour tests.
- [x] Ajouter un provider embeddings deterministe pour tests.
- [x] Valider le pipeline chunks -> embeddings -> index vectoriel local.
- [x] Brancher un provider embeddings local ou configurable via `sentence-transformers`.
- [x] Ajouter une factory de provider embeddings configuree par nom.
- [x] Documenter le flux RAG complet dans `docs/rag-flow-mermaid.md`.
- [x] Remplir/valider les squelettes fiscaux puis associer les questions couvrables.
- [x] Remplir les 3 squelettes fiscaux (`bf-ras-residents.md`, `bf-ras-non-residents.md`, `bf-loyers.md`) avec le texte litteral extrait du PDF officiel CGI dgi.bf (articles 107, 120-128, 206-219), en `validation_status: draft`.
- [x] Passer les 3 squelettes a `validation_status: validated` par auto-validation du porteur du projet (indisponibilite d'expert-comptable/fiscaliste au moment de la decision; `validated_by` le mentionne explicitement) et relancer l'export vers `docs/reference/rag-source-corpus.generated.csv` (3 sources exportees, 9 blocs, 0 bloquee).
- [x] Corriger `RagChunker`/`chunk_corpus_blocks`: un CSV exporte multi-sources faisait attribuer a tort le titre du premier bloc a tous les chunks; nouvelle fonction `chunk_corpus_blocks` (chunking par source), testee.
- [x] Ajouter un filtre de mots vides francais a `LexicalRetriever` (`api/app/rag_source/lexical_retriever.py`), teste; ameliore le classement sans le resoudre completement (voir limite ci-dessous).
- [x] Identifier le theme manquant pour chacune des 13 questions `pending_source` (voir `docs/reference/rag-question-expectations.csv` et `docs/rag-corpus-inventory.md`).
- [x] Ajouter `PROC-001-S6` (exclusion hors perimetre RAS) a `docs/reference/rag-mini-corpus.csv`, sans dependre d'une source fiscale externe; resout RAG-Q015 et RAG-Q016 (retrieval verifie par test).
- [x] Verifier empiriquement (tests) le retrieval des questions dont la source est desormais validee: RAG-Q011 et RAG-Q017 passent `ready` (top-1 unique et correct); RAG-Q001, Q002, Q004, Q006, Q008, Q012, Q014 restent `pending_source` car le retrieval lexical ne classe pas le bon passage de facon fiable (ex-aequo ou mauvais article en tete) malgre une source validee — 16 questions pretes au total (au lieu de 12).
- [ ] Calibrer le modele multilingue reel pour fiabiliser les 7 questions bloquees par la precision lexicale: le reranking hybride lexical/vectoriel est raccorde au tool, limite aux candidats ayant une ancre lexicale, trace par la politique `tax-rag-hybrid-rerank-v1` et corrige une ambiguite naturelle en test; l'execution reelle attend le rebuild Docker incluant l'extra `embeddings`.
- [ ] Faire rediger par un expert-comptable ou fiscaliste la doctrine/commentaire manquant pour les 2 questions sans aucun contenu disponible (Q007 honoraires, Q013 loyer/entretien/prestation).
- [ ] Faire relire par un expert-comptable ou fiscaliste les 3 squelettes fiscaux auto-valides; corriger et re-exporter si une erreur est trouvee.

## Couche FastAPI Future

- [x] Initialiser FastAPI autour du coeur metier.
- [x] Configurer le prefixe global `/api`.
- [x] Ajouter `GET /api/health`.
- [x] Reprendre les routes `account_mapping` apres stabilisation de la logique interne.
- [x] Creer `GET /api/account-mappings`.
- [x] Creer `POST /api/account-mappings/import-from-files` avec sources configurees cote serveur.
- [x] Refuser les chemins utilisateur dans `POST /api/account-mappings/import-from-files`.

## Tests et Verification

- [x] Cadrer la strategie actuelle: tests unitaires uniquement pour le moment.
- [x] Ajouter les tests des objets metier et contrats.
- [x] Ajouter les tests unitaires du service d'import CSV.
- [x] Renforcer les tests unitaires sur les cas limites: fichier vide, extension non supportee, libelle vide, doublons plan comptable.
- [ ] Reporter les tests d'integration Excel/Docker a une phase ulterieure.
- [x] Ajouter les tests unitaires du repository fichier ou memoire.
- [x] Ajouter les tests unitaires de l'ordre stable du repository `account_mapping`.
- [x] Ajouter les tests unitaires du service `account_mapping`.
- [x] Ajouter les tests unitaires du classifieur RAS preliminaire.
- [x] Ajouter les tests unitaires du loader de referentiel RAS.
- [x] Ajouter les tests unitaires du domaine `rag_source`.
- [x] Ajouter les tests unitaires du chunker fiscal.
- [x] Ajouter les tests unitaires prouvant le support de sources RAG non fiscales.
- [x] Ajouter les tests unitaires du loader de corpus RAG.
- [x] Ajouter les tests unitaires du retriever lexical.
- [x] Ajouter le test de flux local RAG sans LLM.
- [x] Ajouter les tests unitaires du validateur de sources RAG Markdown.
- [x] Ajouter les tests unitaires du loader Markdown de sources RAG.
- [x] Ajouter les tests unitaires de l'export Markdown vers CSV corpus RAG.
- [x] Ajouter les tests unitaires du provider embeddings deterministe.
- [x] Ajouter les tests unitaires de l'index vectoriel memoire.
- [x] Ajouter le test de pipeline vectoriel local.
- [x] Ajouter les tests unitaires du provider `sentence-transformers` optionnel.
- [x] Ajouter les tests unitaires de la factory embeddings.
- [x] Ajouter les tests unitaires des tools internes Agent Excel.
- [x] Ajouter les tests unitaires des racines multiples autorisees pour les tools Excel.
- [x] Ajouter les tests unitaires de validation/execution des tool calls Agent Excel.
- [x] Ajouter les tests unitaires de l'orchestrateur agent interne.
- [x] Ajouter les tests unitaires des garde-fous de sortie agent.
- [x] Ajouter les tests unitaires du timeout global orchestrateur.
- [x] Ajouter les tests unitaires du fallback de modeles LLM.
- [x] Ajouter les tests unitaires du registre de modeles LLM configurable.
- [x] Ajouter les tests unitaires de l'adapter LLM `openai-compatible`.
- [x] Ajouter les tests unitaires du smoke check LLM sans contenu sensible.
- [x] Ajouter les tests unitaires du wrapper LLM resilient: retry, echec borne, circuit breaker.
- [x] Ajouter les tests unitaires de la factory LLM et du provider interne controle.
- [x] Ajouter les tests unitaires de l'audit LLM sans contenu sensible et timeout mesure.
- [x] Ajouter les tests unitaires de refus d'un tool call modele avec arguments invalides.
- [x] Ajouter les tests unitaires du validateur de schema Grand Livre minifie.
- [x] Ajouter les tests unitaires du rapport interne Grand Livre minifie.
- [x] Ajouter les tests unitaires du classifieur de schema Grand Livre canonique.
- [x] Ajouter les tests unitaires du tool interne `analyze_ledger`.
- [x] Ajouter les tests unitaires du tool interne `classify_ledger_schema`.
- [x] Ajouter les tests unitaires des tools internes `detect_data_quality_issues` et `detect_tax_candidates`.
- [x] Historique: ajouter les tests unitaires du routeur deterministe de tools agent, ensuite remplaces par les tests LLM-first.
- [x] Ajouter les tests unitaires du choix LLM-first `Explique-moi cet Excel` vers `analyze_ledger`, `calculate_ledger_metrics`, `aggregate_ledger`, `detect_data_quality_issues` et `detect_tax_candidates`.
- [x] Ajouter les tests unitaires du router `agent`.
- [x] Ajouter les tests unitaires des erreurs HTTP sanitisees du router `agent`.
- [x] Ajouter les tests unitaires des tools agent autorises par defaut.
- [x] Ajouter les tests unitaires du stockage temporaire de fichiers agent.
- [x] Ajouter les tests unitaires du resolver session/fichier agent.
- [x] Ajouter les tests unitaires du scanner/validateur Excel upload.
- [x] Ajouter les tests unitaires de la policy bloquant l'indexation RAG des uploads non anonymises.
- [x] Ajouter les tests unitaires du service interne d'upload agent.
- [x] Ajouter les tests unitaires du router d'upload agent.
- [x] Ajouter les tests unitaires sur les fixtures CSV representatives.
- [x] Ajouter le test health.
- [x] Ajouter les tests unitaires du router `account_mapping`.
- [x] Ajouter les tests unitaires du router d'import `account_mapping`.
- [x] Verifier l'import des 139 comptes GL.
- [x] Verifier que 138 comptes obtiennent un libelle depuis le plan comptable.
- [x] Verifier que `44910002` ressort comme compte sans libelle.
- [x] Executer les tests metier/import disponibles localement: `PYTHONPATH=. python3 -m pytest app/account_mapping/tests -q` avec 33 tests passes.
- [x] Executer les tests chunker disponibles localement: `PYTHONPATH=. python3 -m pytest app/rag_source/tests/test_chunker.py -q` avec 5 tests passes.
- [x] Executer les tests RAG source disponibles localement: `PYTHONPATH=. python3 -m pytest app/rag_source/tests -q` avec 43 tests passes.
- [x] Executer tous les tests API via Docker: `npm run api:test` avec 238 tests passes.
- [x] Executer le lint API localement: `PYTHONPATH=/tmp/bfh-python-deps:. python3 -m ruff check app tests scripts`.
- [x] Executer le typecheck API localement: `PYTHONPATH=/tmp/bfh-python-deps:. python3 -m mypy app tests scripts`.
- [x] Executer lint, typecheck et compilation API via Docker apres ajout Gemini/Groq.
- [x] Verifier l'absence de secrets: `python3 api/scripts/secret_scanner.py .`.
- [x] Aligner `npm run secrets:check` sur les fichiers suivis Git pour ignorer les `.env` locaux.
- [x] Verifier le smoke LLM sans cle externe: provider interne `internal/controlled-response`.
- [x] Executer les tests Agent Excel/LLM disponibles localement: `PYTHONPATH=. python3 -m pytest app/excel_agent/tests app/llm/tests -q` avec 12 tests passes.
- [x] Verifier la compilation Python: `PYTHONPATH=. python3 -m compileall app tests`.
- [x] Executer lint, typecheck, compilation et tests API via Docker.

## CI/CD Future

- [ ] Etudier les pipelines existants dans `portefolio` et autres projets de reference.
- [x] Ajouter une CI API: lint, typecheck, tests et compilation Python.
- [x] Ajouter le build Docker API dans la CI.
- [ ] Ajouter une CI front quand le socle front existe.
- [x] Ajouter les controles de secrets avant merge via script local et CI.
- [ ] Ajouter une strategie CD apres validation de l'environnement cible.

## Sessions Agent, Fichiers et Requetes Deterministes

- [x] Persister les references `session_id` / `file_id` pour ne pas perdre les uploads apres reload API.
- [x] Ajouter `active_file_id` sur une session agent pour piloter le panneau de contexte front.
- [x] Permettre a un upload Excel de rejoindre une session existante via `session_id`.
- [x] Marquer le dernier upload d'une session comme fichier actif par defaut.
- [x] Ajouter `GET /api/agent/sessions/{session_id}/context` pour la troisieme colonne front.
- [x] Retourner un etat vide stable quand aucune session ou aucun fichier actif n'existe.
- [x] Retourner le fichier actif, les fichiers de session et les derniers evenements agent.
- [x] Generer un dashboard fichier deterministe sans LLM: resume, schema, metriques, graphique top comptes, qualite donnees.
- [x] Enrichir le dashboard avec graphes multi-dimensions: comptes, periodes, types de piece, TVA, fournisseurs, clients, qualite et candidats fiscaux.
- [x] Remplacer l'indicateur global `Montant` par des soldes metier par nature de compte dans le contrat dashboard: normal side du compte, devise, ecritures utilisees/exclues et natures variables non calculables.
- [x] Ajouter un contrat de graphe riche: `chart_id`, `kind`, `metric`, `labels`, `values`, `series`, `metadata`.
- [x] Retourner des erreurs stables si un fichier est expire, supprime ou introuvable: `file_expired`, `file_missing`.
- [x] Ajouter un contrat front stable pour les fichiers agent: statut, expiration, nom original safe, taille, type MIME, dates.
- [x] Historique: construire un routeur deterministe initial pour les questions GL simples.
- [x] Remplacer le routeur deterministe du flux agent normal par un choix de tools pilote par le LLM.
- [x] Supprimer le fallback automatique `analyze_ledger` quand le LLM ne demande aucun tool.
- [x] Masquer `file_path` et `sheet_name` des schemas tools visibles par le LLM, puis les injecter cote serveur.
- [x] Appliquer une pagination par defaut et une limite stricte des lignes retournees pour `query_ledger_entries`.
- [x] Stabiliser le payload `query_ledger_entries`: total trouve, page affichee, page_size, filtres, colonnes retournees, entries.
- [x] Retourner un message clair et structure si une requete ledger donne 0 resultat.
- [x] Retourner `invalid_filter` quand un filtre utilisateur ne peut pas etre interprete proprement.
- [x] Ajouter les tests metier: question compte -> `query_ledger_entries`.
- [x] Ajouter les tests metier: compte + periode -> `query_ledger_entries`.
- [x] Ajouter les tests metier: compte inexistant -> 0 resultat + message clair.
- [x] Ajouter les tests metier: pagination stricte et limite de lignes.
- [x] Ajouter les tests metier: fichier expire/supprime -> code `file_expired` ou `file_missing`.
- [x] Ajouter les tests API pour contexte session vide, contexte avec fichier actif et upload dans session existante.
- [x] Verifier le flux runtime Docker/Postgres: upload Excel -> liste fichiers -> run agent -> liste conversations -> contexte session.
- [x] Valider la persistance agent: `npm run api:test`, `npm run api:lint`, `npm run api:typecheck`, `npm run api:compile`.

## Challenge et Rapprochement des Tools Agent Excel

- [x] Basculer le flux chat normal en LLM-first: le modele choisit le tool autorise; les tools gardent les calculs deterministes.
- [x] Supprimer `api/app/agent/tool_router.py` et ses tests pour eviter les listes de mots-cles figees.
- [x] Adapter les tests orchestrateur LLM-first: RAG, calcul RAS, qualite, candidats RAS, requetes GL et analyses globales.
- [x] Validation ciblee: `python -m pytest app/agent/tests/test_orchestrator.py -q` -> 26 tests passes.
- [ ] Reprendre les challenges runtime question par question via l'interface/API avec format: question, tools, reponse, insuffisances.

### Ordre de challenge GL — priorite actuelle

- [x] 1. Ambiguites a refuser ou clarifier:
  - [x] « Donne-moi le solde du compte 61365 » — aucun calcul prefixe automatique; alerte sur compte `61365000`.
  - [x] « Montre les ecritures du compte 445 » — aucun calcul prefixe automatique; alerte sur `44531001`, `44531002`, `44585100`.
  - [x] « Quel est le total de 2024 ? » — clarification obligatoire: metrique, perimetre et devise.
  - [x] « Analyse les charges » — clarification obligatoire: metrique, regroupement et perimetre.
- [ ] 2. Structure simple du fichier:
  - [ ] « Quelles feuilles contient ce fichier ? »
  - [ ] « Quelles colonnes contient la feuille active ? »
  - [ ] « Le GL permet-il de calculer des soldes fiables ? »
- [ ] 3. Consultation et filtres:
  - [ ] « Affiche les ecritures du compte 61365000 en 2024, periode 12. »
  - [ ] « Affiche la page 2 avec 20 ecritures. »
  - [ ] « Cherche un compte inexistant. »
- [ ] 4. Soldes et rapprochements:
  - [ ] « Calcule le solde du compte 61365000 en 2024, periode 12. »
  - [ ] « Montre brut, debit, credit, solde, cles utilisees et exclusions par devise. »
  - [ ] « Explique l'ecart avec la somme brute Excel sans modifier le calcul. »
- [ ] 5. Agregations:
  - [x] « Regroupe le compte 61365000 par periode en 2024. » — filtre exercice applique et periodes triees chronologiquement.
  - [ ] « Regroupe debit, credit et solde par compte et devise. »
  - [ ] « Donne les dix comptes aux soldes absolus les plus eleves. »
- [ ] 6. Qualite et cas limites:
  - [ ] « Liste les lignes structurelles, cles inconnues et montants inutilisables. »
  - [ ] « Distingue anomalies de fichier et anomalies comptables. »
  - [ ] « Verifie un GL multi-devises sans additionner les devises. »
- [ ] 7. Analyse complexe croisee:
  - [ ] « Analyse les charges 2024 par compte, periode et devise avec exclusions. »
  - [ ] « Identifie les avoirs et extournes sans les compter deux fois. »
  - [ ] « Detecte les candidats RAS puis rapproche leurs contreparties dans les pieces. »

### Ordre de challenge RAS — audit metier

- [x] 1. Detection simple des candidats RAS:
  - [x] Question: « Detecte les pieces candidates a la RAS dans ce Grand Livre. »
  - [x] Tool attendu: `detect_ras_candidates`.
  - [x] Verifier: nombre de candidats, exclusions, signaux, absence de decision fiscale ferme.
  - [x] Resultat challenge `GL_anonymise_2500.xlsx`: LLM choisit `detect_ras_candidates`; tool OK apres masquage de `column_mapping` au modele et acceptation de `column_mapping: {}`/`limit`; 2 500 lignes, 2 205 pieces evaluees, 611 pieces candidates, 0 rejet, decision `review_only_no_tax_conclusion`.
- [x] 2. Detection avec filtres:
  - [x] Question: « Detecte les candidats RAS pour l'exercice 2024 uniquement. »
  - [x] Tool attendu: `detect_ras_candidates`.
  - [x] Verifier: filtre exercice applique, aucun candidat hors periode, compteurs coherents.
  - [x] Resultat challenge `GL_anonymise_2500.xlsx`: LLM choisit `detect_ras_candidates`; filtre `fiscal_year=2024` applique; 2 500 lignes source, 1 237 lignes filtrees, 1 095 pieces evaluees, 296 pieces candidates, 0 rejet, montant candidat `59 945 000 XOF`.
- [x] 3. Reconstruction d'une piece:
  - [x] Question: « Reconstitue la piece comptable <piece> de l'exercice <annee>. »
  - [x] Tool attendu: `reconstruct_accounting_entry`.
  - [x] Verifier: lignes groupees par piece, debit/credit par devise, cles inconnues signalees.
  - [x] Resultat challenge `GL_anonymise_2500.xlsx` avec piece `2024002341` / exercice `2024`: LLM choisit `reconstruct_accounting_entry`; selecteur normalise `document_number=2024002341`, `fiscal_year=2024`; piece trouvee avec 2 lignes (`61365000` 452 000 XOF, `34552001` 81 360 XOF), journal `KR`, periode 11; piece non equilibree, debit 533 360 XOF, credit 0 XOF, ecart 533 360 XOF.
- [x] 4. Recherche de contrepartie RAS:
  - [x] Question: « Pour cette piece candidate, cherche si une RAS a ete comptabilisee dans la meme piece. »
  - [x] Tool attendu: `find_ras_counterpart`.
  - [x] Verifier: meme piece prioritaire, comptes RAS mappes, pas de double comptage.
  - [x] Resultat challenge `GL_anonymise_2500.xlsx`: LLM choisit `find_ras_counterpart`; 611 candidats detectes au sens large, 518 pieces analysees pour contrepartie, 93 hors scope rapprochement; 59 contreparties RAS trouvees dans la meme piece, 459 indeterminees, 0 non trouvee dans le perimetre; montant confirme `1 693 625 XOF`; scope incomplet documente (`journal_is_document_type_proxy`, `missing_company_scope`, `posting_date_is_document_date_proxy`).
- [x] 5. Cas sans contrepartie RAS:
  - [x] Question: « Verifie cette piece candidate sans ligne RAS apparente. »
  - [x] Tool attendu: `find_ras_counterpart`.
  - [x] Verifier: absence qualifiee comme `RAS non retrouvee dans le GL` seulement si scope complet.
  - [x] Resultat challenge `GL_anonymise_2500.xlsx`: LLM choisit `find_ras_counterpart`; 59 contreparties trouvees dans la meme piece, 459 cas indetermines, 0 cas qualifie `not_found_in_scope` car le perimetre GL est incomplet; la reponse ne conclut pas a une omission RAS. Limite restante: le tool retourne un resume global, pas encore le detail d'une piece precise sans contrepartie.
- [x] 6. Evaluation comptable RAS:
  - [x] Question: « Evalue la comptabilisation RAS de ce candidat avec les faits fournis. »
  - [x] Tool attendu: `assess_ras_accounting`.
  - [x] Verifier: attendu, comptabilise, ecart, devise, tolerance, faits manquants.
  - [x] Resultat challenge `GL_anonymise_2500.xlsx`: LLM choisit `assess_ras_accounting` avec `candidate_id` et `base_audit_id`; faits utilisateur UTF-8 extraits; regle `resident_standard_2025` resolue provisoirement; attendu `5 000 XOF`, comptabilise `16 250 XOF`, ecart `11 250 XOF`, alerte `ras_recorded_above_expected`, aucune information manquante. Insuffisance observee: sans accents/ponctuation correcte, certains faits ne sont pas extraits et le calcul reste non calculable.
- [x] 7. Audit batch:
  - [x] Question: « Lance un audit RAS du Grand Livre et retourne les candidats a revoir. »
  - [x] Tool attendu: `run_ras_audit_batch`.
  - [x] Verifier: `audit_id`, candidats opaques, limite de sortie, pas de faits globaux appliques.
  - [x] Resultat challenge `GL_anonymise_2500.xlsx`: apres ajout de `RAS_FACT_CONTEXT_SIGNING_KEY` et `RAS_USER_FACT_PATTERNS_PATH` dans Docker, LLM choisit `run_ras_audit_batch`; audit persiste avec `audit_id`; 611 candidats, 404 potentiels, 207 indetermines, 20 IDs retournes, 591 restants; scope incomplet documente (`journal_is_document_type_proxy`, `missing_company_scope`, `posting_date_is_document_date_proxy`). Correction persistance: `flush()` de l'audit parent avant insertion des cas enfants.
- [ ] 8. Enchainement mono-candidat:
  - [ ] Question: « Audite la RAS sur un fichier contenant un seul candidat. »
  - [ ] Tools attendus: `run_ras_audit_batch` puis `assess_ras_accounting`.
  - [ ] Verifier: enchainement automatique uniquement si un seul candidat.
- [ ] 9. Multi-candidats avec faits utilisateur:
  - [ ] Question: « Tous les prestataires sont residents et immatricules IFU, audite tout. »
  - [ ] Tool attendu: `run_ras_audit_batch`.
  - [ ] Verifier: refus d'appliquer les faits utilisateur globalement a plusieurs candidats.
- [x] 10. Rapport d'audit RAS:
  - [x] Question: « Genere le rapport de l'audit RAS <audit_id>. »
  - [x] Tool attendu: `generate_ras_audit_report`.
  - [x] Verifier: statuts, montants par devise, limites, sources, aucune donnee brute sensible.
  - [x] Resultat challenge `audit_id=0dce731bc9f44c73a63f3f31c6d5a460`: LLM choisit `generate_ras_audit_report`; 611 cas, statuts `applicability_probable_to_confirm=404` et `indeterminate_missing_data=207`; ajout de `recorded_amount_summaries` pour afficher les montants comptabilises observes par devise sans inventer de montant theorique.
- [ ] 11. Robustesse tool-calling RAS:
  - [ ] Verifier choix du bon tool avec tous les tools visibles.
  - [ ] Verifier arguments synonymes ou incomplets.
  - [ ] Verifier refus propre si `audit_id`, piece, date, devise ou faits requis manquent.
  - [ ] Verifier que le LLM n'invente ni taux, ni categorie RAS, ni montant.

### Ordre restant apres le challenge GL

- [ ] 8. Executer le challenge RAS audit metier selon la section dediee ci-dessus.
- [ ] 9. Challenger le RAG juridique sur CGI et loi de finances 2026 avec citations et refus hors source.
  - [x] Corriger le routage naturel: une question fiscale sans formule `sources indexees` appelle `query_tax_rag`.
  - [x] Corriger la reponse RAG: commencer par la reponse directe si les citations la contiennent, puis citer les sources utiles.
  - [x] Resultat challenge runtime: question RAS resident IFU 2026 -> tool `query_tax_rag`, reponse directe `5 %`, premiere citation `Loi de finances 2026`, article 15 modifiant CGI article 207.
  - [ ] Tester le refus hors source et les questions juridiques ambigues avant validation complete.
- [ ] 10. Calibrer les embeddings multilingues reels apres rebuild Docker et revue du jeu d'or.
- [ ] 11. Completer les faits generateurs, echeances et categories juridiques encore non sourcees.
- [ ] 12. Finaliser l'enchainement multi-candidats sans interpretation numerique du LLM.
- [ ] 13. Valider volumes, performances, lint, types, tests et non-regression finale.

- [x] Challenger `calculate_ledger_metrics`: filtres compte/exercice/periode, cles debit-credit, montants source negatifs, devise, compte inexistant et invariants de rapprochement (85 tests API passes; challenges runtime reels passes).
- [x] Challenger partiellement `query_ledger_entries`: filtres compte/exercice, pagination, signe des montants selon les cles, rendu deterministe et alertes de prefixe de compte; approfondir cles inconnues, multi-devises et pages suivantes.
- [ ] Challenger `aggregate_ledger`: contrat corrige et valide en runtime (`34211100`: 15 lignes, 9 utilisees, 6 exclues explicites; compte `61365000`/2024 regroupe par periode avec tri chronologique); terminer le rapprochement Excel multi-devises avant de cocher.
- [ ] Challenger `detect_data_quality_issues`: compteurs techniques rapproches sur 2506 lignes (9 categories conformes), mais corriger le double signalement des memes 6 lignes, distinguer lignes structurelles/vides et limiter `missing_counterparty` aux ecritures dont le tiers est reellement requis avant validation.
- [ ] Challenger `detect_tax_candidates`: compteurs/montants rapproches et statut `review_required` conforme, mais 87 lignes non-residentes sont double-comptees dans `resident_services`, actions CSV tronquees par virgules non quotees, justification/source/version absentes du payload et comptes serialises avec `.0`; corriger avant validation fiscale.
- [ ] Challenger `classify_ledger_schema`: mapping reel 11/11 conforme et ambiguite de deux montants correctement bloquee, mais une meme colonne peut etre affectee a `account` et `customer` sans confirmation; `is_usable=true` meme sans cle de comptabilisation alors que les soldes sont impossibles. Ajouter unicite des sources et readiness par capacite avant validation.
- [ ] Challenger `analyze_ledger`: dimensions physiques 2506x21 et mapping 11/11 rapproches, mais distinguer 2506 lignes physiques de 2500 ecritures candidates et 6 lignes structurelles; clarifier `is_valid` (colonnes presentes malgre valeurs critiques invalides) et ajouter readiness par capacite heritee du classifieur.
- [ ] Challenger `profile_sheet`: dimensions, valeurs non vides, manquantes et ratios rapproches exactement sur le fichier reel (2506x21); le type `text` de `Date piece` est conforme aux cellules source stockees en chaines. Avant validation, distinguer les 2500 ecritures des 6 lignes structurelles et ne pas presenter les identifiants (`Compte`, cle, client, fournisseur) comme des nombres metier au risque de perdre les zeros initiaux.
- [x] Challenger `get_columns`: ordre reel des 21 colonnes conforme sur le GL cible, espaces externes retires, en-tete vide normalise (`column_N`), accents/caracteres speciaux conserves, doublons normalises rejetes avant le renommage silencieux Pandas et classeur ferme explicitement.
- [x] Challenger `list_sheets`: ordre, feuilles multiples/vides et noms accentues ou speciaux conformes; exposer `visible`, `hidden` ou `veryHidden` et verifier par renommage que le classeur est libere sous Windows.
- [x] Corriger la reponse de solde sans correspondance: distinguer aucune ecriture, ecritures toutes ininterpretables et vrai solde comptable nul; ne jamais afficher `0.00` comme solde dans les deux premiers cas.

## Audit RAS fonde sur le Grand Livre — Roadmap backend prioritaire

### 0. Recentrage du perimetre

- [x] Retenir le Grand Livre comme seule source obligatoire du premier perimetre.
- [x] Ne pas exiger de declaration fiscale ni de referentiel fournisseur externe.
- [x] Nommer une absence `RAS non retrouvee dans le GL`, jamais `omission de declaration`.
- [x] Conserver le RAG fiscal pour les questions sourcees et la constitution du referentiel.
- [x] Imposer les calculs et conclusions fiscales aux services deterministes, pas au LLM.
- [x] Geler les routes et ecrans multi-declarations hors correctifs critiques; les routes `/api/tax-declarations/**` restent compatibles mais sont marquees `deprecated` et `tax-declarations-experimental` dans OpenAPI; un test d'architecture interdit au backend RAS actif de dependre de ces modules.

### 1. Contrats d'audit et jeu d'or

- [x] Definir le contrat canonique d'une ecriture GL RAS: source, societe, exercice, periode, journal, piece, ligne, date, compte, tiers, libelle, cle, montant et devise.
- [x] Definir les statuts: conforme, montant incoherent, RAS non retrouvee, applicabilite probable, indeterminable et hors perimetre.
- [x] Definir les preuves et motifs obligatoires pour chaque statut; un statut ferme exige une base complete et les preuves comptable, juridique, calculatoire et de completude attendues.
- [x] Definir la readiness par capacite et interdire un constat ferme si le GL ou la cartographie est incomplet.
- [x] Constituer un jeu d'or entierement synthetique couvrant candidats, non-candidats, pieces multi-lignes, extournes, regularisations, devises et cles inconnues; 8 scenarios et 26 lignes, sans resultat juridique invente.
- [x] Etablir les gates du jeu d'or: rappel candidats 100 %, precision alertes fermes 100 %, explication des indeterminations 100 % et ecart absolu de calcul nul.
- [x] Valider le noyau et le jeu d'or `app/ras_audit`: 17 tests passes, Ruff et mypy strict passes.

### 2. Matrice juridique exhaustive RAS

- [x] Limiter la matrice active aux articles et categories RAS du Burkina Faso; le loader et les contrats n'acceptent que la juridiction `BF` pour ce referentiel.
- [ ] Inventorier toutes les categories RAS du CGI applicable et de la seule loi de finances 2026 retenue dans le perimetre actif; conserver les textes anterieurs hors index actif.
- [ ] Completer pour chaque categorie: beneficiaire, residence, territorialite, operation, fait generateur, assiette, seuil, taux, exemption, echeance et faits obligatoires.
  - [x] Livrer une premiere matrice de 27 lignes couvrant residents, non-residents, loyers et categories non determinees; separer conditions, assiette, methode, taux, dates, priorite et faits obligatoires.
  - [ ] Completer fait generateur et echeance apres correction du referentiel contradictoire.
    - [x] Modeliser dans `bf-ras-tax-event-rules.csv` le paiement resident, la mise en paiement non-resident et le loyer acquis; exiger statut et date attestes et dater la regle sur cet evenement plutot que sur la date comptable de charge.
- [x] Versionner chaque regle avec dates, article, document, URL, empreintes SHA-256 distinctes des preuves de champ et de taux, ainsi que niveau d'assurance de source.
- [x] Signaler explicitement toute source manquante, contradiction ou categorie non resolue; 12 lignes restent bloquees plutot que rendues calculables sans preuve de champ suffisante.
- [x] Soumettre chaque regle au validateur de referentiel avant son activation: colonnes, types, dates, taux, unicite, chevauchements, statut et integrite des deux sources sont controles.
- [x] Ajouter les tests normal, limite, exception, chevauchement de dates et information manquante pour chaque regle: 49 contrats couvrent les 15 lignes actives a leurs bornes, le retrait individuel de chaque fait obligatoire et l'impossibilite d'activer les 12 lignes bloquees; les chevauchements restent refuses par le loader.

### 3. Ingestion et readiness du Grand Livre

- [x] Implementer le tool `normalize_gl` sur les briques Excel existantes: mapping explicite et unique, empreinte SHA-256, valeurs sources et zeros initiaux conserves en interne, rejets et anomalies explicites, sortie LLM limitee au resume.
- [x] Implementer le tool `assess_gl_readiness` avec readiness distincte pour detection, resolution juridique, calcul et rapprochement; sortie resumee et aucune alerte fiscale ferme.
- [x] Rendre configurables les alias de colonnes et la cartographie des comptes de charges et de RAS, sans numero de compte active par defaut.
  - [x] Ajouter le referentiel versionne `ras-gl-column-aliases.csv` et la resolution automatique stricte des variantes francaises/SAP, avec blocage des correspondances ambigues.
  - [x] Definir le loader versionne des comptes exacts/prefixes de charges candidates et de RAS a payer, scopes par societe et periode; disponibilite derivee du mapping charge, jamais d'un argument LLM.
  - [x] Renseigner `RAS_LEDGER_ACCOUNT_MAPPING_PATH` avec le mapping organisationnel versionne: rapprocher exhaustivement les 13 comptes observes dans le GL au plan fourni, activer 4 charges candidates et 3 comptes RAS uniquement sur correspondances exactes, exclure 5 comptes hors perimetre et conserver `51200500` indetermine car son libelle de charge contredit 151 mouvements crediteurs; tracer les empreintes du plan et du GL.
- [x] Reconstituer les pieces uniquement par societe + exercice + journal + numero de piece; identifiant technique SHA-256 et aucune fusion sur montant, libelle ou tiers.
- [x] Controler cles de comptabilisation, devise, doublons, lignes structurelles et perimetre temporel; le gate `ras-uploaded-sheet-scope-v4` bloque montants, devises, dates, periodes, exercices ou numeros de ligne incomplets, doublons, contradictions intra-piece, scope societe absent et champs comptables issus de proxies, sans supposer un exercice civil.
- [x] Tester les grands fichiers, feuilles multiples, schemas ambigus, multi-devises et donnees partielles.
  - [x] Valider un batch de 1 800 lignes et 600 candidats: persistance integrale, sortie agent bornee a 20 identifiants et 580 cas restants signales; remplacer le plafond implicite de 500 par `RAS_BATCH_MAX_CANDIDATES`, configure a 5 000 par defaut et borne serveur a 20 000.
  - [x] Verifier au niveau tool l'isolation de la feuille explicitement selectionnee, le refus d'un mapping tiers ambigu, le blocage de completude sur devises contradictoires et les donnees techniques partielles.
- [x] Valider normalisation, readiness et mappings: 40 tests unitaires/contrats, 6 tests d'integration Excel cibles, Ruff et mypy strict sur les 28 fichiers concernes passes.
  - [x] Corriger le schema organisationnel reel dans `bf.ras-gl-columns.v2`: distinguer fournisseur et client puis deriver le tiers ligne par ligne, completer les alias des 21 colonnes, normaliser les cles SAP a un chiffre avec zero initial et synthetiser un numero de ligne technique stable; reconstruire les pieces sans societe tout en bloquant tout constat ferme d'absence par `missing_company_scope`.
  - [x] Challenger sur `GL_anonymise_2500.xlsx`: 2 500 lignes acceptees, 611 pieces candidates, 59 contreparties RAS dans la meme piece et aucune fausse absence emise; le scope societe manque, tandis que `Date piece` et `Type de piece` restent explicitement des proxies de la date comptable et du journal.
  - [x] Mettre en cache au plus 4 feuilles immuables pendant la seule duree de vie d'un executeur, avec invalidation taille/mtime et detection de modification pendant lecture: sur le GL 2 500 lignes, premiere preparation 11,3 s puis detection 1,6 s et rapprochement 1,1 s sans relecture Excel; aucun cache global de donnees client.

### 4. Detection hybride des candidats RAS

- [x] Implementer `detect_ras_candidates` au niveau piece avec filtres deterministes larges sur comptes, sens de comptabilisation, libelles et signaux disponibles dans le GL; ne pas doubler les charges multi-lignes ni les extournes.
- [x] Externaliser comptes, mots-cles, exclusions et taxonomie operationnelle dans des referentiels versionnes; les signaux textuels sont explicitement `review_only` et ne constituent pas une regle fiscale.
- [x] Completer la normalisation linguistique deterministe par une similarite optionnelle via embeddings locaux normalises; refuser le fournisseur hash deterministe comme faux moteur semantique et garder le modele desactive tant qu'il n'est pas calibre.
- [ ] Implementer completement `classify_transaction_semantics`; le moteur d'embeddings, la politique versionnee, les seuils, marges, traces du modele et sorties agregees sont livres, mais l'eventuelle suggestion LLM expliquee sur les seuls cas ambigus reste a encadrer et tester.
- [x] Interdire au LLM de fixer `soumisRas`, la categorie finale, un taux ou une anomalie dans le contrat de `detect_ras_candidates`; le tool ne retourne que des signaux de revue agreges.
- [x] Retourner signaux positifs, exclusions et informations manquantes dans la detection, ainsi que scores agreges, fournisseur, modele, version de politique et statut de calibration dans la classification semantique, sans exposer les libelles.
- [ ] Calibrer seuils et scores sur le jeu d'or; mesurer faux negatifs et faux positifs par categorie.
  - [x] Versionner un jeu de calibration semantique non sensible et implementer l'evaluateur de precision/rappel, faux positifs et faux negatifs par categorie; le jeu synthetique valide le protocole sans promouvoir le modele en statut `validated`.
  - [ ] Executer la calibration avec le modele d'embeddings local cible sur un jeu d'or metier relu, puis versionner les seuils retenus et les metriques obtenues.
- [x] Valider le premier moteur deterministe de detection: rappel et precision de detection 100 % sur les 8 scenarios synthétiques, 7 tests dedies, integration Excel sans exposition des cellules, routage RAS prioritaire, Ruff et mypy strict passes.
- [x] Valider le moteur hybride: paraphrase semantique detectee, faible similarite rejetee, marge ambigue conservee, libelle absent explicite, hash refuse et modele desactive refuse; 97 tests RAS/registre/integration passes avant raccordement hybride final.

### 5. Resolution juridique et calcul theorique

- [x] Implementer `resolve_applicable_ras_rule` avec selection deterministe par date, priorite et faits etablis; le tool reste hors liste LLM par defaut jusqu'a signature serveur de la provenance des faits.
- [x] Retourner faits manquants, ambiguite ou lacune de source lorsqu'un fait juridique obligatoire manque, notamment residence, IFU, nature precise, exemption, etablissement stable ou convention.
- [x] Permettre a une question utilisateur d'apporter des faits explicites, traces separement du GL.
  - [x] Definir le contrat de faits avec source `user`, `gl`, `organization` ou `legal_document`; la sortie masque les valeurs et expose seulement nom et provenance.
  - [x] Extraire uniquement les formulations explicites via un referentiel versionne; exclure tout fait contradictoire.
  - [x] Signer le contexte HMAC avec empreinte du message, positions, session, fichier, versions et expiration; refuser les `facts` libres du LLM.
  - [x] Resoudre une regle depuis une formulation utilisateur reelle sans exiger `regime`: cette famille est deduite des faits discriminants; aucun choix n'est fait si ces faits manquent.
  - [x] Persister avec le resultat du tool l'empreinte du message, les versions, les noms de faits et les references de preuve, sans valeur fiscale, secret ni jeton.
  - [x] Autoriser automatiquement les tools juridiques au LLM uniquement lorsque la cle d'attestation serveur est configuree; exiger en plus le mapping comptable pour les tools de rapprochement et d'audit batch.
- [x] Implementer `calculate_theoretical_ras` avec `Decimal`, assiette, seuil, taux et devise explicites; externaliser les parametres progressifs IRF et ne pratiquer aucun arrondi faute de regle sourcee.
- [x] Refuser tout calcul inter-devise ou toute conversion sans taux et source explicites; conserver la devise source pour le regime non-resident et bloquer les loyers hors XOF.
- [x] Exposer la trace complete: provenance des faits sans valeurs dans le resolver, regle, formule, base, attendu, devise, article, URL, empreinte et version des parametres dans le calculateur.
- [x] Valider resolution et calcul: taux plats dates 2024-2026, seuil resident, exemption prouvee, non-resident sans conversion, convention bloquee, IRF progressif externalise, devise incompatible et dossier incomplet; 122 tests RAS/registre/integration passes, Ruff et mypy strict sur 44 fichiers passes.

### 6. Rapprochement de la RAS comptabilisee

- [x] Implementer `reconstruct_accounting_entry` pour regrouper les lignes d'une meme piece et rapprocher debit/credit par devise selon les cles connues.
- [x] Implementer `find_ras_counterpart` au niveau de la piece avec cartographie versionnee des charges candidates et comptes RAS, sans double comptage des lignes de charge.
- [x] Rapprocher d'abord dans la meme piece par societe, journal, exercice et devise; utiliser tiers et date uniquement pour proposer une piece liee non confirmee.
- [x] Rechercher regularisations, extournes et comptabilisations differees dans une fenetre configurable de 0 a 366 jours; conserver separement montants confirmes, potentiels et ajustements.
- [x] Implementer `assess_ras_accounting` sur une piece explicitement selectionnee et comparer attendu, comptabilise et ecart dans la devise du GL avec tolerance versionnee.
- [x] N'emettre `ras_non_retrouvee_dans_gl` que si applicabilite et cartographie sont prouvees et si le serveur atteste la couverture technique de toute la feuille chargee: aucune ligne rejetee ou non regroupee, aucune cle inconnue et mapping RAS applicable. Ne jamais assimiler cette couverture a l'exhaustivite declarative ou organisationnelle.
- [x] Tester pieces regroupees, retenues partielles, multiples taux, avoirs, extournes, paiements partiels et comptes inconnus.
  - [x] Refuser une evaluation a taux unique lorsque les signaux d'une meme piece indiquent plusieurs categories RAS; exiger une ventilation du candidat.
  - [x] Tester plusieurs lignes de RAS dans une meme piece et leur somme nette unique; qualifier separement retenue partielle, sur-retenue et inversion nette.
  - [x] Bloquer le calcul d'un paiement partiel lorsque `payment_amount` et `tax_base_amount` attestes different: aucune allocation prorata n'est inventee; accepter leur egalite et conserver une exemption prouvee a zero.
  - [x] Ne jamais persister le montant d'une piece seulement potentiellement liee comme une RAS comptabilisee confirmee.
  - [x] Tester la reconstruction seule: pieces multi-lignes, separation societe/exercice/journal, cle inconnue, doublon de ligne, dates/devises contradictoires et montant source negatif.
  - [x] Tester la contrepartie: meme piece, absence dans un GL complet, regularisation potentielle, extourne potentielle, incoherence de devise, GL incomplet et zeros initiaux preserves.
  - [x] Tester l'evaluation comptable: egalite exacte, ecart, RAS non retrouvee dans un scope complet, exemption a zero, piece liee non confirmee, ajustement non applique, devise incompatible et calcul incomplet.
  - [x] Tester l'attestation serveur du perimetre charge: feuille entierement interpretable acceptee; cle absente ou inconnue bloquant tout constat ferme d'absence.
  - [x] Exclure un avoir pur comptabilise au credit d'un compte de charge meme si son libelle contient un signal RAS; netter dans la meme piece les mouvements debiteurs et crediteurs par devise; garder un compte inconnu hors candidat sans signal et seulement `text_only` avec signal explicite.
- [x] Valider la reconstruction: 34 tests `ras_audit`, 14 tests registre/integration cibles, Ruff et mypy strict sur les 30 fichiers concernes passes.
- [x] Valider `find_ras_counterpart`: 38 tests `ras_audit`, 15 tests registre/integration cibles, Ruff et mypy strict sur les 32 fichiers concernes passes.
- [x] Valider `assess_ras_accounting` de bout en bout sur classeur synthetique: date et devise derivees du GL, regle 2025 a 5 %, attendu et comptabilise a 5 000 XOF, ecart nul et aucune cellule exposee; 132 tests RAS/registre/integration passes.

### 7. RAG fiscal et agent tool-calling

- [x] Disposer d'un corpus RAG fiscal source, versionne et interrogeable avec citations.
- [x] Implementer `query_tax_rag` sur les sources Markdown validees avec article, passage borne, version, URL, empreinte, score et applicabilite datee; sortie explicitement non decisionnelle.
- [x] Limiter le perimetre actif des lois de finances a 2026 dans les retrievers lexical et vectoriel, tout en conservant les millesimes 2024-2025 comme archives non indexees; garder le CGI et les autres sources validees, sans retroactivite.
- [x] Raccorder optionnellement `query_tax_rag` au retriever vectoriel multilingue par reranking RRF; ne jamais activer le provider hash de test, ne jamais contourner un refus lexical, exposer mode et version de politique, et embarquer l'extra Docker `embeddings`.
- [x] Separer strictement reponse juridique RAG et execution d'une regle structuree; le rendu des citations est deterministe et remplace toute reformulation LLM non sourcee.
- [x] Enregistrer tous les tools RAS avec schemas d'entree/sortie stricts et limites de ressources.
  - [x] Enregistrer `normalize_gl`, `assess_gl_readiness`, `reconstruct_accounting_entry`, `find_ras_counterpart`, `detect_ras_candidates`, `classify_transaction_semantics`, `resolve_applicable_ras_rule`, `calculate_theoretical_ras`, `run_ras_audit_batch`, `assess_ras_accounting`, `generate_ras_audit_report` et `query_tax_rag` avec sorties minimales et protections explicites.
  - [x] Fermer les schemas des 12 tools avec `additionalProperties=false`; valider a la frontiere chaines, entiers, nombres, booleens, objets, tableaux, enums et bornes; borner RAG a 5 passages, fenetre de rapprochement a 366 jours et batch a 20 000 candidats maximum.
- [x] Router deterministement les demandes GL simples avant tout appel LLM: feuilles, colonnes, profil, schema, requete filtree, solde, aggregation, qualite, candidats, analyse globale, audit RAS et recherche juridique.
  - [x] Router une demande de candidats RAS vers `detect_ras_candidates`, avec compatibilite descendante vers l'ancien tool seulement lorsqu'il n'est pas autorise.
  - [x] Router les demandes explicites de resolution ou de calcul RAS vers les tools juridiques uniquement lorsqu'un fait generateur date valide est present; conserver les formats ISO et `JJ/MM/AAAA`, refuser les dates absentes ou impossibles et ne jamais laisser le LLM inventer la date; valider de bout en bout extraction, attestation, resolution et calcul depuis une question francaise complete.
- [ ] Autoriser l'agent a enchainer detection, resolution, calcul et rapprochement sans interpreter les nombres.
  - [x] Activer resolution et calcul uniquement avec attestation HMAC configuree; activer batch et rapprochement uniquement avec mapping comptable configure; exiger les deux pour l'evaluation complete.
  - [x] Router une demande d'audit RAS vers le batch persiste, retourner des identifiants candidats opaques et enchainer automatiquement l'evaluation lorsque le batch contient exactement un candidat.
  - [x] Refuser l'application automatique de faits utilisateur globaux lorsque le batch contient plusieurs candidats; chaque cas devra etre enrichi separement.
  - [x] Verifier qu'un candidat appartient au batch et au hash du GL avant enrichissement; interdire consultation et derivation depuis une autre session ou un autre fichier atteste.
- [x] Tester les refus: tool absent, argument invalide, source non applicable, timeout et resultat incomplet.
  - [x] Tester faits inconnus, source modifiee, regle active non resolue, chevauchement, seuil, exemption, convention manquante, categorie bloquee et valeurs non exposees.
  - [x] Rendre cote serveur les resultats RAS et RAG, y compris le calcul incomplet, sans appel de synthese LLM; afficher statut, motif et faits manquants sans permettre au modele d'inventer taux ou montant.

### 8. Rapport, robustesse et gate backend

- [x] Implementer `generate_ras_audit_report` avec synthese et detail exportable par candidat persiste.
  - [x] Implementer le generateur pur JSON/CSV avec identifiant reproductible derive du hash source, des resultats et versions de referentiels.
  - [x] Ajouter les tables, migration et repository pour persister un run d'audit, ses versions, l'empreinte de provenance et ses cas uniques.
  - [x] Persister automatiquement chaque evaluation comptable reussie, retourner son `audit_id` et enregistrer le tool d'export; aucun payload de cas LLM n'est accepte.
  - [x] Etendre un audit persiste a plusieurs candidats dans un meme run batch, sans appliquer de faits utilisateur globaux ni produire de constat fiscal ferme.
  - [x] Permettre l'enrichissement d'un candidat du batch dans une nouvelle version immuable liee par `parent_audit_id`, sans ecraser le rapport precedent.
- [x] Afficher dans le contrat de rapport statut, calcul attendu/comptabilise/ecart, devise, informations manquantes, limites, completude et localisateurs juridiques sans libelle ni tiers brut.
- [x] Distinguer `supported_provisional`, `potential` et `indeterminate`; totaliser attendu, comptabilise et ecart separement par niveau et devise sans addition inter-devise.
- [x] Ajouter journal d'audit, correlation des runs, version des referentiels et reproductibilite du resultat.
  - [x] Conserver `audit_id`, `parent_audit_id`, `agent_run_id`, hash du GL, versions de referentiels, empreinte du contexte et horodatage; relier automatiquement l'audit au run agent qui retourne son identifiant.
  - [x] Ajouter les evenements metier append-only sequences de creation, derivation et generation de rapport, avec metadonnees minimales sans donnees fiscales brutes.
  - [x] Inclure dans l'empreinte reproductible du rapport statut, certitude, regle et version, montants, devise, faits manquants, anomalies, sources juridiques et completude; deux generations du meme audit conservent le meme `report_id` tandis qu'une trace differente change l'identifiant.
- [x] Proteger et minimiser les libelles, tiers et montants dans logs, traces LLM et exports: aucun chemin absolu ni nom de feuille n'est envoye au modele, les erreurs Excel persistees sont generiques, les messages fiscaux sensibles sont remplaces par un contexte final minimal et les rapports excluent libelles et tiers bruts.
- [ ] Challenger chaque tool sur le jeu d'or et rapprocher les resultats au GL source.
  - [x] Challenger sur un classeur Excel derive des 26 lignes du jeu d'or `normalize_gl`, `assess_gl_readiness`, `reconstruct_accounting_entry`, `detect_ras_candidates`, `find_ras_counterpart`, `run_ras_audit_batch` et `generate_ras_audit_report`: 11 pieces, 7 candidats et 26 lignes groupees rapproches; corriger le double comptage inter-couches de `unknown_posting_key`.
  - [x] Challenger les tools juridiques sur la matrice contractuelle dediee plutot que forcer des conclusions dans le jeu d'or comptable, dont les 8 scenarios laissent volontairement `legal_rule_id` vide.
- [ ] Valider lint, types, tests unitaires, tests d'integration, performance et non-regression RAG.
  - [x] Valider le lot faits attestes, fait generateur source, matrice juridique contractuelle, challenge tools sur jeu d'or et GL anonymise reel, schemas tools fermes, protocole de calibration semantique, mapping organisationnel, partenaires fournisseur/client, avoirs et comptes inconnus, persistance minimale, journal et empreinte reproductible, gates, enchainement mono-candidat, isolation, couverture technique v4, volumetrie 600 candidats, feuilles multiples, schema ambigu, multi-devises, paiement partiel bloque, refus multi-categories, ecarts de retenue, routage juridique date, perimetre loi de finances 2026 et isolation de l'ancien perimetre: 425 tests repartis RAG/RAS (260), Excel/tools (85), ledger (24), agent (47), routes/persistance (9) passent; Ruff et mypy passent sur les fichiers source modifies. La commande monolithique depasse le timeout Windows, les partitions sont vertes.
- [ ] Declarer le backend robuste uniquement lorsque les metriques du jeu d'or et les gates sont atteintes.
- [ ] Demarrer alors seulement l'adaptation du front decrite dans `front/todo.md`.

### 9. Lots ulterieurs

- [ ] Ajouter `calculate_ras_deadline` puis calendrier et notifications apres stabilisation du coeur d'audit.
- [ ] Reconsiderer le chargement des declarations RAS pour confirmer les omissions declaratives dans une phase separee.
- [ ] Reconsiderer factures, contrats, paiements et referentiel partenaires comme enrichissements optionnels.

## Ancien perimetre multi-declarations — implemente mais gele

Cette section conserve la trace des composants TVA, RAS, IUTS et IS deja livres. Elle ne constitue plus la roadmap active; aucun nouvel investissement n'est prevu hors correctif critique tant que le backend d'audit RAS sur GL n'est pas robuste.

- [x] Prioriser TVA, puis RAS, IUTS et IS.
- [x] Creer le domaine canonique `tax_declaration`.
- [x] Detecter PDF, image, Excel, XML et CSV par contenu.
- [x] Calculer l'empreinte SHA-256 de chaque source.
- [x] Definir provenance, confiance et statut non resolu.
- [x] Valider le socle: Ruff, mypy strict et 9 tests passes.
- [x] Sourcer le schema TVA sur l'imprime officiel DGI.
- [x] Definir le schema TVA `bf.vat.v1`.
- [x] Garder les identifiants contribuable dynamiques.
- [x] Extraire les lignes TVA depuis CSV et Excel.
- [x] Normaliser base, taux et montant sans estimation.
- [x] Valider l'extracteur TVA: Ruff, mypy et 13 tests passes.
- [x] Extraire les lignes TVA depuis XML sans entites externes.
- [x] Detecter automatiquement une structure TVA tabulaire.
- [x] Retourner `unresolved` sans estimation si extraction impossible.
- [x] Exposer `POST /api/tax-declarations/ingest`.
- [x] Limiter la taille des declarations importees.
- [x] Valider l'API d'ingestion: Ruff, mypy et 20 tests passes.
- [x] Extraire le texte des PDF natifs avec `pypdf`.
- [x] Ajouter l'OCR local Tesseract pour scans et images.
- [x] Rasteriser les PDF scannes avec `pypdfium2`.
- [x] Plafonner la confiance OCR a 0,70.
- [x] Limiter les PDF a 50 pages et 30 secondes par OCR.
- [x] Valider PDF/OCR: Ruff, mypy et 20 tests metier passes.
- [ ] Revalider l'OCR reel dans Docker; BuildKit local reste bloque.
- [x] Versionner les formules TVA 14 et 19 hors du code.
- [x] Sourcer chaque formule sur l'imprime officiel DGI.
- [x] Valider unicite des lignes et resolution des montants.
- [x] Ne jamais assimiler une ligne absente a zero.
- [x] Retourner attendu, declare, ecart et lignes concernees.
- [x] Exposer `POST /api/tax-declarations/analyze`.
- [x] Valider les couches TVA initiales: Ruff, mypy et 31 tests passes.
- [x] Referencer les taux TVA de l'article 317 hors du code.
- [x] Versionner les taux avec leur date d'applicabilite.
- [x] Controler les taux 18 % et 10 % par periode.
- [x] Controler l'echeance mensuelle de l'article 334.
- [x] Ne pas appliquer une regle datee sans periode fiable.
- [x] Retourner dates attendue et declaree pour l'echeance.
- [x] Valider les controles CGI TVA: Ruff, mypy et 35 tests passes.
- [x] Extraire le credit TVA a reporter des documents.
- [x] Versionner la regle de continuite du credit TVA.
- [x] Verifier que les periodes comparees sont consecutives.
- [x] Rapprocher le report precedent avec la ligne 21 courante.
- [x] Retourner attendu, repris et ecart historique.
- [x] Exposer `POST /api/tax-declarations/analyze-history`.
- [x] Valider l'historique TVA: Ruff, mypy et 40 tests passes.
- [x] Definir une cartographie versionnee des comptes TVA du Grand Livre.
- [x] Rendre compte, ligne, sens, devise et tolerance configurables.
- [x] Filtrer le Grand Livre par compte, exercice et periode.
- [x] Utiliser les cles de comptabilisation pour debit et credit.
- [x] Rapprocher les lignes TVA 19 et 20 par devise.
- [x] Echouer si une ecriture comptable est exclue.
- [x] Retourner comptes, mappings et sources utilises.
- [x] Exposer `POST /api/tax-declarations/reconcile-ledger`.
- [x] Valider le rapprochement GL: Ruff, mypy et 46 tests passes.
- [x] Versionner les niveaux d'assurance limitee, renforcee et haute.
- [x] Determiner les niveaux atteints et les controles manquants sans decision LLM.
- [x] Exposer le niveau d'assurance et ses couches manquantes dans l'analyse TVA.
- [x] Normaliser les factures et paiements CSV/Excel avec identifiants partenaires dynamiques.
- [x] Rapprocher factures, declaration et paiements par couches deterministes.
- [x] Exposer le detail des preuves et ecarts sans donnees sensibles inutiles.
- [x] Exposer `POST /api/tax-declarations/reconcile-supporting-documents`.
- [x] Extraire les factures et paiements XML sans entites externes.
- [x] Extraire les tableaux explicites des PDF, scans et images sans estimation.
- [x] Valider les pieces justificatives: Ruff, mypy et 73 tests passes.
- [ ] Revalider l'OCR reel des pieces dans Docker; BuildKit local reste bloque.
- [x] Sourcer les principaux imprimes RAS DGI: residents, non-residents et non-determines.
- [x] Definir le schema canonique RAS `bf.withholding.v1` sans deduire le regime du taux.
- [x] Detecter et extraire les declarations RAS CSV/Excel aux en-tetes explicites.
- [x] Conserver les structures RAS ambigues non resolues.
- [x] Versionner les regles RAS 2024, 2025 et 2026 par regime et categorie explicite.
- [x] Controler taux, base et montant RAS avec source et ecart detailles.
- [x] Ne pas appliquer une categorie expiree ou une convention fiscale non renseignee.
- [x] Integrer l'analyse RAS dans `POST /api/tax-declarations/analyze`.
- [x] Valider le moteur RAS: Ruff, mypy et 94 tests passes.
- [x] Controler les echeances RAS par regime et periode, avec date attendue, date declaree, source officielle et statut explicite.
- [x] Valider les echeances RAS: 27 tests cibles passes, Ruff `app tests` et mypy sur 174 fichiers applicatifs passes.
- [x] Extraire les declarations RAS XML, PDF natif, scan et image sans interpreter les structures ambigues.
- [x] Valider le domaine declarations fiscales apres le multi-format RAS: 96 tests passes, Ruff et mypy passes.
- [x] Sourcer le formulaire IUTS/TPA et les articles 112, 113 et 116 du CGI DGI.
- [x] Verifier que les lois de finances 2025 et 2026 ne modifient pas les articles IUTS controles.
- [x] Definir le schema canonique IUTS `bf.iuts.v1` avec identifiants salaries dynamiques.
- [x] Detecter et extraire les declarations IUTS CSV, Excel, XML, PDF natif, scan et image.
- [x] Versionner le bareme progressif, les reductions pour charges et l'echeance hors du code.
- [x] Controler le montant IUTS par salarie et l'echeance sans supposer l'option semestrielle.
- [x] Integrer l'analyse IUTS dans `POST /api/tax-declarations/analyze`.
- [x] Valider le moteur IUTS: 126 tests declarations/API passes, Ruff et mypy passes.
- [x] Sourcer et implementer ensuite la declaration IS.
- [x] Sourcer les imprimes IS et les articles 48, 87, 89, 91, 92 et 95 du CGI DGI (recherche web, a faire valider par un expert-comptable ou fiscaliste avant production; voir `docs/open-questions.md`).
- [x] Definir le schema canonique IS `bf.is.v1` avec extracteurs CSV/Excel, XML, PDF natif, scan et image.
- [x] Versionner le taux IS (27,5 %), le plancher IMFPIC par regime et l'echeance annuelle hors du code.
- [x] Controler le taux IS declare et le plancher IMFPIC declare, sans decision LLM.
- [x] Integrer l'analyse IS dans `POST /api/tax-declarations/analyze`.
- [x] Valider le moteur IS: tests unitaires rule loader, extracteurs et service de validation passes.
- [x] Trouve en testant l'IS via un vrai front (navigateur, pas seulement pytest): `api/.env` local (non versionne) n'avait pas `CORPORATE_INCOME_TAX_VALIDATION_RULES_PATH`, provoquant un 500 "referentiel de validation IS indisponible" en environnement reel — seul `.env.example` avait ete mis a jour. Corrige localement. A verifier: tout environnement de deploiement (staging/prod) cree avant l'ajout de l'IS a probablement le meme trou de configuration.
- [x] Recalculer l'IMFPIC a 0,5 % du CA annuel HT arrondi aux 100 000 FCFA inferieurs, puis appliquer le plancher par regime.
- [x] Versionner et controler les traitements IMFPIC explicites: standard, activite exclusive, CGA, cumul CGA/activite exclusive et premier exercice exonere.
- [x] Valider l'IMFPIC via le service et l'API: 155 tests declarations/API passes, Ruff et mypy passes.
- [x] Controler les acomptes provisionnels IS via un flux historique du type `analyze-history` (necessite l'IS du de l'exercice precedent). Ordre suivi:
  - [x] Ajouter un champ optionnel `provisional_installments_paid` a la declaration annuelle IS (simplification documentee dans `docs/open-questions.md`: le vrai formulaire DGI des acomptes est un document distinct non modelise pour l'instant).
  - [x] Versionner la regle des acomptes (75 % de l'IS du de l'exercice precedent, article 91) dans `docs/reference/bf-is-validation-rules.csv`.
  - [x] Ajouter `corporate_income_tax_historical_validation.py` (miroir de `vat_historical_validation.py`): continuite des exercices + controle du montant des acomptes.
  - [x] Brancher l'IS sur `POST /api/tax-declarations/analyze-history` (parametre `declaration_type`, defaut TVA conserve).
  - [x] Tests: acomptes corrects, acomptes incorrects, exercices non consecutifs, exercice non clos au 31 decembre (403 tests API passes, Ruff et mypy passes).
  - [x] Ne pas generaliser le controle historique a RAS/IUTS: aucun report ou acompte inter-periodes n'est source dans les referentiels actuels; ajouter un controle uniquement si une future regle officielle l'exige.
- [x] Couvrir TVA, RAS, IUTS et IS.
- [x] Accepter Excel, CSV, XML, PDF, scan et image.
- [x] Detecter automatiquement format, structure et encodage.
- [x] Definir un schema canonique versionne par declaration.
- [x] Conserver valeur source, valeur normalisee et provenance.
- [x] Attribuer un score de confiance a chaque extraction.
- [x] Laisser les donnees incertaines non resolues automatiquement.

### Phase 1 - Declarations seules, sans Grand Livre

- [ ] Completer la collecte locale des sources officielles 2023-2026 pour TVA, RAS, IUTS et IS, en partant des textes les plus recents puis en reconstruisant les versions anterieures applicables.
  - [x] Prendre le CGI consolide officiel le plus recent comme referentiel juridique principal: version web DGI 2024; conserver le PDF officiel 2023 comme photographie juridique 2023, avec identite SHA-256 prouvee face au PDF DGI.
  - [x] Traiter 2023-2026 comme perimetre d'analyse; deduire chaque date d'applicabilite du CGI, des lois de finances et des textes modificatifs, sans l'inferer de l'annee seule.
  - [ ] Recenser et empreinter les lois de finances 2023, 2024, 2025 et 2026 depuis les sites officiels.
    - [x] Acquerir et verifier par taille + SHA-256 le CGI 2023, les lois initiales 2023-2026 et la loi rectificative 2024; manifeste de 6 documents et script de rehydratation valides.
    - [ ] Localiser le texte promulgue officiel de la loi rectificative 2025; son adoption est confirmee mais seul l'expose des motifs est actuellement publie par la DGI.
  - [ ] Etablir la matrice exhaustive `impot x article CGI x modification legislative x instruction x formulaire x periode`.
    - [x] Etablir la matrice initiale des 17 articles actuellement controles: 38 intervalles couvrant 2023-2026, sans chevauchement et avec statut de verification explicite.
    - [ ] Etendre la matrice aux categories attendues encore absentes des moteurs de controles.
  - [ ] Reconstituer article par article la version applicable en 2023, 2024, 2025 et 2026.
  - [x] Utiliser instructions et formulaires comme complements pratiques sans prevaloir sur le CGI ou la loi.
  - [x] Detecter et signaler chaque article modifie, manquant ou contradictoire avec une raison explicite dans l'inventaire et la matrice d'applicabilite.
  - [ ] Detecter les categories fiscales attendues absentes des referentiels structures.
  - [ ] Generer ensuite les regles deterministes versionnees avec date, article, URL, empreinte et preuve d'applicabilite.
- [x] Collecter les sources officielles utiles au perimetre actuel: CGI, lois de finances, instructions et imprimes DGI.
  - [x] Indexer les extraits CGI, les imprimes de structure TVA/IUTS/IS, les lois de finances RAS 2024-2026 et les instructions contextuelles: 16 sources, 37 blocs, 0 source bloquee.
  - [x] Inventorier 15 sources officielles (CGI 2023/2024, lois initiales et rectificatives, instructions et imprimes) avec statut d'usage, statut corpus et ecart explicite.
  - [x] Verifier dans les PDF officiels les articles RAS des lois de finances 2024, 2025 et 2026, puis les rapprocher du referentiel deterministe avant indexation.
  - [x] Dater l'entree en vigueur du CGI initial au 1er janvier 2018 et resoudre l'ancienne echeance au 20 de l'imprime d'acomptes IS sans la reutiliser.
  - [x] Qualifier les instructions administratives TVA/IUTS comme contexte seulement, faute de preuves transactionnelles dans les declarations.
- [x] Versionner chaque source et son applicabilite: dates confirmees pour 10 sources, statut `not_stated` explicite pour les 6 documents officiels sans borne fiable, sans date inventee.
- [x] Vectoriser les textes valides pour recherche et justification: chargement Markdown, index en memoire, requete vectorisee, URL officielle, priorite CGI/loi sur les formulaires a score egal, citations versionnees et empreinte SHA-256 conservees; 69 tests RAG passes, Ruff et mypy passes.
- [x] Structurer assiette, taux, seuil, exception et echeance.
- [x] Relier chaque regle a son article officiel.
- [x] Interdire au LLM toute decision fiscale finale.
- [x] Executer les validations avec un moteur deterministe.
- [x] Controler successivement format, completude et coherence.
- [x] Controler les regles fiscales TVA, RAS, IUTS et IS, puis l'historique uniquement pour TVA et IS lorsque la regle sourcee depend d'une autre periode.
- [x] Produire une assurance limitee sans Grand Livre.
- [x] Detecter dynamiquement IFU et identifiants equivalents: IFU/NIF/TIN/identifiant fiscal ou type source explicite, sans hypothese sur la longueur ou la forme de la valeur; type et zeros initiaux conserves dans les pieces, la RAS et l'IS; 170 tests declarations/API passes, Ruff et mypy passes.
- [ ] Versionner tolerances, arrondis et exceptions.
- [ ] Tracer extraction, transformation, regle, preuve et resultat.
- [ ] Chiffrer et minimiser les donnees fiscales sensibles.
- [ ] Tester chaque regle avec cas normal, limite et anomalie.

### Phase 2 - Rapprochements externes, hors MVP initial

- [x] Rapprocher Grand Livre, pieces et paiements disponibles (mecanismes deja implementes, non requis au demarrage de la phase 1).
  - [x] Generaliser le contrat de cartographie GL avec type de declaration, champ selecteur et champ montant explicites; conserver les valeurs TVA par defaut.
  - [x] Rapprocher une declaration RAS au GL via `withholding_tax`, `line_code` et `withheld_amount`, sans reutiliser implicitement `tax_amount`; 159 tests declarations/API passes, Ruff et mypy passes.
  - [x] Etendre le rapprochement GL a l'IUTS et a l'IS avec des cartographies organisationnelles explicites; tests de rapprochement passes pour les quatre declarations.
  - [x] Generaliser le contrat des pieces et paiements a la RAS: montant fiscal, selecteur et champ canonique explicites, sans imposer l'arithmetique HT + TVA; conservation des zeros initiaux.
  - [x] Etendre les pieces et paiements a l'IUTS et a l'IS avec montant fiscal et montant de paiement attendu distincts; 165 tests declarations/API passes, Ruff et mypy passes.
- [x] Produire une assurance renforcee avec rapprochement comptable: politiques v2 propres a TVA/RAS/IUTS/IS, historique exige uniquement pour TVA/IS, composition controles fiscaux + GL exposee par l'API; cas RAS renforce passe, 165 tests declarations/API passes, Ruff et mypy passes.
- [ ] Rapprocher les partenaires par identifiants et attributs disponibles.
- [ ] Scorer les doublons sans fusion automatique incertaine.

## Migration Infrastructure Prioritaire

- [x] Introduire PostgreSQL local pour les metadonnees agent, pas pour remplacer les calculs Excel immediatement.
- [x] Ajouter les dependances DB et migrations versionnees avec SQLAlchemy + Alembic.
- [x] Ajouter le script racine `npm run api:db:migrate` pour appliquer les migrations locales.
- [x] Creer les tables minimales: `agent_sessions`, `agent_files`, `agent_messages`, `agent_runs`, `agent_run_events`, `agent_tool_results`.
- [x] Persister les fichiers eux-memes sur disque ou storage, et stocker seulement les metadonnees en base.
- [x] Remplacer l'index memoire des uploads par un repository persistant quand `DATABASE_URL` est configure.
- [x] Exposer l'API locale du projet sur `http://localhost:8001` pour eviter le backend historique deja present sur `8000`.
- [x] Conserver les endpoints et contrats existants pendant la migration.
- [ ] Ajouter plus tard une implementation PostgreSQL de `AccountMappingRepository` si le besoin metier le justifie.
