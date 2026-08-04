# Fonctionnalites — Audit RAS fonde sur le Grand Livre

## Finalite

Le produit analyse un Grand Livre pour identifier les depenses potentiellement soumises a la retenue a la source, rechercher la retenue comptabilisee et expliquer les ecarts a partir de sources juridiques officielles.

Le perimetre initial n'inclut ni declaration fiscale ni referentiel fournisseur externe. Une absence detectee signifie donc « RAS non retrouvee dans le GL analyse », jamais « declaration omise ».

## Principes de surete

- Le LLM ne calcule aucun montant fiscal.
- Le LLM ne choisit ni le taux ni la categorie fiscale finale.
- Toute conclusion repose sur une regle deterministe versionnee et une trace comptable.
- Toute reponse juridique cite le document, l'article, la version et la periode applicable.
- Une information manquante produit un statut `indeterminable`, jamais une hypothese silencieuse.
- Les montants sont rapproches par devise, sans conversion implicite.

## Pipeline d'audit RAS

1. Ingerer et normaliser le Grand Livre sans perdre les valeurs sources.
2. Evaluer si les colonnes requises sont disponibles pour chaque capacite.
3. Detecter une population large de depenses candidates.
4. Enrichir la nature des operations par NLP et similarite semantique.
5. Utiliser le LLM uniquement pour proposer une interpretation des libelles ambigus et relever les faits manquants.
6. Reconstituer les lignes d'une meme piece comptable.
7. Selectionner la regle RAS applicable depuis le referentiel juridique versionne.
8. Calculer la RAS theorique seulement si la base, la date, la categorie et les autres faits requis sont etablis.
9. Rechercher la contrepartie RAS, les regularisations et les extournes dans le GL.
10. Produire un constat explicable et un rapport d'audit tracable.

## Detection des candidats

La detection combine plusieurs signaux sans referentiel fournisseur externe:

- comptes de charges et autres comptes eligibles selon une cartographie versionnee;
- libelle de l'ecriture et libelle de la piece;
- journal, type de document, date, devise et montant;
- cle de comptabilisation et sens debit/credit;
- tiers present dans le GL, lorsqu'il existe;
- structure et equilibre des lignes partageant la meme piece;
- taxonomie RAS, NLP, embeddings et score de confiance.

Le resultat conserve les signaux positifs, les exclusions, les informations manquantes et la version des referentiels utilises.

## Rapprochement comptable RAS

Pour chaque candidat, le moteur recherche une contrepartie dans les comptes RAS configures. Le rapprochement utilise en priorite l'identifiant de piece, puis le journal, la societe, l'exercice, la date, le tiers, la devise et les liens de regularisation disponibles.

Les statuts cibles sont:

- `ras_comptabilisee_conforme`;
- `ras_comptabilisee_montant_incoherent`;
- `ras_non_retrouvee_dans_gl`;
- `applicabilite_probable_a_confirmer`;
- `indeterminable_donnees_manquantes`;
- `hors_perimetre_justifie`.

Une absence ne devient un constat ferme dans le fichier analyse que si le serveur a couvert techniquement toute la feuille chargee, la cartographie des comptes RAS est applicable, l'operation est juridiquement determinable et les fenetres de regularisation ont ete controlees. Cette preuve technique n'affirme jamais que le fichier represente tout le GL de l'organisation ni qu'une declaration a ete omise.

Le fait generateur est versionne separement des taux: paiement pour les prestataires residents, mise en paiement pour les non-residents et loyer acquis pour la periode. Sans statut et date d'evenement explicitement attestes, le calcul reste indeterminable; une charge non payee ne devient pas automatiquement une RAS exigible.

