# Fiche projet (synthèse)

Source : fiche « Détection automatique des artéfacts de mouvement dans les images de scanner 4D (FR) », plateforme Clinique de l'IA d'aivancity (consultée le 01/10/2026).

## Informations clés

| | |
|---|---|
| Entreprise | Institut Rafaël |
| Niveau | PGE3-FR, PGE4 |
| Année / semestre | 2026-2027, semestre 1 |
| Domaine | IA & Santé |
| Type | Projet entreprise |
| Chef de projet entreprise | Alain Toledano |

## L'entreprise

L'Institut Rafaël a été fondé en 2018 à Levallois-Perret. C'est un centre de santé intégrative, créé à l'origine comme « Maison de l'Après Cancer ». Il accompagne les patients avec une approche globale : oncologie, activité physique adaptée, nutrition, psychologie, sophrologie, onco-esthétique et accompagnement social. Ses trois missions sont le soin, la recherche et la formation.

## Objectifs (fiche)

1. Comprendre le fonctionnement et les spécificités des acquisitions scanner 4D.
2. Identifier et caractériser les principaux artéfacts liés aux mouvements du patient.
3. Construire un jeu de données adapté à l'apprentissage et à l'évaluation d'un modèle d'IA.
4. Développer un modèle qui détecte automatiquement la présence d'artéfacts.
5. Localiser les zones de l'image concernées par les artéfacts détectés.
6. Évaluer les performances du modèle et sa robustesse sur différentes acquisitions.
7. Proposer une visualisation qui permet au physicien d'identifier rapidement les zones problématiques.
8. Développer un prototype intégrable au workflow clinique et, si c'est faisable, au PACS.
9. Concevoir l'outil comme une aide à la décision qui complète la validation du physicien médical.

## Livrables attendus (fiche)

| # | Livrable | Emplacement prévu dans le dépôt |
|---|---|---|
| L1 | État de l'art sur la détection des artéfacts en 4DCT | `docs/03_etat_de_l_art.md` |
| L2 | Pipeline d'import, d'anonymisation, de préparation et d'exploitation des DICOM | `src/` + `docs/06_architecture.md` |
| L3 | Protocole d'annotation des artéfacts, établi avec les professionnels de santé | `docs/05_protocole_annotation.md` |
| L4 | Jeu de données préparé pour l'entraînement et l'évaluation | `data/processed/` (hors Git) + fiche descriptive |
| L5 | Modèle d'IA de détection et de localisation | `src/`, `models/` |
| L6 | Évaluation quantitative des performances | `docs/07_evaluation.md`, `reports/` |
| L7 | Interface de visualisation des artéfacts détectés | `app/` |
| L8 | Prototype d'intégration au workflow clinique / module compatible PACS | `deploy/` |
| L9 | Documentation technique et utilisateur | `docs/` |
| L10 | Présentation finale et démonstration | `reports/` |

## Compétences mobilisées

Python, DICOM, imagerie, vision, deep learning, PyTorch, MONAI, PACS, annotation, validation, radiothérapie, Git.
