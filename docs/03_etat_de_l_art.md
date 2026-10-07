# État de l'art (livrable L1) : plan de travail

> Document à compléter au fil de la revue. Les références listées sont des **points de départ à vérifier** (auteurs, année, contenu exact) avant d'être citées dans le livrable final.

## 1. Le scanner 4D en radiothérapie
- Principe : acquisition synchronisée à un signal respiratoire, puis tri rétrospectif des projections ou des coupes en N phases (souvent 10).
- Modes : hélicoïdal à faible pitch ou axial / ciné. Tri par phase ou par amplitude.
- Produits dérivés : MIP, MinIP, AveIP, ITV.
- Rôle dans le workflow : simulation → délinéation → planification → traitement.

## 2. Typologie des artéfacts de mouvement en 4DCT
Catégories souvent décrites dans la littérature, à confronter au vocabulaire des physiciens de l'Institut :
- **Duplication / dédoublement** d'une structure (diaphragme, tumeur).
- **Données manquantes / incomplètes** (structure tronquée).
- **Chevauchement / overlapping**.
- **Flou / blurring**.
- **Discontinuités** entre lits de table ou entre coupes adjacentes (effet « marche d'escalier » visible en sagittal / coronal).
- Causes : respiration irrégulière (amplitude, fréquence, dérive de la ligne de base), mouvement volontaire, erreurs de tri, mauvaise détection des pics du signal.

Point de départ : Yamamoto T. et al., *Retrospective analysis of artifacts in four-dimensional CT images of 50 abdominal and thoracic radiotherapy patients*, IJROBP, 2008. Étude souvent citée pour la fréquence élevée des artéfacts en 4DCT et pour sa classification.

## 3. Détection automatique : familles d'approches
- **Méthodes classiques** : métriques de similarité ou de discontinuité entre coupes adjacentes, analyse du signal respiratoire (irrégularité), cohérence entre phases (recalage).
- **Apprentissage supervisé** : CNN 2D / 2.5D / 3D pour classer une coupe, une phase ou un examen. Localisation par carte d'activation (Grad-CAM), détection ou segmentation.
- **Détection d'anomalies / non supervisé** : auto-encodeurs ou modèles génératifs entraînés sur des images « propres ».
- **Données synthétiques** : simulation d'artéfacts sur des 4DCT propres (permutation de coupes entre phases, perturbation du signal respiratoire) pour pallier le manque d'annotations.
- **Approches voisines** : contrôle qualité automatique en IRM (mouvement) et en CT, réduction / correction d'artéfacts 4DCT (utile pour les méthodes de simulation).

## 4. Jeux de données publics à explorer
À vérifier : licence, disponibilité, présence d'artéfacts.
- DIR-Lab 4DCT (cas thoraciques avec landmarks).
- Collections 4D-Lung et autres collections 4DCT sur The Cancer Imaging Archive (TCIA).
- POPI-model.

## 5. Outils et écosystème
- **DICOM** : pydicom, SimpleITK, dcm2niix, highdicom (création DICOM SEG / SR).
- **Anonymisation** : profils de dé-identification DICOM PS3.15 (Annexe E), deid, outils de type CTP.
- **Deep learning** : PyTorch, MONAI (transforms, réseaux 3D), MONAI Label (annotation assistée), MONAI Deploy (packaging d'applications cliniques).
- **PACS de développement** : Orthanc. Visualisation : 3D Slicer, OHIF.

## 6. Synthèse et positionnement
_À rédiger : quelles lacunes le projet adresse, quelle approche est retenue et pourquoi._

## Bibliographie
_Format : auteurs, titre, revue / conférence, année, DOI. Une ligne par référence vérifiée._
