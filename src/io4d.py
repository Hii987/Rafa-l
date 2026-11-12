"""
Chargement de scanners 4D (4DCT) depuis des exports DICOM ou des fichiers NIfTI.

Représentation interne commune : un objet Scan4D contenant
    vol      : np.ndarray float32 [P, Z, Y, X] en unités Hounsfield
    phases   : liste des pourcentages de phase respiratoire (ex. [0, 10, ..., 90])
    spacing  : (sz, sy, sx) en mm
    origin   : (x, y, z) de la première coupe, convention LPS (DICOM)
    head_at_high_z : True si la tête est du côté des indices z élevés
               (None = inconnu ; sert à placer les artefacts côté diaphragme)
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

import numpy as np

PHASE_RE = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*%")


@dataclass
class Scan4D:
    patient_id: str
    scan_id: str
    vol: np.ndarray                      # [P, Z, Y, X] float32, HU
    phases: list[int]
    spacing: tuple[float, float, float]  # (z, y, x) en mm
    origin: tuple[float, float, float] = (0.0, 0.0, 0.0)
    meta: dict = field(default_factory=dict)
    head_at_high_z: bool | None = None

    @property
    def n_phases(self) -> int:
        return self.vol.shape[0]


# ---------------------------------------------------------------------------
# DICOM
# ---------------------------------------------------------------------------
def _phase_from_description(desc: str) -> float | None:
    """Extrait la phase (%) de SeriesDescription, ex. 'Gated, 30.0%' -> 30."""
    m = PHASE_RE.search(desc or "")
    return float(m.group(1)) if m else None


# Attributs d'instance qui peuvent distinguer les phases quand un constructeur
# range TOUTES les phases dans une seule série (ex. certains exports Siemens).
SPLIT_TAGS = ["TemporalPositionIndex", "NominalPercentageOfCardiacPhase", "TriggerTime",
              "ImageComments", "AcquisitionNumber"]


def _split_multiphase(items: list[dict]) -> tuple[dict, str] | None:
    """
    Une série contient plusieurs instances à la même position z : c'est un 4DCT
    « série unique ». On cherche un attribut qui la découpe en groupes de même
    taille, chacun sans doublon de z. Dernier recours : découpage par blocs
    consécutifs d'InstanceNumber (phase par phase).
    Retourne ({phase_%: [(z, path)]}, méthode) ou None.
    """
    zs = [round(it["z"], 2) for it in items]
    n_rep = len(zs) // len(set(zs))
    if n_rep < 2:
        return None

    def valid(groups):
        sizes = {len(g) for g in groups.values()}
        return (len(groups) == n_rep and len(sizes) == 1
                and all(len({round(i['z'], 2) for i in g}) == len(g) for g in groups.values()))

    for tag in SPLIT_TAGS:
        groups = defaultdict(list)
        for it in items:
            groups[str(it["tags"].get(tag))].append(it)
        if "None" not in groups and valid(groups):
            keys = sorted(groups, key=lambda k: _sort_key(k))
            return _to_phases(keys, groups), tag
    # dernier recours : blocs consécutifs d'InstanceNumber
    ordered = sorted(items, key=lambda it: it["tags"].get("InstanceNumber") or 0)
    nz = len(ordered) // n_rep
    groups = {str(k): ordered[k * nz:(k + 1) * nz] for k in range(n_rep)}
    if valid(groups):
        return _to_phases(sorted(groups, key=int), groups), "InstanceNumber (blocs)"
    return None


def _sort_key(k: str):
    m = re.search(r"-?\d+(?:\.\d+)?", k)
    return float(m.group()) if m else k


def _to_phases(keys, groups) -> dict:
    """Clés -> pourcentages : la valeur elle-même si elle contient un %, sinon rang*100/n."""
    out = {}
    for rank, k in enumerate(keys):
        m = PHASE_RE.search(k)
        ph = float(m.group(1)) if m else round(rank * 100 / len(keys), 1)
        out[ph] = [(i["z"], i["path"]) for i in groups[k]]
    return out


def scan_dicom_folder(root: str | Path, exclude_cbct: bool = True, verbose: bool = False) -> dict:
    """
    Parcourt un dossier d'export PACS et regroupe les fichiers par 4DCT.

    Un 4DCT = les séries CT gatées (un pourcentage dans SeriesDescription) d'une
    même étude et d'un même référentiel spatial. Deux organisations sont gérées :
      - une série par phase (Philips, GE, la plupart des exports) ;
      - toutes les phases dans une seule série (découpée par _split_multiphase).
    Les CBCT (ex. 4D-CBCT de 4D-Lung) sont exclus par défaut.
    Retourne {(patient_id, scan_key): {phase: [(z, path), ...]}}.
    """
    import pydicom

    series: dict = defaultdict(list)
    info: dict = {}
    for f in Path(root).rglob("*"):
        if not f.is_file():
            continue
        try:
            ds = pydicom.dcmread(f, stop_before_pixels=True)
        except Exception:
            continue
        if getattr(ds, "Modality", "") != "CT" or not hasattr(ds, "ImagePositionPatient"):
            continue
        model = str(getattr(ds, "ManufacturerModelName", ""))
        if exclude_cbct and "cone beam" in model.lower():
            continue
        desc = str(getattr(ds, "SeriesDescription", ""))
        if _phase_from_description(desc) is None:
            continue  # série non gatée (CT standard, MIP, AVG…)
        uid = str(ds.SeriesInstanceUID)
        info[uid] = dict(
            pid=str(getattr(ds, "PatientID", "unknown")),
            key=(str(getattr(ds, "StudyInstanceUID", "")), str(getattr(ds, "FrameOfReferenceUID", "")),
                 str(getattr(ds, "SeriesDate", ""))),
            desc=desc,
        )
        tags = {}
        for t in SPLIT_TAGS + ["InstanceNumber"]:
            v = getattr(ds, t, None)
            tags[t] = None if v in (None, "") else (float(v) if isinstance(v, (int, float)) else str(v))
        series[uid].append({"z": float(ds.ImagePositionPatient[2]), "path": f, "tags": tags})

    groups: dict = defaultdict(lambda: defaultdict(list))
    for uid, items in series.items():
        meta = info[uid]
        split = _split_multiphase(items)
        if split is not None:
            by_phase, method = split
            if verbose:
                print(f"  série unique multi-phases ({meta['desc']}) : {len(by_phase)} phases via {method}")
            for ph, lst in by_phase.items():
                groups[(meta["pid"], meta["key"])][ph].extend(lst)
        else:
            ph = _phase_from_description(meta["desc"])
            groups[(meta["pid"], meta["key"])][ph].extend((it["z"], it["path"]) for it in items)
    return groups


def _read_series(items: list[tuple[float, Path]]):
    """Lit une série triée en z ; retourne (volume HU, z, spacing yx, origin)."""
    import pydicom

    items = sorted(items, key=lambda t: t[0])
    zs, slices = [], []
    first = None
    for z, f in items:
        ds = pydicom.dcmread(f)
        if first is None:
            first = ds
        arr = ds.pixel_array.astype(np.float32)
        arr = arr * float(getattr(ds, "RescaleSlope", 1)) + float(getattr(ds, "RescaleIntercept", 0))
        slices.append(arr)
        zs.append(z)
    vol = np.stack(slices)
    ps = [float(v) for v in first.PixelSpacing]  # (row, col) = (y, x)
    origin = tuple(float(v) for v in first.ImagePositionPatient)
    return vol, np.array(zs), (ps[0], ps[1]), origin


def load_dicom_4dct(root: str | Path, min_phases: int = 4) -> Iterator[Scan4D]:
    """
    Charge un par un (générateur) les 4DCT trouvés dans un dossier DICOM :
    un seul 4DCT en mémoire à la fois (~1,5 Go chacun en float32).

    Les phases d'un même 4DCT sont recoupées sur leur étendue z commune
    (certains constructeurs reconstruisent des phases de longueurs légèrement
    différentes), pour obtenir un tableau 4D régulier.
    """
    groups = scan_dicom_folder(root)
    for i, ((pid, key), by_phase) in enumerate(sorted(groups.items())):
        if len(by_phase) < min_phases:
            continue
        phases = sorted(by_phase)
        vols, zlists = [], []
        for p in phases:
            v, zs, sp_yx, origin = _read_series(by_phase[p])
            vols.append(v)
            zlists.append(zs)
        # étendue z commune (tolérance 0,1 mm)
        zmin = max(z.min() for z in zlists)
        zmax = min(z.max() for z in zlists)
        cropped = []
        for v, z in zip(vols, zlists):
            sel = (z >= zmin - 0.1) & (z <= zmax + 0.1)
            cropped.append(v[sel])
        nz = min(c.shape[0] for c in cropped)
        vol4d = np.stack([c[:nz] for c in cropped]).astype(np.float32)
        dz = float(np.median(np.diff(zlists[0]))) if len(zlists[0]) > 1 else 1.0
        yield Scan4D(
            patient_id=pid,
            scan_id=f"{pid}_s{i:02d}",
            vol=vol4d,
            phases=[int(round(p)) for p in phases],
            spacing=(abs(dz), sp_yx[0], sp_yx[1]),
            origin=(origin[0], origin[1], float(zmin)),
            meta={"study": key[0], "date": key[2]},
            # coupes triées par z croissant ; en LPS, +z = vers la tête
            head_at_high_z=True,
        )


# ---------------------------------------------------------------------------
# NIfTI / MHA / MHD / NRRD : un dossier par 4DCT, un fichier par phase
# (…_00.nii.gz, …_10.nii.gz…). Couvre POPI (.mhd) et DIR-Lab après conversion.
# ---------------------------------------------------------------------------
def load_nifti_4dct(folder: str | Path, patient_id: str | None = None) -> Scan4D:
    import SimpleITK as sitk

    folder = Path(folder)
    files = sorted(f for ext in ("*.nii", "*.nii.gz", "*.mha", "*.mhd", "*.nrrd") for f in folder.glob(ext))
    by_phase = {}
    for f in files:
        stem = re.sub(r"\.(nii\.gz|nii|mha|mhd|nrrd)$", "", f.name)
        nums = re.findall(r"(\d{1,3})", stem)
        if nums:
            by_phase[int(nums[-1])] = f
    if not by_phase:
        raise ValueError(f"Aucune phase trouvée dans {folder}")
    phases = sorted(by_phase)
    imgs = [sitk.ReadImage(str(by_phase[p])) for p in phases]
    vol = np.stack([sitk.GetArrayFromImage(im).astype(np.float32) for im in imgs])
    sx, sy, sz = imgs[0].GetSpacing()
    return Scan4D(
        patient_id=patient_id or folder.name,
        scan_id=folder.name,
        vol=vol,
        phases=phases,
        spacing=(sz, sy, sx),
        origin=imgs[0].GetOrigin(),
        # 3e colonne de la matrice de direction : sens de l'axe k en LPS (+z = tête)
        head_at_high_z=bool(imgs[0].GetDirection()[8] > 0),
    )


def save_nifti(arr: np.ndarray, spacing_zyx, origin, path: str | Path, dtype=np.float32):
    """Écrit un volume 3D [Z, Y, X] en NIfTI avec la bonne géométrie."""
    import SimpleITK as sitk

    img = sitk.GetImageFromArray(arr.astype(dtype))
    img.SetSpacing((float(spacing_zyx[2]), float(spacing_zyx[1]), float(spacing_zyx[0])))
    img.SetOrigin(tuple(float(o) for o in origin))
    sitk.WriteImage(img, str(path), useCompression=True)
