# Deploiement VPS

Ce projet se deploie avec Docker Compose depuis la branche `codex2`.

## Capacite VPS Actuelle

Derniere verification: VPS `ubuntu-s-2vcpu-4gb-fra1-01`.

- CPU: 2 vCPU.
- RAM: 3.8 GiB, environ 1.9 GiB disponible.
- Swap: 2 GiB, deja partiellement utilisee.
- Disque: 77 GiB, environ 12 GiB libres.
- Docker et Docker Compose disponibles.
- Plusieurs conteneurs tournent deja; garder les embeddings locaux desactives.

Conclusion: deploiement API + front possible avec LLM externes. Eviter les modeles locaux et nettoyer Docker si le build manque d'espace disque.

## Variables

Copier l'exemple puis renseigner les secrets:

```bash
cp .env.prod.example .env.prod
```

Variables obligatoires a remplacer:

- `POSTGRES_PASSWORD`
- `NEXT_PUBLIC_BASE_URL`
- `CORS_ORIGINS`
- `RAS_FACT_CONTEXT_SIGNING_KEY`
- `LLM_PROVIDER_CHAIN`
- `LLM_OPENAI_COMPATIBLE_API_KEY`
- `LLM_OPENAI_COMPATIBLE_BASE_URL`

Sur le VPS actuel, conserver:

```bash
RAG_EMBEDDING_PROVIDER=disabled
RAS_SEMANTIC_EMBEDDING_PROVIDER=disabled
```

## Commandes

```bash
git switch codex2
git pull --ff-only origin codex2
npm run prod:build
npm run prod:migrate
npm run prod:up
npm run prod:ps
```

Verification:

```bash
curl -fsS http://127.0.0.1:8001/api/health
curl -fsS http://127.0.0.1:3009
```

## Reverse Proxy

Le compose expose uniquement sur `127.0.0.1`:

- API: `127.0.0.1:8001`
- Front: `127.0.0.1:3009`
- PostgreSQL: `127.0.0.1:5435`

Le domaine public doit pointer vers le front. Les appels `/api/*` sont proxifies par Next vers le service API interne.

## Rollback

```bash
git log --oneline -5
git switch codex2
git reset --hard <commit_precedent>
npm run prod:build
npm run prod:up
```

Ne pas supprimer les volumes Docker pendant un rollback applicatif.
