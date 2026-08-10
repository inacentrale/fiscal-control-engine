# Todo API

Checklist active du backend d'audit RAS fonde sur le Grand Livre.

L'historique detaille des travaux termines et de l'ancien perimetre
multi-declarations est conserve dans `docs/api-roadmap-history.md`.

## Gate backend courant

Ordre de travail: terminer les points ci-dessous avant de declarer le backend
robuste et avant d'adapter le parcours front RAS.

- [x] Stabiliser le gate qualite technique dans un environnement Docker
  reproductible sous Windows: Ruff, mypy strict et suite pytest complete.
  - Validation du 10 aout 2026: Ruff passe, mypy strict passe sur 294 fichiers
    et les 785 tests passent dans un conteneur jetable avec SQLite isole.
  - Le `.venv` Docker vit hors du volume Windows, la racine du depot est montee
    sous `/workspace` et les sorties pytest sont ignorees par Git.
- [ ] Completer le gate par les mesures de performance sur grands GL et la
  non-regression RAG avant de declarer le backend robuste.
- [ ] Terminer le challenge des tools GL encore partiellement valides:
  `aggregate_ledger`, `detect_data_quality_issues`, `detect_tax_candidates`,
  `classify_ledger_schema`, `analyze_ledger`, `profile_sheet` et les pages
  suivantes/multi-devises de `query_ledger_entries`.
  - [x] Rejouer la premiere question d'utilisation normale sur le GL anonymise:
    cinq tools executes avec succes; suppression du solde global, categories
    traduites et motifs presentes avec volume, montant, preuves et verification.
    Quatre tests de rendu passent, ainsi que Ruff et mypy cibles.
  - [x] Supprimer aussi moyenne/minimum/maximum de la synthese et franciser le
    rendu de `detect_ras_candidates`: origines de detection, faits manquants,
    statuts, certitudes, alertes et motifs; masquer les indicateurs et codes
    techniques de perimetre dans les reponses utilisateur. Rejeu API valide sur
    2 500 ecritures, 2 205 pieces evaluees et 611 pieces candidates.
  - [ ] Router cette question explicitement RAS vers `detect_ras_candidates`
    afin de presenter les pieces candidates plutot que les seules categories
    agregees par ecriture.
- [ ] Terminer le challenge RAS: multi-candidats, robustesse du tool-calling,
  arguments incomplets et refus lorsque les faits requis manquent.
  - [x] Enchainer automatiquement la reconstitution d'une piece precise et la
    recherche de sa contrepartie RAS avec le meme selecteur; restituer les
    preuves et limites en francais metier. Rejeu valide sur la piece
    `5000000573` de l'exercice 2022: deux tools executes en 29 secondes,
    contrepartie indeterminable faute de perimetre societe.
