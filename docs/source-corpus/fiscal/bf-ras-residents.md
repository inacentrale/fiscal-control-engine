# BF - RAS Residents

## Metadonnees

- `domain`: `fiscal`
- `country`: `BF`
- `source_type`: `tax_code`
- `title`: `Code General des Impots du Burkina Faso - Section 2 (Retenue a la source sur les sommes versees aux prestataires residents), articles 206 a 209`
- `version`: `Texte consolide dgi.bf (loi adoptee le 20 decembre 2017, fichier LOI-PORTANT-CODE-GENERAL-DES-IMPOTS-FINAL.pdf) - A CONFIRMER par rapprochement avec la derniere loi de finances en vigueur, le taux de l'article 207 pouvant etre revu chaque annee (voir docs/reference/bf-withholding-validation-rules.csv)`
- `applicable_from`: `2018-01-01`
- `applicable_to`: ``
- `applicability_status`: `confirmed`
- `source_url`: `https://dgi.bf/wp-content/uploads/2023/10/LOI-PORTANT-CODE-GENERAL-DES-IMPOTS-FINAL.pdf`
- `language`: `fr`
- `origin`: `anonymized_reference`
- `themes`: `prestataire resident; honoraires; commissions; IFU`
- `validation_status`: `validated`
- `validated_by`: `Audrey Ouedraogo (auto-validation, sans relecture fiscale externe)`
- `validated_at`: `2026-08-03`

## Source

Extrait litteral du Code General des Impots du Burkina Faso, Livre 1, Titre 1,
Chapitre 8 (Prelevement et retenues a la source a titre d'acompte sur les
impots sur les benefices), Section 2, articles 206 a 209.

Fichier source: `https://dgi.bf/wp-content/uploads/2023/10/LOI-PORTANT-CODE-GENERAL-DES-IMPOTS-FINAL.pdf`
(pages 55-56 du PDF).

Prepare par extraction directe du texte du PDF officiel (lecture page par
page, pas de resume ni de reformulation). Auto-valide par le porteur du
projet (voir `validated_by`) pour debloquer l'indexation, mais **pas
relu par un expert-comptable ou fiscaliste**: une relecture professionnelle
reste a faire des que possible et pourrait modifier ce contenu. Le taux
cite a l'article 207 correspond a celui deja retenu dans
`docs/reference/bf-withholding-validation-rules.csv` (regime `resident`),
mais ce dernier reste la source de verite pour le calcul déterministe; ce
document sert uniquement de justification/explication citable.

## Blocs

### Champ d'application - prestataires residents

- `block_reference`: `article 206`
- `block_type`: `article`
- `theme`: `prestataire resident`

```text
Art.206.- 1) Sont soumises a une retenue a la source les sommes versees en
remuneration de prestations de toute nature fournies ou utilisees sur le
territoire national, par des debiteurs etablis au Burkina Faso :
- a des personnes qui y resident ;
- ou a des personnes non residentes dans la mesure ou elles y disposent
  d'un etablissement stable tel que defini a l'article 47.

2) Sont notamment consideres comme debiteurs etablis au Burkina Faso :
- les personnes physiques ou morales relevant de l'impot sur les societes,
  de l'impot sur les benefices industriels, commerciaux et agricoles ou de
  l'impot sur les benefices des professions non commerciales, selon le
  regime du reel d'imposition ;
- l'Etat, les collectivites territoriales et les etablissements publics ;
- les projets et programmes ;
- les organisations non gouvernementales, les associations et les
  fondations.

3) Par prestation de toute nature fournie ou utilisee, on entend toute
operation de nature lucrative autre qu'une vente de biens ou une location
d'immeubles dont le montant est egal ou superieur a cinquante mille
(50 000) francs CFA hors taxes.

4) La retenue n'est pas due sur les sommes versees aux contribuables
relevant de la direction des grandes entreprises et a ceux beneficiant
d'une exoneration totale des impots sur les benefices. Pour beneficier de
cette exoneration, les contribuables doivent presenter leur attestation
d'exoneration delivree par la direction generale des impots.
```

### Taux de la retenue

- `block_reference`: `article 207`
- `block_type`: `article`
- `theme`: `taux`

```text
Art.207.- Le taux de la retenue est fixe a :
- 5 % du montant hors taxes des sommes versees pour les personnes
  justifiant d'une immatriculation a l'identifiant financier unique (IFU).
  Ce taux est reduit a 1 % pour les travaux immobiliers et les travaux
  publics ;
- 25 % du montant des sommes versees pour les personnes non salariees ne
  justifiant pas d'une immatriculation a l'identifiant financier unique
  (IFU).
```

### Modalites de versement, attestation et imputation

- `block_reference`: `articles 208 et 209`
- `block_type`: `article`
- `theme`: `modalites`

```text
Art.208.- 1) Les retenues afferentes aux paiements effectues au cours d'un
mois determine doivent etre versees au plus tard le 20 du mois suivant
aupres du service des impots du lieu du siege social ou du principal
etablissement ou du domicile de la partie versante.

2) Les versements sont effectues au vu d'une declaration reglementaire
comportant pour chaque prestataire faisant l'objet d'une retenue les
indications suivantes :
- nom et prenom(s) ou raison sociale et forme juridique du prestataire ;
- profession ou activite ;
- numero d'identification financier unique (IFU) ;
- adresses geographique et postale ;
- date et montant de la facture ;
- date et montant des paiements ;
- retenue operee.

3) La declaration doit etre accompagnee, pour chaque prestataire
precompte, d'une attestation individuelle de retenue a la source etablie
conformement au modele prescrit par l'administration.

Art.209.- 1) Les retenues supportees au cours d'un exercice donne sont
imputables sur les cotisations du minimum forfaitaire de perception ou sur
les acomptes provisionnels exigibles au titre du meme exercice.

2) Si le montant des retenues excede celui du minimum forfaitaire de
perception ou des acomptes provisionnels, l'excedent est impute sur la ou
les cotisations ulterieures d'impot sur les societes, d'impot sur les
benefices industriels, commerciaux et agricoles ou d'impot sur les
benefices des professions non commerciales.

3) Les credits de retenues residuels sont imputables exclusivement sur les
cotisations de l'impot sur les societes, de l'impot sur les benefices
industriels, commerciaux et agricoles ou de l'impot sur les benefices des
professions non commerciales dues au titre de l'exercice au cours duquel
les prelevements ont ete supportes et des exercices suivants.
```

## Notes

- Le squelette d'origine prevoyait deux blocs distincts « Honoraires
  Residents » et « Commissions Residents ». Le texte du CGI ne fait pas
  cette distinction: l'article 206 vise uniformement « les prestations de
  toute nature », qui couvre honoraires, commissions et autres prestations
  de services. Les blocs ci-dessus suivent donc la structure reelle des
  articles plutot qu'une distinction qui n'existe pas dans la loi.
- Statut `validated` obtenu par auto-validation du porteur du projet, pas
  par une revue d'expert-comptable ou fiscaliste. A faire relire des que
  possible; voir `docs/open-questions.md`.
