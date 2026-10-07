# Roadmap

Semestre 1, 2026-2027. Les dates sont indicatives et seront ajustées au calendrier aivancity et à la disponibilité des données.

```
Phase 0  Cadrage & état de l'art           ███░░░░░░░░░░░░
Phase 1  Données : accès, pipeline, EDA     ░░████░░░░░░░░░
Phase 2  Annotation & jeu de données        ░░░░████░░░░░░░
Phase 3  Modélisation (détection + loc.)    ░░░░░░█████░░░░
Phase 4  Évaluation & robustesse            ░░░░░░░░░███░░░
Phase 5  Visualisation & prototype PACS     ░░░░░░░░░████░░
Phase 6  Documentation, soutenance          ░░░░░░░░░░░░███
```

## Phase 0 : Cadrage et état de l'art
- Réunion de lancement avec l'Institut Rafaël. Réponses aux [questions ouvertes](01_cadrage.md#questions-ouvertes-pour-linstitut-rafaël).
- Montée en compétence : 4DCT, workflow de radiothérapie, DICOM, PACS.
- Revue de littérature → **L1**.
- Recensement des jeux de données publics 4DCT.
- Mise en place de l'environnement : dépôt, conventions, environnement Python.
- **Jalon M0** : cadrage validé par le chef de projet.

## Phase 1 : Données
- Obtenir l'accès aux exports DICOM dans un cadre conforme.
- Pipeline d'import → anonymisation → conversion → contrôle (**L2**).
- Analyse exploratoire : métadonnées, nombre de phases, épaisseur de coupe, variabilité des acquisitions.
- **Jalon M1** : pipeline reproductible sur au moins un examen complet.

## Phase 2 : Annotation et jeu de données
- Co-construire le protocole d'annotation avec les physiciens (**L3**).
- Choisir l'outil d'annotation (MONAI Label + 3D Slicer, ou outil plus léger).
- Annotation pilote, puis mesure de l'accord inter-annotateurs et révision du protocole.
- Découpage train / validation / test **par patient**. Simulation éventuelle d'artéfacts.
- **Jalon M2** : jeu de données v1 figé et documenté (**L4**).

## Phase 3 : Modélisation
- Baselines simples : métriques de discontinuité inter-coupes, corrélation entre phases.
- Modèles deep learning : classification (examen / phase / coupe) puis localisation (heatmap, détection ou segmentation).
- Suivi des expériences avec configs versionnées dans `configs/`.
- **Jalon M3** : premier modèle meilleur que les baselines (**L5**).

## Phase 4 : Évaluation
- Métriques définies dans [07_evaluation.md](07_evaluation.md).
- Robustesse par sous-groupes (scanner, localisation, amplitude respiratoire).
- Lecture des erreurs avec un physicien.
- **Jalon M4** : rapport d'évaluation (**L6**).

## Phase 5 : Visualisation et prototype clinique
- Interface de visualisation : coupes, vues sagittale et coronale, superposition des zones suspectes (**L7**).
- Prototype d'intégration : Orthanc local → MONAI Deploy / service DICOM, restitution DICOM SEG ou SR (**L8**).
- **Jalon M5** : démonstration de bout en bout sur un examen.

## Phase 6 : Clôture
- Documentation technique et utilisateur (**L9**).
- Présentation finale et démonstration (**L10**).
- Liste des limites et des pistes de poursuite.