La cartographie des comptes est propre a chaque organisation. Elle est chargee via `RAS_LEDGER_ACCOUNT_MAPPING_PATH`. Le mapping actif analyse les comptes observes du GL fourni dans `docs/reference/ras-ledger-account-mapping.organization.csv`; les comptes ambigus restent dans le rapport de revue sans etre actives. L'absence de societe dans le GL bloque tout constat ferme via `missing_company_scope`. De meme, `Date piece` et `Type de piece` peuvent servir a reconstruire prudemment une piece, mais restent des proxies explicites de la date comptable et du journal: ils ne permettent jamais de conclure fermement a une absence de contrepartie RAS.

Les colonnes `Fournisseur` et `Client` sont normalisees separement puis le tiers est derive ligne par ligne. Deux identifiants differents sur une meme ligne produisent une anomalie sans choix arbitraire. Une lecture de feuille est mise en cache au plus quatre fois pendant la seule vie de l'executeur, avec invalidation si le fichier change; aucun cache global de donnees client n'est conserve.

## Referentiel juridique et RAG

La matrice RAS couvre toutes les categories identifiees dans le CGI et les lois de finances, completees par les instructions et formulaires DGI lorsqu'ils apportent une precision pratique. Chaque regle structure:

- categorie et nature d'operation;
- qualite et residence du beneficiaire lorsqu'elles sont requises;
- territorialite et fait generateur;
- assiette, seuil, taux, exemption et echeance;
- date de debut et de fin d'applicabilite;
- article, document officiel, URL et empreinte de la source;
- faits obligatoires et motif d'indetermination.

Le RAG sert deux usages distincts:

- repondre aux questions fiscales en langage naturel avec citations;
- fournir les passages probants lors de la constitution et de la revue du referentiel.

Le contenu retrouve par le RAG n'est pas execute directement comme une regle fiscale.

## Tools backend cibles

### `normalize_gl`

Valide le fichier, detecte le schema, normalise les champs et conserve provenance, devise et valeurs sources.

### `assess_gl_readiness`

Indique les controles possibles ou impossibles selon les colonnes et la qualite du GL.

### `detect_ras_candidates`

Filtre les pieces, combine la cartographie comptable, le sens des cles de comptabilisation, les signaux textuels versionnes et, lorsqu'il est active, le classificateur semantique. Les charges multilignes et extournes ne sont pas doublees. La sortie est une synthese de revue sans cellules, categorie fiscale, taux ni conclusion d'assujettissement.

### `classify_transaction_semantics`

Rapproche les libelles de la taxonomie operationnelle avec des embeddings locaux normalises. Le resultat trace fournisseur, modele, politique, scores et informations manquantes; une marge insuffisante reste ambigue. Le hash deterministe du RAG est explicitement interdit pour cet usage. Le moteur est desactive par defaut jusqu'a installation de l'extra `embeddings` et calibration du modele multilingue configure par `RAS_SEMANTIC_EMBEDDING_PROVIDER`, `RAS_SEMANTIC_EMBEDDING_MODEL_NAME` et `RAS_SEMANTIC_POLICY_PATH`.

### `reconstruct_accounting_entry`

Regroupe les lignes liees a une piece et expose debit, credit, comptes, tiers, dates et devise.

### `query_tax_rag`

Recherche lexicalement le CGI et les sources Markdown fiscales validees, avec la seule loi de finances 2026 active, puis retourne passage borne, article, version, URL, empreinte SHA-256, score et applicabilite a la date demandee. Un vrai provider `sentence-transformers` peut reranger les passages ayant deja une ancre lexicale; le hash de test ne peut pas activer ce mode et le semantique ne contourne jamais un refus sans preuve textuelle. Le statut `retrieval_only_no_tax_decision` interdit d'utiliser le retrieval comme decision fiscale.

### `resolve_applicable_ras_rule`

Selectionne deterministement une regle versionnee a partir des faits etablis. Les preuves du champ et du taux sont distinctes et verifiees par empreinte. Le moteur retourne les faits manquants, les ambiguities et les lacunes de source; les categories non determinees restent bloquees tant que leur champ legal complet manque.

### `calculate_theoretical_ras`

