CAHIER DES CHARGES
Agent IA de Revue Fiscale
Détection préventive des anomalies TVA et Retenue à la Source avant déclaration
RAM — Direction Financière / Finance Décentralisée
Périmètre OHADA — Burkina Faso


Sommaire
1. Contexte et objectifs
2. Périmètre du projet
3. Architecture fonctionnelle cible
4. Catalogue de contrôles fiscaux
5. Données nécessaires (inputs)
6. Architecture technique
7. Feuille de route
8. Gouvernance et limites du système


1. Contexte et objectifs
Les entités décentralisées de la RAM, soumises au système OHADA, externalisent aujourd'hui la gestion fiscale à des cabinets locaux. Ce modèle ne dispose d'aucun mécanisme de vérification indépendante en interne avant le dépôt des déclarations, ce qui expose les entités à des redressements fiscaux consécutifs à des déclarations non conformes.
L'objectif du projet est de concevoir un agent IA de revue fiscale capable d'analyser les données comptables produites par le cabinet fiscal afin de détecter automatiquement les incohérences liées à la TVA et à la Retenue à la Source (RAS), avant la validation par le responsable financier (RF).
1.1 Positionnement pré-déclaratif
Le système n'intervient pas en audit rétrospectif. Il s'insère entre la clôture du Grand Livre (GL) et le dépôt de la déclaration, afin de permettre une correction avant que l'anomalie ne devienne un risque de redressement.
1.2 Ce que le système n'est pas
•	Il ne remplace ni le cabinet fiscal ni le responsable financier : la décision finale reste humaine.
•	Il ne calcule pas les déclarations fiscales : il contrôle la cohérence des données qui les alimentent.
•	Le LLM n'intervient qu'en explication des anomalies déjà détectées par des règles déterministes — jamais en décision.
2. Périmètre du projet
2.2 Cas d'usage de référence
•	TVA non récupérable sur charge (crédit de TVA)
•	Retenue à la source 
1.	Prestations de services (Non-résidents)
2.	Prestations de services (Résidents)
3.	Loyers
•	Charges non déductibles (amendes fiscales)
3. Architecture fonctionnelle cible
L'architecture repose sur quatre modules fonctionnels. Chaque module peut être présenté, pour la communication auprès des parties prenantes métier, comme un agent ayant un rôle d'auditeur junior spécialisé — sans que cela implique une architecture technique distribuée.
Module technique	Rôle métier (« agent »)	Fonction
Base documentaire	Agent Fiscal Expert	CGI par pays, doctrine, procédures internes — sert de référentiel au RAG.
Moteur de règles déterministe	Agent Revue TVA / Agent Revue RAS	Applique les contrôles
Couche LLM (Mistral, local)	Agent Rapport & Recommandations	Rédige l'explication de chaque anomalie en citant la règle ou l'article concerné — jamais de décision.

La distinction « agents par rôle métier » plutôt que « agents par technologie » facilite la présentation à une DAF : chaque agent reflète une étape déjà connue d'une mission de revue fiscale classique.
3.1 Principe directeur : déterministe
La classification fiscale (conforme / non conforme) doit rester déterministe, car la loi fiscale est binaire. le LLM n'interviennent qu'en complément, jamais en substitution du moteur de règles.
4. Catalogue de contrôles fiscaux
Ce catalogue constitue le cœur du moteur de règles. Chaque contrôle doit être décliné par pays (CI / SN / CM) lors de l'implémentation, en associant l'article correspondant du CGI national applicable.
4.1 Contrôles TVA
#	Contrôle	Logique de détection	Risque par défaut
T1	TVA déclarée = TVA comptabilisée	Écart entre la TVA collectée déclarée et la TVA comptabilisée au GL.	Élevé
T2	TVA récupérée sans facture conforme	TVA déduite en l'absence de facture justificative valide (mentions obligatoires).	Élevé
T3	TVA sur dépense non récupérable	TVA déduite sur une dépense non éligible (restaurant, véhicule de tourisme, amende, etc.).	Moyen
T4	TVA déductible > TVA des factures	Le montant de TVA déduit dépasse celui figurant sur les factures sources.	Élevé
T5	Écart entre achats et TVA	Incohérence entre le volume d'achats comptabilisés et la TVA déductible correspondante.	Moyen
T6	Taux de TVA appliqué incorrect	Le taux facturé ne correspond pas au taux légal en vigueur dans le pays.	Moyen

4.2 Contrôles Retenue à la Source (RAS)
#	Contrôle	Logique de détection	Risque par défaut
R1	Paiement soumis à RAS sans retenue	Un paiement entrant dans le champ de la RAS (honoraires, commissions...) ne présente aucune retenue comptabilisée.	Élevé
R2	Taux de RAS incorrect	Le taux appliqué ne correspond pas au taux légal selon la nature de la prestation.	Moyen
R3	Prestataire étranger sans contrôle de convention fiscale	Paiement à un prestataire étranger sans vérification de l'existence d'une convention de non double imposition.	Élevé
R4	RAS déclarée ≠ RAS comptabilisée	Écart entre le montant de RAS déclaré et celui comptabilisé au GL.	Élevé
R5	Paiement sans justificatif contractuel	Paiement significatif sans contrat ni bon de commande associé.	Moyen

Niveaux de risque par défaut, à ajuster lors du calibrage avec le RF et le Service de Contrôle et de Normalisation des Flux.
5. Données nécessaires (inputs)
•	Grand Livre des comptes
•	Référentiel fiscal par pays : taux de TVA et de RAS, calendrier des échéances
•	Mapping comptes comptables → catégories fiscales
•	Textes réglementaires (CGI par pays, doctrine, procédures internes) pour la base documentaire
6. Architecture technique
La stack retenue privilégie la simplicité et la confidentialité des données, sans dépendance à une orchestration multi-agents distribuée : le pipeline de contrôle est linéaire et ne justifie pas cette complexité supplémentaire à ce stade.
Composant	Choix retenu
Prototype / POC	Python + Pandas (moteur de règles) + React (interface)
Backend cible	Python FastAPI
Frontend cible	React + Tailwind CSS
Base relationnelle	PostgreSQL
Recherche documentaire (RAG)	ChromaDB
LLM (explication uniquement)	Ollama + Mistral 7B, déployé en local/ API (Grock, Gemini, OpenAI)



7. Feuille de route
Plan en huit semaines, structuré pour valider la logique métier avant d'investir dans l'infrastructure.
Semaine	Phase	Objectif
1	Cadrage	Formaliser 15 à 20 règles TVA/RAS à partir du catalogue ; préparer un jeu de données CSV représentatif.
2	Moteur de règles	Développer le moteur de règles en Python/Pandas sur le CSV ; interface réact minimale affichant les écarts détectés.
3	RAG	Indexer les CGI et procédures internes dans ChromaDB ; connecter Ollama/Mistral pour expliquer chaque anomalie avec sa base légale.
4	Rapport & démo	Générer un rapport de revue fiscale (HTML/PDF) ; tester sur des cas réels ; préparer la démonstration au RF.
7	Migration infrastructure	Migrer le CSV vers PostgreSQL ; commencer la connexion du frontend React.
8	Validation finale	Tests de bout en bout, ajustement des seuils avec le RF, préparation du rapport de stage final.


8. Gouvernance et limites du système
•	Le responsable financier conserve la décision finale sur toute anomalie détectée.
•	Le système constitue un second niveau de contrôle indépendant, documenté et traçable — il ne remplace pas le cabinet fiscal.
•	Aucune donnée du Grand Livre ne doit transiter par une API cloud : le LLM et la base vectorielle sont déployés localement.

