# Dataset d'artefacts 4DCT simulés — Institut Rafaël × aivancity

Génère un jeu d'entraînement **propre / avec artefacts** à partir de scanners 4D,
avec une vérité terrain voxel par voxel, directement au format **nnU-Net v2**
(utilisable aussi avec MONAI / Swin UNETR).

## Par où commencer (4 commandes, moins de 10 Go)

```bash
# 0. Installer les dépendances (une seule fois)
pip install -r requirements.txt

# 1. Télécharger 15 vrais 4DCT (15 patients différents de TCIA 4D-Lung, ~9,1 Go)
python download_4dct.py --dataset 4d_lung --one-per-patient --max-gb 9.5 --out data

# 2. Vérifier ce qui a été téléchargé (patients, phases, nombre de coupes)
python inspect_dicom.py data/4d_lung

# 3. Fabriquer le jeu d'entraînement (cas propres + cas avec artefacts)
python build_dataset.py --source dicom --input data/4d_lung --out dataset \
       --phases 0,50 --n-artifact 1 --crop-body

# 4. Contrôler le résultat, puis regarder l'image produite
python verify_dataset.py dataset/Dataset501_4DCTArtifacts
python preview.py dataset/Dataset501_4DCTArtifacts --out apercu.png
```

Ajouter `--dry-run` à l'étape 1 pour voir la sélection sans rien télécharger.

## Installation

```bash
pip install -r requirements.txt
```

## Récupérer les données publiques

