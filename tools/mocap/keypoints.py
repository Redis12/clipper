"""Squelette 2D de notre Goku découpé (library/_mocap/clips), image par image (08/11).
Le Goku Pivot dessine les membres ARRIÈRE plus foncés : peau (248,208,172) vs (248,216,188), pantalon (228,68,16) vs
(236,76,28), bottes (0,24,56) vs (0,28,64) → on sépare bras/jambe avant et arrière par la couleur, puis pour chaque
membre : départ (épaule / hanche), bout (main / cheville), coude ou genou = point du chemin le plus « central » du
membre (chemin le long de l'axe médian) le plus éloigné de la corde.
    kp = keypoints.extract(rgba, r)   # r = rayon de la tête (≈ 0,062 × hauteur de Goku debout)
    → {"head", "neck", "hip", "sh_f", "el_f", "wr_f", "sh_b", "el_b", "wr_b", "kn_f", "an_f", "toe_f", "kn_b", "an_b",
       "toe_b", "facing"}  (points (x, y) en px de l'image, None si invisible)
"""
import math

import numpy as np
from scipy import ndimage as ndi
from skimage.graph import route_through_array

import reskin
import skins


def _path(mask, soft, a, b):
    """chemin de a à b qui suit le milieu de `mask` (peut passer par `soft`, plus cher)."""
    dt = ndi.distance_transform_edt(mask)
    cost = np.full(mask.shape, 60.0)
    cost[soft] = 8.0
    cost[mask] = 1.0 / (1.0 + dt[mask]) + 0.05
    try:
        idx, _ = route_through_array(cost, (int(a[1]), int(a[0])), (int(b[1]), int(b[0])), fully_connected=True,
                                     geometric=True)
    except Exception:
        return None
    return np.array([(x, y) for y, x in idx], float)


def _bend(path, a, b, frac=0.5):
    """coude / genou : point du chemin le plus loin de la corde a→b (sinon le milieu)."""
    if path is None or len(path) < 3:
        return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    ax, ay = a
    dx, dy = b[0] - ax, b[1] - ay
    L = math.hypot(dx, dy) or 1.0
    dev = np.abs((path[:, 0] - ax) * dy - (path[:, 1] - ay) * dx) / L
    # on ne cherche que dans la partie centrale du membre
    s = np.cumsum(np.r_[0, np.hypot(*np.diff(path, axis=0).T)])
    s /= s[-1] or 1.0
    ok = (s > 0.25) & (s < 0.75)
    if dev[ok].max(initial=0) < 0.05 * L:
        j = int(np.argmin(np.abs(s - frac)))
    else:
        j = int(np.argmax(np.where(ok, dev, -1)))
    return tuple(path[j])


def _nearest(mask, p):
    ys, xs = np.nonzero(mask)
    if not len(ys):
        return None
    j = int(np.argmin((xs - p[0]) ** 2 + (ys - p[1]) ** 2))
    return (float(xs[j]), float(ys[j]))


def _farthest(mask, p):
    ys, xs = np.nonzero(mask)
    if not len(ys):
        return None
    j = int(np.argmax((xs - p[0]) ** 2 + (ys - p[1]) ** 2))
    return (float(xs[j]), float(ys[j]))


