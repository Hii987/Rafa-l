"""
Planche de contrôle visuel : pour quelques cas artefactés, affiche en vue
CORONALE (celle qu'utilisent les physiciens) :
  phase propre | phase corrompue | label (rouge = DS, bleu = INT) | |différence|
avec les frontières des blocs affectés en pointillés.

À montrer au physicien : s'il ne distingue pas les artefacts simulés de vrais
artefacts, la simulation est assez réaliste.

Usage : python preview.py /chemin/Dataset501_4DCTArtifacts --n 6 --out preview.png
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import SimpleITK as sitk


def load(p):
    return sitk.GetArrayFromImage(sitk.ReadImage(str(p))).astype(np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ds_dir")
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--out", default="preview.png")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    ds = Path(args.ds_dir)
    meta = list(csv.DictReader(open(ds / "metadata.csv")))
    arts = [r for r in meta if r["kind"] == "artifact"]
    rng = np.random.default_rng(args.seed)
    # prendre des cas variés : au moins un DS_overlap, un DS_duplicate, un INT si possible
    picked = []
    for t in ("DS_overlap", "DS_duplicate", "INT"):
        c = [r for r in arts if t in r["event_types"] and r not in picked]
        if c:
            picked.append(c[int(rng.integers(len(c)))])
    rest = [r for r in arts if r not in picked]
    rng.shuffle(rest)
    picked += rest[: max(0, args.n - len(picked))]

    fig, axes = plt.subplots(len(picked), 4, figsize=(13, 3.3 * len(picked)))
    axes = np.atleast_2d(axes)
    for row, r in zip(axes, picked):
        d_img, d_lab = ("imagesTr", "labelsTr") if r["split"] == "train" else ("imagesTs", "labelsTs")
        clean_id = r["case_id"].rsplit("_art", 1)[0] + "_clean"
        corrupted = load(ds / d_img / f"{r['case_id']}_0000.nii.gz")
        lab = load(ds / d_lab / f"{r['case_id']}.nii.gz")
        clean_path = ds / d_img / f"{clean_id}_0000.nii.gz"
        clean = load(clean_path) if clean_path.exists() else corrupted
        # coupe coronale qui contient le plus de voxels labellisés
        y = int(np.argmax((lab > 0).sum(axis=(0, 2))))
        sz, sy, sx = (float(v) for v in r["spacing_zyx"].split("x"))
        aspect = sz / sx
        # tête en haut : si la tête est du côté des z élevés, l'indice 0 va en bas
        origin = "lower" if r.get("head_at_high_z") == "True" else "upper"
        win = dict(cmap="gray", vmin=-1000, vmax=300, aspect=aspect, origin=origin)
        row[0].imshow(clean[:, y, :], **win)
        row[1].imshow(corrupted[:, y, :], **win)
        row[2].imshow(corrupted[:, y, :], **win)
        ov = np.zeros(lab[:, y, :].shape + (4,))
        ov[lab[:, y, :] == 1] = (1, 0.15, 0.15, 0.55)
        ov[lab[:, y, :] == 2] = (0.2, 0.5, 1, 0.55)
        row[2].imshow(ov, aspect=aspect, origin=origin)
        row[3].imshow(np.abs(corrupted - clean)[:, y, :], cmap="magma", vmin=0, vmax=600, aspect=aspect, origin=origin)
        for e in json.loads(r["events_json"]):
            for a in row[1:]:
                for z in (e["z0"] - 0.5, e["z1"] - 0.5):
                    a.axhline(z, ls=":", lw=0.8, color="yellow" if e["kind"].startswith("DS") else "cyan")
        row[0].set_ylabel(f"{r['case_id']}\n{r['event_types']}", fontsize=7)
        for a, t in zip(row, ["propre", "corrompue", "label (rouge DS / bleu INT)", "|différence| HU"]):
            a.set_title(t, fontsize=9)
            a.set_xticks([]); a.set_yticks([])
    fig.suptitle("Vue coronale — tête en haut, pointillés = blocs (positions de table) modifiés", fontsize=10)
    fig.tight_layout()
    fig.savefig(args.out, dpi=110)
    print("écrit :", args.out)


if __name__ == "__main__":
    main()
