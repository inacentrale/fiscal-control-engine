---
name: api-rules
description: Regles API FastAPI, Pandas, PostgreSQL et moteur fiscal.
trigger: glob
globs:
  - "api/**/*"
---

# Regles API

## Stack et Perimetre

- Le CDC fait autorite: le backend cible est Python FastAPI.
- Le POC initial utilise Python + Pandas sur CSV pour valider le moteur de regles avant l'infrastructure.
- L'environnement de developpement API passe par Docker et les scripts racine `package.json`.
- Ne pas ajouter de `Makefile` API sans decision explicite.
- Les routes sont exposees sous le prefixe global `/api`.
- Ne pas ajouter de prefixe `/v1` tant qu'il n'est pas explicitement demande.
- Le premier domaine metier est `account-mapping`.

## Architecture FastAPI

- Organiser par domaine: routers, schemas, services, repositories si necessaire, constantes et tests.
- Les routers orchestrent HTTP: validation, appel de service, reponse. Aucune regle metier lourde dans un router.
- Les services portent les cas d'usage et les regles metier.
- Le coeur metier doit rester independant de FastAPI, Pandas et PostgreSQL quand c'est raisonnable.
- Definir des objets et contrats metier stables avant les adapters HTTP ou stockage.
- Les traitements de fichiers, CSV et Pandas doivent rester encapsules dans des services applicatifs.
- Les acces stockage passent par des repositories/interfaces pour pouvoir remplacer fichier/memoire par PostgreSQL sans reecrire le metier.
- Ne jamais retourner directement un modele ORM: utiliser un schema de reponse explicite.
- Les dependances FastAPI doivent rester explicites et testables.

## Validation et Contrats

- Contract-first: definir les schemas Pydantic et contrats de reponse avant la logique.
- Toute entree externe est non fiable: body, query, params, fichiers, cookies et webhooks futurs.
- Utiliser des guard clauses et echouer explicitement sur les etats invalides.
- Ne pas retourner ou passer `None` volontairement pour masquer une erreur; preferer un type explicite ou une exception.

## Configuration et Secrets

- Centraliser la configuration dans un module dedie, par exemple via `pydantic-settings`.
- Ne pas lire les variables d'environnement directement dans les routers ou services metier.
- Ne jamais commit de secret. Documenter les variables attendues dans `api/.env.example`.

## Constantes

- Centraliser constantes techniques stables, limites, chemins et noms de colonnes dans des modules `constants.py` par domaine.
- Les mots-cles fiscaux, justifications, actions requises, seuils et taux doivent vivre dans un referentiel versionne ou en base, pas dans le code metier.
- Ne pas enfouir de mots-cles fiscaux, seuils, taux, noms de colonnes ou textes de justification dans les services.
- Les constantes techniques doivent porter le vocabulaire metier et rester importables dans les tests unitaires.
- Les seuils et taux fiscaux devront venir d'un referentiel documente avant usage en production.

## Donnees, CSV et Base de Donnees

- Le POC demarre avec CSV/Pandas, conformement a la feuille de route.
- Pandas sert a importer, nettoyer et normaliser; les regles fiscales ne doivent pas dependre de DataFrames partout.
- PostgreSQL est la base relationnelle cible, a introduire lors de la migration infrastructure.
- La migration PostgreSQL doit conserver les contrats API et les services metier existants.
- Toute evolution de schema PostgreSQL future doit avoir une migration versionnee, par exemple Alembic si SQLAlchemy est retenu.
- Definir contraintes, index et unicites dans la base quand ils protegent une regle metier.

## Moteur Fiscal

- La classification fiscale et les controles sont deterministes.
- Ne pas utiliser de LLM pour decider `soumisRas`, `categorieRas`, un taux ou une anomalie.
- Toute classification automatique doit conserver une justification et un niveau de confiance.
- Les comptes ambigus restent en statut `a_confirmer_metier`.
- Les taux et seuils fiscaux doivent venir d'un referentiel documente, pas de valeurs magiques.

## Tests

- TDD prefere pour les nouvelles regles metier et comportements unitaires.
- Tester les cas heureux, erreurs, etats invalides et limites utiles.
- Les mocks doivent representer les contrats reels.
- Ne pas creer de tests dedies aux schemas Pydantic ou au cablage simple sans valeur metier.
- Placer les tests dans le dossier `tests` du domaine, par exemple `api/app/account_mapping/tests`.
- Avant de terminer un changement API: executer les scripts racine pertinents, par exemple `npm run api:lint`, `npm run api:typecheck` et `npm run api:test`.
- Si Docker n'est pas disponible localement, le noter dans `api/todo.md` et verifier au minimum la syntaxe des fichiers modifiés.

## Logs

- Utiliser des logs structures uniquement pour les flux critiques: imports, controles fiscaux, integrations externes futures, generation de rapports.
- Inclure un identifiant de correlation quand un flux traverse plusieurs services.
- Ne jamais logguer les fichiers complets, secrets, donnees personnelles ou montants sensibles inutiles.