Calcule la base, le taux et le montant avec `Decimal`. Les parametres progressifs IRF sont externalises et sources. Aucune conversion de devise ni aucun arrondi n'est applique sans regle explicite; cette absence reste visible dans la trace. Si un montant paye atteste differe de l'assiette fiscale attestee, le calcul est bloque faute de regle sourcee d'allocation du paiement partiel; aucun prorata n'est invente.

### `find_ras_counterpart`

Recherche la retenue comptabilisee, les regularisations et les extournes sans rapprochement inter-devise implicite.

### `assess_ras_accounting`

Enchaine sur une piece selectionnee la resolution, le calcul et la contrepartie comptable. La date et la devise viennent du GL; le moteur expose attendu, comptabilise, ecart, tolerance, statut, preuves et limites. Les pieces liees et ajustements potentiels ne sont jamais appliques comme s'ils etaient confirmes. Le LLM ne peut pas declarer le GL complet: le serveur atteste seulement la couverture technique de la feuille. Le gate versionne controle lignes lisibles et regroupables, cles connues, mapping applicable, montants, codes devise, dates, periodes, exercices, numeros de ligne, doublons et contradictions intra-piece; ses motifs de blocage sont exposes par les tools. Lorsqu'un `base_audit_id` est fourni, le candidat enrichi produit une nouvelle version d'audit sans modifier l'ancienne.

### `run_ras_audit_batch`

Detecte et persiste tous les candidats d'un GL dans un audit unique. Chaque cas reste `potential` ou `indeterminate` tant que ses faits juridiques propres ne sont pas etablis. Le batch n'applique aucun fait utilisateur global et refuse la troncature silencieuse au-dela de la limite configuree. Cette limite est imposee par le serveur via `RAS_BATCH_MAX_CANDIDATES` (5 000 par defaut, maximum 20 000); la sortie agent reste bornee aux 20 premiers identifiants et indique le nombre de cas restants.

Les chemins absolus, noms de feuilles et messages fiscaux bruts ne sont pas recopies dans la trace de synthese LLM. Les erreurs Excel conservees utilisent des codes stables et des messages generiques; les rapports RAS n'exportent ni libelle ni tiers brut.

Les sorties RAS calculables ou incompletes et les reponses RAG sourcees sont rendues deterministement par l'API. Elles ne declenchent aucun appel LLM de synthese: un statut incomplet conserve son motif et ses faits manquants, sans taux ni montant invente.

### `generate_ras_audit_report`

Genere une synthese et un detail des candidats, ecarts, montants, devises, sources et traces depuis un `audit_id` persiste. Le tool n'accepte ni cas ni montant fourni par le LLM. Chaque evaluation comptable reussie enregistre le hash du GL, les versions de referentiels et l'empreinte du contexte utilisateur, jamais le jeton HMAC. Le `report_id` est reproductible et couvre toute la trace metier utile: statut, certitude, regle et version, montants, devise, faits manquants, anomalies, sources juridiques et completude.

### `calculate_ras_deadline`

Determine l'echeance applicable depuis une regle versionnee. Les notifications proactives seront ajoutees apres stabilisation du coeur d'audit.

## Questions en langage naturel

L'agent peut repondre a deux familles de questions:

- questions sur le GL, en appelant exclusivement les tools de calcul et de rapprochement;
- questions juridiques, en interrogeant le RAG et en citant les sources.

Une question combinant un prestataire ou une operation precise avec une demande de calcul declenche la collecte des faits obligatoires, la resolution de la regle puis le calculateur deterministe. Seules les formulations explicitement reconnues par le referentiel sont attestees; les contradictions sont exclues. Le contexte est signe cote serveur, expire apres quinze minutes et reste distinct des donnees du GL.

## Ordre de livraison

1. Backend: contrats, referentiels, detection, calcul, rapprochement, RAG et rapports.
2. Backend: tests de robustesse, jeux d'or, performances et observabilite.
3. Frontend: parcours d'audit, exploration des preuves, questions RAG et rapports.
4. Plus tard: declarations fiscales, rapprochement declaratif, calendrier et notifications.
