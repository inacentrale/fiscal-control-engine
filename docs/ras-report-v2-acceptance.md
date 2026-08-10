# Acceptation du rapport RAS v2

Ce document sert de grille de revue metier du rapport RAS v2. Il ne remplace
pas une validation fiscale et ne cree aucune regle fiscale.

## Perimetre de la revue

- Jeu d'or synthetique versionne dans `api/app/ras_audit/tests/fixtures/golden/`.
- Grand Livre anonymise `docs/GL_anonymise_2500.xlsx`.
- Exports JSON, CSV, Excel et PDF produits depuis le meme `report_id`.
- Contrat attendu: `2.0.0`; libelles attendus: `ras-report-labels-v1`.

## Criteres bloquants

- [ ] Le sens de l'ecart `comptabilise - theorique` est compris sans aide.
- [ ] Insuffisances et excedents ne se compensent ni entre cas, ni entre
  devises, ni entre niveaux de certitude.
- [ ] Aucun cas probable ou indeterminable n'est presente comme une conclusion
  fiscale certaine.
- [ ] Les actions proposees sont adaptees a une revue humaine et ne prescrivent
  ni taux, ni assiette, ni montant non source.
- [ ] Les faits manquants permettent de comprendre exactement ce qui bloque la
  conclusion, sans afficher de donnee client inutile.
- [ ] Les references juridiques et versions de referentiels sont suffisantes
  pour refaire la revue.
- [ ] Le PDF est une synthese lisible; l'Excel reste le support de travail
  detaille.

## Criteres de contenu

- [ ] La synthese distingue cas conclus, probables, indeterminables, bloques et
  en erreur.
- [ ] Les montants sont presentes par devise et niveau de certitude.
- [ ] La priorite et l'action de chaque cas correspondent au statut affiche.
- [ ] La periode, la piece pseudonymisee, le compte, la nature, le fait
  generateur, l'assiette, le taux, la tolerance et l'arrondi sont explicites
  lorsqu'ils sont disponibles et restent vides sinon.
- [ ] Les codes machine restent accessibles avec leurs libelles metier.

## Criteres de format et securite

- [ ] Le classeur contient `Synthese`, `Regularisations`, `Cas indetermines`,
  `Faits manquants`, `Details` et `References`.
- [ ] Les filtres, en-tetes et largeurs permettent une revue sans retraitement
  manuel preliminaire.
- [ ] Les exports ne contiennent ni cellule brute, ni libelle libre, ni tiers,
  ni identifiant fiscal non necessaire.
- [ ] Les valeurs commencant par `=`, `+`, `-` ou `@` ne sont jamais executees
  comme formules dans CSV ou Excel.
- [ ] Les quatre formats correspondent au meme audit et au meme `report_id`.

## Decision

- Relecteur:
- Fonction:
- Date:
- Jeu de donnees et `report_id` verifies:
- Decision: accepte / accepte avec reserves / refuse
- Reserves ou corrections demandees:
