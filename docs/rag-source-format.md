# Format des Sources RAG

## Objectif

Une source RAG est un document valide qui pourra servir a expliquer un resultat deja produit par une logique deterministe ou metier.

Dans le premier perimetre, cette logique concerne la fiscalite. Le socle RAG reste volontairement generique pour pouvoir accueillir plus tard d'autres domaines: conformite, finance, procedures internes, juridique, achats, risques.

Le document ne doit jamais servir a faire decider le LLM a la place du moteur ou de l'humain.

## Types de Sources

- `tax_code`: code fiscal ou texte legal.
- `doctrine`: doctrine ou commentaire fiscal.
- `internal_procedure`: procedure interne validee.
- `rate_reference`: referentiel de taux, seuils ou periodes.
- `business_note`: note metier ou note de validation.
- `policy`: politique ou regle interne.
- `knowledge_base`: base de connaissance.
- `report`: rapport ou synthese validee.
- `contract`: contrat ou modele contractuel.

## Origines

- `anonymized_reference`: document anonymise et prepare par l'equipe projet.
- `user_upload`: document ajoute par l'utilisateur dans son espace de travail.

Un upload utilisateur reste en `pending_review` tant qu'il n'a pas ete valide. Il ne doit pas etre indexe automatiquement.

## Metadonnees Obligatoires

Chaque source doit avoir:

- `domain`: domaine metier, par exemple `fiscal`, `compliance`, `finance`.
- `source_type`: type de source.
- `title`: titre clair.
- `version`: annee, date ou version documentaire.
- `language`: langue du document, par exemple `fr`.
- `origin`: origine du document.
- `source_path`: chemin ou identifiant de stockage.
- `themes`: au moins un theme metier.
- `text_sha256`: empreinte du texte extrait.

Pour une source fiscale, ajouter aussi:

- `country`: pays concerne, par exemple `BF`.

Pour `user_upload`, ajouter aussi:

- `owner_reference`: identifiant opaque du proprietaire ou de l'espace de travail.

`owner_reference` ne doit pas contenir de nom, email, secret ou information fiscale sensible.

## Statuts

- `pending_review`: document recu mais non validable pour le RAG.
- `active`: document valide et indexable.
- `rejected`: document refuse.
- `archived`: document conserve mais non utilise.

Seules les sources `active` peuvent etre indexees.

## Flux Upload Utilisateur

1. L'utilisateur depose le document hors du chat ou dans une zone dediee.
2. Le backend stocke le fichier sans exposer son contenu dans les logs.
3. Le backend extrait le texte et calcule `text_sha256`.
4. La source est creee en `pending_review`.
5. Une validation humaine ou metier la passe en `active`.
6. Le pipeline RAG peut ensuite la decouper, indexer et citer.

## Regles

- Pas de source sans version.
- Pas de source sans domaine.
- Pas de source sans theme metier.
- Pas de source fiscale sans validation explicite.
- Pas d'indexation automatique d'un upload utilisateur.
- Pas de donnees fiscales sensibles dans les logs, tests ou prompts.
- Pas de citation sans metadonnees de source.

Les sources a completer vivent dans `docs/source-corpus/`.

La validation des sources est definie dans `docs/source-corpus/validation.md`.
