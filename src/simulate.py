"""
Générateur d'artefacts 4DCT synthétiques, avec vérité terrain voxel par voxel.

Principe physique
-----------------
Un 4DCT est acquis par blocs successifs le long de z (une « position de table »
en mode ciné, ou une portion d'hélice en mode hélicoïdal). Chaque bloc est trié
dans une phase respiratoire selon le signal respiratoire. Quand la respiration
est irrégulière, deux erreurs se produisent :

  DS  (double structure / binning) : un bloc de la phase P contient en réalité
       l'anatomie d'un autre état respiratoire. On le simule en remplaçant ce
       bloc par le même bloc pris dans une autre phase (« overlap »), ou décalé
       en z (« duplicate », qui produit des structures dédoublées).
  INT (interpolation) : des données de projection manquent ; le reconstructeur
       interpole entre les coupes valides. On le simule en remplaçant l'intérieur
       d'un bloc par une interpolation linéaire entre ses deux coupes bordantes.

Améliorations reprises de Cisneros et al., Med Phys 2025 (doi:10.1002/mp.70191)
---------------------------------------------------------------------------------
  1. Phase source = phase OPPOSÉE ± 2 (leur option « S2 », la meilleure ; une
     phase au hasard, « S3 », dégradait l'apprentissage).
  2. Règle de réalisme : le bloc inséré doit contenir MOINS de poumon que
     l'original (diaphragme répété plutôt que diaphragme manquant).
  3. Artefacts placés dans la moitié INFÉRIEURE des poumons, près du diaphragme,
     là où le mouvement respiratoire est le plus grand.
  4. Transition adoucie le long de z (flou gaussien de largeur aléatoire) et léger
     décalage du bloc en coronal / sagittal, pour imiter l'erreur de reconstruction.

Labels
------
0 = fond, 1 = DS, 2 = INT. Un voxel n'est labellisé que s'il est réellement
modifié de façon visible (|Δ| > seuil HU) et situé dans le corps : un artefact
inséré dans une zone qui ne bouge pas est invisible, donc non labellisé, et
l'échantillon est rejeté s'il ne reste presque rien.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
from scipy import ndimage as ndi

LABEL_DS, LABEL_INT = 1, 2


# ---------------------------------------------------------------------------
# Masques anatomiques simples (sans dépendance lourde)
# ---------------------------------------------------------------------------
def body_mask(vol3d: np.ndarray, thr: float = -500.0) -> np.ndarray:
    """Corps du patient : plus grande composante au-dessus de -500 HU, trous bouchés coupe par coupe."""
    m = vol3d > thr
    lab, n = ndi.label(m)
    if n == 0:
        return m
    sizes = ndi.sum(m, lab, range(1, n + 1))
    m = lab == (int(np.argmax(sizes)) + 1)
    for z in range(m.shape[0]):
        m[z] = ndi.binary_fill_holes(m[z])
    return m


def lung_mask(vol3d: np.ndarray, body: np.ndarray | None = None) -> np.ndarray:
    """Poumons approximatifs : air (< -400 HU) à l'intérieur du corps, petites composantes retirées."""
    if body is None:
        body = body_mask(vol3d)
    m = (vol3d < -400) & body
    m = ndi.binary_opening(m, iterations=1)
    lab, n = ndi.label(m)
    if n == 0:
        return m
    sizes = ndi.sum(m, lab, range(1, n + 1))
    keep = [i + 1 for i, s in enumerate(sizes) if s > 0.0005 * m.size]
    return np.isin(lab, keep)


def region_of_interest(vol3d: np.ndarray, dilate_mm: float = 15.0, spacing=(1, 1, 1)) -> np.ndarray:
    """
    Zone où l'on accepte de labelliser : poumons dilatés (pour inclure le dôme
    diaphragmatique, le médiastin et le cœur, où les artefacts sont visibles),
    restreinte au corps.
    """
    body = body_mask(vol3d)
    lung = lung_mask(vol3d, body)
    if lung.sum() == 0:
        return body
    # dilatation isotrope en mm (tient compte de l'espacement anisotrope)
    dist = ndi.distance_transform_edt(~lung, sampling=spacing)
    return (dist <= dilate_mm) & body


