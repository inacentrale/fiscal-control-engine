# Instructions Projet

Ces regles s'appliquent a tout assistant, modele et extension qui travaille sur ce projet.

## Projet

- Agent de revue fiscale pre-declaratif pour les donnees comptables OHADA, avec premier perimetre Burkina Faso.
- Objectif initial: harmoniser les fichiers du Grand Livre avec le plan comptable, puis cartographier les comptes soumis ou potentiellement soumis a la retenue a la source.
- La decision fiscale reste deterministe et humaine: le LLM explique les anomalies detectees par les regles, il ne decide pas.
- Les documents d'intention durables vivent dans `docs/`.
- Les skills projet vivent dans `docs/skills/` et servent de guides ponctuels.
- Le suivi des taches vit dans les todos de domaine: `api/todo.md` et `front/todo.md`. Ne pas creer de todo a la racine ni dans `docs/`.

## Regles Transversales

- Faire des changements petits, explicites, verifiables et faciles a relire.
- Lire les regles du perimetre avant modification:
  - `api/**`: lire `.agents/rules/api.md`.
  - `front/**`: lire `.agents/rules/front.md`.
- Pour toute modification de plan ou checklist, utiliser l'esprit de `docs/skills/todo-plan-tracker/SKILL.md`.
- Ne pas inventer de regle fiscale. Documenter toute ambiguite metier avant implementation.
- Toute donnee externe est non fiable et doit etre validee a la frontiere.
- Ne jamais exposer de secret, de donnee personnelle, de donnee fiscale sensible ou de fichier client dans le code, les logs ou les tests.
- Toute logique metier modifiee doit etre testee.
- Executer les controles pertinents avant de terminer: lint, types/build, tests.

## Discipline

- Preferer KISS et YAGNI: pas d'abstraction speculative.
- Les commentaires expliquent uniquement un choix metier, une contrainte externe ou un contournement non evident.
- Ne pas refactorer ni reformater du code non concerne.
- Travailler avec les fichiers existants et ne pas ecraser les changements utilisateur.
