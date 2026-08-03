# Etat Actuel Du Projet

```mermaid
flowchart TD
    U[Utilisateur] --> UP[Upload Excel Grand Livre]
    UP --> API[API FastAPI]
    API --> TMP[Stockage temporaire securise]
    API --> AG[Agent Excel]

    AG --> TOOLS[Tools internes]
    TOOLS --> META[list_sheets / get_columns / profile_sheet]
    TOOLS --> LEDGER[analyze_ledger]

    LEDGER --> VALID[Validation colonnes Grand Livre]
    VALID --> REPORT[Rapport structure sans valeurs sensibles]

    API --> MAP[Account Mapping]
    MAP --> IMPORT[Import fichiers configures]
    IMPORT --> JOIN[Mapping GL + Plan comptable]
    JOIN --> RAS[Detection comptes sans libelle / RAS preliminaire]

    AG --> LLM[LLM compatible OpenAI]
    LLM --> FALLBACK[Fallback interne si LLM absent]

    CI[CI API] --> CHECKS[Tests / Lint / Typecheck / Docker / Secrets]
```

Resume: l'API sait recevoir un Excel, l'analyser, produire un mapping comptable et preparer l'agent LLM sans lui confier la decision fiscale.

## Detail `analyze_ledger`

```mermaid
flowchart TD
    F[Fichier Grand Livre] --> S[Lecture feuille Excel]
    S --> C[Controle colonnes attendues]
    C --> P[Profil colonnes]
    P --> R[Rapport: lignes, colonnes, schema, valeurs manquantes]
    R --> SAFE[Aucune valeur de cellule exposee]
```

## Agent, RAG Et Embeddings

```mermaid
flowchart TD
    DOC[Sources documentaires] --> CH[Chunking]
    CH --> EMB[Embeddings]
    EMB --> IDX[Index vectoriel]

    U[Question utilisateur] --> AG[Agent]
    AG --> EX[Tool Excel: analyze_ledger]
    AG --> RAG[Tool RAG: retrieve_sources]
    RAG --> IDX
    IDX --> SRC[Chunks pertinents]
    SRC --> AG
    EX --> AG
    AG --> LLM[LLM encadre]
    LLM --> REP[Reponse avec sources et garde-fous]
```
