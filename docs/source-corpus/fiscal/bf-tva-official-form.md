# BF - Imprime officiel TVA

## Metadonnees

- `domain`: `fiscal`
- `country`: `BF`
- `source_type`: `official_form`
- `title`: `Declaration de la taxe sur la valeur ajoutee - DGI Burkina Faso`
- `version`: `Fichier DGI publie sous le chemin 2023/10`
- `applicable_from`: ``
- `applicable_to`: ``
- `applicability_status`: `not_stated`
- `source_url`: `https://dgi.bf/wp-content/uploads/2023/10/DECLARATION-DE-LA-TAXE-SUR-LA-VALEUR-AJOUTEE.pdf`
- `language`: `fr`
- `origin`: `anonymized_reference`
- `themes`: `TVA; formulaire; lignes de declaration; credit TVA`
- `validation_status`: `validated`
- `validated_by`: `Audrey Ouedraogo (auto-validation, sans relecture fiscale externe)`
- `validated_at`: `2026-08-03`

## Source

Structure transcrite depuis l'imprime PDF publie sur la page officielle des
imprimes de la DGI. La date d'applicabilite n'est pas indiquee par le document
et reste donc non resolue.

## Blocs

### Chiffre d'affaires global hors TVA

- `block_reference`: `lignes 01 a 14`
- `block_type`: `section`
- `theme`: `operations TVA`

```text
Les lignes 01 a 13 ventilent les operations taxables, les marches et contrats,
les exportations et les autres operations non taxables. La ligne 14 porte le
montant total des operations, calcule comme la somme des lignes 01 a 13.
```

### TVA brute

- `block_reference`: `lignes 15 a 19`
- `block_type`: `section`
- `theme`: `TVA brute`

```text
La ligne 15 concerne les operations au taux normal de 18 %, la ligne 16 les
operations au taux reduit de 10 %, les lignes 17 et 18 les reversions, et la
ligne 19 le montant total de TVA brute obtenu par somme des lignes 15 a 18.
```

### TVA nette et credit

- `block_reference`: `lignes 20 a 27 et synthese`
- `block_type`: `section`
- `theme`: `TVA nette et credit a reporter`

```text
Les lignes 20 a 27 recensent la TVA deductible, le credit precedent, les
credits demandes ou non demandes en remboursement et les autres deductions.
L'imprime calcule ensuite soit la TVA nette a payer, soit le credit de TVA a
reporter, a partir de la TVA brute et des deductions admises.
```
