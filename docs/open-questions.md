# Points Non Clarifies

Ce document garde les questions et decisions a reprendre plus tard. Elles ne bloquent pas le socle actuel, mais elles devront etre tranchees avant de stabiliser le mapping fiscal et la future base de donnees.

## Modele de Mapping

- Faut-il conserver la source exacte du fichier importe pour chaque mapping ?
- Faut-il modeliser un resultat d'import dedie avec statistiques ?
- Quelles statistiques d'import sont obligatoires ?
  - total de lignes lues;
  - comptes valides;
  - comptes ignores;
  - doublons;
  - erreurs;
  - comptes sans libelle.
- Quel format donner aux erreurs metier structurees ?
- `confidence` doit-il rester une chaine ou devenir une enum ?

## Classification RAS

- Les categories RAS minimales sont-elles suffisantes ?
  - prestations de services residents;
  - prestations de services non-residents;
  - charges immobilieres / loyers;
  - hors perimetre;
  - a confirmer.
- Faut-il separer le statut de qualification comptable du statut fiscal ?
- Quels libelles comptables permettent une pre-classification automatique fiable ?
- Quels comptes doivent obligatoirement rester en validation metier ?

### Contradiction des echeances RAS a corriger avant activation

- `docs/reference/bf-withholding-deadline-rules.csv` indique le jour 15 pour les regimes resident et non-resident.
- Les extraits locaux `bf-ras-residents.md` (article 208) et `bf-ras-non-residents.md` (article 214) indiquent le jour 20 du mois suivant.
- `bf-loyers.md` (article 217) indique le jour 10 du mois suivant pour les retenues sur loyers.
- Le nouveau moteur ne doit utiliser aucune de ces echeances avant correction et validation par periode du referentiel.

### Champ des contribuables non determines incomplet

- Les lois de finances 2024-2026 confirment des taux a l'article 221, mais le corpus local ne contient pas le texte complet de l'article 220 definissant le champ.
- Les variantes concernees sont inventoriees dans `bf-ras-legal-rules.csv` avec le statut `blocked_missing_scope_source`; leurs taux ne sont jamais activables en calcul.

### Fait generateur RAS modelise, assurance juridique encore provisoire

- `bf-ras-tax-event-rules.csv` distingue le paiement resident, la mise en paiement non-resident et le loyer acquis pour la periode, avec articles, URL et empreintes.
- La resolution exige le statut et la date de l'evenement attestes; l'evaluation GL date la regle sur cet evenement et non sur la seule date comptable de charge.
- Le referentiel reste `active_provisional` sans revue fiscale externe; cette assurance doit etre levee avant le gate de production.

## Donnees et Stockage

- Le stockage fichier/memoire suffit-il jusqu'a la validation du POC ?
- Quel sera le schema PostgreSQL cible pour les mappings ?
- Faut-il historiser les imports successifs ?
- Faut-il conserver les lignes sources ou seulement les mappings resultants ?

## Tests

- Quels cas doivent rester unitaires uniquement ?
- Quand introduire les tests d'integration Excel reels ?
- Faut-il creer des fixtures anonymisees derivees des fichiers fournis ?

## Impot sur les Societes (IS)

- Les articles CGI cites dans `docs/reference/bf-is-validation-rules.csv`
  (taux art. 87, assiette art. 48, IMFPIC art. 89, echeance art. 95, acomptes
  art. 91/92) proviennent d'une recherche web automatisee sur
  `https://dgi.bf/verification/CGI` et sur les imprimes `dgi.bf/imprimes/`,
  pas d'un document fourni par l'utilisateur ni d'une verification humaine.
  A faire valider par un expert-comptable ou un fiscaliste avant tout usage
  en production.
- L'assiette du taux de 0,5 % de l'IMFPIC a ete confirmee dans les articles
  88 et 89 du CGI DGI: chiffre d'affaires annuel hors taxes, arrondi aux
  100 000 FCFA inferieurs. Le moteur controle ce calcul, le plancher par
  regime et les traitements explicites prevus aux articles 89 et 90.
- Les acomptes provisionnels IS sont controles par le flux historique
  `POST /api/tax-declarations/analyze-history`. La modelisation simplifiee
  du formulaire distinct reste documentee ci-dessous.
- L'echeance annuelle IS (30 avril, art. 95) n'est evaluee que pour un
  exercice clos au 31 decembre; les exercices a cheval sur une autre date de
  cloture retournent `NOT_EVALUATED` plutot qu'une date devinee.
- Simplification assumee pour les acomptes provisionnels: le champ
  `provisional_installments_paid` a ete ajoute directement a la declaration
  annuelle IS (`bf.is.v1`). Le vrai formulaire DGI est pourtant un document
  distinct (`DECLARATION-DES-ACOMPTES-PROVISIONNELS-IMPOT-SUR-LES-SOCIETES-.pdf`,
  champs 01 a 05: IS du N-1, 75 % de ce montant, montant par acompte,
  deduction des prelevements subis, solde a verser). Ce document distinct
  n'est pas modelise (pas d'extracteur, pas de champs 02-04). Choix fait
  avec l'utilisateur pour rester sur un changement de taille raisonnable;
  a reconsiderer si un besoin metier plus precis (ex. deduction des
  retenues subies) se presente.
- Divergence documentaire resolue: l'imprime DGI des acomptes reprend
  l'echeance historique au 20 du CGI entre en vigueur en 2018. L'article 92
  a ensuite ete modifie par la loi n035-2020/AN, article 13, avec une
  echeance au 15. Le moteur ne controle actuellement que le montant
  historique des acomptes et l'ancienne echeance reste exclue du corpus.

## Squelettes Fiscaux RAG (RAS residents, RAS non-residents, Loyers)

- Les 3 squelettes de `docs/source-corpus/fiscal/` ont ete remplis avec le
  texte litteral du CGI (articles 107, 120-128, 206-219), extrait par
  lecture programmatique directe du PDF officiel dgi.bf (`pypdf`, page par
  page), pas par resume ou reformulation d'un modele. Le texte est donc
  fidele a la source telle que lue.
- Le decoupage en blocs du squelette RAS residents a ete adapte: le CGI ne
  distingue pas « honoraires » et « commissions » comme deux dispositions
  separees (article 206 vise uniformement « les prestations de toute
  nature »); voir la section Notes de `bf-ras-residents.md`.
- **Decision du 2026-08-03**: sur demande explicite de l'utilisateur, qui
  n'a pas d'expert-comptable ou fiscaliste disponible pour le moment, les 3
  fichiers sont passes `validation_status: validated` avec
  `validated_by: Audrey Ouedraogo (auto-validation, sans relecture fiscale
  externe)` plutot que de rester bloques indefiniment sur
  `validation_status: draft`. Ce n'est **pas** une validation par un
  professionnel: c'est l'utilisateur qui assume la responsabilite de ce
  contenu pour debloquer l'indexation maintenant. Une vraie relecture
  fiscale reste a faire des que possible; si elle revele une erreur, les 3
  fichiers et le CSV genere (`docs/reference/rag-source-corpus.generated.csv`)
  devront etre corriges et re-exportes.
- Les 13 questions `pending_source` de
  `docs/reference/rag-question-expectations.csv` ont ete reassociees aux
  chunks generes suite a cette auto-validation (voir ce fichier pour le
  detail question par question).