- [x] Terminer l'orchestration RAS de bout en bout sans interpretation
  numerique du LLM.
  - [x] Definir un contrat d'orchestration versionne et une machine d'etats par
    candidat: `detected`, `awaiting_facts`, `rule_resolved`, `calculated`,
    `counterpart_assessed`, `reported`, `blocked` ou `failed`.
  - [x] Faire porter au serveur l'ordre autorise des tools et leurs
    preconditions; le LLM peut demander une intention mais ne choisit ni les
    donnees intermediaires, ni la regle, ni le taux, ni les montants transmis a
    l'etape suivante.
  - [x] Demarrer chaque audit par `normalize_gl` puis
    `assess_gl_readiness`; interrompre uniquement les capacites bloquees et
    conserver les autres capacites evaluables.
  - [x] Enchainer `detect_ras_candidates` puis `run_ras_audit_batch` en
    persistant le hash du GL, la feuille, les versions de referentiels et les
    identifiants opaques de tous les candidats.
  - [x] Pour chaque candidat, reconstruire la piece et rechercher la
    contrepartie avec `reconstruct_accounting_entry` et
    `find_ras_counterpart`, sans reutiliser un resultat provenant d'un autre
    fichier, audit, session ou candidat.
  - [x] Separer le traitement multi-candidats en jobs unitaires idempotents;
    borner la concurrence, reprendre apres interruption et eviter tout double
    calcul ou double enregistrement.
  - [x] Extraire et attester les faits propres a chaque candidat; ne jamais
    appliquer automatiquement une affirmation utilisateur globale a plusieurs
    candidats.
  - [x] Suspendre un candidat en `awaiting_facts` lorsque residence, IFU,
    nature, exemption, fait generateur, date, assiette ou autre fait obligatoire
    manque; retourner une demande de clarification structuree et minimale.
  - [x] Reprendre un candidat enrichi dans une nouvelle version immuable de
    l'audit, verifier l'attestation HMAC et conserver la provenance de chaque
    fait sans exposer sa valeur au LLM.
  - [x] Appeler `resolve_applicable_ras_rule` uniquement avec les faits
    attestes et une date applicable; conserver `indeterminate` en cas de source
    manquante, contradiction, chevauchement ou categorie non resolue.
  - [x] Appeler `calculate_theoretical_ras` uniquement apres resolution unique
    de la regle et validation de l'assiette, du fait generateur et de la devise;
    refuser arrondi, prorata ou conversion non sources.
  - [x] Appeler `assess_ras_accounting` uniquement avec le calcul deterministe,
    la piece et la contrepartie du meme candidat; n'emettre un constat ferme
    d'absence que si les preuves de completude requises sont presentes.
  - [x] Generer automatiquement une nouvelle version du rapport avec
    `generate_ras_audit_report` apres chaque lot termine, en distinguant cas
    conclus, probables, indeterminables, bloques et en erreur.
  - [x] Exposer dans le stream agent les transitions d'etat, la progression,
    les faits manquants et les erreurs sanitisees, sans cellules, libelles,
    tiers ou montants sensibles inutiles.
  - [x] Definir les politiques de retry, timeout, annulation et reprise pour
    chaque etape; ne jamais transformer un echec technique en conclusion
    fiscale.
  - [x] Ajouter les tests unitaires de la machine d'etats et des preconditions,
    puis les tests d'integration mono-candidat, multi-candidats, reprise,
    idempotence, isolation session/fichier, donnees manquantes et echec partiel.
  - [x] Valider le flux complet sur le jeu d'or et un GL anonymise: resultats
    reproductibles, aucun nombre interprete par le LLM, aucune fuite de donnee,
    metriques de gate atteintes et rapport identique apres reprise.
  - Validation du 10 aout 2026: Ruff et mypy passent sur 287 fichiers; 33 tests
    cibles d'orchestration passent, le challenge tools du jeu d'or passe, et le
    GL anonymise de 2 500 lignes produit 611 candidats et un rapport identique
    lors d'une regeneration.
