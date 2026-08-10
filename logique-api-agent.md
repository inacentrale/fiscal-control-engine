# Logique API Agent Fiscal

Ce document décrit l'architecture API actuelle du projet `fiscal-control-engine`.

## 1. Vue Actuelle

```mermaid
flowchart LR
    Front[Front utilisateur] --> API[FastAPI /api]

    API --> Agent[Agent fiscal]
    API --> Files[Uploads et fichiers]
    API --> Dashboard[Dashboard fichier actif]
    API --> Mapping[Account mapping]
    API --> TaxDecl[Tax declarations deprecated]
    API --> Health[Health check]

    Files --> Storage[Fichiers locaux]
    Files --> DB[(PostgreSQL)]

    Agent --> ExcelTools[Tools Excel / Grand Livre]
    Agent --> RasTools[Tools RAS]
    Agent --> RagTools[RAG lois / CGI]
    Agent --> LLM[Gemini / Groq / fallback interne]

    ExcelTools --> Ledger[Analyse Grand Livre]
    RasTools --> RasAudit[Audit RAS]
    RagTools --> Sources[Sources fiscales validees]

    RasAudit --> DB
    Agent --> DB
```

## 2. Flux Upload Fichier

```mermaid
flowchart TD
    U[Utilisateur] --> A[POST /api/agent/files]
    A --> B[Copie temporaire]
    B --> C[Validation Excel]
    C --> D[Extraction feuilles]
    D --> E[Stockage fichier local]
    E --> F[Metadonnees PostgreSQL]
    F --> G[session_id / file_id]
    G --> Front[Retour front]

    C -->|erreur| X[Erreur stable: invalid / unsupported / too_large]
```

## 3. Flux Question Agent

```mermaid
flowchart TD
    U[Question utilisateur] --> A[POST /api/agent/runs]
    A --> B[Resolution session_id + file_id]
    B --> C{Fichier requis ?}

    C -->|oui| D[Verifier fichier actif]
    C -->|non| E[Question sans fichier]

    D --> F[AgentRunRequest]
    E --> F

    F --> G[Selection outil]
    G --> H{Type de question}

    H -->|Grand Livre| GL[Tools Grand Livre]
    H -->|RAS comptable| RAS[Tools RAS]
    H -->|Lois / CGI| RAG[query_tax_rag]
    H -->|Libre| LLM[LLM choisit outil autorise]

    GL --> R[Resultats structures]
    RAS --> R
    RAG --> R
    LLM --> R

    R --> Answer[Reponse Markdown]
    Answer --> Persist[Persistance run / events / tool results]
    Persist --> Front[Retour front]
```

## 4. Grand Livre

```mermaid
flowchart LR
    Ledger[Grand Livre] --> Schema[classify_ledger_schema]
    Ledger --> Analyze[analyze_ledger]
    Ledger --> Metrics[calculate_ledger_metrics]
    Ledger --> Aggregate[aggregate_ledger]
    Ledger --> Query[query_ledger_entries]
    Ledger --> Quality[detect_data_quality_issues]

    Schema --> Canonical[Schema canonique]
    Analyze --> Overview[Vue globale]
    Metrics --> KPI[KPI et soldes]
    Aggregate --> Charts[Agregats par compte / periode / TVA / tiers]
    Query --> Table[Ecritures paginees]
    Quality --> Issues[Anomalies qualite]
```

## 5. RAS

RAS signifie `retenue a la source`. Dans l'API, la logique RAS est separee en trois niveaux: reperer les pieces a revoir, verifier la comptabilisation, puis comparer avec la regle fiscale si les faits sont suffisants.

### 5.1 Reperage Des Candidats RAS

```mermaid
flowchart TD
    GL[Grand Livre] --> Mapping[Mapping comptes RAS]
    GL --> TextSignals[Signaux dans les libelles]

    Mapping --> Detect[detect_ras_candidates]
    TextSignals --> Detect

    Detect --> Cases[Pieces candidates]
    Cases --> Status[Statuts: compte + libelle / compte seul / libelle seul]
    Cases --> Review[Revue humaine requise]
```

