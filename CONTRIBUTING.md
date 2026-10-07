# Conventions de travail

## Branches
- `main` : branche stable, mise à jour uniquement par Pull Request relue.
- `feat/<sujet>`, `fix/<sujet>`, `docs/<sujet>`, `exp/<sujet>` (expériences).

## Commits
Messages courts, à l'impératif, préfixés par leur type : `feat:`, `fix:`, `docs:`, `exp:`, `refactor:`, `test:`, `chore:`.
Exemple : `docs: ajoute la typologie des artéfacts au protocole d'annotation`.

## Pull Requests
- Une PR = un sujet.
- Au moins une relecture par un autre membre de l'équipe.
- Avant d'ouvrir une PR, vérifier qu'**aucune donnée patient, aucune capture d'écran identifiante et aucun secret** n'est inclus.

## Notebooks
- Les notebooks servent à l'exploration. Le code réutilisable va dans `src/`.
- Effacer les sorties avant de commiter si elles contiennent des images de patients.
- Nommage : `NN_initiales_sujet.ipynb` (ex. `01_ab_exploration_metadonnees.ipynb`).

## Expériences
- Chaque expérience est décrite par un fichier dans `configs/` et rattachée à un commit.
- Les résultats chiffrés sont consignés dans `reports/`.

## Décisions
Toute décision structurante (format des données, architecture du modèle, outil d'annotation, mode d'intégration PACS) est documentée dans `docs/decisions/` à partir du modèle `0000-template.md`.
