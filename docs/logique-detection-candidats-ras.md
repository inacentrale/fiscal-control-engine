# Logique de détection des candidats à la RAS

## 1. Objet du document

Ce document explique comment la solution identifie, dans un Grand Livre (GL),
les opérations qui doivent être examinées au titre de la retenue à la source
(RAS). Il présente également la valeur ajoutée du produit, ses limites actuelles
et les améliorations recommandées.

Il est destiné aux responsables financiers, fiscalistes, auditeurs, équipes
comptables et équipes techniques.

> Une opération détectée est un **candidat à vérifier**. La détection ne signifie
> ni que l'opération est définitivement soumise à la RAS, ni qu'une RAS a été
> omise.

## 2. Principe général

La solution fonctionne comme un outil de présélection et d'aide à la revue. Elle
réduit un GL potentiellement volumineux à une population de pièces présentant un
ou plusieurs indices pertinents.

La démarche comporte quatre niveaux distincts :

1. normaliser et contrôler les données du GL ;
2. détecter les pièces candidates ;
3. rechercher une RAS comptabilisée ou une écriture potentiellement liée ;
4. évaluer fiscalement le candidat seulement si les faits et la règle juridique
   applicable sont suffisamment établis.

Le moteur déterministe conserve la décision. Le LLM sert à comprendre la demande
de l'utilisateur et à expliquer les résultats ; il ne choisit ni le taux, ni la
règle fiscale, ni le montant de RAS.

## 3. Données utilisées

### 3.1 Données comptables principales

Selon leur disponibilité dans le fichier, le moteur exploite notamment :

- la référence réelle de la pièce ;
- le numéro de compte ;
- le libellé de l'écriture ;
- la date comptable ou la date de pièce ;
- l'exercice et la période ;
- le journal ou le type de pièce ;
- la clé de comptabilisation et le sens débit/crédit ;
- le montant et la devise ;
- le fournisseur, le client ou le tiers ;
- le code société ;
- les lignes appartenant à la même pièce.

Toutes ces informations ne sont pas toujours présentes. Leur absence réduit le
niveau de certitude et peut rendre certaines vérifications indéterminables.

### 3.2 Cartographie des comptes

Les comptes sont comparés à une cartographie versionnée et propre à
l'organisation. Elle distingue au minimum :

- les comptes de charges susceptibles de contenir des opérations soumises à la
  RAS ;
- les comptes de RAS à payer utilisés pour rechercher la retenue comptabilisée.

Dans la configuration organisationnelle actuelle, les comptes de charges activés
sont `51201000`, `61312000`, `61361600` et `61365000`. Les comptes de RAS activés
sont `44531001`, `44531002` et `44585100`. Cette liste correspond au référentiel
actuel du projet et ne doit pas être considérée comme universelle.

### 3.3 Signaux textuels et sémantiques

Les libellés sont comparés à une taxonomie versionnée contenant des expressions
positives, des exclusions et des natures d'opérations possibles, par exemple les
loyers, honoraires, commissions ou prestations.

Un classificateur sémantique peut compléter la recherche littérale pour reconnaître
des formulations proches. Il reste une aide au classement : une similarité ou un
« signal sémantique fort » n'est pas une preuve fiscale.

## 4. Déroulement détaillé de la détection

### Étape 1 — Normalisation du Grand Livre

Le fichier est lu et ses colonnes sont rapprochées du schéma comptable canonique.
Les montants, dates, devises, comptes, clés de comptabilisation, références et
tiers sont normalisés sans perdre leur provenance.

Les lignes illisibles, valeurs incohérentes ou colonnes absentes sont recensées.
La solution évalue ensuite les contrôles qu'elle peut réellement effectuer.

### Étape 2 — Reconstruction des pièces

Les lignes sont regroupées en écritures comptables. La référence de pièce est le
premier lien lorsqu'elle est exploitable, complétée par les informations de
contexte disponibles.

Cette reconstruction évite de considérer séparément plusieurs lignes appartenant
à la même opération et limite les doubles comptages.

### Étape 3 — Recherche d'un indice comptable

Pour chaque ligne, le moteur vérifie si le compte correspond à un compte de
charge candidat applicable à la société et à la date analysées.

Le sens comptable est contrôlé à partir de la clé de comptabilisation :

