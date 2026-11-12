"""
Contrôle qualité / baseline non-deep-learning.

Deux scores, calculés pour une phase p d'un 4DCT :

  score_binning : une vraie frontière anatomique (apex, coupole diaphragmatique)
      existe aussi dans les phases voisines, à quelques coupes près, puisque la
      respiration est continue. Un artefact de binning crée au contraire une
      discontinuité qui n'existe QUE dans la phase p. On compare donc la
      discontinuité entre coupes adjacentes de la phase p à la plus forte
      discontinuité observée au même endroit (±window coupes) dans p-1 et p+1.

  score_interp : des coupes interpolées n'ont plus de bruit propre ; leur
      dérivée seconde le long de z est anormalement faible. On compare la
      dérivée seconde la plus faible à sa valeur typique.

Usages : repérer les phases « propres » qui contiennent déjà un vrai artefact
(fréquent sur données cliniques) et servir de premier baseline (étape 5).
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi


def _adjacent_diff(vol3d: np.ndarray, roi: np.ndarray) -> np.ndarray:
    """d[z] = moyenne de |I(z+1) - I(z)| dans la ROI, z = 0..Z-2."""
    Z = vol3d.shape[0]
    d = np.zeros(Z - 1, np.float32)
    for z in range(Z - 1):
        m = roi[z] | roi[z + 1]
        if m.sum() > 50:
            d[z] = float(np.abs(vol3d[z + 1][m] - vol3d[z][m]).mean())
    return d


def binning_profile(target: np.ndarray, neighbors: list[np.ndarray], roi: np.ndarray,
                    window: int = 3) -> np.ndarray:
    """Rapport discontinuité(phase p) / discontinuité max des phases voisines autour du même z."""
    d = _adjacent_diff(target, roi)
    ref = np.max([ndi.maximum_filter1d(_adjacent_diff(n, roi), size=2 * window + 1) for n in neighbors], axis=0)
    floor = np.median(d[d > 0]) if (d > 0).any() else 1.0
    return d / (ref + floor)


def interp_profile(target: np.ndarray, roi: np.ndarray) -> np.ndarray:
    """Rapport (dérivée seconde typique) / (dérivée seconde en z) ; élevé = coupe trop lisse."""
    Z = target.shape[0]
    s = np.zeros(Z, np.float32)
    for z in range(1, Z - 1):
        m = roi[z]
        if m.sum() > 50:
            s[z] = float(np.abs(target[z + 1][m] - 2 * target[z][m] + target[z - 1][m]).mean())
    valid = s[s > 0]
    if valid.size < 5:
        return np.zeros_like(s)
    med = np.median(valid)
    out = np.zeros_like(s)
    out[s > 0] = med / (s[s > 0] + 1e-3)
    return out


def scores(target: np.ndarray, neighbors: list[np.ndarray], roi: np.ndarray) -> dict:
    b = binning_profile(target, neighbors, roi)
    i = interp_profile(target, roi)
    # un artefact INT occupe plusieurs coupes : on prend la médiane glissante sur 3 coupes
    i3 = ndi.median_filter(i, size=3)
    return {"score_binning": float(b.max()), "score_interp": float(i3.max())}
