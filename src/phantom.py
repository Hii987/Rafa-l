"""
Fantôme thoracique 4D synthétique, SANS artefact, pour tester le pipeline
avant d'avoir les vraies données (TCIA 4D-Lung ou Institut Rafaël).

Contenu : corps (tissus mous), deux poumons, dôme diaphragmatique + foie
qui montent et descendent avec la respiration, vaisseaux pulmonaires qui
suivent le mouvement, tumeur dans le poumon droit, rachis immobile.
Ce n'est PAS réaliste anatomiquement : il sert uniquement à vérifier que le
code tourne et que les artefacts sont bien placés.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from io4d import Scan4D


def make_phantom(seed: int = 0, shape=(80, 128, 128), n_phases: int = 10,
                 spacing=(2.5, 2.5, 2.5), amplitude_mm: float = None) -> Scan4D:
    rng = np.random.default_rng(seed)
    Z, Y, X = shape
    dz = spacing[0]
    A = amplitude_mm if amplitude_mm is not None else rng.uniform(10, 20)  # amplitude SI du diaphragme
    zz, yy, xx = np.meshgrid(np.arange(Z), np.arange(Y), np.arange(X), indexing="ij")
    cy, cx = Y / 2, X / 2

    body = ((yy - cy) / (0.38 * Y)) ** 2 + ((xx - cx) / (0.46 * X)) ** 2 < 1
    spine = ((yy - (cy + 0.25 * Y)) / (0.07 * Y)) ** 2 + ((xx - cx) / (0.06 * X)) ** 2 < 1

    # vaisseaux : positions fixes en (y, x), hauteur relative dans le poumon
    n_vessels = 60
    vy = rng.uniform(cy - 0.25 * Y, cy + 0.2 * Y, n_vessels)
    vx = np.concatenate([rng.uniform(cx - 0.38 * X, cx - 0.1 * X, n_vessels // 2),
                         rng.uniform(cx + 0.1 * X, cx + 0.38 * X, n_vessels - n_vessels // 2)])
    vz = rng.uniform(0.1, 0.85, n_vessels)
    vr = rng.uniform(1.0, 2.2, n_vessels)

    tumor_c = np.array([0.55 * Z, cy - 0.05 * Y, cx - 0.22 * X])
    tumor_r = rng.uniform(3, 5)

    dome0 = 0.70 * Z  # position du diaphragme en expiration (indice z, haut = 0)
    phases = list(range(0, 100, 100 // n_phases))[:n_phases]
    vols = []
    for p in phases:
        s = 0.5 * (1 - np.cos(2 * np.pi * p / 100))   # 0 en fin d'expiration, 1 en fin d'inspiration
        shift = s * A / dz                               # descente du diaphragme en coupes
        # dôme : plus haut au centre de chaque poumon
        r2_left = ((yy - cy) / (0.3 * Y)) ** 2 + ((xx - (cx - 0.22 * X)) / (0.2 * X)) ** 2
        r2_right = ((yy - cy) / (0.3 * Y)) ** 2 + ((xx - (cx + 0.22 * X)) / (0.2 * X)) ** 2
        dome = dome0 + shift + 6 * np.minimum(r2_left, r2_right)
        apex = 0.06 * Z + 0.12 * Z * np.minimum(r2_left, r2_right)   # sommet arrondi
        lungs = body & ~spine & (np.minimum(r2_left, r2_right) < 1) & (zz > apex) & (zz < dome)
        mediast = body & (np.abs(xx - cx) < 0.09 * X) & (zz < dome)
        lungs &= ~mediast

        v = np.full(shape, -1000.0, np.float32)    # air extérieur
        v[body] = 40.0                              # tissus mous
        v[body & (zz >= dome)] = 60.0               # foie / abdomen
        v[lungs] = -820.0
        v[spine] = 700.0

        # vaisseaux : se déplacent vers le bas proportionnellement à leur hauteur
        for y0, x0, h, r in zip(vy, vx, vz, vr):
            z_top = 0.08 * Z
            z_c = z_top + h * (dome0 - z_top) + h * shift
            d2 = ((zz - z_c) * dz / 2.5) ** 2 + (yy - y0) ** 2 + (xx - x0) ** 2
            v[(d2 < r ** 2) & lungs] = 30.0
        # tumeur
        tc = tumor_c + np.array([0.8 * shift, 0, 0])
        d2 = (zz - tc[0]) ** 2 + (yy - tc[1]) ** 2 + (xx - tc[2]) ** 2
        v[(d2 < tumor_r ** 2) & body] = 35.0

        v = ndi.gaussian_filter(v, 0.7)
        v += rng.normal(0, 12, shape).astype(np.float32)
        vols.append(v.astype(np.float32))

    return Scan4D(
        patient_id=f"PHANTOM{seed:03d}",
        scan_id=f"PHANTOM{seed:03d}_s00",
        vol=np.stack(vols),
        phases=phases,
        spacing=spacing,
        meta={"amplitude_mm": float(A), "synthetic": True},
        head_at_high_z=False,  # indice 0 = apex
    )
