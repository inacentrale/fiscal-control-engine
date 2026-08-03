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
- [x] Ajouter un routeur deterministe de tools: choisir le ou les tools selon l'intention utilisateur avant appel LLM, puis tester chaque intention separement.
- [x] Router une demande generale du type `Explique-moi cet Excel` vers une analyse globale multi-tools avant appel LLM.
- [x] Ajouter des tests de consistance tool par tool: fixture Excel anonymisee, sortie attendue stable, absence de donnees sensibles, limites de lignes respectees.

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
- [ ] Remplir/valider les squelettes fiscaux puis associer les 13 questions restantes.

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
- [x] Ajouter les tests unitaires du routeur deterministe de tools agent.
- [x] Ajouter les tests unitaires du routage `Explique-moi cet Excel` vers `analyze_ledger`, `calculate_ledger_metrics`, `aggregate_ledger`, `detect_data_quality_issues` et `detect_tax_candidates`.
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
- [x] Ajouter un contrat de graphe riche: `chart_id`, `kind`, `metric`, `labels`, `values`, `series`, `metadata`.
- [x] Retourner des erreurs stables si un fichier est expire, supprime ou introuvable: `file_expired`, `file_missing`.
- [x] Ajouter un contrat front stable pour les fichiers agent: statut, expiration, nom original safe, taille, type MIME, dates.
- [x] Renforcer le routeur deterministe de questions: detecter un compte et router vers `query_ledger_entries`.
- [x] Renforcer le routeur deterministe de questions: detecter periode, TVA, fournisseur, client, montant min/max.
- [x] Construire automatiquement les arguments tool fiables, par exemple `{"filters": {"account": "44585100"}}`.
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

- [x] Challenger `calculate_ledger_metrics`: filtres compte/exercice/periode, cles debit-credit, montants source negatifs, devise, compte inexistant et invariants de rapprochement (85 tests API passes; challenges runtime reels passes).
- [x] Challenger partiellement `query_ledger_entries`: filtres compte/exercice, pagination et signe des montants selon les cles; approfondir cles inconnues, multi-devises et pages suivantes.
- [ ] Challenger `aggregate_ledger`: contrat corrige et valide en runtime (`34211100`: 15 lignes, 9 utilisees, 6 exclues explicites; compte `61365000`/2024 regroupe par periode); terminer le rapprochement Excel multi-devises et valider la regle de classement avant de cocher.
- [ ] Challenger `detect_data_quality_issues`: compteurs techniques rapproches sur 2506 lignes (9 categories conformes), mais corriger le double signalement des memes 6 lignes, distinguer lignes structurelles/vides et limiter `missing_counterparty` aux ecritures dont le tiers est reellement requis avant validation.
- [ ] Challenger `detect_tax_candidates`: compteurs/montants rapproches et statut `review_required` conforme, mais 87 lignes non-residentes sont double-comptees dans `resident_services`, actions CSV tronquees par virgules non quotees, justification/source/version absentes du payload et comptes serialises avec `.0`; corriger avant validation fiscale.
- [ ] Challenger `classify_ledger_schema`: mapping reel 11/11 conforme et ambiguite de deux montants correctement bloquee, mais une meme colonne peut etre affectee a `account` et `customer` sans confirmation; `is_usable=true` meme sans cle de comptabilisation alors que les soldes sont impossibles. Ajouter unicite des sources et readiness par capacite avant validation.
- [ ] Challenger `analyze_ledger`: dimensions physiques 2506x21 et mapping 11/11 rapproches, mais distinguer 2506 lignes physiques de 2500 ecritures candidates et 6 lignes structurelles; clarifier `is_valid` (colonnes presentes malgre valeurs critiques invalides) et ajouter readiness par capacite heritee du classifieur.
- [ ] Challenger `profile_sheet`: dimensions, valeurs non vides, manquantes et ratios rapproches exactement sur le fichier reel (2506x21); le type `text` de `Date piece` est conforme aux cellules source stockees en chaines. Avant validation, distinguer les 2500 ecritures des 6 lignes structurelles et ne pas presenter les identifiants (`Compte`, cle, client, fournisseur) comme des nombres metier au risque de perdre les zeros initiaux.
- [ ] Challenger `get_columns`: ordre reel des 21 colonnes conforme; espaces externes retires, en-tete vide normalise (`column_N`) et accents/caracteres speciaux conserves. Avant validation, signaler les doublons au lieu d'accepter le renommage silencieux Pandas (`Montant.1`) et fermer explicitement le classeur pour eviter son verrouillage sous Windows.
- [ ] Challenger `list_sheets`: ordre, feuilles multiples/vides et noms accentues ou speciaux conformes sur classeur cible. Avant validation, exposer l'etat visible/masque (une feuille technique masquee est actuellement retournee sans distinction) et fermer explicitement le classeur pour eviter son verrouillage sous Windows.
- [ ] Corriger la reponse de solde sans correspondance pour distinguer « aucun solde calculable » d'un solde comptable nul.

## Gestion des Declarations Fiscales

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
- [ ] Sourcer et implementer ensuite la declaration IS.
- [ ] Couvrir TVA, RAS, IUTS et IS.
- [ ] Accepter Excel, CSV, XML, PDF, scan et image.
- [ ] Detecter automatiquement format, structure et encodage.
- [ ] Definir un schema canonique versionne par declaration.
- [ ] Conserver valeur source, valeur normalisee et provenance.    
- [ ] Attribuer un score de confiance a chaque extraction.
- [ ] Laisser les donnees incertaines non resolues automatiquement.
- [ ] Collecter CGI, lois, instructions et imprimes officiels DGI.
- [ ] Versionner chaque source et sa date d'application.
- [ ] Vectoriser les textes pour recherche et justification.
- [ ] Structurer assiette, taux, seuil, exception et echeance.
- [ ] Relier chaque regle a son article officiel.
- [ ] Interdire au LLM toute decision fiscale finale.
- [ ] Executer les validations avec un moteur deterministe.
- [ ] Controler successivement format, completude et coherence.
- [ ] Controler ensuite regles fiscales et historique.
- [ ] Rapprocher enfin Grand Livre, pieces et paiements disponibles.
- [ ] Produire une assurance limitee sans Grand Livre.
- [ ] Produire une assurance renforcee avec rapprochement comptable.
- [ ] Detecter dynamiquement IFU et identifiants equivalents.
- [ ] Rapprocher les partenaires par identifiants et attributs disponibles.
- [ ] Scorer les doublons sans fusion automatique incertaine.
- [ ] Versionner tolerances, arrondis et exceptions.
- [ ] Tracer extraction, transformation, regle, preuve et resultat.
- [ ] Chiffrer et minimiser les donnees fiscales sensibles.
- [ ] Tester chaque regle avec cas normal, limite et anomalie.

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
