"""
Convertit les 4DCT DIR-Lab (fichiers bruts .img, entiers 16 bits) en un dossier
NIfTI par cas, lisible par build_dataset.py --source nifti.

DIR-Lab n'est pas sur IDC : l'accès se demande via le formulaire du site
(gratuit, liens Dropbox envoyés par mail) :
https://med.emory.edu/departments/radiation-oncology/research-laboratories/deformable-image-registration/

Le nombre de coupes est déduit de la taille du fichier. Les tailles en x/y et
l'espacement viennent de la page DIR-Lab : à vérifier avec le README fourni
dans chaque archive. Si les valeurs lues sont toutes positives, on retire 1024
pour revenir en unités Hounsfield (l'air doit être proche de -1000 HU).

Usage :
  python convert_dirlab.py --input Case1Pack/Images --case 1 --out data/dirlab_nifti
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import numpy as np

from io4d import save_nifti

# (nx, ny, taille de pixel en mm) — z toujours 2,5 mm
DIRLAB = {
    1: (256, 256, 0.97), 2: (256, 256, 1.16), 3: (256, 256, 1.15), 4: (256, 256, 1.13),
    5: (256, 256, 1.10), 6: (512, 512, 0.97), 7: (512, 512, 0.97), 8: (512, 512, 0.97),
    9: (512, 512, 0.97), 10: (512, 512, 0.97),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="dossier contenant les .img d'un cas")
    ap.add_argument("--case", type=int, required=True, choices=range(1, 11))
    ap.add_argument("--out", required=True)
    ap.add_argument("--flip-z", action="store_true", help="inverser l'ordre des coupes si le volume est à l'envers")
    args = ap.parse_args()

    nx, ny, px = DIRLAB[args.case]
    out = Path(args.out) / f"DIRLAB-case{args.case:02d}"
    out.mkdir(parents=True, exist_ok=True)
    files = sorted(Path(args.input).glob("*.img"))
    if not files:
        raise SystemExit("Aucun fichier .img trouvé")
    for f in files:
        m = re.search(r"T(\d{2})", f.name)
        if not m:
            print("ignoré (pas de phase Txx dans le nom) :", f.name)
            continue
        raw = np.fromfile(f, dtype="<i2")
        nz = raw.size // (nx * ny)
        if nz * nx * ny != raw.size:
            raise SystemExit(f"{f.name} : taille incompatible avec {nx}x{ny} — vérifier la table DIRLAB")
        vol = raw.reshape(nz, ny, nx).astype(np.float32)
        if vol.min() >= 0:
            vol -= 1024
        if args.flip_z:
            vol = vol[::-1]
        dst = out / f"phase_{int(m.group(1)):02d}.nii.gz"
        save_nifti(vol, (2.5, px, px), (0.0, 0.0, 0.0), dst)
        print(f"{f.name} -> {dst.name}  ({nz}x{ny}x{nx}, HU médian {np.median(vol):.0f})")


if __name__ == "__main__":
    main()