- un mouvement dans le sens normal du compte constitue un indice comptable ;
- une clé inconnue conserve le cas comme indéterminé ;
- un mouvement uniquement au crédit d'un compte de charge est traité comme un
  avoir ou une extourne, et non comme une nouvelle charge candidate ;
- lorsqu'une pièce comporte charge et extourne, les montants sont compensés par
  devise.

### Étape 4 — Recherche d'un indice textuel

Le moteur analyse les libellés des lignes de la pièce :

- une expression positive produit un indice textuel ;
- une expression d'exclusion peut écarter un cas reposant uniquement sur le
  texte ;
- une exclusion textuelle n'annule pas un indice comptable provenant d'un compte
  explicitement configuré ;
- un rapprochement sémantique ambigu conserve le cas à vérifier au lieu de
  produire une conclusion arbitraire.

### Étape 5 — Classement du candidat

| Indices observés | Classement | Interprétation métier |
| --- | --- | --- |
| Compte et libellé | Détecté par le compte et le libellé | Candidat renforcé par deux indices indépendants |
| Compte uniquement | Détecté par le compte | Nature réelle de l'opération à confirmer |
| Libellé uniquement | Détecté par le libellé | Compte non cartographié ou opération à vérifier manuellement |
| Clé ou sémantique ambiguë | Données insuffisantes | Candidat conservé, mais qualification impossible |
| Aucun indice ou exclusion textuelle seule | Non retenu | Pièce absente de la population de revue |

Les éléments présentés au financier doivent permettre de retrouver le candidat :
référence réelle, date, compte, libellé, montant, devise et motif de détection.

### Étape 6 — Recherche de la RAS comptabilisée

La recherche de contrepartie intervient après la détection :

1. le moteur recherche d'abord une ligne utilisant un compte de RAS configuré
   dans la même écriture ;
2. à défaut, il recherche une écriture potentiellement liée sur la même société,
   le même exercice, le même tiers et la même devise, dans une fenêtre actuelle
   de 31 jours autour de la date ;
3. une correspondance trouvée dans une autre pièce reste **probable à confirmer** ;
4. une correspondance dans une autre devise n'est jamais rapprochée
   automatiquement ;
5. l'absence ne devient « RAS non retrouvée dans le GL analysé » que si la
   couverture technique du fichier et la cartographie des comptes sont jugées
   suffisantes ; sinon le résultat reste indéterminé.

Les références SAP générées indépendamment peuvent empêcher un rapprochement par
numéro de pièce. La recherche secondaire par société, exercice, tiers, devise et
proximité de date limite ce problème, mais ne prouve pas à elle seule qu'il s'agit
de la même opération.

### Étape 7 — Évaluation fiscale séparée

La détection comptable ne suffit pas pour calculer une RAS théorique. Il faut
notamment établir, selon la catégorie concernée :

- la nature exacte de l'opération ;
- la résidence et la qualité du bénéficiaire ;
- la présence d'un IFU lorsque ce fait est juridiquement pertinent ;
- la territorialité ;
- le fait générateur et sa date ;
- l'assiette fiscale ;
- une éventuelle exemption ;
- la règle en vigueur à la date concernée.

Si un fait obligatoire manque, le moteur ne fabrique ni taux ni montant. Le cas
reste « applicabilité probable à confirmer » ou « données manquantes ».

## 5. Exemple simplifié

Une pièce contient une charge débitée sur le compte `61365000`, avec le libellé
« honoraires cabinet », pour 1 000 000 XOF.

- Le compte appartient à la cartographie des charges candidates.
- Le libellé correspond à un signal lié aux honoraires.
- La pièce est donc classée « détectée par le compte et le libellé ».
- Le moteur recherche ensuite une ligne sur un compte de RAS configuré dans la
  même pièce.
- S'il trouve une telle ligne, il restitue la RAS comptabilisée sans encore
  affirmer que son montant est fiscalement correct.
- Pour comparer la retenue comptabilisée à la retenue théorique, le moteur doit
  encore disposer des faits juridiques nécessaires et résoudre la règle
  applicable à la date du fait générateur.

## 6. Valeur ajoutée de la solution

### Pour le responsable financier

- Réduire plusieurs milliers d'écritures à une liste ciblée et actionnable.
- Retrouver chaque pièce grâce à sa référence réelle et aux informations
  comptables utiles.
- Prioriser la revue selon la force des indices et les informations manquantes.
- Repérer les comptes ou libellés inhabituels qui échapperaient à un contrôle
  limité aux seuls numéros de comptes.
