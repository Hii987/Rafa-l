# Architecture cible

> Vision cible, à affiner. Chaque choix structurant fera l'objet d'une ADR dans `docs/decisions/`.

## Vue d'ensemble

```
            ┌─────────────────────────────────────────────────────────────┐
            │                     Environnement Institut                  │
 PACS ─────▶│  Import DICOM ─▶ Anonymisation ─▶ Préparation 4D ─▶ Modèle  │
            │                                                     │       │
            │                     Visualisation ◀── Résultats ◀───┘       │
            │                        (app/)        (scores, localisation) │
            │                                         │                   │
            │                                         ▼                   │
 PACS ◀─────│                         Export DICOM SEG / SR / rapport      │
            └─────────────────────────────────────────────────────────────┘
```

## Modules prévus (`src/`)

| Module | Rôle |
|---|---|
| `io` | Lecture des séries DICOM, regroupement par phase (tags, descriptions de série, tags privés) |
| `anonymization` | Dé-identification, remappage des UIDs, journalisation |
| `preprocessing` | Rééchantillonnage, fenêtrage HU, reconstruction du volume 4D (phase × z × y × x) |
| `simulation` | Génération d'artéfacts synthétiques sur volumes propres (optionnel) |
| `datasets` | Datasets / transforms MONAI, splits par patient |
| `models` | Baselines et réseaux de détection / localisation |
| `training` / `evaluation` | Entraînement, métriques, rapports |
| `export` | Restitution des résultats en DICOM (SEG / SR / Secondary Capture) |

## Pistes de modélisation
1. **Baseline sans apprentissage** : score de discontinuité entre coupes adjacentes (différences, NCC, gradient cranio-caudal) par phase. Un pic de score signale une coupe suspecte.
2. **Classification 2D / 2.5D** sur des coupes sagittales et coronales reformatées, où les artéfacts sont les plus visibles. Localisation par Grad-CAM ou par score coupe à coupe.
3. **Modèle 3D / 4D** exploitant la cohérence entre phases.
4. **Détection d'anomalies** entraînée sur des examens jugés propres, si les annotations positives sont rares.

## Intégration clinique (livrable L8)
- **Développement** : PACS local **Orthanc** alimenté avec des données anonymisées.
- **Packaging** : MONAI Deploy App SDK (application packagée en conteneur), ou service Python déclenché à la réception d'une série.
- **Restitution** : DICOM SEG (zones suspectes) et/ou DICOM SR (verdict, scores), relisibles dans le PACS / viewer. Alternative : Secondary Capture avec superposition.
- **Contraintes** : pas de modification des séries d'origine. Résultats clairement marqués « aide à la décision, non validé cliniquement ».

## Visualisation (livrable L7)
Options à comparer : application web légère (Streamlit / Gradio), extension OHIF, module 3D Slicer.
Contenu minimal : navigation dans les phases et les coupes, vues sagittale et coronale, surlignage des plages suspectes, score par phase, verdict global.
