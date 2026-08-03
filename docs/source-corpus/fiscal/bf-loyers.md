# BF - Loyers et Charges Immobilieres

## Metadonnees

- `domain`: `fiscal`
- `country`: `BF`
- `source_type`: `tax_code`
- `title`: `Code General des Impots du Burkina Faso - Impot sur les revenus fonciers (articles 120 a 128) et retenue a la source sur les loyers (articles 215 a 219)`
- `version`: `Texte consolide dgi.bf (loi adoptee le 20 decembre 2017, fichier LOI-PORTANT-CODE-GENERAL-DES-IMPOTS-FINAL.pdf) - A CONFIRMER par rapprochement avec la derniere loi de finances en vigueur`
- `applicable_from`: `2018-01-01`
- `applicable_to`: ``
- `applicability_status`: `confirmed`
- `source_url`: `https://dgi.bf/wp-content/uploads/2023/10/LOI-PORTANT-CODE-GENERAL-DES-IMPOTS-FINAL.pdf`
- `language`: `fr`
- `origin`: `anonymized_reference`
- `themes`: `loyers; location immobiliere; charges immobilieres; bail; IRF`
- `validation_status`: `validated`
- `validated_by`: `Audrey Ouedraogo (auto-validation, sans relecture fiscale externe)`
- `validated_at`: `2026-08-03`

## Source

Extrait litteral du Code General des Impots du Burkina Faso, Livre 1,
Titre 1, Chapitre 5 (Impot sur les revenus fonciers - IRF), articles 120 a
128, et Chapitre 8, Section 4 (Retenue a la source de l'impot sur les
revenus fonciers), articles 215 a 219.

Fichier source: `https://dgi.bf/wp-content/uploads/2023/10/LOI-PORTANT-CODE-GENERAL-DES-IMPOTS-FINAL.pdf`
(pages 34-36 et 58 du PDF).

Prepare par extraction directe du texte du PDF officiel (lecture page par
page, pas de resume ni de reformulation). Auto-valide par le porteur du
projet (voir `validated_by`) pour debloquer l'indexation, mais **pas
relu par un expert-comptable ou fiscaliste**: une relecture professionnelle
reste a faire des que possible et pourrait modifier ce contenu.

## Blocs

### Loyers - champ d'application et exonerations

- `block_reference`: `articles 120 a 123`
- `block_type`: `article`
- `theme`: `loyers`

```text
Art.120.- L'impot sur les revenus fonciers (IRF), percu au profit du
budget de l'Etat, est applicable aux revenus de la location des immeubles
batis ou non batis quel que soit leur usage, ainsi que les revenus
accessoires.
Sont egalement soumis a l'impot, les gains resultant des sous-locations
d'immeubles batis ou non batis et des baux a construction.

Art.121.- L'impot est du par les personnes beneficiaires de revenus
fonciers.
Sont compris dans la categorie des revenus fonciers :
- 1° les revenus des proprietes baties telles que les maisons et usines
  ainsi que ceux provenant de l'outillage des etablissements industriels
  attaches au fonds a perpetuelle demeure, ou reposant sur des fondations
  speciales faisant corps avec l'ensemble, et de toutes installations
  commerciales ou industrielles assimilables a des constructions ;
- 2° la location du droit d'affichage, de la concession du droit
  d'exploitation des carrieres, de redevances analogues ayant leur
  origine dans le droit de propriete ou d'usufruit ;
- 3° les revenus des proprietes non baties de toute nature y compris ceux
  des terrains occupes par des carrieres et mines.

Art.122.- Ne sont pas soumis a l'impot sur les revenus fonciers :
1) Les loyers de toute nature d'immeubles appartenant a des personnes
   morales soumises a l'impot sur les societes.
2) Les loyers de toute nature d'immeubles appartenant a l'Etat, aux
   collectivites territoriales et a leurs etablissements publics n'ayant
   pas un caractere industriel et commercial.
3) Les loyers des chambres d'hotel et d'etablissements assimiles.
4) Les loyers dont le cumul par bailleur n'excede pas vingt mille
   (20 000) francs CFA par mois.
5) Les personnes salariees retraitees des secteurs public et prive et les
   conjoints survivants de retraites dans la limite d'un seul immeuble,
   sous reserve que le bail ou le cumul des baux sur l'immeuble loue
   n'excede pas cinq cent mille (500 000) francs CFA et que ledit
   immeuble ait ete acquis ou construit pendant la periode d'activite.
   Le choix de l'immeuble objet du bail ou des baux exoneres est
   definitif. Lorsque le bail ou le cumul des baux depasse cinq cent
   mille (500 000) francs CFA, le supplement de loyer est soumis a
   l'impot sur les revenus fonciers aux conditions de droit commun.
   Pour le benefice effectif de cette mesure, les interesses doivent
   adresser au directeur general des impots une demande comprenant les
   pieces justificatives de leur statut ainsi que tout document attestant
   de l'acquisition ou de la construction de l'immeuble pendant la
   periode d'activite et une copie du contrat de bail dument enregistre
   ou de la quittance de renouvellement du bail. Le benefice de
   l'exoneration constate par decision du directeur general des impots
   prend effet a compter de la date d'introduction de la demande.
6) Les entreprises publiques ou privees ayant pour principal objet la
   promotion de l'habitat social peuvent beneficier de l'exoneration de
   l'impot sur les revenus fonciers par decret pris en Conseil des
   Ministres sur proposition du Ministre charge des Finances apres avis
   du Ministre charge de l'Habitat.

Art.123.- Sauf dispositions expresses contraires, l'impot sur les revenus
fonciers s'applique :
- aux revenus des immeubles situes au Burkina Faso ;
- aux revenus des immeubles situes a l'etranger lorsque le bailleur
  reside au Burkina Faso ou y exerce ses activites, sous reserve des
  conventions internationales relatives aux doubles impositions.
```