- Identifier une RAS présente dans la pièce, une contrepartie potentielle ou un
  dossier nécessitant une recherche complémentaire.

### Pour l'audit et la conformité

- Appliquer la même logique de contrôle à l'ensemble du fichier.
- Conserver les versions de cartographies, règles et preuves utilisées.
- Rendre le résultat explicable : motif, montant, preuve et information à
  vérifier.
- Distinguer une anomalie constatée d'une simple suspicion.
- Éviter qu'un LLM invente une règle, un taux ou une conclusion fiscale.

### Pour l'organisation

- Capitaliser progressivement la connaissance du plan comptable et des pratiques
  de comptabilisation internes.
- Réduire le temps consacré aux recherches manuelles répétitives.
- Faciliter le dialogue entre comptabilité, fiscalité, contrôle interne et audit.
- Préparer une piste de revue reproductible sans remplacer la validation humaine.

## 7. Limites actuelles

### 7.1 Limites liées aux données du GL

- La société, le tiers, la date, la clé de comptabilisation ou la devise peuvent
  être absents ou mal renseignés.
- Le type de pièce et la date de pièce ne sont parfois que des substituts du
  journal et de la date comptable.
- Le numéro de pièce peut être unique à chaque écriture SAP et ne pas relier la
  charge à une régularisation ultérieure.
- Un extrait de GL ne garantit pas que toutes les périodes, sociétés ou écritures
  nécessaires ont été fournies.
- Une colonne de rapprochement vide ne peut pas servir de preuve de lien.

### 7.2 Limites de la cartographie comptable

- Le référentiel actuel est adapté au plan et au GL étudiés ; il n'est pas
  exhaustif pour toutes les organisations.
- Un compte non cartographié peut générer un faux négatif.
- Un compte regroupant plusieurs natures peut générer des faux positifs.
- Toute modification du plan comptable nécessite une revue et une nouvelle
  version du mapping.

### 7.3 Limites de l'analyse des libellés

- Les libellés courts, génériques, fautifs ou internes sont difficiles à
  interpréter.
- Un mot pertinent peut apparaître dans une opération finalement hors périmètre.
- Le classificateur sémantique doit encore être calibré et validé par des
  professionnels sur un jeu d'or représentatif.
- Le volume de « signaux sémantiques à confirmer » n'est utile que si chaque
  pièce correspondante est consultable avec sa preuve.

### 7.4 Limites du rapprochement des contreparties

- Une contrepartie dans la même pièce est la preuve comptable la plus forte, mais
  les pratiques SAP peuvent enregistrer la retenue dans une autre pièce.
- La correspondance secondaire par tiers, date et montant est probabiliste.
- Le tiers peut manquer, varier entre écritures ou être partagé par plusieurs
  opérations proches.
- Une fenêtre fixe de 31 jours peut manquer une régularisation tardive ou relier
  deux opérations différentes.
- Aucun rapprochement automatique inter-devise n'est réalisé.

### 7.5 Limites fiscales et juridiques

- Un GL seul ne contient généralement pas la résidence, l'IFU, le contrat,
  l'exemption, la territorialité ou le fait générateur attesté.
- Les textes fiscaux évoluent ; la matrice juridique et le corpus RAG doivent être
  maintenus, validés et datés.
- La validation exhaustive de la matrice RAS 2026 et de certaines catégories
  reste à finaliser.
- L'absence de ligne RAS dans le GL ne prouve ni une omission déclarative, ni une
  dette fiscale.

### 7.6 Limites opérationnelles actuelles

- La performance doit encore être mesurée et encadrée sur de très grands GL.
- La lisibilité du rapport doit être validée par un responsable financier et un
  fiscaliste ou expert-comptable.
- Les taux de précision et de rappel doivent être mesurés sur des données métier
  annotées, et pas uniquement sur des scénarios techniques.

## 8. Recommandations et améliorations

### Priorité 1 — Fiabiliser la population détectée

1. Faire annoter par un financier et un fiscaliste un jeu d'or représentatif :
   candidat, non-candidat, motif, nature et contrepartie réelle.
2. Mesurer par catégorie la précision, le rappel, les faux positifs et les faux
   négatifs.
3. Revoir et versionner la cartographie des comptes pour chaque société, période
   et évolution du plan comptable.
