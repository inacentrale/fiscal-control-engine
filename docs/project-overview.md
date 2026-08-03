# Vue Projet

## Objectif

Bank Files Harmonizer est un agent de revue fiscale pre-declaratif pour les donnees comptables OHADA, avec un premier perimetre Burkina Faso.

Le systeme analyse les donnees issues du Grand Livre avant depot des declarations afin de detecter des incoherences TVA et Retenue a la Source (RAS). Il sert de second niveau de controle interne pour le responsable financier.

## Ce que le systeme fait

- Harmoniser les fichiers comptables fournis par le cabinet fiscal.
- Cartographier les comptes comptables vers des categories fiscales.
- Appliquer des regles deterministes de controle TVA/RAS.
- Produire des anomalies explicables et tracables.
- Preparer ensuite un rapport de revue fiscale.

## Ce que le systeme ne fait pas

- Il ne remplace pas le cabinet fiscal.
- Il ne remplace pas la decision du responsable financier.
- Il ne calcule pas les declarations fiscales finales.
- Il ne laisse pas un LLM decider de la conformite fiscale.
- Il ne transmet pas les donnees du Grand Livre a une API cloud.

## Principe Directeur

La decision fiscale est deterministe.

Le LLM peut expliquer une anomalie deja detectee par le moteur de regles, mais il ne decide jamais:

- qu'un compte est soumis a RAS;
- qu'un taux est applicable;
- qu'une ecriture est conforme ou non conforme;
- qu'une anomalie doit etre retenue.

## Architecture Cible

| Module | Role |
| --- | --- |
| Import et normalisation | Lire Excel/CSV, nettoyer les donnees et produire des objets metier typés |
| Mapping comptes | Relier comptes du Grand Livre, plan comptable et categories fiscales |
| Moteur de regles | Appliquer les controles TVA/RAS de maniere deterministe |
| Base documentaire | Stocker CGI, doctrine et procedures internes pour justification |
| RAG local | Retrouver les textes utiles pour expliquer une anomalie |
| LLM local/API controlee | Rediger une explication, sans decision fiscale |
| API FastAPI | Exposer les services au frontend |
| Front React | Permettre au RF de consulter, filtrer, confirmer et exporter |

## Stack Retenue

- POC: Python + Pandas sur fichiers CSV/Excel.
- Backend cible: Python FastAPI.
- Frontend cible: React + Tailwind CSS.
- Base relationnelle cible: PostgreSQL, apres validation du POC.
- Recherche documentaire cible: ChromaDB.
- LLM cible: Ollama + Mistral local, ou API controlee selon contraintes.

## Strategie Actuelle

Le projet commence par un coeur metier stable, independant de FastAPI, Pandas et PostgreSQL autant que possible.

L'objectif est d'eviter de refaire le travail:

- Pandas reste limite a l'import et a la normalisation.
- Les regles fiscales manipulent des objets metier typés.
- Les mots-cles et textes metier de pre-classification vivent dans un referentiel versionne, pas dans le code.
- Le stockage passe par une interface remplacable.
- PostgreSQL arrivera plus tard sans casser les contrats metier.

## Tests

Pour le moment, la priorite est aux tests unitaires.

Les tests d'integration, E2E, Docker, PostgreSQL, ChromaDB et LLM sont differes jusqu'a stabilisation du coeur metier et de l'import.

Les tests unitaires doivent challenger:

- les contrats metier;
- les entrees invalides;
- les colonnes manquantes;
- les doublons;
- les libelles absents;
- les fichiers non supportes;
- les cas ambigus qui doivent rester a confirmer par le metier.

## Documents Lies

- [Cahier des charges](CDC_Agent_IA_Revue_Fiscale_SAHEL%20.md)
- [Sources Excel](excel-sources.md)
- [Skills projet](skills/README.md)