### 5.2 Verification Comptable RAS

```mermaid
flowchart TD
    Cases[Pieces candidates] --> Counterpart[find_ras_counterpart]
    Cases --> Entry[reconstruct_accounting_entry]

    Counterpart --> Found[RAS comptabilisee]
    Counterpart --> Missing[RAS absente ou non trouvee]
    Counterpart --> Potential[Piece liee potentielle]

    Entry --> Balance[Controle debit / credit par devise]

    Cases --> Batch[run_ras_audit_batch]
    Batch --> DB[(ras_audit_runs / ras_audit_cases)]
    DB --> Report[generate_ras_audit_report]
```

### 5.3 Regle Fiscale Et Calcul

```mermaid
flowchart TD
    Facts[Faits explicites: date / residence / IFU / nature / montant / devise] --> Resolve[resolve_applicable_ras_rule]
    Rules[Regles stockees dans docs/reference/*.csv] --> Resolve
    Sources[Sources officielles + hash] --> Resolve

    Resolve --> Calc[calculate_theoretical_ras]
    Calc --> Assess[assess_ras_accounting]

    Accounting[RAS comptabilisee dans le GL] --> Assess
    Assess --> Result[Resultat: conforme / ecart / indetermine]
```

Important: la RAS n'est pas decidee par le LLM. Le LLM peut expliquer. Les tools reperent, calculent et signalent les cas a revoir.

## 6. Lois / CGI / RAG Fiscal

```mermaid
flowchart TD
    Internet[Sources officielles DGI / finances] --> Audit[Collecte manuelle ou script controle]
    Audit --> Manifest[Manifest officiel: URL / chemin / SHA256 / date verification]
    Manifest --> LocalDocs[PDF ou copie locale conservee]
    LocalDocs --> Markdown[Extraits Markdown valides]
    Markdown --> Validate[Validation metadata / source / hash]
    Validate --> Inventory[Inventaire corpus RAG genere]
    Validate --> Chunks[Chunking article / section / paragraphe]
    Chunks --> Lexical[Recherche lexicale]
    Chunks --> Vector[Index vectoriel si embeddings actifs]

    Query[Question juridique directe utilisateur] --> Tool[Tool query_tax_rag]
    Tool --> Lexical
    Tool --> Vector
    Lexical --> Rerank[Classement / reranking]
    Vector --> Rerank

    Rerank --> Citations[Citations: article, version, URL, hash, applicabilite]
    Citations --> Agent[Agent repond avec sources]
```

Important: l'API ne cherche pas les lois sur Internet a chaque question. Elle interroge un corpus local deja collecte, valide, versionne et rattache a des sources officielles.

```mermaid
flowchart LR
    User[Question: CGI / loi / taux / article] --> Agent[Agent fiscal]
    Agent --> Tool[query_tax_rag]
    Tool --> Corpus[docs/source-corpus/fiscal]
    Tool --> Ref[docs/reference/bf-tax-official-document-manifest.csv]
    Corpus --> Results[Passages trouves]
    Ref --> Proof[URL officielle + hash + date verification]
    Results --> Answer[Reponse citee]
    Proof --> Answer
```

Les references juridiques ont deux usages distincts:

```mermaid
flowchart TD
    Sources[CGI / lois / DGI] --> RAG[Corpus Markdown pour questions naturelles]
    Sources --> Rules[CSV de regles fiscales structurees]

    RAG --> Query[query_tax_rag]
    Query --> Explain[Informer et citer]

    Rules --> Resolve[resolve_applicable_ras_rule]
    Resolve --> Calc[calculate_theoretical_ras]
    Calc --> Assess[assess_ras_accounting]

    Explain --> NoDecision[Pas de decision fiscale]
    Assess --> Provisional[Calcul provisoire si faits complets]
```

## 6.1 Stockage Des Regles Fiscales

