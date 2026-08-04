# Analyse Grand Livre — Audit RAS

Agent de revue fiscale pre-declaratif specialise dans la retenue a la source (RAS), a partir du Grand Livre OHADA, avec un premier perimetre Burkina Faso.

Le backend `agent` et `ras_audit` constitue le perimetre actif. Les routes historiques `/api/tax-declarations/**` restent disponibles uniquement pour compatibilite, sont marquees `deprecated` dans OpenAPI et sont gelees hors correctif critique. Elles ne font pas partie du gate de robustesse RAS et ne doivent recevoir aucune nouvelle fonctionnalite avant une phase ulterieure explicitement decidee.

## Objectif

Le projet aide le responsable financier a reperer les depenses potentiellement soumises a la RAS et a verifier si une retenue correspondante est effectivement comptabilisee dans le Grand Livre.

Sans declaration fiscale, le systeme detecte une omission de comptabilisation dans le GL, pas une omission de declaration. Les controles et calculs restent deterministes; le LLM explique les resultats, analyse les libelles ambigus et orchestre des tools, mais ne fixe ni l'assujettissement final ni le taux.

Le RAG fiscal reste un service distinct et transversal. Il permet d'interroger en langage naturel le CGI, les lois de finances et les documents DGI, avec citations et periode d'applicabilite.

## Perimetre Initial

- Source comptable obligatoire: Grand Livre uniquement.
- Aucun referentiel fournisseur externe requis.
- Detection des candidats RAS par regles comptables, NLP et similarite semantique.
- Recherche de la contrepartie RAS dans les lignes de la piece et dans les regularisations associees.
- Calcul theorique uniquement lorsque les faits requis sont disponibles.
- Sortie explicite: conforme, montant incoherent, RAS non retrouvee ou indeterminable.
- Backend prioritaire; le front sera adapte apres validation de la robustesse des services et tools.

## Etat Actuel

- API FastAPI structuree.
- Upload Excel securise pour le Grand Livre.
- Agent Excel avec tools internes pour profiler, normaliser, filtrer et agreger le GL.
- Analyse du Grand Livre minifie: schema, lignes, colonnes, valeurs manquantes, sans exposer les valeurs de cellules.
- Mapping comptes Grand Livre + Plan comptable.
- Import `account_mapping` depuis fichiers configures cote serveur.
- RAG fiscal source et versionne sur les documents officiels disponibles.
- Referentiels RAS versionnes et moteur de validation deterministe existants, a recentrer sur l'audit GL.
- Adapter LLM `openai-compatible` avec fallback interne.
- CI API: secrets, lint, typecheck, tests, compilation Python, build Docker.

## Stack Cible

- API: Python FastAPI.
- Import/POC: Python + Pandas + CSV/Excel.
- Frontend: React + Tailwind CSS.
- Base cible: PostgreSQL apres validation du POC.
- RAG: index fiscal source et citations verifiables; stockage vectoriel remplacable.
- LLM: orchestration, explication et analyse semantique assistee, jamais calcul ni decision fiscale finale.

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
- [Fonctionnalites et tools RAS](docs/FEATURES.md)
- [Etat actuel du projet](docs/current-project-state.md)
- [Sources Excel](docs/excel-sources.md)
- [Questions ouvertes](docs/open-questions.md)
- [Plan API](api/todo.md)
- [Plan Front](front/todo.md)
