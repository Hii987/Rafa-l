"""
Vérifie l'intégrité d'un dataset produit par build_dataset.py, avant d'entraîner.

Contrôles :
  - chaque cas a tous ses canaux + son label, avec la même géométrie ;
  - les labels ne contiennent que 0, 1, 2 ; les cas « clean » ont un label vide ;
  - aucun patient n'apparaît dans deux folds différents, ni à la fois en train et en test ;
  - splits_final.json couvre exactement les cas d'entraînement ;
  - numTraining de dataset.json est cohérent.

Usage : python verify_dataset.py /chemin/nnUNet_raw/Dataset501_4DCTArtifacts
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import SimpleITK as sitk


def main(ds_dir: str):
    ds = Path(ds_dir)
    meta = list(csv.DictReader(open(ds / "metadata.csv")))
    dj = json.loads((ds / "dataset.json").read_text())
    splits = json.loads((ds / "splits_final.json").read_text())
    n_ch = len(dj["channel_names"])
    errors = []

    for r in meta:
        img_dir, lab_dir = ("imagesTr", "labelsTr") if r["split"] == "train" else ("imagesTs", "labelsTs")
        lab_path = ds / lab_dir / f"{r['case_id']}.nii.gz"
        if not lab_path.exists():
            errors.append(f"label manquant : {lab_path.name}")
            continue
        lab = sitk.ReadImage(str(lab_path))
        arr = sitk.GetArrayFromImage(lab)
        vals = set(np.unique(arr).tolist())
        if not vals <= {0, 1, 2}:
            errors.append(f"{r['case_id']} : valeurs de label inattendues {vals}")
        if r["kind"] == "clean" and arr.any():
            errors.append(f"{r['case_id']} : cas propre avec label non vide")
        if r["kind"] == "artifact" and not arr.any():
            errors.append(f"{r['case_id']} : cas artefacté avec label vide")
        for c in range(n_ch):
            p = ds / img_dir / f"{r['case_id']}_{c:04d}.nii.gz"
            if not p.exists():
                errors.append(f"canal manquant : {p.name}")
                continue
            im = sitk.ReadImage(str(p))
            if im.GetSize() != lab.GetSize() or not np.allclose(im.GetSpacing(), lab.GetSpacing()):
                errors.append(f"{p.name} : géométrie différente du label")

    # fuites patient
    pat_folds = defaultdict(set)
    for r in meta:
        pat_folds[r["patient_id"]].add(r["fold"] if r["split"] == "train" else "TEST")
    for p, f in pat_folds.items():
        if len(f) > 1:
            errors.append(f"FUITE : patient {p} présent dans {sorted(f)}")

    train_ids = {r["case_id"] for r in meta if r["split"] == "train"}
    case_pat = {r["case_id"]: r["patient_id"] for r in meta}
    for i, s in enumerate(splits):
        if set(s["train"]) | set(s["val"]) != train_ids:
            errors.append(f"fold {i} : ne couvre pas exactement les cas d'entraînement")
        if {case_pat[c] for c in s["train"]} & {case_pat[c] for c in s["val"]}:
            errors.append(f"fold {i} : un patient est à la fois en train et en val")
    if dj["numTraining"] != len(train_ids):
        errors.append(f"numTraining={dj['numTraining']} mais {len(train_ids)} cas d'entraînement")

    # résumé
    by = defaultdict(int)
    for r in meta:
        by[(r["split"], r["kind"])] += 1
    print("Répartition :", dict(by))
    types = defaultdict(int)
    for r in meta:
        for t in filter(None, r["event_types"].split("|")):
            types[t] += 1
    print("Événements simulés :", dict(types))
    print(f"Patients : {len(pat_folds)} ; folds : {len(splits)} ; canaux : {n_ch}")
    if errors:
        print(f"\n{len(errors)} PROBLÈME(S) :")
        for e in errors[:50]:
            print("  -", e)
        sys.exit(1)
    print("\nOK : aucun problème détecté.")


if __name__ == "__main__":
    main(sys.argv[1])
