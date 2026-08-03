# Strategie de Chunking RAG

## Objectif

Le chunking decoupe les sources validees en passages citables et recherchables.

Il intervient avant les embeddings.

## Principe

Le decoupage doit suivre la structure du document:

1. article, section ou paragraphe pour les textes fiscaux et juridiques;
2. section ou note pour les procedures internes;
3. page ou bloc logique pour les autres documents;
4. fenetre de mots seulement si le bloc est trop long.

Le systeme ne decoupe pas d'abord par taille fixe, car cela peut casser une logique metier ou juridique.

## Contrat Interne

Le chunker recoit:

- un `RagSourceDocument` actif;
- des `RagTextBlock` deja structures par article, section, paragraphe, page ou note.

Il produit des `RagChunk` contenant:

- ordre du chunk;
- reference du chunk;
- texte;
- reference article ou section;
- type de bloc;
- metadonnees source;
- hash du texte source.

## Parametres Actuels

- `DEFAULT_CHUNK_MAX_WORDS = 800`
- `DEFAULT_CHUNK_OVERLAP_WORDS = 80`

Ces valeurs sont techniques et pourront etre ajustees apres evaluation du corpus.

## Regles

- Seuls les documents `active` peuvent etre chunkes.
- Chaque chunk conserve sa source et sa version.
- Chaque chunk doit etre citable.
- Aucun embedding n'est cree a cette etape.
- Aucun LLM n'intervient dans le chunking.

## Suite

La prochaine etape est d'associer les questions fiscales restantes a un petit corpus fiscal valide avant les embeddings.