def extract(a, r, state=None):
    state = {} if state is None else state
    S = skins.segment(a, r, state)
    vis, orange, navy, dark, skin, white, lime, red = reskin._masks(a)
    R, G, B = [a[..., i].astype(int) for i in range(3)]
    kp = {}
    head = S["head"]
    if head is None:
        return None
    cx, cy, side, neck = head
    kp["head"] = (cx, cy)
    kp["neck"] = neck or state.get("neck")
    kp["facing"] = 1 if side >= 0 else -1
    # hanche = centre de la ceinture (sinon haut du pantalon)
    hip = state.get("belt")
    pants = S["pants"]
    if hip is None and pants.any():
        ys, xs = np.nonzero(pants)
        top = ys < np.percentile(ys, 15)
        hip = (float(xs[top].mean()), float(ys[top].mean()))
    kp["hip"] = hip
    body = orange | navy | S["under"]
    # ---- jambes : pantalon clair = avant, foncé = arrière ; bottes : bleu 64 = avant, 56 = arrière
    light = S["light"]
    bl, bn = ndi.label(S["boots"])
    boots = {"f": np.zeros_like(vis), "b": np.zeros_like(vis)}
    for i in range(1, bn + 1):
        m = bl == i
        if m.sum() < 0.15 * r * r:
            continue
        boots["f" if np.median(B[m]) >= 60 else "b"] |= m
    for s_, pm in (("f", pants & light), ("b", pants & ~light)):
        bm = boots[s_]
        if not bm.any() or not pm.any() or hip is None:
            kp[f"kn_{s_}"] = kp[f"an_{s_}"] = kp[f"toe_{s_}"] = None
            continue
        an = _nearest(bm & ndi.binary_dilation(pm, iterations=4), hip) or _nearest(bm, hip)
        toe = _farthest(bm, an)
        # cheville = milieu du haut de la botte
        top_b = bm & ndi.binary_dilation(pm, iterations=4)
        if top_b.sum() > 5:
            ys, xs = np.nonzero(top_b)
            an = (float(xs.mean()), float(ys.mean()))
        start = _nearest(pm, hip)
        path = _path(pm | bm, body, start, an)
        kp[f"an_{s_}"], kp[f"toe_{s_}"] = an, toe
        kp[f"kn_{s_}"] = _bend(path, hip, an)
    # ---- bras : peau claire = avant (sans le visage), peau foncée = arrière ; poignets + mains
    arm_all = (S["arms"] | S["hands"] | S["wrists"]) & ~S["remove"]
    back_skin = skin & (G < 212) & ~S["remove"]
    front_skin = skin & (G >= 212) & ~S["remove"]
    chest = None
    if kp["neck"] and hip:
        chest = (kp["neck"][0] * 0.75 + hip[0] * 0.25, kp["neck"][1] * 0.75 + hip[1] * 0.25)
    armset = arm_all
    lab, n = ndi.label(ndi.binary_dilation(armset, iterations=2))
    lab = lab * armset
    comps = []
    for i in range(1, n + 1):
        m = lab == i
        if m.sum() < 0.12 * r * r:
            continue
        sk_ = m & skin
        g = np.median(G[sk_]) if sk_.any() else 220
        comps.append((m.sum(), m, g))
    comps.sort(key=lambda c: -c[0])
    arms = {}
    if len(comps) >= 2:
        (n1, m1, g1), (n2, m2, g2) = comps[:2]
        if g1 >= g2:
            arms = {"f": m1, "b": m2}
        else:
            arms = {"f": m2, "b": m1}
    elif len(comps) == 1:
        m = comps[0][1]
        fm = m & ((front_skin) | (S["wrists"] & ndi.binary_dilation(front_skin, iterations=3)))
        bm = m & ((back_skin) | (S["wrists"] & ndi.binary_dilation(back_skin, iterations=3)))
        arms = {"f": fm, "b": bm}
    for s_ in ("f", "b"):
        m = arms.get(s_)
        if m is None or not m.any() or chest is None:
            kp[f"sh_{s_}"] = kp[f"el_{s_}"] = kp[f"wr_{s_}"] = None
            continue
        sh = _nearest(m, chest)
        wr = _farthest(m, sh)
        path = _path(m, body | S["under"], sh, wr)
        kp[f"sh_{s_}"], kp[f"wr_{s_}"] = sh, wr
        kp[f"el_{s_}"] = _bend(path, sh, wr)
    return kp


def angle(p, q):
    """angle absolu (0 = droite, 90 = haut) de p vers q (y de l'image vers le bas)"""
    return math.degrees(math.atan2(-(q[1] - p[1]), q[0] - p[0]))


def to_pose(kp, prev=None):
    """points → angles des 13 os (rôles de stickanim), le perso est dessiné tel quel (pas de miroir)."""
    prev = prev or {}
    P = dict(prev)
    if kp is None:
        return P
    hip, neck, head = kp["hip"], kp["neck"], kp["head"]
    if hip and neck:
        a = angle(hip, neck)
        P["hip"] = P["spine"] = P["chest"] = a
    if neck and head:
        P["neck"] = P["head"] = angle(neck, head)
    for s_ in ("f", "b"):
        if kp.get(f"sh_{s_}") and kp.get(f"el_{s_}") and kp.get(f"wr_{s_}"):
            P[f"uarm_{s_}"] = angle(kp[f"sh_{s_}"], kp[f"el_{s_}"])
            P[f"farm_{s_}"] = angle(kp[f"el_{s_}"], kp[f"wr_{s_}"])
        if hip and kp.get(f"kn_{s_}") and kp.get(f"an_{s_}"):
            P[f"thigh_{s_}"] = angle(hip, kp[f"kn_{s_}"])
            P[f"shin_{s_}"] = angle(kp[f"kn_{s_}"], kp[f"an_{s_}"])
    return P
