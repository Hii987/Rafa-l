# data/

Ce dossier est **local uniquement**. Son contenu est ignoré par Git (seuls ce README et les `.gitkeep` sont versionnés).

| Dossier | Contenu | Sensibilité |
|---|---|---|
| `raw/` | Exports DICOM bruts du PACS | **Identifiant**, accès restreint, ne jamais copier hors environnement autorisé |
| `interim/` | DICOM anonymisés, conversions intermédiaires | Pseudonymisé |
| `processed/` | Volumes prêts pour l'entraînement / l'évaluation, splits | Pseudonymisé |
| `annotations/` | Labels issus du protocole d'annotation | Pseudonymisé |

Voir [docs/04_donnees_et_conformite.md](../docs/04_donnees_et_conformite.md).
