# Entraîner le modèle sur Kaggle

Ce guide permet à chaque membre de l'équipe d'entraîner le modèle de détection d'artefacts (nnU-Net v2) **gratuitement sur un GPU Kaggle**, sans rien installer sur son ordinateur. Il s'utilise avec le notebook d'entraînement de l'équipe.

Kaggle évolue souvent (quotas, durées, menus). Les valeurs ci-dessous étaient justes au moment de la rédaction : vérifie-les sur ton compte en cas de doute.

## En résumé

```
1. Une personne construit le dataset (sur son ordinateur)       → Dataset501_4DCTArtifacts/
2. Elle l'envoie sur Kaggle en « Dataset » privé partagé        → visible par toute l'équipe
3. Chacun importe le notebook d'entraînement de l'équipe dans Kaggle
4. Chacun entraîne UN fold (0 à 4) sur GPU                      → 5 modèles en parallèle
5. On regroupe les 5 folds                                      → ensemble final
```

## 0. Prérequis (une fois par personne)

1. Créer un compte sur [kaggle.com](https://www.kaggle.com).
2. **Vérifier son numéro de téléphone** : *Settings* → *Phone verification*. Sans ça, pas de GPU et pas d'accès Internet dans les notebooks.
3. Quota GPU : environ **30 h par semaine**, visible dans *Settings*. Une session dure au maximum **12 h** environ.

## 1. Construire le dataset (une seule personne)

Sur son ordinateur, depuis le dépôt cloné (moins de 10 Go de téléchargement) :

```bash
pip install -r requirements.txt
cd src
python download_4dct.py --dataset 4d_lung --one-per-patient --max-gb 9.5 --out ../data
python inspect_dicom.py ../data/4d_lung
python build_dataset.py --source dicom --input ../data/4d_lung --out ../dataset \
       --phases 0,50 --n-artifact 1 --crop-body
python verify_dataset.py ../dataset/Dataset501_4DCTArtifacts
```

Le dossier à partager est `dataset/Dataset501_4DCTArtifacts`. Il contient `dataset.json`, `imagesTr/`, `labelsTr/`, `imagesTs/`, `labelsTs/`, `splits_final.json` et `metadata.csv`.

> Pour tester sans attendre le téléchargement, on peut d'abord générer un dataset fantôme :
> `python build_dataset.py --source phantom --n-phantoms 6 --out ../dataset_phantom`.
> Il sert **uniquement à vérifier que tout marche**, jamais à entraîner le modèle final.

## 2. Mettre le dataset sur Kaggle (la même personne)

### Option A : par le site (le plus simple)
1. Compresser le dossier : clic droit sur `Dataset501_4DCTArtifacts` → *Compresser* (macOS) → `Dataset501_4DCTArtifacts.zip`.
2. Sur Kaggle : *Create* → *New Dataset* → glisser le `.zip`.
3. Titre : par exemple `4dct-artifacts-dataset501`.
4. Laisser le dataset en **Private**.
5. Une fois créé : onglet *Settings* du dataset → *Sharing* → ajouter chaque membre de l'équipe (pseudo Kaggle ou email).

### Option B : en ligne de commande
```bash
pip install kaggle
# Kaggle → Settings → API → « Create New Token » : place le fichier kaggle.json dans ~/.kaggle/
mkdir kaggle_upload && cd kaggle_upload
zip -r Dataset501_4DCTArtifacts.zip ../dataset/Dataset501_4DCTArtifacts
kaggle datasets init -p .        # crée dataset-metadata.json : y mettre un titre et "id": "<pseudo>/4dct-artifacts-dataset501"
kaggle datasets create -p .      # privé par défaut
```
Ensuite, partager le dataset avec l'équipe comme à l'étape A.5.

Pourquoi un dataset privé ? Les images viennent de TCIA, qui est public et anonymisé, mais leur redistribution suit les conditions de TCIA. On garde donc le dataset privé, réservé à l'équipe.

## 3. Ouvrir le notebook d'entraînement (chaque membre)

1. Sur Kaggle : *Create* → *New Notebook* → *File* → *Import Notebook* → choisir le notebook d'entraînement de l'équipe.
2. Panneau de droite :
   - *Session options* → *Accelerator* → **GPU T4 x2** ou **GPU P100** ;
   - *Session options* → *Internet* → **On** (pour installer nnU-Net) ;
   - *Input* → *Add Input* → chercher le dataset partagé à l'étape 2 → *Add*.
3. Dans le notebook, régler ton numéro de **fold** (voir la répartition ci-dessous) et la **durée d'entraînement** (voir section 5).

### Commandes nnU-Net de référence

Dans un notebook Kaggle, le dataset ajouté en *Input* est en **lecture seule** dans `/kaggle/input/…`, et seul `/kaggle/working` est sauvegardé. Une organisation qui fonctionne :

```python
import os
os.environ["nnUNet_raw"] = "/tmp/nnUNet_raw"                  # contient Dataset501_4DCTArtifacts (copie ou lien vers /kaggle/input/…)
os.environ["nnUNet_preprocessed"] = "/tmp/nnUNet_preprocessed"  # gros fichiers, pas besoin de les sauvegarder
os.environ["nnUNet_results"] = "/kaggle/working/nnUNet_results" # sauvegardé à la fin d'un Commit
```

```bash
pip install nnunetv2
nnUNetv2_plan_and_preprocess -d 501 -c 3d_fullres --verify_dataset_integrity
# IMPORTANT : remplacer les folds automatiques par NOS folds groupés par patient
cp $nnUNet_raw/Dataset501_4DCTArtifacts/splits_final.json $nnUNet_preprocessed/Dataset501_4DCTArtifacts/
nnUNetv2_train 501 3d_fullres <FOLD> -tr <TRAINER>
```

### Répartition des folds dans l'équipe

`splits_final.json` découpe les patients d'entraînement en 5 folds, **groupés par patient**. Chacun entraîne un fold différent :

| Fold | Membre |
|---|---|
| 0 | _à compléter_ |
| 1 | _à compléter_ |
| 2 | _à compléter_ |
| 3 | _à compléter_ |
| 4 | _à compléter_ |

## 4. Lancer l'entraînement

- **Pour tester** (quelques minutes) : trainer `nnUNetTrainer_1epoch`, puis *Run All*. Le notebook doit aller jusqu'au bout sans erreur.
- **Pour le vrai entraînement** : *Save Version* → **Save & Run All (Commit)**. Le notebook tourne en arrière-plan (on peut fermer l'onglet), jusqu'à 12 h environ. À la fin, tout ce qui est dans `/kaggle/working` est sauvegardé dans l'onglet *Output* de la version.

> ⚠️ En mode interactif (cellule par cellule), **rien n'est sauvegardé** quand la session s'arrête. Pour un entraînement long, il faut toujours passer par *Save & Run All (Commit)*.

## 5. Choisir la durée d'entraînement

Par défaut, nnU-Net fait **1000 epochs**, souvent trop long pour une session Kaggle. On choisit donc un trainer de durée fixe, livré avec nnU-Net (option `-tr`) :

| `TRAINER` | Epochs |
|---|---|
| `nnUNetTrainer_1epoch` | 1 (test) |
| `nnUNetTrainer_50epochs` | 50 |
| `nnUNetTrainer_100epochs` | 100 |
| `nnUNetTrainer_250epochs` | 250 |
| `nnUNetTrainer_500epochs` | 500 |
| `nnUNetTrainer` | 1000 (défaut) |

**Méthode** : lancer d'abord `nnUNetTrainer_1epoch`, lire la ligne `Epoch time: … s` dans la sortie, puis choisir le trainer qui tient dans **~11 h** (marge de sécurité) :
`nombre d'epochs ≈ 11 × 3600 / temps d'une epoch`.

**Tout le monde dans l'équipe doit utiliser le même trainer**, sinon les 5 folds ne sont pas comparables.

### Reprendre un entraînement interrompu
nnU-Net sauvegarde un point de reprise (`checkpoint_latest.pth`) toutes les 50 epochs. Pour continuer dans une nouvelle session :
1. *Add Input* → onglet *Your Work* → choisir **la version précédente de ton propre notebook** (son *Output* contient `nnUNet_results`).
2. Recopier ce dossier `nnUNet_results` dans `/kaggle/working/`, puis relancer avec le **même** fold, le **même** trainer et l'option `--c` :
   `nnUNetv2_train 501 3d_fullres <FOLD> -tr <TRAINER> --c`

## 6. Récupérer et comparer les résultats

Dans l'onglet *Output* de la version terminée :
- `nnUNet_results/Dataset501_4DCTArtifacts/<TRAINER>__nnUNetPlans__3d_fullres/fold_<N>/` contient :
  - `checkpoint_final.pth`, le modèle entraîné ;
  - `progress.png`, les courbes de loss et de Dice à regarder en premier ;
  - `validation/summary.json`, les scores sur la validation du fold ;
- scores sur le **jeu de test** (patients jamais vus) :
  ```bash
  nnUNetv2_predict -i $nnUNet_raw/Dataset501_4DCTArtifacts/imagesTs -o /kaggle/working/test_pred_fold<N> \
                   -d 501 -c 3d_fullres -tr <TRAINER> -f <N>
  nnUNetv2_evaluate_folder $nnUNet_raw/Dataset501_4DCTArtifacts/labelsTs /kaggle/working/test_pred_fold<N> \
                   -djfile <dossier_du_trainer>/dataset.json -pfile <dossier_du_trainer>/plans.json
  ```
  Les scores sont écrits dans `test_pred_fold<N>/summary.json`.

Reporter les scores (Dice moyen par label : 1 = DS, 2 = INT) dans `reports/` avec la version du dataset, le trainer et le fold. Voir [07_evaluation.md](07_evaluation.md).

### Ensemble des 5 folds
Quand les 5 folds sont finis, une personne :
1. ajoute en *Input* les 5 notebooks (outputs) de l'équipe ;
2. copie les 5 dossiers `fold_X` dans un même dossier `nnUNet_results/.../<TRAINER>__nnUNetPlans__3d_fullres/` ;
3. lance la prédiction avec tous les folds :
   ```bash
   nnUNetv2_predict -i <imagesTs> -o pred_ensemble -d 501 -c 3d_fullres -tr <TRAINER> -f 0 1 2 3 4
   ```

## Problèmes fréquents

| Symptôme | Cause / solution |
|---|---|
| `pip install` échoue, pas d'Internet | *Internet* sur **On** (téléphone vérifié obligatoire) |
| nnU-Net ne trouve pas `Dataset501_4DCTArtifacts` | Le dataset n'est pas ajouté en *Input*, ou `nnUNet_raw` ne pointe pas vers le dossier qui le contient |
| `CUDA out of memory` | Choisir **GPU P100** ou **T4 x2**, pas de GPU plus petit. Ne lancer qu'un entraînement à la fois |
| La session s'arrête avant la fin | Choisir un trainer plus court, ou reprendre avec `--c` (section 5) |
| Résultats perdus | L'entraînement a été lancé en interactif : utiliser *Save & Run All (Commit)* |
| `No space left on device` | Les données prétraitées sont dans `/tmp` (non sauvegardé, grand disque). Ne rien copier d'autre dans `/kaggle/working` (limité à ~20 Go) |