Toutes les sources sont des **vrais scanners de patients**, en 3D (chaque phase
est un volume 3D complet) et en 4D (toutes les phases d'une respiration).

| Jeu | Type | Patients / examens | Taille | Accès |
|---|---|---|---|---|
| TCIA 4D-Lung | 4DCT Philips, 10 phases | 20 / 80 | 46,6 Go | `download_4dct.py --dataset 4d_lung` |
| TCIA CT-vs-PET-Ventilation | 4DCT Siemens (série unique) | 20 / 20 | 8,5 Go | `--dataset ctvspet` |
| TCIA RIDER Lung PET-CT | 4DCT GE, 6 ou 10 phases | 5 / 5 | 1,4 Go | `--dataset rider` |
| DIR-Lab | 4DCT, 10 phases | 10 / 10 | ~1 Go | formulaire gratuit, puis `convert_dirlab.py` |
| POPI (CREATIS Lyon) | 4DCT, 10 phases | quelques cas | < 1 Go | site CREATIS, fichiers `.mhd` lus directement |
| CT-vs-PET (apnée) | 3D insp. + exp. | 20 | 3,5 Go | `--dataset ctvspet_bh` |
| LCTSC | 3D thorax | 60 | 4,9 Go | `--dataset lctsc` |
| NSCLC-Radiomics | 3D thorax | 422 | 26,3 Go | `--dataset nsclc` |

Les quatre premiers jeux 4D (4D-Lung, CT-vs-PET, DIR-Lab, POPI) sont les jeux
publics utilisés par Cisneros et al. 2025.

```bash
pip install idc-index
python download_4dct.py --list                                   # tout voir, sans télécharger
python download_4dct.py --dataset 4d_lung --max-patients 2 --out data/   # premier essai (~1,2 Go)
python inspect_dicom.py data/4d_lung                             # vérifier les phases trouvées
```

Points d'attention :
- 4D-Lung contient aussi 507 **4D-CBCT** (130 Go) : le script de téléchargement
  et le chargeur les excluent automatiquement.
- Plusieurs 4DCT par patient dans 4D-Lung (jusqu'à 8) : le découpage train/test
  par patient est indispensable, il est fait par `build_dataset.py`.
- CT-vs-PET range toutes les phases dans **une seule série** : `io4d.py` la découpe
  automatiquement ; `inspect_dicom.py` indique quelle méthode a été utilisée.
  À vérifier visuellement sur le premier cas.
- Ces 4DCT cliniques contiennent déjà de **vrais artefacts** (fréquents) : c'est
  une bonne chose pour l'évaluation, à condition de les repérer (scores QC + revue).

## Démarrage rapide

```bash
# 1. Tester tout le pipeline sans aucune donnée (fantômes synthétiques)
python build_dataset.py --source phantom --n-phantoms 6 --out out_phantom
python verify_dataset.py out_phantom/Dataset501_4DCTArtifacts
python preview.py out_phantom/Dataset501_4DCTArtifacts --out preview.png

# 2. Sur TCIA 4D-Lung
python download_4dct.py --dataset 4d_lung --max-patients 5 --out /data
python inspect_dicom.py /data/4d_lung                  # vérifier les phases détectées
python build_dataset.py --source dicom --input /data/4d_lung \
       --out $nnUNet_raw --phases 0,20,50,70 --n-artifact 2 --context 1 --crop-body
python verify_dataset.py $nnUNet_raw/Dataset501_4DCTArtifacts
python preview.py $nnUNet_raw/Dataset501_4DCTArtifacts --out preview_4dlung.png
```

## Ce que produit le script

```
Dataset501_4DCTArtifacts/
├── dataset.json          # 3 canaux "CT", labels 0 fond / 1 DS / 2 INT
├── imagesTr/  {cas}_0000.nii.gz   phase analysée (corrompue ou non)
│              {cas}_0001.nii.gz   phase P-1 (propre)
│              {cas}_0002.nii.gz   phase P+1 (propre)
├── labelsTr/  {cas}.nii.gz        masque d'artefact voxel par voxel
├── imagesTs/, labelsTs/           patients réservés au test (jamais vus)
├── splits_final.json              5 folds GROUPÉS PAR PATIENT
└── metadata.csv                   1 ligne par cas (type, coupes touchées, scores QC…)
```

Pour chaque phase cible : **1 cas propre** + **N cas artefactés** (`--n-artifact`).

## Comment les artefacts sont simulés

Un 4DCT est acquis par blocs le long de z (positions de table). Les artefacts
sont donc insérés **par blocs alignés sur des frontières de table**
(`--couch-mm`, 20 mm par défaut ; à régler sur le protocole de l'Institut).

| Type | Simulation | Label |
|---|---|---|
| `DS_overlap` | bloc remplacé par le même bloc d'une autre phase | 1 |
| `DS_duplicate` | idem, mais décalé en z → structures dédoublées | 1 |
| `INT` | intérieur du bloc remplacé par une interpolation linéaire, bruit ré-injecté | 2 |

Choix importants, pour que le modèle apprenne l'anatomie et pas un raccourci :

- **La phase source d'un DS n'est jamais une phase voisine** (écart ≥ 2 phases) : les
  voisines sont des canaux d'entrée, le réseau pourrait sinon repérer une simple copie.
- **Pas de changement du niveau de bruit** : rien n'est ajouté aux blocs DS ; pour INT,
  on ré-injecte exactement le bruit que l'interpolation a fait disparaître
  (bruit estimé sur l'image elle-même).
- **Seuls les voxels réellement modifiés (> 100 HU) dans la zone pulmonaire élargie
  sont labellisés.** Un artefact inséré dans une zone immobile est invisible : il est
  rejeté plutôt que labellisé à tort.

## Contrôle qualité (`qc.py`)

Les données cliniques contiennent souvent déjà de vrais artefacts : une phase
« propre » ne l'est pas forcément. Deux scores sont calculés pour chaque phase :

- `score_binning` : discontinuité entre coupes **absente des phases voisines** ;
- `score_interp` : coupes anormalement linéaires le long de z.

Les phases propres au-dessus des seuils sont marquées `suspicious_clean` dans
`metadata.csv` (ou exclues avec `--skip-suspicious`). **Les seuils par défaut
(1,3 et 1,5) ont été réglés sur le fantôme : il faut les recalibrer sur 4D-Lung**
en regardant la distribution des scores et quelques cas visuellement.

Sur le fantôme, ces scores donnent déjà un baseline : AUC ≈ 0,89 pour DS et
1,0 pour INT (le fantôme est beaucoup plus facile que des données réelles).

## Entraîner avec nnU-Net

```bash
nnUNetv2_plan_and_preprocess -d 501 --verify_dataset_integrity
# IMPORTANT : utiliser NOS folds groupés par patient
cp $nnUNet_raw/Dataset501_4DCTArtifacts/splits_final.json $nnUNet_preprocessed/Dataset501_4DCTArtifacts/
nnUNetv2_train 501 3d_fullres 0      # puis folds 1 à 4
nnUNetv2_predict -i $nnUNet_raw/Dataset501_4DCTArtifacts/imagesTs -o pred_test \
                 -d 501 -c 3d_fullres --save_probabilities
```

## Limites connues

- Les phases voisines (canaux 1 et 2) sont laissées propres ; sur données réelles,
  elles peuvent elles aussi contenir des artefacts.
- La simulation suppose un mode ciné (blocs). En hélicoïdal, les frontières sont
  moins nettes : à valider avec le physicien.
- **Le fantôme sert uniquement à tester le code.** Il n'est pas réaliste et ne doit
  pas servir à entraîner le modèle final.
- Volume disque : sans `--crop-body`, un cas clinique 3 canaux (≈ 100 × 512 × 512)
  pèse environ 300 Mo en mémoire, nettement moins en `.nii.gz`. Utiliser
  `--crop-body` et limiter `--phases` au début.

## Fichiers

| Fichier | Rôle |
|---|---|
| `io4d.py` | lecture DICOM (tri en z, HU, 4DCT en une ou plusieurs séries, exclusion CBCT) et NIfTI/MHD |
| `simulate.py` | masques poumon/corps, générateur d'artefacts DS / INT |
| `qc.py` | scores de discontinuité (QC + baseline) |
| `phantom.py` | fantôme thoracique 4D synthétique pour les tests |
| `build_dataset.py` | construction du dataset nnU-Net + splits par patient |
| `verify_dataset.py` | vérification d'intégrité avant entraînement |
| `preview.py` | planche coronale propre / corrompu / label / différence |
| `inspect_dicom.py` | inventaire d'un export DICOM avant traitement |
| `download_4dct.py` | téléchargement des jeux publics (IDC / TCIA) |
| `convert_dirlab.py` | conversion des fichiers bruts DIR-Lab en NIfTI |
