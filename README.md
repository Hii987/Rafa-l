# Détection automatique des artéfacts de mouvement dans les scanners 4D

Projet **Clinique de l'IA** (aivancity) en partenariat avec l'**Institut Rafaël** (Levallois-Perret).
PGE3-FR / PGE4, semestre 1 de l'année 2026-2027, domaine IA & Santé.

> **Statut : cadrage.** Aucun code n'est encore écrit. Le dépôt contient la structure, la documentation de cadrage et les conventions de travail.

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
├── src/                   Code source du pipeline et du modèle (à venir)
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
| [CONTRIBUTING.md](CONTRIBUTING.md) | Conventions Git et règles de travail |

## Stack technique envisagée

Python, PyTorch, [MONAI](https://monai.io/) (et MONAI Label / MONAI Deploy), pydicom / SimpleITK, Git.
Choix définitifs à acter dans `docs/decisions/` une fois les données disponibles.

## ⚠️ Données de santé

Aucune donnée patient, même anonymisée, ne doit être poussée sur ce dépôt. Voir [docs/04_donnees_et_conformite.md](docs/04_donnees_et_conformite.md).

## Contacts

- Chef de projet côté entreprise : Alain Toledano (Institut Rafaël)
- Équipe étudiante : _à compléter_
