# Détection automatique des artéfacts de mouvement dans les scanners 4D

Projet **Clinique de l'IA** (aivancity) en partenariat avec l'**Institut Rafaël** (Levallois-Perret).
PGE3-FR / PGE4, semestre 1 de l'année 2026-2027, domaine IA & Santé.

> **Statut :** le pipeline de construction du dataset (artefacts simulés sur des 4DCT publics) est en place. L'entraînement du modèle (nnU-Net v2) se fait sur **Kaggle** : voir le guide [docs/08_entrainement_kaggle.md](docs/08_entrainement_kaggle.md).

## Démarrage rapide pour l'équipe

| Je veux… | Où regarder |
|---|---|
| Comprendre le projet | Ce README, puis [docs/00_fiche_projet.md](docs/00_fiche_projet.md) et [docs/01_cadrage.md](docs/01_cadrage.md) |
| Construire le dataset | [src/README_pipeline.md](src/README_pipeline.md), section « Par où commencer » |
| **Entraîner le modèle sur Kaggle** | [docs/08_entrainement_kaggle.md](docs/08_entrainement_kaggle.md) |
| Contribuer au code ou à la doc | [CONTRIBUTING.md](CONTRIBUTING.md) et la section « Travailler à plusieurs » ci-dessous |

### Installation locale

```bash
git clone https://github.com/Hii987/Rafa-l.git
cd Rafa-l
pip install -r requirements.txt
cd src        # les scripts du pipeline se lancent depuis ce dossier
python build_dataset.py --source phantom --n-phantoms 6 --out ../dataset_phantom   # test sans données (~2 min)
```

### Travailler à plusieurs

1. Chacun travaille sur **sa propre branche** : `git checkout -b <prenom>`.
2. Avant de commencer : `git pull origin main` pour récupérer le travail des autres.
3. Quand c'est prêt : `git add …`, `git commit -m "…"`, `git push origin <prenom>`.
4. Sur GitHub, ouvrir une **Pull Request** (PR) vers `main`. Un autre membre la relit, puis clique sur *Merge*.

Ne jamais pousser de données (DICOM, NIfTI, dataset, poids de modèle) sur GitHub : le `.gitignore` les bloque. Le dataset se partage **via Kaggle** (voir le guide).

## Contexte

Les scanners 4D (4DCT) servent à préparer les traitements de radiothérapie en tenant compte des mouvements anatomiques, en particulier de la respiration. Pendant l'acquisition, des **artéfacts de mouvement** peuvent dégrader les images. Aujourd'hui, le physicien médical contrôle la qualité **à l'œil**, phase par phase. C'est long, et le résultat dépend de son expérience.

Quand la qualité est jugée insuffisante, il peut demander une acquisition complémentaire ou intégrer cette incertitude dans le plan de traitement.

## Objectif

Développer un outil d'IA qui **détecte et localise automatiquement** les artéfacts de mouvement dans les images 4DCT. L'outil sert d'**aide à la décision** : il complète la validation du physicien médical, il ne la remplace pas. À terme, il doit pouvoir s'intégrer sous forme de module ou de plugin dans le **PACS** clinique.

Données : images 4DCT exportées du PACS au format **DICOM**.

## Organisation du dépôt

```
.
├── docs/                  Documentation projet (cadrage, état de l'art, protocoles, architecture)
│   └── decisions/         Décisions d'architecture (ADR)
├── data/                  Données locales, JAMAIS versionnées (voir data/README.md)
│   ├── raw/               Exports DICOM bruts (accès restreint)
│   ├── interim/           Données anonymisées / converties
│   ├── processed/         Jeux prêts pour l'entraînement / l'évaluation
│   └── annotations/       Annotations des artéfacts
├── src/                   Pipeline de construction du dataset (voir src/README_pipeline.md)
├── notebooks/             Exploration et analyses
├── configs/               Fichiers de configuration (expériences, pipeline)
├── models/                Poids entraînés (non versionnés)
├── reports/               Résultats d'évaluation, figures
├── app/                   Interface de visualisation (à venir)
├── deploy/                Prototype d'intégration clinique / PACS (à venir)
└── tests/                 Tests
```

## Documentation

| Document | Contenu |
|---|---|
| [docs/00_fiche_projet.md](docs/00_fiche_projet.md) | Synthèse de la fiche projet officielle |
| [docs/01_cadrage.md](docs/01_cadrage.md) | Problématique, périmètre, hypothèses, questions ouvertes pour l'Institut |
| [docs/02_roadmap.md](docs/02_roadmap.md) | Phases, jalons et livrables sur le semestre |
| [docs/03_etat_de_l_art.md](docs/03_etat_de_l_art.md) | Plan de l'état de l'art et pistes bibliographiques |
| [docs/04_donnees_et_conformite.md](docs/04_donnees_et_conformite.md) | Données DICOM, anonymisation, RGPD, sécurité |
| [docs/05_protocole_annotation.md](docs/05_protocole_annotation.md) | Brouillon du protocole d'annotation à valider avec les physiciens |
| [docs/06_architecture.md](docs/06_architecture.md) | Architecture cible du pipeline et pistes d'intégration PACS |
| [docs/07_evaluation.md](docs/07_evaluation.md) | Stratégie d'évaluation et métriques |
| [docs/08_entrainement_kaggle.md](docs/08_entrainement_kaggle.md) | Entraîner le modèle nnU-Net sur un GPU Kaggle, en équipe |
| [src/README_pipeline.md](src/README_pipeline.md) | Pipeline de construction du dataset d'artefacts simulés |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Conventions Git et règles de travail |

## Stack technique envisagée

Python, pydicom / SimpleITK, PyTorch, [nnU-Net v2](https://github.com/MIC-DKFZ/nnUNet) (entraînement sur Kaggle), [MONAI](https://monai.io/) (MONAI Label / MONAI Deploy pour l'annotation et l'intégration), Git.

## ⚠️ Données de santé

Aucune donnée patient, même anonymisée, ne doit être poussée sur ce dépôt. Voir [docs/04_donnees_et_conformite.md](docs/04_donnees_et_conformite.md).

## Contacts

- Chef de projet côté entreprise : Alain Toledano (Institut Rafaël)
- Équipe étudiante : _à compléter_
