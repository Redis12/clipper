"""Repères du corps lus dans les classes de couleur (fit2.labels) : 2 bottes, cheveux (tête), ceinture (bassin),
2 poignets (bracelets bleus), mains (peau au bout des bracelets). Sert à guider la recopie quand le Goku de la référence
fait des grands gestes (sprint, fente, coup de poing) : la comparaison pixel par pixel seule s'enferme dans des poses
compactes fausses, les repères tirent chaque membre au bon endroit.
"""
import numpy as np
from scipy import ndimage as ndi

S3 = np.ones((3, 3))


def _blobs(mask, n, min_px=6):
    lab, k = ndi.label(mask, structure=S3)
    if k == 0:
        return []
    sizes = ndi.sum(mask, lab, range(1, k + 1))
    order = [i for i in np.argsort(-sizes) if sizes[i] >= min_px][:n]
    cs = ndi.center_of_mass(mask, lab, [i + 1 for i in order])
    return [(float(c[1]), float(c[0]), float(sizes[i])) for c, i in zip(cs, order)]


def find(lab):
    """lab = classes (fit2.labels) → dict de repères (x, y) en px de l'image."""
    out = {}
    boots = _blobs(lab == 7, 2, 10)
    out["boots"] = [(x, y) for x, y, _ in boots]
    hair = lab == 1
    if hair.sum() > 30:
        ys, xs = np.nonzero(hair)
        out["head"] = (float(xs.mean()), float(ys.mean()))
    blue = _blobs(lab == 4, 3, 4)
    if blue:
        out["belt"] = blue[0][:2]
        out["wrists"] = [(x, y) for x, y, _ in blue[1:]]
    allm = lab > 0
    if allm.sum() > 50:                                  # points extrêmes : poing tendu, pied tendu, haut des cheveux
        ys, xs = np.nonzero(allm)
        i, j = xs.argmax(), xs.argmin()
        out["right"], out["left"] = (float(xs[i]), float(ys[i])), (float(xs[j]), float(ys[j]))
    skin = np.isin(lab, (5, 6))
    if skin.sum() > 10:
        ys, xs = np.nonzero(skin)
        i = xs.argmax()
        out["skin_r"] = (float(xs[i]), float(ys[i]))           # main la plus en avant (coup de poing)
    orange = np.isin(lab, (2, 3))
    if orange.any():
        ys, xs = np.nonzero(orange)
        out["body"] = (float(xs.mean()), float(ys.mean()))
    return out


def _pair(a, b, miss):
    """distance entre 2 listes de points sans ordre (bottes, poignets)."""
    if not a and not b:
        return 0.0
    if len(a) != len(b):
        base = miss * abs(len(a) - len(b))
        n = min(len(a), len(b))
        if n == 0:
            return base
        a, b = a[:n], b[:n]
    else:
        base = 0.0
    if len(a) == 1:
        return base + float(np.hypot(a[0][0] - b[0][0], a[0][1] - b[0][1]))
    d1 = np.hypot(a[0][0] - b[0][0], a[0][1] - b[0][1]) + np.hypot(a[1][0] - b[1][0], a[1][1] - b[1][1])
    d2 = np.hypot(a[0][0] - b[1][0], a[0][1] - b[1][1]) + np.hypot(a[1][0] - b[0][0], a[1][1] - b[0][1])
    return base + float(min(d1, d2))


def dist(r, c, miss=25.0):
    """écart (px) entre les repères de la référence r et ceux de la recopie c."""
    d = _pair(r.get("boots", []), c.get("boots", []), miss) * 1.5
    d += _pair(r.get("wrists", []), c.get("wrists", []), miss * 0.6)
    for k, w in (("head", 1.5), ("belt", 1.0), ("body", 1.0), ("right", 1.0), ("left", 1.0), ("skin_r", 1.5)):
        if k in r and k in c:
            d += w * float(np.hypot(r[k][0] - c[k][0], r[k][1] - c[k][1]))
        elif k in r or k in c:
            d += miss
    return d