```mermaid
flowchart TD
    Official[Sources officielles: CGI / lois de finances / DGI] --> Extraction[Extraction controlee des points utiles]

    Extraction --> LegalRules[bf-ras-legal-rules.csv]
    Extraction --> TaxEvents[bf-ras-tax-event-rules.csv]
    Extraction --> CalcParams[bf-ras-calculation-parameters.csv]
    Extraction --> Deadlines[bf-withholding-deadline-rules.csv]
    Extraction --> Manifest[bf-tax-official-document-manifest.csv]

    Manifest --> Proof[Preuve: URL officielle / chemin local / SHA256 / date]

    LegalRules --> RuleLoader[Chargement API des regles]
    TaxEvents --> RuleLoader
    CalcParams --> RuleLoader
    Deadlines --> RuleLoader

    RuleLoader --> Resolve[resolve_applicable_ras_rule]
    Resolve --> Calc[calculate_theoretical_ras]
    Calc --> Assess[assess_ras_accounting]

    Proof --> Resolve
    Proof --> Calc
```

Les regles fiscales calculables sont donc stockees directement dans `docs/reference/*.csv`. Le corpus RAG sert a expliquer et citer; les CSV servent a resoudre une regle et calculer.

## 7. Dashboard Front

```mermaid
flowchart TD
    A[GET /api/agent/sessions/:session_id/context] --> B[Fichier actif]
    B --> C[build_file_dashboard]

    C --> GL[Stats Grand Livre]
    C --> Quality[Qualite donnees]
    C --> Charts[Graphes]
    C --> Ras[RAS review]

    GL --> Payload[Payload dashboard front]
    Quality --> Payload
    Charts --> Payload
    Ras --> Payload

    Charts --> C1[Comptes]
    Charts --> C2[Periodes]
    Charts --> C3[TVA]
    Charts --> C4[Fournisseurs / clients]
    Ras --> R1[Candidats]
    Ras --> R2[Montants]
    Ras --> R3[Signaux]
    Ras --> R4[Statuts]
```

## 8. Persistance

```mermaid
flowchart TD
    Docker[Docker compose] --> DB[(PostgreSQL)]
    API[API] --> DB
    API --> LocalFiles[Stockage fichiers locaux]

    DB --> S[agent_sessions]
    DB --> F[agent_files]
    DB --> R[agent_runs]
    DB --> M[agent_messages]
    DB --> E[agent_run_events]
    DB --> T[agent_tool_results]

    DB --> AR[ras_audit_runs]
    DB --> AC[ras_audit_cases]
    DB --> AE[ras_audit_events]

    Migrations[Alembic migrations] --> DB
```

## 9. Architecture Cible A Realigner

```mermaid
flowchart LR
    API[FastAPI] --> Files[files]
    API --> Agent[agent]
    API --> Dashboard[dashboard]
    API --> Ledger[ledger]
    API --> RasReview[ras_review]
    API --> TaxLaw[tax_law_rag]
    API --> RasRules[ras_rules]

    Agent --> Ledger
    Agent --> RasReview
    Agent --> TaxLaw
    Agent --> RasRules

    Dashboard --> Ledger
    Dashboard --> RasReview

    Ledger --> Excel[Pandas / Excel adapters]
    RasReview --> RasDB[(RAS audit DB)]
    TaxLaw --> SourceIndex[Sources + index]
    RasRules --> References[Referentiels versionnes]
```

## 10. Point Qui Cloche Aujourd'hui

```mermaid
flowchart TD
    ExcelAgent[excel_agent] --> GL[Grand Livre]
    ExcelAgent --> RAS[RAS]
    ExcelAgent --> RAG[RAG fiscal]
    ExcelAgent --> Audit[Audit RAS]
    ExcelAgent --> Rules[Regles fiscales]

    Orchestrator[agent/orchestrator.py] --> Routing[Routing]
    Orchestrator --> Prompt[Prompts]
    Orchestrator --> Fallback[Fallback]
    Orchestrator --> Answers[Format reponses]
    Orchestrator --> Guardrails[Garde-fous]

    Dashboard[dashboard_service.py] --> Tools[Execution directe de tools]

    Problem[Probleme principal] --> P1[Frontieres metier floues]
    Problem --> P2[Modules trop charges]
    Problem --> P3[Dashboard trop couple aux tools]
    Problem --> P4[RAS / GL / RAG pas assez separes]
```
