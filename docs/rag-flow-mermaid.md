# Schémas Mermaid Agent, Excel, RAG

Objectif: comprendre ce que fait l'IA et ce qu'elle ne fait pas.

Le principe central: **les calculs, lectures Excel, contrôles et classifications restent déterministes**. Le LLM orchestre et explique, mais il ne décide pas seul.

## Vue Globale

```mermaid
flowchart TD
    U[Utilisateur] --> F[Front Dashboard]

    F -->|Upload Excel| AF[agent_file]
    AF -->|session_id + file_id + sheet_names| F

    F -->|Question + reference fichier| AR[Agent Router HTTP]
    AR --> ORCH[Agent Orchestrator]

    ORCH --> TR[Routeur deterministe de tools]
    TR --> EXCEL[excel_agent tools]
    TR --> MAP[account_mapping]
    TR --> RAG[rag_source]

    EXCEL --> CLS[classify_ledger_schema]
    CLS --> LEDGER[ledger_analysis]
    MAP --> RULES[Regles RAS preliminaires]
    RAG --> SOURCES[Sources citees]

    EXCEL --> RES[Resultats structures]
    CLS --> RES
    LEDGER --> RES
    MAP --> RES
    RAG --> RES

    RES --> ORCH
    ORCH --> LLM[LLM externe ou fallback]
    LLM --> TXT[Explication Markdown]
    ORCH --> SAFE[Answer Policy / garde-fous]
    TXT --> SAFE
    SAFE --> F
```

Ce que le LLM reçoit: la question, le contexte fichier, les définitions de tools, puis des résultats structurés. Il ne reçoit pas tout l'Excel brut.

## Module `agent_file`

```mermaid
flowchart TD
    U[Upload Excel] --> V[Validation extension / taille / lisibilite]
    V -->|OK| S[Stockage temporaire]
    V -->|Erreur| E[Erreur HTTP safe]
    S --> M[Metadata fichier]
    M --> R[session_id / file_id / sheet_names]
    R --> F[Front]

    R --> RUN[Run agent futur]
    RUN --> FR[File Resolver]
    FR --> P[Chemin serveur autorise]
```

Rôle: recevoir le fichier, le valider, le stocker temporairement, puis fournir une référence safe. Le front ne manipule pas de chemin serveur.

## Module `excel_agent`

```mermaid
flowchart TD
    TC[Tool call] --> VAL[Validation nom + schema + fichier autorise]
    VAL -->|OK| EXEC[Tool Executor]
    VAL -->|Refus| ERR[Erreur structuree]

    EXEC --> LS[list_sheets]
    EXEC --> GC[get_columns]
    EXEC --> PS[profile_sheet]
    EXEC --> CLS[classify_ledger_schema]
    EXEC --> AL[analyze_ledger]

    LS --> OUT[Sortie structuree]
    GC --> OUT
    PS --> OUT
    CLS --> OUT
    AL --> OUT
```

Rôle: lire Excel de façon contrôlée. Les tools actuels retournent surtout des métadonnées, profils et schémas, pas les lignes complètes.

## Module `ledger_analysis`

```mermaid
flowchart TD
    F[Fichier + feuille] --> P[Profil feuille]
    P --> C[Colonnes detectees]
    C --> CLS[classify_ledger_schema]
    CLS --> MAP[Mapping schema canonique]
    MAP --> CONF{Confiance suffisante ?}

    CONF -->|Oui| CANON[Champs canoniques: account, amount, text, currency, tax_code...]
    CONF -->|Ambigu| ASK[Statut a_confirmer]
    CONF -->|Manquant| MISS[Champ manquant]

    CANON --> AL[analyze_ledger]
    ASK --> SAFE[Aucune supposition LLM]
    MISS --> SAFE
    AL --> R[Rapport: lignes, colonnes, schema, profils]
    R --> SAFE[Aucune ligne complete exposee]
```

Rôle: comprendre le sens des colonnes d'un Excel utilisateur avant l'analyse. Le LLM ne devine pas: les colonnes sont mappees par heuristiques deterministes avec score de confiance.

## Classification du Schéma Canonique

```mermaid
flowchart TD
    COL[Colonnes Excel utilisateur] --> PROF[Profil metadata: nom, type, completude, position]
    PROF --> H[Heuristiques deterministes]

    H --> SYN[Synonymes: Compte, GL Account, Code TVA...]
    H --> TYPE[Types detectes: nombre, texte, date]
    H --> MISS[Taux de valeurs manquantes]

    SYN --> SCORE[Score de confiance]
    TYPE --> SCORE
    MISS --> SCORE

    SCORE --> DEC{Decision mapping}
    DEC -->|score fiable| MAPPED[mapped]
    DEC -->|ambigu| CONFIRM[a_confirmer]
    DEC -->|absent| MISSING[missing]

    MAPPED --> CANON[Schema canonique utilisable]
    CONFIRM --> HUMAN[Validation humaine future]
    MISSING --> BLOCK[Tool suivant limite ou refuse]
```

Objectif: permettre à l'agent de comprendre que `Compte`, `Nº compte` ou `GL Account` peuvent représenter le champ canonique `account`, sans envoyer les lignes brutes au LLM.

## Module `account_mapping`

```mermaid
flowchart TD
    GL[Comptes du Grand Livre] --> JOIN[Jointure]
    PC[Plan comptable] --> JOIN
    REF[Regles RAS CSV] --> CLASS[Classification preliminaire]
    JOIN --> CLASS
    CLASS --> OUT[Compte + libelle + categorie RAS + confiance + justification]
```

Rôle: relier les comptes du Grand Livre au plan comptable et produire une classification RAS préliminaire. Ce module ne dépend pas du LLM.

## Module `rag_source`

```mermaid
flowchart TD
    DOC[Sources documentaires] --> SCAN[Validation source]
    SCAN -->|Indexable| LOAD[Markdown / CSV loader]
    SCAN -->|Draft ou incomplet| BLOCK[Non indexe]
    LOAD --> CHUNK[Chunking]
    CHUNK --> SEARCH[Recherche lexicale / vectorielle]
    SEARCH --> SRC[Passages citables]
    SRC --> LLM[Explication avec sources]
```

Rôle: retrouver les sources et citations. Le RAG apporte du contexte documentaire, pas une décision fiscale.

## Orchestration LLM

```mermaid
flowchart TD
    Q[Question utilisateur] --> REQ[ModelRequest]
    REQ --> G[Groq / Gemini]
    G -->|Tool calls| ORCH[Orchestrateur]
    G -->|Texte direct| POLICY[Answer Policy]
    G -->|Erreur| FB[Fallback suivant]

    ORCH --> TOOLS[Tools deterministes]
    TOOLS --> CTX[Resultats structures compacts]
    CTX --> FINAL[Demande de redaction finale]
    FINAL --> G
    FINAL -->|Fallback interne| DET[Reponse deterministe minimale]
    POLICY --> OUT[Reponse utilisateur]
    DET --> OUT
```

Rôle: le LLM choisit ou formule, mais les résultats fiables viennent des tools.

## Prochains Tools

```mermaid
flowchart TD
    A[classify_ledger_schema] --> A2[analyze_ledger sur schema canonique]
    A2 --> B[aggregate_ledger]
    B --> C[query_ledger_entries]
    C --> D[calculate_ledger_metrics]
    D --> E[detect_data_quality_issues]
    E --> F[detect_tax_candidates]
    F --> G[Routeur deterministe de tools]
```

Pourquoi le routeur déterministe: une question comme "montre les écritures du compte 44585100" doit appeler `query_ledger_entries`, pas dépendre d'un choix libre du LLM.
