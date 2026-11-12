"""
Téléchargement de scanners 4D (et 3D) thoraciques PUBLICS depuis l'Imaging Data
Commons (IDC, NCI), qui héberge en accès libre les collections de TCIA.

Pas de compte, pas de NBIA Data Retriever : le paquet `idc-index` contient
l'index des métadonnées et télécharge directement depuis le stockage public.

    pip install idc-index

Jeux disponibles (tailles mesurées sur l'index IDC v24)
-------------------------------------------------------
4D (une série DICOM par phase respiratoire)
  4d_lung   TCIA 4D-Lung : 20 patients, 80 4DCT, 10 phases, Philips, 46,6 Go.
            Le script NE garde QUE les 4DCT « fan beam » : la collection contient
            aussi 507 4D-CBCT (130 Go) qu'on exclut.
  rider     TCIA RIDER Lung PET-CT : 5 4DCT GE (6 ou 10 phases), ~1,4 Go.
            Certains ne couvrent qu'une partie du thorax (20 coupes).
  ctvspet   TCIA CT-vs-PET-Ventilation-Imaging : 20 4DCT Siemens, 8,5 Go.
            ATTENTION : toutes les phases sont dans UNE seule série DICOM
            (io4d.py les sépare automatiquement ; vérifier avec inspect_dicom.py).

3D (une seule phase / un seul volume)
  ctvspet_bh  les scanners en apnée inspiration + expiration du même jeu (5,1 Go)
  lctsc       LCTSC : 60 scanners thoraciques, souvent la phase 50 % d'un 4DCT (4,9 Go)
  nsclc       NSCLC-Radiomics : 422 scanners thoraciques (26,3 Go)

Exemples
--------
python download_4dct.py --list                                  # tailles, sans rien télécharger
python download_4dct.py --dataset 4d_lung --max-patients 2 --out data/   # ~0,6 Go par 4DCT
python download_4dct.py --dataset 4d_lung --phases 0,50 --max-patients 5 --out data/
python download_4dct.py --dataset 4d_lung rider --one-per-patient --max-gb 9.5 --out data/   # < 10 Go
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

DATASETS = {
    "4d_lung": dict(
        collection="4d_lung", kind="4D",
        where="Modality='CT' AND ManufacturerModelName NOT ILIKE '%cone beam%' "
              "AND SeriesDescription ILIKE '%gated%'"),
    "rider": dict(
        collection="rider_lung_pet_ct", kind="4D",
        where="Modality='CT' AND SeriesDescription LIKE 'T=%'"),
    "ctvspet": dict(
        collection="ct_vs_pet_ventilation_imaging", kind="4D (série unique)",
        where="Modality='CT' AND SeriesDescription LIKE 'Resp%'"),
    "ctvspet_bh": dict(
        collection="ct_vs_pet_ventilation_imaging", kind="3D apnée",
        where="Modality='CT' AND (SeriesDescription ILIKE '%insp%' OR SeriesDescription ILIKE '%exp%') "
              "AND SeriesDescription NOT LIKE 'Resp%'"),
    "lctsc": dict(collection="lctsc", kind="3D", where="Modality='CT'"),
    "nsclc": dict(collection="nsclc_radiomics", kind="3D", where="Modality='CT'"),
}

PHASE_RE = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*%")


def select(client, name, max_patients=None, phases=None, one_per_patient=False):
    d = DATASETS[name]
    df = client.sql_query(f"""
        SELECT collection_id, PatientID, StudyInstanceUID, SeriesInstanceUID, SeriesDescription,
               ManufacturerModelName, instanceCount, series_size_MB
        FROM index WHERE collection_id='{d['collection']}' AND {d['where']}
        ORDER BY PatientID, StudyInstanceUID, SeriesDescription""")
    if phases is not None and d["kind"].startswith("4D") and "unique" not in d["kind"]:
        wanted = {float(p) for p in phases}
        keep = []
        for desc in df["SeriesDescription"]:
            m = PHASE_RE.search(desc or "")
            keep.append(bool(m) and float(m.group(1)) in wanted)
        df = df[keep]
    if one_per_patient:
        # un seul examen par patient : plus de patients différents pour le même volume
        first = df.groupby("PatientID")["StudyInstanceUID"].first()
        df = df[df["StudyInstanceUID"].isin(first.values)]
    if max_patients:
        pats = sorted(df["PatientID"].unique())[:max_patients]
        df = df[df["PatientID"].isin(pats)]
    return df


def cap_size(df, budget_mb):
    """Garde des examens COMPLETS (toutes leurs phases) tant que le budget n'est pas dépassé."""
    keep, total = [], 0.0
    for study, g in df.groupby("StudyInstanceUID", sort=False):
        size = g["series_size_MB"].sum()
        if total + size > budget_mb:
            break
        keep.append(study)
        total += size
    return df[df["StudyInstanceUID"].isin(keep)], total


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", nargs="+", choices=list(DATASETS), help="un ou plusieurs jeux")
    ap.add_argument("--out", default="data", help="dossier de destination")
    ap.add_argument("--max-patients", type=int, help="limiter le nombre de patients (pour commencer petit)")
    ap.add_argument("--phases", help="ne garder que certaines phases, ex. '0,50' (4D-Lung, RIDER)")
    ap.add_argument("--one-per-patient", action="store_true", help="un seul 4DCT par patient")
    ap.add_argument("--max-gb", type=float, help="taille maximale totale à télécharger (tous jeux confondus)")
    ap.add_argument("--list", action="store_true", help="afficher les jeux et leur taille, sans télécharger")
    ap.add_argument("--dry-run", action="store_true", help="afficher la sélection, sans télécharger")
    args = ap.parse_args()

    from idc_index import IDCClient
    client = IDCClient()
    print(f"Index IDC {client.get_idc_version()}")

    names = list(DATASETS) if args.list else (args.dataset or [])
    if not names:
        ap.error("préciser --dataset ou --list")
    phases = args.phases.split(",") if args.phases else None

    budget = args.max_gb * 1024 if args.max_gb else float("inf")
    for name in names:
        df = select(client, name, args.max_patients, phases, args.one_per_patient)
        if not args.list:
            df, used = cap_size(df, budget)
            budget -= used
        n_scans = df["StudyInstanceUID"].nunique()
        gb = df["series_size_MB"].sum() / 1024
        print(f"\n[{name}] {DATASETS[name]['kind']} — {df['PatientID'].nunique()} patients, "
              f"{n_scans} examens, {len(df)} séries, {gb:.1f} Go")
        if args.list or args.dry_run:
            print(df[["PatientID", "SeriesDescription", "instanceCount"]].head(12).to_string(index=False))
            continue
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        df.to_csv(out / f"manifest_{name}.csv", index=False)
        client.download_from_selection(
            downloadDir=str(out),
            seriesInstanceUID=df["SeriesInstanceUID"].tolist(),
            dirTemplate="%collection_id/%PatientID/%StudyInstanceUID/%SeriesInstanceUID",
            show_progress_bar=True,
        )
        print(f"  -> {out / DATASETS[name]['collection']}")


if __name__ == "__main__":
    main()