def lower_lung_zrange(lung: np.ndarray, frac: float = 0.5, margin: int = 6,
                      head_at_high_z: bool | None = None) -> tuple[int, int]:
    """
    Plage d'indices z [a, b) couvrant la partie INFÉRIEURE des poumons (fraction
    `frac` de leur hauteur, côté diaphragme), plus `margin` coupes sous la base.

    L'orientation de l'axe z dépend de la source (DICOM trié par position :
    indice 0 = pieds ; fantôme : indice 0 = tête) : elle doit être fournie par
    `head_at_high_z` (lue dans les métadonnées, voir Scan4D). La règle anatomique
    de secours (section pulmonaire plus grande à la base) n'est utilisée que si
    l'orientation est inconnue : elle se trompe souvent sur données cliniques
    (apex coupé par le champ, gaz abdominal pris pour du poumon).
    """
    Z = lung.shape[0]
    # Ne garder que les grosses composantes (les poumons) : les bulles de gaz
    # digestif sous le diaphragme fausseraient la position de la base.
    lab, n = ndi.label(lung)
    if n > 1:
        sizes = ndi.sum(lung, lab, range(1, n + 1))
        lung = np.isin(lab, np.flatnonzero(sizes >= 0.1 * sizes.max()) + 1)
    area = lung.reshape(Z, -1).sum(1).astype(float)
    zs = np.flatnonzero(area > 0.1 * area.max()) if area.max() > 0 else np.array([])
    if zs.size < 4 or frac >= 1.0:
        return 0, Z
    lo, hi = int(zs[0]), int(zs[-1]) + 1
    h = hi - lo
    if head_at_high_z is None:
        q = max(1, h // 4)
        base_at_high = area[hi - q:hi].mean() >= area[lo:lo + q].mean()
    else:
        base_at_high = not head_at_high_z
    n = max(2, int(round(frac * h)))
    if base_at_high:
        return max(0, hi - n), min(Z, hi + margin)
    return max(0, lo - margin), min(Z, lo + n)


# ---------------------------------------------------------------------------
# Géométrie d'acquisition
# ---------------------------------------------------------------------------
def couch_boundaries(nz: int, dz_mm: float, couch_mm: float, rng: np.random.Generator) -> np.ndarray:
    """
    Indices z des frontières entre positions de table.
    couch_mm ≈ couverture du détecteur en mode ciné (20–40 mm sur un 16 barrettes).
    Un décalage aléatoire évite que les frontières tombent toujours au même endroit.
    """
    step = max(2, int(round(couch_mm / dz_mm)))
    offset = int(rng.integers(0, step))
    return np.arange(offset, nz, step)


@dataclass
class ArtifactEvent:
    kind: str          # "DS_overlap", "DS_duplicate", "INT"
    z0: int            # première coupe affectée (incluse)
    z1: int            # dernière coupe affectée (exclue)
    src_phase: int | None
    shift: int
    n_voxels: int
    mean_abs_hu: float
    sigma_z: float = 0.0          # largeur de la transition le long de z (coupes)
    inplane_shift: tuple = (0, 0)  # décalage (y, x) du bloc, en voxels

    def to_dict(self):
        return asdict(self)


# ---------------------------------------------------------------------------
# Artefacts élémentaires
# ---------------------------------------------------------------------------
def _pick_slab(bounds, nz, n_blocks, rng, roi_z):
    """Choisit un bloc [z0, z1) aligné sur les frontières, au moins à moitié dans la zone autorisée."""
    cand = []
    edges = np.concatenate([[0], bounds, [nz]])
    edges = np.unique(edges)
    for i in range(len(edges) - n_blocks):
        z0, z1 = int(edges[i]), int(edges[i + n_blocks])
        if z1 - z0 >= 2 and roi_z[z0:z1].mean() >= 0.5:
            cand.append((z0, z1))
    if not cand:
        return None
    return cand[int(rng.integers(len(cand)))]


def source_candidates(p: int, P: int, mode: str = "opposite_pm2", min_phase_gap: int = 2) -> list[int]:
    """
    Choisit la phase dont on emprunte le bloc.
      opposite_pm2 : phase opposée ± 2 (Cisneros « S2 », recommandé)
      opposite     : exactement la phase opposée (« S1 »)
      random       : n'importe quelle phase (« S3 »)
    Dans tous les cas, jamais une phase voisine (écart circulaire ≥ min_phase_gap) :
    les voisines sont des canaux d'entrée, le réseau repérerait une simple copie.
    """
    opp = (p + P // 2) % P
    if mode == "opposite":
        cand = [opp]
    elif mode == "opposite_pm2":
        cand = [(opp + d) % P for d in range(-2, 3)]
    else:
        cand = list(range(P))

    def gap(q):
        g = abs(q - p) % P
        return min(g, P - g)

    return [q for q in cand if gap(q) >= min_phase_gap] or [opp]


def pick_source_phase(p: int, P: int, rng, mode: str = "opposite_pm2", min_phase_gap: int = 2) -> int:
    cand = source_candidates(p, P, mode, min_phase_gap)
    return int(cand[int(rng.integers(len(cand)))])


def _roll_fill(block: np.ndarray, dy: int, dx: int) -> np.ndarray:
    """Décalage entier en (y, x) ; les bords découverts gardent le contenu d'origine (pas d'interpolation, donc pas de lissage du bruit)."""
    out = block.copy()
    Y, X = block.shape[1:]
    ys = slice(max(0, dy), Y + min(0, dy)); yd = slice(max(0, -dy), Y + min(0, -dy))
    xs = slice(max(0, dx), X + min(0, dx)); xd = slice(max(0, -dx), X + min(0, -dx))
    out[:, ys, xs] = block[:, yd, xd]
    return out


def apply_ds(vol4d, p, z0, z1, rng, mode="overlap", source_mode="opposite_pm2",
             sigma_z=0.0, inplane_shift=(0, 0), sigma_noise=None, min_phase_gap=2, src=None,
             region: np.ndarray | None = None, sigma_xy: float = 2.0):
    """
    Remplace le bloc [z0, z1) de la phase p par la même zone d'une autre phase.

    Poids de mélange W(z, y, x) = w(z) · r(z, y, x) :
      w(z) : indicatrice du bloc, lissée le long de z (largeur sigma_z ; 0 = bords nets) ;
      r    : zone pulmonaire élargie (`region`), adoucie en bordure et EXACTEMENT nulle
             en dehors. Ainsi le contour du corps, la colonne, etc. ne sont jamais
             modifiés sans être labellisés (le décalage du bloc les déplacerait sinon).
    Mélanger deux images réduit le bruit : on ré-injecte le bruit manquant, pour ne
    pas donner au réseau un raccourci (« zones trop lisses »).

    Retourne (volume [Z,Y,X], phase source, décalage z, w[Z]).
    """
    P, Z = vol4d.shape[:2]
    if src is None:
        src = pick_source_phase(p, P, rng, source_mode, min_phase_gap)
    clean = vol4d[p]
    shift = 0
    if mode == "duplicate":
        shift = int(rng.integers(2, max(3, (z1 - z0) // 2 + 2))) * int(rng.choice([-1, 1]))
        if z0 - shift < 0 or z1 - shift > Z:
            shift = 0

    w = np.zeros(Z, np.float32)
    w[z0:z1] = 1.0
    if sigma_z > 0:
        w = ndi.gaussian_filter1d(w, sigma_z, mode="constant")
        w = np.clip(w / max(w.max(), 1e-6), 0, 1)
    zs = np.flatnonzero(w > 1e-3)
    a, b = int(zs[0]), int(zs[-1]) + 1

    donor = vol4d[src, max(0, a - shift):min(Z, b - shift)]
    if donor.shape[0] != b - a:  # bord du volume : on retombe sans décalage z
        shift, donor = 0, vol4d[src, a:b]
    if any(inplane_shift):
        donor = _roll_fill(donor, int(inplane_shift[0]), int(inplane_shift[1]))

    W = np.broadcast_to(w[a:b, None, None], donor.shape).astype(np.float32)
    if region is not None:
        r = ndi.gaussian_filter(region[a:b].astype(np.float32), (0, sigma_xy, sigma_xy))
        r = np.where(region[a:b], np.clip(2 * r, 0, 1), 0.0).astype(np.float32)
        W = W * r
    base = clean[a:b]
    mixed = (1 - W) * base + W * donor
    if sigma_noise is None:
        sigma_noise = estimate_noise(clean)
    part = (W > 0.01) & (W < 0.99)
    if part.any():
        wp = W[part]
        mixed[part] += rng.normal(0, 1, int(part.sum())).astype(np.float32) * \
            (sigma_noise * np.sqrt(np.clip(1 - ((1 - wp) ** 2 + wp ** 2), 0, None))).astype(np.float32)
    out = clean.copy()
    out[a:b] = mixed
    return out.astype(np.float32), src, shift, w


def estimate_noise(vol3d: np.ndarray, lo: float = -200, hi: float = 200) -> float:
    """
    Écart-type du bruit (HU), estimé dans les tissus mous homogènes à partir
    des différences entre coupes adjacentes (robuste via la MAD).
    """
    a, b = vol3d[:-1], vol3d[1:]
    m = (a > lo) & (a < hi) & (b > lo) & (b < hi)
    if m.sum() < 1000:
        return 10.0
    d = (a[m] - b[m])
    return float(1.4826 * np.median(np.abs(d - np.median(d))) / np.sqrt(2))


def apply_int(vol3d, z0, z1, rng, sigma_noise: float | None = None, jitter: float = 0.0):
    """
    Remplace l'intérieur du bloc par une interpolation linéaire entre z0-1 et z1.
    Une interpolation réduit le bruit (moyenne de deux coupes) : on ré-injecte
    le bruit manquant, sinon le réseau apprendrait juste à repérer des coupes
    « trop lisses » au lieu de l'artefact anatomique.
    """
    Z = vol3d.shape[0]
    if jitter > 0:  # bornes légèrement aléatoires (Cisneros : décalage gaussien)
        z0 = int(np.clip(z0 + round(rng.normal(0, jitter)), 1, Z - 3))
        z1 = int(np.clip(z1 + round(rng.normal(0, jitter)), z0 + 2, Z - 1))
    a, b = max(0, z0 - 1), min(Z - 1, z1)
    out = vol3d.copy()
    n = b - a
    if n < 2:
        return out
    if sigma_noise is None:
        sigma_noise = estimate_noise(vol3d)
    top, bot = vol3d[a], vol3d[b]
    for k, z in enumerate(range(a + 1, b), start=1):
        w = k / n
        missing = sigma_noise * np.sqrt(max(0.0, 1 - ((1 - w) ** 2 + w ** 2)))
        out[z] = (1 - w) * top + w * bot + rng.normal(0, missing, top.shape).astype(np.float32)
    return out


# ---------------------------------------------------------------------------
# Générateur principal
# ---------------------------------------------------------------------------
@dataclass
class SimConfig:
    couch_mm: float = 20.0         # couverture d'une position de table
    p_ds: float = 0.65             # probabilité qu'un événement soit DS (sinon INT)
    p_duplicate: float = 0.3       # parmi les DS : part de « duplicate » (décalage en z)
    source_mode: str = "opposite_pm2"  # "opposite_pm2" (S2, recommandé), "opposite" (S1), "random" (S3)
    require_less_lung: bool = True # le bloc inséré doit contenir moins de poumon que l'original
    less_lung_frac: float = 0.6    # part minimale des voxels modifiés qui « gagnent » du tissu
    lower_lung_frac: float = 0.5   # artefacts dans cette fraction inférieure des poumons (1.0 = partout)
    sigma_z_max: float = 1.5       # largeur max de la transition en z (coupes) ; tirée dans [0, max]
    max_inplane_shift_mm: float = 3.0  # décalage max du bloc en coronal / sagittal
    int_jitter: float = 1.0        # écart-type du décalage des bornes INT (coupes)
    max_events: int = 3            # nombre max d'artefacts dans un volume
    max_blocks: int = 2            # un artefact peut couvrir 1 à 2 positions de table
    diff_thr_hu: float = 100.0     # seuil de visibilité pour labelliser un voxel
    min_voxels: int = 200          # en dessous : artefact jugé invisible -> rejeté
    max_tries: int = 40


def simulate_artifacts(vol4d: np.ndarray, p: int, spacing, rng: np.random.Generator,
                       cfg: SimConfig = SimConfig(), roi: np.ndarray | None = None,
                       head_at_high_z: bool | None = None):
    """
    Corrompt la phase p d'un 4DCT propre.
    head_at_high_z : True si la tête est du côté des indices z élevés (voir Scan4D).
    Retourne (volume corrompu [Z,Y,X], label uint8 [Z,Y,X], liste d'ArtifactEvent).
    Retourne (None, None, []) si aucun artefact visible n'a pu être inséré.
    """
    clean = vol4d[p]
    Z = clean.shape[0]
    if roi is None:
        roi = region_of_interest(clean, spacing=spacing)
    body = body_mask(clean)
    lung = lung_mask(clean, body)
    za, zb = lower_lung_zrange(lung, cfg.lower_lung_frac, head_at_high_z=head_at_high_z)
    roi_z = roi.reshape(Z, -1).any(1)
    roi_z[:za] = False
    roi_z[zb:] = False
    bounds = couch_boundaries(Z, spacing[0], cfg.couch_mm, rng)
    sigma_noise = estimate_noise(clean)
    max_shift = [int(round(cfg.max_inplane_shift_mm / s_)) for s_ in spacing[1:]]

    out = clean.copy()
    label = np.zeros(clean.shape, np.uint8)
    events: list[ArtifactEvent] = []
    used = np.zeros(Z, bool)
    n_target = int(rng.integers(1, cfg.max_events + 1))
    # Type de chaque artefact décidé à l'avance : si un DS est difficile à placer
    # (règle « moins de poumon »), on réessaie un DS au lieu de basculer sur un INT,
    # ce qui garde la proportion p_ds sur l'ensemble du jeu.
    plan = ["DS" if rng.random() < cfg.p_ds else "INT" for _ in range(n_target)]

    for _ in range(cfg.max_tries):
        if len(events) >= n_target:
            break
        n_blocks = int(rng.integers(1, cfg.max_blocks + 1))
        slab = _pick_slab(bounds, Z, n_blocks, rng, roi_z)
        if slab is None:
            break
        z0, z1 = slab
        sigma_z = float(rng.uniform(0, cfg.sigma_z_max))
        m = int(np.ceil(4 * sigma_z)) + 1          # étendue de la transition
        e0, e1 = max(0, z0 - m), min(Z, z1 + m)
        if used[max(0, e0 - 1):e1 + 1].any():
            continue  # pas de chevauchement entre deux artefacts

        accepted = None
        if plan[len(events)] == "DS":
            mode = "duplicate" if rng.random() < cfg.p_duplicate else "overlap"
            shift_yx = tuple(int(rng.integers(-ms, ms + 1)) if ms > 0 else 0 for ms in max_shift)
            cands = source_candidates(p, vol4d.shape[0], cfg.source_mode)
            for src in rng.permutation(cands):
                new, src, shift, _w = apply_ds(vol4d, p, z0, z1, rng, mode=mode, sigma_z=sigma_z,
                                               inplane_shift=shift_yx, sigma_noise=sigma_noise, src=int(src),
                                               region=roi)
                signed = new[e0:e1] - clean[e0:e1]
                vis = ndi.binary_closing((np.abs(signed) > cfg.diff_thr_hu) & roi[e0:e1], iterations=1) & roi[e0:e1]
                if vis.sum() < cfg.min_voxels:
                    continue  # artefact invisible (zone immobile)
                # « moins de poumon » = les voxels modifiés deviennent majoritairement plus denses
                if cfg.require_less_lung and float((signed[vis] > 0).mean()) < cfg.less_lung_frac:
                    continue
                accepted = (new, int(src), shift, shift_yx, sigma_z, f"DS_{mode}", LABEL_DS, signed, vis)
                break
        else:
            if z1 - z0 < 3:
                z1 = min(Z - 1, z0 + 3)
            new = apply_int(out, z0, z1, rng, sigma_noise=sigma_noise, jitter=cfg.int_jitter)
            e0, e1 = max(0, z0 - 3), min(Z, z1 + 3)
            if used[e0:e1].any():
                continue
            signed = new[e0:e1] - clean[e0:e1]
            # Une interpolation à travers la coupole mélange poumon et foie jusque dans
            # l'abdomen : on labellise donc dans tout le CORPS, pas seulement près des poumons.
            vis = ndi.binary_closing((np.abs(signed) > cfg.diff_thr_hu) & body[e0:e1], iterations=1) & body[e0:e1]
            if vis.sum() >= cfg.min_voxels:
                accepted = (new, None, 0, (0, 0), 0.0, "INT", LABEL_INT, signed, vis)
        if accepted is None:
            continue
        new, src, shift, shift_yx, sigma_z, kind, lab_val, signed, vis = accepted
        diff = np.abs(signed)
        nvox = int(vis.sum())

        out[e0:e1] = new[e0:e1]
        label[e0:e1][vis] = lab_val
        zz = np.flatnonzero(vis.reshape(e1 - e0, -1).any(1))
        used[e0:e1] = True
        events.append(ArtifactEvent(kind, e0 + int(zz[0]), e0 + int(zz[-1]) + 1, src, shift, nvox,
                                    float(diff[vis].mean()), round(sigma_z, 2), shift_yx))

    if not events:
        return None, None, []
    return out.astype(np.float32), label, events


def slice_labels(label: np.ndarray, min_voxels: int = 20) -> np.ndarray:
    """Label par coupe axiale : 0 propre, 1 DS, 2 INT (classe majoritaire)."""
    out = np.zeros(label.shape[0], np.uint8)
    for z in range(label.shape[0]):
        ds = int((label[z] == LABEL_DS).sum())
        it = int((label[z] == LABEL_INT).sum())
        if max(ds, it) >= min_voxels:
            out[z] = LABEL_DS if ds >= it else LABEL_INT
    return out