### Base imposable et taux IRF

- `block_reference`: `articles 125 et 126`
- `block_type`: `article`
- `theme`: `loyers`

```text
Art.125.- 1) Le revenu net imposable est egal au loyer brut, taxe sur la
valeur ajoutee non comprise, acquis par le bailleur au cours du mois ou
de la periode consideree et au titre de chaque location, sous deduction
d'un abattement forfaitaire de 50 %.

2) Le loyer brut comprend les produits de toute nature provenant de la
location ou de la sous-location d'immeubles, notamment :
- les loyers ;
- les depenses incombant normalement au bailleur, mises
  contractuellement a la charge du locataire ;
- la valeur mensuelle de l'amortissement des investissements realises par
  le preneur calcule selon la duree du contrat, majoree des indemnites,
  avantages ou prestations de toute nature servis au bailleur en
  execution d'un bail a construction ;
- les supplements de loyers et autres revenus exceptionnels ;
- les sommes recues des locataires a titre de depot de garantie, des lors
  qu'elles sont utilisees par le bailleur pour couvrir des loyers.

Art.126.- Le montant de l'impot sur les revenus fonciers est obtenu par
application des taux progressifs par tranches ci-apres au revenu net
imposable :
- tranche de 0 a 100 000 francs CFA : 18 % ;
- au-dessus de 100 000 francs CFA : 25 %.
```

### Bail et justificatifs - retenue a la source sur les loyers

- `block_reference`: `articles 215 a 219`
- `block_type`: `article`
- `theme`: `bail`

```text
Art.215.- Sont soumis a une retenue a la source, les loyers des immeubles
batis ou non batis pris a bail par les locataires suivants etablis au
Burkina Faso :
- les personnes physiques ou morales relevant du regime reel
  d'imposition ;
- l'Etat, les collectivites territoriales et les etablissements publics ;
- les associations, les fondations, les organisations non
  gouvernementales, les projets et programmes ;
- les representations diplomatiques et consulaires ainsi que les
  organismes internationaux et assimiles.

Art.216.- Le montant de la retenue est egal au montant de l'impot sur les
revenus fonciers du sur le loyer.
L'impot est calcule conformement aux dispositions des articles 125 et
126.

Art.217.- Les retenues d'un mois determine doivent etre reversees au
service des impots au plus tard le 10 du mois suivant sur un formulaire
conforme au modele de l'administration fiscale.
Toutefois, lorsque la periodicite du reglement est superieure a un mois,
les retenues doivent etre versees au plus tard le 10 du mois suivant la
periode ecoulee.

Art.218.- Les locataires sont tenus de remettre a leur bailleur un etat
des versements effectues au service des impots. L'etat des versements
doit etre vise par le receveur des impots competent et comporter les
references de la quittance de reglement.
Cet etat doit contenir les indications suivantes :
- nom, prenoms, profession, domicile, adresse complete et numero
  d'identification financier unique (IFU) le cas echeant du locataire ;
- nom, prenoms, profession, domicile, adresse complete et eventuellement
  numero d'identification financier unique (IFU) du bailleur ;
- montant des sommes versees au bailleur ;
- montant brut du loyer ;
- periode au titre de laquelle les versements ont ete effectues ;
- montant de l'impot retenu a la source.

Art.219.- Tout bailleur d'immeuble soumis a la retenue a la source sur les
loyers est tenu de souscrire au plus tard le 15 fevrier et le 15 aout de
chaque annee aupres du service des impots du lieu de situation de
l'immeuble loue, sur un formulaire conforme au modele de l'administration
fiscale, une declaration indiquant le montant des loyers percus et
l'impot sur les revenus fonciers acquitte sur lesdits loyers.
```

## Notes

- Statut `validated` obtenu par auto-validation du porteur du projet, pas
  par une revue d'expert-comptable ou fiscaliste. A faire relire des que
  possible; voir `docs/open-questions.md`.
