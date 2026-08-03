# BF - RAS Non-Residents

## Metadonnees

- `domain`: `fiscal`
- `country`: `BF`
- `source_type`: `tax_code`
- `title`: `Code General des Impots du Burkina Faso - Section 3 (Retenue a la source sur les sommes versees aux prestataires non-residents), articles 210 a 214, et definition du domicile fiscal (article 107)`
- `version`: `Texte consolide dgi.bf (loi adoptee le 20 decembre 2017, fichier LOI-PORTANT-CODE-GENERAL-DES-IMPOTS-FINAL.pdf) - A CONFIRMER par rapprochement avec la derniere loi de finances et toute convention fiscale bilaterale applicable au prestataire concerne`
- `applicable_from`: `2018-01-01`
- `applicable_to`: ``
- `applicability_status`: `confirmed`
- `source_url`: `https://dgi.bf/wp-content/uploads/2023/10/LOI-PORTANT-CODE-GENERAL-DES-IMPOTS-FINAL.pdf`
- `language`: `fr`
- `origin`: `anonymized_reference`
- `themes`: `prestataire non resident; residence fiscale; convention fiscale; verification humaine`
- `validation_status`: `validated`
- `validated_by`: `Audrey Ouedraogo (auto-validation, sans relecture fiscale externe)`
- `validated_at`: `2026-08-03`

## Source

Extrait litteral du Code General des Impots du Burkina Faso, Livre 1,
Titre 1, Chapitre 8, Section 3, articles 210 a 214, et Chapitre 1
(Impot unique sur les traitements et salaires), article 107 §2 pour la
definition du domicile fiscal.

Fichier source: `https://dgi.bf/wp-content/uploads/2023/10/LOI-PORTANT-CODE-GENERAL-DES-IMPOTS-FINAL.pdf`
(pages 30 et 57 du PDF).

Prepare par extraction directe du texte du PDF officiel (lecture page par
page, pas de resume ni de reformulation). Auto-valide par le porteur du
projet (voir `validated_by`) pour debloquer l'indexation, mais **pas
relu par un expert-comptable ou fiscaliste**: une relecture professionnelle
reste a faire des que possible et pourrait modifier ce contenu, en
particulier l'application d'une convention fiscale bilaterale. Le taux
cite a l'article 212 correspond a celui deja retenu dans
`docs/reference/bf-withholding-validation-rules.csv` (regime
`nonresident`), qui reste la source de verite pour le calcul deterministe;
ce document sert uniquement de justification/explication citable. Toute
convention fiscale bilaterale applicable au prestataire non-resident
concerne doit etre verifiee separement et peut modifier le taux ou
l'assujettissement (l'article 210 le rappelle explicitement).

## Blocs

### Prestataires non-residents - champ d'application

- `block_reference`: `articles 210 et 211`
- `block_type`: `article`
- `theme`: `prestataire non resident`

```text
Art.210.- Sous reserve des dispositions des conventions internationales
relatives aux doubles impositions, une retenue a la source est operee sur
les sommes que les personnes physiques ou morales non residentes au
Burkina Faso percoivent en remuneration de prestations de toute nature
fournies ou utilisees au Burkina Faso.

Art.211.- La retenue a la source s'applique aux remunerations payees
notamment :
- pour la fourniture d'etudes et de conseils de toute nature, de
  prestations d'ingenieries, d'informatique, de comptabilite, d'audit,
  de publicite, de formation, de communication, d'assistance technique ;
- pour la participation aux frais de siege ;
- pour l'usage ou la concession de l'usage d'un brevet, d'une marque de
  fabrique de commerce, d'une franchise commerciale, d'un dessin, d'un
  modele, d'un plan, d'une formule ou d'un procede secret ainsi que d'un
  equipement industriel, commercial ou scientifique ne constituant pas un
  bien immobilier ;
- pour les informations ayant trait a une experience acquise dans le
  domaine industriel, commercial, agricole ou scientifique ;
- pour l'usage ou la concession de l'usage d'un droit d'auteur sur une
  oeuvre litteraire, artistique ou scientifique y compris les productions
  cinematographiques, televisuelles, audiovisuelles, radiophoniques,
  theatrales et artistiques ;
- aux artistes de theatre et de music-hall, musiciens-danseurs, acteurs,
  comediens, modeles et autres artistes de spectacles et de la mode et
  aux sportifs, non domicilies au Burkina Faso, qui participent a des
  manifestations organisees ou produites au Burkina Faso.
```

### Taux, redevables et modalites

- `block_reference`: `articles 212 a 214`
- `block_type`: `article`
- `theme`: `taux`

```text
Art.212.- Le taux de la retenue a la source est fixe a 20 % du montant net
des sommes versees aux personnes non etablies au Burkina Faso, y compris
les sommes et frais accessoires exposes par le debiteur au profit du
prestataire.
Le montant de la retenue ne saurait etre pris en charge par le debiteur.

Art.213.- Sont redevables de la retenue a la source de 20 % :
- les personnes physiques ou morales relevant d'un impot sur les
  benefices selon un regime du reel ;
- l'Etat, les collectivites territoriales et les etablissements publics ;
- les projets et programmes ;
- les organisations non gouvernementales, les associations et les
  fondations.

Art.214.- Les retenues afferentes aux sommes mises en paiement au cours
d'un mois donne doivent etre versees au plus tard le 20 du mois suivant au
service des impots de rattachement.

Les versements sont effectues au vu d'une declaration reglementaire
comportant pour chaque personne faisant l'objet d'une retenue, les
indications suivantes :
- nom(s) et prenom(s) ou raison sociale et forme juridique ;
- activite ou profession ;
- adresses geographique, boite postale et numero de telephone ;
- nationalite ;
- nature des prestations fournies ;
- date et montant des paiements ;
- montant de la retenue operee.

La declaration doit etre accompagnee pour chaque prestataire precompte
d'une attestation individuelle de retenue a la source etablie conformement
au modele prescrit par l'administration.
```

### Residence fiscale

- `block_reference`: `article 107, paragraphe 2`
- `block_type`: `article`
- `theme`: `residence fiscale`

```text
Sous reserve des dispositions des conventions internationales relatives
aux doubles impositions, sont considerees comme ayant leur domicile
fiscal au Burkina Faso :
- 1° les personnes qui y possedent ou y jouissent d'un foyer d'habitation
  permanent ;
- 2° les personnes qui, sans disposer au Burkina Faso d'un foyer
  d'habitation permanent dans les conditions definies au point 1°, ont
  neanmoins au Burkina Faso le centre de leurs interets vitaux ;
- 3° dans le cas ou les personnes n'ont pas de foyer d'habitation
  permanent au Burkina Faso ou si le centre de leurs interets vitaux ne
  peut pas etre determine, elles sont considerees comme ayant leur
  domicile au Burkina Faso si elles y sejournent de facon habituelle
  pendant au moins cent quatre-vingt-trois (183) jours de facon continue
  ou non sur une periode de douze (12) mois.
```

## Notes

- Extrait de l'article 107 (personnes imposables a l'impot unique sur les
  traitements et salaires), reutilise ici car c'est la ou le CGI definit
  les criteres generaux du domicile/residence fiscale; il n'existe pas
  d'article distinct intitule « residence fiscale » dans le texte source.
- Statut `validated` obtenu par auto-validation du porteur du projet, pas
  par une revue d'expert-comptable ou fiscaliste. A faire relire des que
  possible; voir `docs/open-questions.md`.