- [ ] Ameliorer le rapport d'audit RAS pour la revue operationnelle.
  - [x] Definir et versionner le contrat de rapport v2 en preservant la
    compatibilite JSON/CSV et la reproductibilite de `report_id`.
  - [x] Ajouter une synthese executive: cas analyses, conclus, probables,
    indeterminables, bloques et en erreur, taux de completude et principales
    causes de blocage.
  - [x] Separer par devise les montants theoriques, comptabilises, insuffisants
    et excedentaires; documenter explicitement le sens de l'ecart
    `comptabilise - theorique` sans compensation entre devises ou certitudes.
  - [x] Enrichir chaque cas avec les donnees operationnelles strictement
    necessaires: periode, reference de piece adaptee au canal, compte, nature
    normalisee, fait generateur, assiette, taux, tolerance et justification
    concise.
  - [x] Traduire les statuts, faits manquants et anomalies techniques en
    libelles metier versionnes.
  - [x] Ajouter une priorite de revue et une action proposee deterministes,
    sans laisser le LLM fixer une conclusion fiscale ou un montant.
  - [x] Produire un export Excel principal avec feuilles `Synthese`,
    `Regularisations`, `Cas indetermines`, `Faits manquants`, `Details` et
    `References`; conserver JSON pour l'audit machine et CSV pour le detail.
  - [x] Ajouter ensuite un PDF de synthese lisible et imprimable, sans en faire
    le support de travail detaille ni dupliquer des donnees sensibles inutiles.
  - [x] Exposer les nouveaux formats dans l'API avec noms de fichiers,
    media-types, isolation session/fichier et limites de taille explicites.
  - [x] Tester totaux, signes, multi-devises, arrondis sources, cas vides,
    donnees manquantes, caracteres Excel/CSV dangereux et absence de fuite de
    cellules, tiers, libelles ou identifiants fiscaux non necessaires.
  - [x] Reprendre le rapport telechargeable comme une synthese destinee a un
    profil financier, avec des colonnes, statuts, priorites et actions
    entierement rediges en francais metier.
  - [x] Retirer de toutes les feuilles et de tous les formats telechargeables
    `candidate_id`, `rule_id`, les codes internes et les versions techniques;
    conserver la tracabilite necessaire uniquement cote serveur.
  - [x] Alimenter les colonnes operationnelles indispensables: periode,
    reference reelle de la piece dans l'Excel interne, compte, nature de
    l'operation, fournisseur pseudonymise, assiette, taux, RAS theorique,
    RAS comptabilisee et ecart. L'apercu authentifie utilise aussi la reference
    reelle; les exports JSON/CSV telechargeables restent pseudonymises.
  - [x] Remplacer les lignes presque vides par un constat metier explicite qui
    indique les informations absentes, pourquoi la conclusion est impossible
    et quelle verification concrete doit etre realisee.
  - [x] Recomposer le classeur autour des feuilles `Synthese`, `Anomalies` et
    `Dossiers incomplets`, sans onglet technique ni feuille de references
    juridiques exposee a l'utilisateur.
  - [x] Enrichir la synthese avec les volumes controles, anomalies, montants a
    regulariser, dossiers incomplets et principales causes, sans compensation
    entre devises.
  - [x] Verifier que PDF, CSV et JSON sont effectivement telechargeables depuis
    l'interface, tout en conservant Excel comme format de travail principal.
  - [ ] Faire tester la lisibilite et l'utilite operationnelle du rapport par
    un profil finance avant de figer le nouveau contrat de presentation.
  - [ ] Valider les exports sur le jeu d'or et le GL anonymise avec un fiscaliste
    ou expert-comptable, puis figer les criteres d'acceptation avant adaptation
    de l'interface dans `front/todo.md`.
    - Validation technique terminee le 10 aout 2026 sur le jeu d'or et le GL
      anonymise de 2 500 lignes; grille metier preparee dans
      `docs/ras-report-v2-acceptance.md`. Relecture externe encore requise.
    - Controles passes: Ruff, Mypy (294 fichiers), 16 tests cibles, lint et
      typecheck front. Validation reproductible: 611 candidats et exports
      JSON, CSV, XLSX et PDF generes sous la limite de 20 Mio.
    - Validation technique du 10 aout 2026: rapport sans identifiants ni codes
      internes, colonnes metier francaises, tiers pseudonymises et references
      reelles des pieces dans l'Excel interne; classeur `Synthese`, `Anomalies`
      et `Dossiers incomplets`; 611 dossiers reproduits dans les quatre formats.
      La validation externe par un professionnel reste requise.
    - Rejeu API final sur le fichier actif: 43 dossiers et 43 anomalies,
      natures francisees, references reelles dans l'apercu authentifie et
      l'Excel, tiers pseudonymises; aucun `candidate_id`,
      `rule_id`, `action_code` ou `source_sha256` dans l'apercu JSON.
- [ ] Challenger chaque tool sur le jeu d'or et rapprocher les resultats au GL
  source, y compris les gates juridiques separes du jeu d'or comptable.
- [ ] Calibrer le classificateur semantique avec le modele d'embeddings local
  cible sur un jeu d'or metier relu; versionner seuils, precision, rappel, faux
  positifs et faux negatifs par categorie.
- [ ] Completer et valider la matrice juridique RAS active: inventaire exhaustif
  CGI/loi de finances 2026, faits generateurs, echeances, categories et champs
  obligatoires encore bloques ou contradictoires.
- [ ] Challenger le RAG juridique sur les refus hors source et les questions
  ambigues, puis verifier la non-regression des citations.