4. Afficher systématiquement les pièces détectées avec référence réelle, date,
   compte, libellé, montant, motif, preuve et contrôle demandé.
5. Remplacer l'expression isolée « signal sémantique fort » par une formulation
   métier et la liste des pièces concernées.

### Priorité 2 — Améliorer le rapprochement comptable

1. Construire un score explicable de correspondance entre pièces en combinant :
   société, exercice, tiers, devise, date, montant, compte, journal, texte et
   référence de paiement ou de rapprochement lorsqu'elle existe.
2. Définir des niveaux distincts : correspondance certaine, probable, faible et
   absence de correspondance exploitable.
3. Afficher les critères qui ont produit le score et laisser le financier
   confirmer ou rejeter la proposition.
4. Apprendre des validations humaines uniquement après gouvernance et
   versionnement, sans transformer automatiquement une corrélation en règle
   fiscale.
5. Rendre la fenêtre temporelle configurable selon le processus comptable de
   l'organisation.

### Priorité 3 — Enrichir les faits nécessaires

1. Permettre au financier de compléter, pour une pièce sélectionnée, les faits
   manquants avec leur provenance : facture, contrat, fiche fournisseur ou preuve
   de paiement.
2. Ajouter un référentiel fournisseur validé contenant les seuls attributs
   nécessaires, notamment résidence et statut IFU, avec contrôle d'accès et
   traçabilité.
3. Connecter ultérieurement les factures, paiements et données fournisseurs sans
   mélanger une donnée proposée et une donnée attestée.
4. Conserver chaque enrichissement dans une nouvelle version immuable de l'audit.

### Priorité 4 — Maintenir le droit fiscal à jour

1. Mettre en place un import administrateur de PDF et d'URL officielles.
2. Archiver la source originale, son empreinte, sa date d'application et son
   statut de validation.
3. Comparer une nouvelle loi de finances aux règles actives sans l'activer
   automatiquement.
4. Exiger une validation humaine avant indexation dans le RAG et publication dans
   le moteur déterministe.
5. Tester la sélection des règles pour chaque exercice, ainsi que les cas de
   contradiction, remplacement ou absence de source.

### Priorité 5 — Valider l'usage et l'industrialisation

1. Faire une recette du rapport avec des utilisateurs finance et fiscalité.
2. Définir des seuils d'acceptation métier avant mise en production.
3. Tester les performances, la reprise après erreur et la reproductibilité sur
   des GL de tailles réalistes.
4. Mettre en place des indicateurs de suivi : dossiers détectés, confirmés,
   rejetés, indéterminés, temps de revue et causes principales de blocage.
5. Maintenir la séparation entre détection, preuve comptable, calcul fiscal et
   décision humaine.

## 9. Démarche recommandée au financier

Pour chaque candidat présenté :

1. retrouver la référence réelle dans le GL ou SAP ;
2. vérifier la nature de la charge à partir du libellé, de la facture et du
   contrat ;
3. vérifier le compte, le tiers, la date, le montant et la devise ;
4. rechercher la ligne RAS dans la même pièce ;
5. examiner les écritures proposées comme potentiellement liées ;
6. confirmer le fait générateur et les faits juridiques requis ;
7. comparer, seulement après résolution de la règle, la RAS théorique à la RAS
   comptabilisée ;
8. documenter la conclusion et la preuve utilisée.

## 10. Conclusion

La valeur principale de la solution n'est pas de remplacer le fiscaliste. Elle
consiste à rendre la revue du Grand Livre plus exhaustive, plus rapide, plus
homogène et plus explicable.

La détection actuelle constitue une base fonctionnelle solide pour présélectionner
les pièces. Pour atteindre un niveau de confiance opérationnel élevé, les travaux
les plus importants sont la calibration sur un jeu d'or métier, l'enrichissement
de la cartographie organisationnelle, le scoring explicable des rapprochements,
la maintenance juridique versionnée et la validation du rapport par ses futurs
utilisateurs.

## 11. Références internes au projet

- `api/app/ras_audit/candidate_detection.py` : règles de détection des candidats ;
- `api/app/ras_audit/counterpart.py` : recherche des contreparties comptables ;
- `docs/reference/ras-ledger-account-mapping.organization.csv` : cartographie
  organisationnelle actuelle ;
- `docs/FEATURES.md` : architecture fonctionnelle de l'audit RAS ;
- `api/todo.md` : travaux restants et validations attendues.
