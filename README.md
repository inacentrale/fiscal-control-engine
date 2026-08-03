# Sahel Fiscal Review Agent

Agent de revue fiscale pre-declaratif pour analyser les donnees comptables OHADA, avec un premier perimetre Burkina Faso.

## Objectif

Le projet aide le responsable financier a analyser le Grand Livre avant depot fiscal, reperer les incoherences possibles et preparer des controles TVA/RAS explicables.

Le systeme ne remplace ni le cabinet fiscal ni la decision humaine. Les controles fiscaux restent deterministes; le LLM explique, mais ne decide pas.

## Etat Actuel

- API FastAPI structuree.
- Upload Excel securise pour le Grand Livre.
- Agent Excel avec tools internes: `list_sheets`, `get_columns`, `profile_sheet`, `analyze_ledger`.
- Analyse du Grand Livre minifie: schema, lignes, colonnes, valeurs manquantes, sans exposer les valeurs de cellules.
- Mapping comptes Grand Livre + Plan comptable.
- Import `account_mapping` depuis fichiers configures cote serveur.
- Adapter LLM `openai-compatible` avec fallback interne.
- CI API: secrets, lint, typecheck, tests, compilation Python, build Docker.

## Stack Cible

- API: Python FastAPI.
- Import/POC: Python + Pandas + CSV/Excel.
- Frontend: React + Tailwind CSS.
- Base cible: PostgreSQL apres validation du POC.
- RAG cible: ChromaDB.
- LLM: explication uniquement, jamais decision fiscale.

## Structure

```text
api/      API FastAPI, agent, tools Excel, mapping, tests
docs/     cahier des charges, schemas, sources Excel, referentiels
front/    frontend Next.js
```

## Commandes

Commandes API via Docker:

```bash
npm run api:build
npm run api:dev
npm run api:test
npm run api:lint
npm run api:typecheck
npm run api:compile
npm run secrets:check
```

L'API locale est exposee par defaut sur `http://localhost:8001`.

Frontend:

```bash
cd front
npm install
npm run dev
```

Ouvrir ensuite `http://localhost:3002`.
Le proxy Next.js envoie `/api/*` vers `http://localhost:8001/api/*` par defaut.

Controles front:

```bash
cd front
npm run lint
npm run typecheck
npm run build
```

Verification locale API sans Docker:

```bash
cd api
PYTHONPATH=. python3 -m pytest -q
PYTHONPATH=. python3 -m ruff check app tests scripts
PYTHONPATH=. python3 -m mypy app tests scripts
```

## Documents Utiles

- [Vue projet](docs/project-overview.md)
- [Etat actuel du projet](docs/current-project-state.md)
- [Sources Excel](docs/excel-sources.md)
- [Questions ouvertes](docs/open-questions.md)
- [Plan API](api/todo.md)
- [Plan Front](front/todo.md)