- [ ] Construire la chaine versionnee de mise a jour des sources et regles
  fiscales utilisees par le RAG et le moteur deterministe.
  - [ ] Definir les contrats metier et le schema PostgreSQL immuable pour les
    documents, articles et regles: source officielle, URL, empreinte SHA-256,
    version, dates d'application, provenance et statut de validation.
  - [ ] Implementer l'import manuel securise d'un PDF ou d'une URL officielle:
    validation, limites de taille, detection des doublons et archivage de
    l'original sans activation automatique.
  - [ ] Extraire et decouper les documents par article ou section, puis produire
    une proposition comparant la nouvelle version aux sources et regles actives.
  - [ ] Implementer le workflow `brouillon`, `a_valider`, `valide`, `remplace`
    ou `contradictoire`, avec validation ou refus humain, auteur, date et motif.
  - [ ] Indexer dans le RAG actif uniquement les sources validees; conserver les
    versions remplacees pour l'historique sans les utiliser pour soutenir une
    reponse courante.
  - [ ] Filtrer la recherche RAG et la resolution deterministe par date
    d'application; refuser de conclure en cas de lacune, chevauchement ou
    contradiction au lieu de choisir arbitrairement une source.
  - [ ] Corriger le classement temporel actuel afin qu'un ancien CGI marque
    `A CONFIRMER` ne soit plus presente comme applicable en 2026.
  - [ ] Ajouter les tests de non-regression par exercice, dates limites,
    remplacement, contradiction, citation, source non validee et doublon.
  - [ ] Dans un second lot, surveiller une liste blanche de sites officiels,
    detecter et archiver les nouveaux documents, puis creer une proposition a
    valider sans jamais publier automatiquement une regle fiscale.
- [ ] Valider les volumes et performances sur grands GL et documenter les
  budgets d'execution acceptables.
- [ ] Declarer le backend robuste uniquement lorsque tous les controles
  precedents et les metriques du jeu d'or sont verts.
- [ ] Demarrer ensuite l'adaptation du front decrite dans `front/todo.md`.

## Prochains lots

- [ ] Encadrer et tester la suggestion LLM optionnelle de
  `classify_transaction_semantics` uniquement pour les cas ambigus, sans lui
  permettre de fixer l'assujettissement, la categorie, le taux ou l'anomalie.
- [ ] Ajouter `calculate_ras_deadline`, puis le calendrier et les notifications,
  apres stabilisation du coeur d'audit.
- [ ] Reconsiderer le chargement des declarations RAS pour confirmer les
  omissions declaratives dans une phase distincte.
- [ ] Reconsiderer factures, contrats, paiements et referentiel partenaires
  comme enrichissements optionnels.
- [ ] Ajouter une implementation PostgreSQL de `AccountMappingRepository`
  uniquement si un besoin metier le justifie.
- [x] Ajouter une CI GitHub Actions executant les controles backend et frontend:
  secrets, Ruff, mypy, pytest, compilation, build Docker, lint, typecheck,
  Vitest et build Next.js.
- [ ] Definir une strategie CD apres validation de l'environnement cible.
- [ ] Executer le smoke test reel du fournisseur `openai-compatible` generique
  lorsqu'il entre dans le perimetre; seuls Gemini et Groq sont prioritaires
  actuellement.

## Blocages et travaux differes

- [ ] Obtenir ou confirmer une source officielle exploitable pour les faits
  generateurs, echeances et categories juridiques encore incomplets; ne pas
  activer de regle fiscale sans preuve suffisante.
- [ ] Faire relire par un expert-comptable ou fiscaliste les sources et
  squelettes fiscaux encore auto-valides, notamment les questions honoraires et
  loyer/entretien/prestation sans doctrine disponible; corriger et re-exporter
  les referentiels si necessaire.
- [ ] Revalider l'OCR reel des declarations et pieces justificatives dans
  Docker; BuildKit local etait bloque lors des validations historiques.
- [ ] Completer la collecte officielle 2023-2026 de l'ancien perimetre
  multi-declarations seulement si ce perimetre est reactive, notamment le texte
  promulgue de la loi rectificative 2025 et la matrice d'applicabilite.
- [ ] Versionner tolerances, arrondis et exceptions, completer la trace
  extraction-transformation-regle-preuve-resultat, puis tester chaque ancienne
  regle avec cas normal, limite et anomalie si le perimetre multi-declarations
  est reactive.
- [ ] Chiffrer et minimiser les donnees fiscales sensibles avant tout usage de
  production.
- [ ] Rapprocher les partenaires et scorer les doublons sans fusion automatique
  incertaine dans un lot ulterieur.
