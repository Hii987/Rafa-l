"""
Construit un jeu d'entraînement « propre / avec artefacts » à partir de 4DCT,
directement au format nnU-Net v2 (utilisable aussi avec MONAI / Swin UNETR).

Pour chaque 4DCT et chaque phase cible P :
  - 1 cas PROPRE     : la phase P telle quelle, label vide ;
  - N cas ARTEFACTÉS : la phase P corrompue (DS et/ou INT), label voxel par voxel.
Canaux d'entrée : canal 0 = phase P, puis les phases voisines (P-1, P+1, ...)
non corrompues, pour que le réseau puisse comparer les états respiratoires.

Le découpage train/val/test se fait PAR PATIENT (jamais par cas), pour éviter
qu'un même patient se retrouve à la fois en entraînement et en évaluation.

Exemples
--------
# Test complet sur fantômes synthétiques (aucune donnée nécessaire)
python build_dataset.py --source phantom --n-phantoms 6 --out out_phantom

# TCIA 4D-Lung (dossier DICOM téléchargé avec NBIA Data Retriever)
python build_dataset.py --source dicom --input /data/4D-Lung --out /data/nnUNet_raw \\
       --phases 0,20,50,70 --n-artifact 2 --context 1 --crop-body

# Un dossier par 4DCT, un NIfTI par phase (…_00.nii.gz … _90.nii.gz)
python build_dataset.py --source nifti --input /data/nifti_4dct --out /data/nnUNet_raw
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import time
from pathlib import Path

import numpy as np

from io4d import Scan4D, load_dicom_4dct, load_nifti_4dct, save_nifti
from qc import scores as qc_scores
from simulate import SimConfig, body_mask, region_of_interest, simulate_artifacts, slice_labels


def safe(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9-]", "-", s)


def iter_scans(args):
    if args.source == "phantom":
        from phantom import make_phantom
        for i in range(args.n_phantoms):
            yield make_phantom(seed=args.seed * 1000 + i)
    elif args.source == "dicom":
        for s in load_dicom_4dct(args.input):
            yield s
    elif args.source == "nifti":
        for d in sorted(p for p in Path(args.input).iterdir() if p.is_dir()):
            yield load_nifti_4dct(d)
    else:
        raise ValueError(args.source)


def body_bbox(scan: Scan4D, margin: int = 4):
    m = body_mask(scan.vol.mean(0))
    idx = np.argwhere(m)
    lo = np.maximum(idx.min(0) - margin, 0)
    hi = np.minimum(idx.max(0) + margin + 1, m.shape)
    return tuple(slice(int(a), int(b)) for a, b in zip(lo, hi))


def z_ranges(sl: np.ndarray) -> str:
    """[0,0,1,1,1,0,2,2] -> '2-4:DS;6-7:INT' (bornes incluses)."""
    names = {1: "DS", 2: "INT"}
    out, z = [], 0
    while z < len(sl):
        if sl[z]:
            k = z
            while k + 1 < len(sl) and sl[k + 1] == sl[z]:
                k += 1
            out.append(f"{z}-{k}:{names[int(sl[z])]}")
            z = k + 1
        else:
            z += 1
    return ";".join(out)


def assign_splits(patients: list[str], test_frac: float, folds: int, rng):
    pats = sorted(set(patients))
    rng.shuffle(pats)
    n_test = int(round(test_frac * len(pats))) if test_frac > 0 else 0
    if test_frac > 0 and len(pats) >= 3:
        n_test = max(1, n_test)
    test = set(pats[:n_test])
    train = pats[n_test:]
    fold_of = {p: i % folds for i, p in enumerate(train)}
    return test, fold_of


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", choices=["phantom", "dicom", "nifti"], required=True)
    ap.add_argument("--input", help="dossier source (dicom / nifti)")
    ap.add_argument("--out", required=True, help="dossier racine nnUNet_raw")
    ap.add_argument("--dataset-id", type=int, default=501)
    ap.add_argument("--dataset-name", default="4DCTArtifacts")
    ap.add_argument("--phases", default="all", help="phases cibles en %%, ex. '0,20,50,70' ou 'all'")
    ap.add_argument("--n-artifact", type=int, default=2, help="versions artefactées par phase cible")
    ap.add_argument("--context", type=int, default=1, help="phases voisines de chaque côté en canaux (0 = 1 canal)")
    ap.add_argument("--crop-body", action="store_true", help="recadrer sur le corps (réduit fortement la taille disque)")
    ap.add_argument("--hu-min", type=float, default=-1024)
    ap.add_argument("--hu-max", type=float, default=1500)
    ap.add_argument("--couch-mm", type=float, default=20.0, help="couverture d'une position de table (mm)")
    ap.add_argument("--qc-bin-thr", type=float, default=1.3, help="seuil du score de binning (phase propre suspecte au-delà)")
    ap.add_argument("--qc-int-thr", type=float, default=1.5, help="seuil du score d'interpolation")
    ap.add_argument("--skip-suspicious", action="store_true", help="ne pas créer de cas propre pour les phases suspectes")
    ap.add_argument("--test-frac", type=float, default=0.2, help="part des PATIENTS réservés au test")
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--n-phantoms", type=int, default=6)
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)
    cfg = SimConfig(couch_mm=args.couch_mm)
    ds_dir = Path(args.out) / f"Dataset{args.dataset_id:03d}_{args.dataset_name}"
    for sub in ("imagesTr", "labelsTr", "imagesTs", "labelsTs"):
        (ds_dir / sub).mkdir(parents=True, exist_ok=True)
    n_ch = 1 + 2 * args.context

    # Les scans sont traités un par un (un 4DCT clinique pèse ~1 Go en mémoire).
    # On écrit d'abord tout dans imagesTr, puis on déplace les patients de test.
    rows = []
    t0 = time.time()
    for scan in iter_scans(args):
        sid = safe(scan.scan_id)
        P = scan.n_phases
        vol = np.clip(scan.vol, args.hu_min, args.hu_max)
        crop = body_bbox(scan) if args.crop_body else (slice(None),) * 3
        vol = vol[(slice(None),) + crop]
        targets = range(P) if args.phases == "all" else [
            scan.phases.index(int(p)) for p in args.phases.split(",") if int(p) in scan.phases]

        for pi in targets:
            ph = scan.phases[pi]
            roi = region_of_interest(vol[pi], spacing=scan.spacing)
            neigh = [pi]
            for k in range(1, args.context + 1):
                neigh += [(pi - k) % P, (pi + k) % P]
            nb_vols = [vol[(pi - 1) % P], vol[(pi + 1) % P]]
            qc = qc_scores(vol[pi], nb_vols, roi)
            suspicious = qc["score_binning"] > args.qc_bin_thr or qc["score_interp"] > args.qc_int_thr

            def write_case(case_id, target_vol, label, kind, events):
                for c, idx in enumerate(neigh):
                    img = target_vol if c == 0 else vol[idx]
                    save_nifti(np.round(img), scan.spacing, scan.origin, ds_dir / "imagesTr" / f"{case_id}_{c:04d}.nii.gz", np.int16)
                save_nifti(label, scan.spacing, scan.origin, ds_dir / "labelsTr" / f"{case_id}.nii.gz", np.uint8)
                sl = slice_labels(label)
                case_qc = qc if kind == "clean" else qc_scores(target_vol, nb_vols, roi)
                rows.append({
                    "case_id": case_id, "patient_id": safe(scan.patient_id), "scan_id": sid,
                    "phase": ph, "kind": kind, "n_events": len(events),
                    "event_types": "|".join(e.kind for e in events),
                    "affected_slices": z_ranges(sl), "n_affected_slices": int((sl > 0).sum()),
                    "n_slices": int(label.shape[0]),
                    "qc_bin_clean": round(qc["score_binning"], 3), "qc_int_clean": round(qc["score_interp"], 3),
                    "qc_bin_case": round(case_qc["score_binning"], 3), "qc_int_case": round(case_qc["score_interp"], 3),
                    "suspicious_clean": suspicious,
                    "shape_zyx": "x".join(map(str, label.shape)),
                    "spacing_zyx": "x".join(f"{s:.3g}" for s in scan.spacing),
                    "head_at_high_z": scan.head_at_high_z,
                    "events_json": json.dumps([e.to_dict() for e in events]),
                })

            # 1) cas propre
            if not (args.skip_suspicious and suspicious):
                write_case(f"{sid}_ph{ph:02d}_clean", vol[pi], np.zeros(vol[pi].shape, np.uint8), "clean", [])
            # 2) cas avec artefacts
            for k in range(args.n_artifact):
                out, lab, events = simulate_artifacts(vol, pi, scan.spacing, rng, cfg, roi=roi,
                                                     head_at_high_z=scan.head_at_high_z)
                if out is None:
                    continue
                write_case(f"{sid}_ph{ph:02d}_art{k}", out, lab, "artifact", events)
        print(f"[{time.time() - t0:6.0f}s] {sid}: {P} phases, forme {vol.shape[1:]}, cas cumulés = {len(rows)}")

    if not rows:
        raise SystemExit("Aucun cas créé : vérifier --input et le nombre de phases détectées.")

    # Découpage par patient
    test_pats, fold_of = assign_splits([r["patient_id"] for r in rows], args.test_frac, args.folds, rng)
    for r in rows:
        if r["patient_id"] in test_pats:
            r["split"], r["fold"] = "test", ""
            for c in range(n_ch):
                f = f"{r['case_id']}_{c:04d}.nii.gz"
                (ds_dir / "imagesTr" / f).rename(ds_dir / "imagesTs" / f)
            (ds_dir / "labelsTr" / f"{r['case_id']}.nii.gz").rename(ds_dir / "labelsTs" / f"{r['case_id']}.nii.gz")
        else:
            r["split"], r["fold"] = "train", fold_of[r["patient_id"]]

    train_rows = [r for r in rows if r["split"] == "train"]
    splits = []
    for f in range(args.folds):
        splits.append({
            "train": sorted(r["case_id"] for r in train_rows if r["fold"] != f),
            "val": sorted(r["case_id"] for r in train_rows if r["fold"] == f),
        })
    (ds_dir / "splits_final.json").write_text(json.dumps(splits, indent=1))

    dataset_json = {
        "channel_names": {str(c): "CT" for c in range(n_ch)},
        "labels": {"background": 0, "artifact_DS": 1, "artifact_INT": 2},
        "numTraining": len(train_rows),
        "file_ending": ".nii.gz",
        "description": "Artefacts 4DCT simulés (DS = binning/double structure, INT = interpolation). "
                       f"Canal 0 = phase analysée, canaux suivants = phases voisines (context={args.context}).",
    }
    (ds_dir / "dataset.json").write_text(json.dumps(dataset_json, indent=2, ensure_ascii=False))

    with open(ds_dir / "metadata.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    n_clean = sum(r["kind"] == "clean" for r in rows)
    print(f"\nTerminé en {time.time() - t0:.0f}s -> {ds_dir}")
    print(f"  {len(rows)} cas : {n_clean} propres, {len(rows) - n_clean} avec artefacts")
    print(f"  train : {len(train_rows)} cas / {len(fold_of)} patients ; test : {len(rows) - len(train_rows)} cas / {len(test_pats)} patients")
    n_susp = sum(r["suspicious_clean"] for r in rows if r["kind"] == "clean")
    print(f"  phases propres suspectes (à vérifier visuellement) : {n_susp}")


if __name__ == "__main__":
    main()
