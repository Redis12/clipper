"""Recopie image par image : pour chaque image d'une vidéo de référence faite avec le MÊME Goku Pivot, on cherche la
pose de notre marionnette (position des hanches, sens, angle de chaque os) qui redonne la même image.
Comparaison = différence de couleur sur une zone autour du perso, le perso étant posé sur le fond vide de la vidéo.
Recherche par descente coordonnée (±pas qui diminuent), en partant de la pose de l'image précédente.
python3 fit.py doc.json dossier_images image_fond_vide sortie.json [début fin]
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "punch"))
import pivot_render as pr  # noqa: E402
import stickanim as sa  # noqa: E402

doc = json.load(open(sys.argv[1]))
FR = sorted(Path(sys.argv[2]).glob("*.png"))
BG = Image.open(sys.argv[3]).convert("RGBA")
OUT = Path(sys.argv[4])
a0 = int(sys.argv[5]) if len(sys.argv) > 5 else 0
a1 = int(sys.argv[6]) if len(sys.argv) > 6 else len(FR)
# 2e départ possible : pose « modèle » (ex. debout), essayée à chaque image en plus de la précédente → évite de
# rester coincé dans une mauvaise pose (jambes repliées derrière le corps…)
TEMPLATE = json.loads(sys.argv[7]) if len(sys.argv) > 7 else None
SCALE = 640 / 768                                         # la vidéo = la scène Pivot (768×432) rendue en 640×360
g = pr.PivotActor(doc, 0, 0, pr.ROLES_PIVOT_GOKU, scale=SCALE)
ROLES = ["hip", "spine", "chest", "neck", "head", "uarm_f", "farm_f", "uarm_b", "farm_b",
         "thigh_f", "shin_f", "thigh_b", "shin_b"]
bga = np.asarray(BG.convert("RGB")).astype(np.int16)


def target(i):
    a = np.asarray(Image.open(FR[i]).convert("RGB")).astype(np.int16)
    m = np.abs(a - bga).sum(2) > 60
    return a, m


def render(p, box):
    x0, y0, x1, y1 = box
    c = BG.crop(box).copy()
    g.flip = p["flip"]
    pose = {r: p[r] for r in ROLES}
    g.draw(c, pose, p["x"] - x0, p["y"] - y0, record=False)
    return np.asarray(c.convert("RGB")).astype(np.int16)


SKIN = np.array([250, 215, 185])


def skinw(a):
    """poids ×4 sur la peau (bras fins : sinon la recherche les ignore)."""
    return 1 + 3 * (np.abs(a - SKIN).sum(2) < 90)


def wrap(d):
    return (d + 180) % 360 - 180


LIMITS = [("thigh_f", "shin_f", -170, 5), ("thigh_b", "shin_b", -170, 5),      # le genou ne plie que dans un sens
          ("uarm_f", "farm_f", -5, 170), ("uarm_b", "farm_b", -5, 170),        # le coude aussi
          ("hip", "spine", -40, 40), ("spine", "chest", -40, 40),
          ("chest", "neck", -45, 45), ("neck", "head", -40, 40)]


import os  # noqa: E402
if os.environ.get("FIT_FREE_KNEES"):                       # vue de face (fente latérale) : le genou peut partir des 2 côtés
    LIMITS = [x for x in LIMITS if not x[0].startswith("thigh")]


def anat(p):
    """pénalité anatomique (degrés hors des limites) : sans elle, le fit trouve des poses tordues qui « passent »
    à l'image (jambe repliée cachée par le pantalon) mais inutilisables pour rejouer le mouvement."""
    pen = 0.0
    for a, b, lo, hi in LIMITS:
        d = wrap(p[b] - p[a])
        pen += max(0.0, lo - d) + max(0.0, d - hi)
    return pen


def loss(p, tgt, box, tw=None):
    r = render(p, box)
    d = np.abs(r - tgt).sum(2)
    w = (tw if tw is not None else 1) + 3 * (np.abs(r - SKIN).sum(2) < 90)
    return float((d * w).mean()) + 1.0 * anat(p)


def init_from_mask(m, prev):
    ys, xs = np.nonzero(m)
    p = dict(prev) if prev else dict(sa.P["idle"], flip=False)
    if not prev:
        p["x"], p["y"] = float(xs.mean()), float(ys.min() + (ys.max() - ys.min()) * 0.55)
    return p


def fit(tgt, m, prev, prev_m):
    ys, xs = np.nonzero(m)
    box = (max(0, int(xs.min()) - 40), max(0, int(ys.min()) - 40), min(640, int(xs.max()) + 40), min(360, int(ys.max()) + 30))
    p = init_from_mask(m, prev)
    if prev is not None and prev_m is not None and prev_m.any():
        py, px = np.nonzero(prev_m)
        p["x"] += xs.mean() - px.mean()
        p["y"] += ys.min() - py.min()
    tc = tgt[box[1]:box[3], box[0]:box[2]]
    tw = skinw(tc)
    L = lambda q: loss(q, tc, box, tw)  # noqa: E731
    best = L(p)
    # sens + échange bras/jambes avant/arrière (ambiguïté de profil)
    cands = []
    q = dict(p, flip=not p["flip"])
    cands.append(q)
    q = dict(p)
    for a, b in (("uarm_f", "uarm_b"), ("farm_f", "farm_b")):
        q[a], q[b] = p[b], p[a]
    cands.append(q)
    q = dict(p)
    for a, b in (("thigh_f", "thigh_b"), ("shin_f", "shin_b")):
        q[a], q[b] = p[b], p[a]
    cands.append(q)
    for q in cands:
        lq = L(q)
        if lq < best:
            p, best = q, lq
    # rotation de tout le buste d'un coup (se pencher : hanche + colonne + cou + tête ensemble)
    TRUNK = ("hip", "spine", "chest", "neck", "head")
    for dr in (-90, -60, -40, -20, 20, 40, 60, 90):
        q = dict(p)
        for k in TRUNK:
            q[k] = p[k] + dr
        lq = L(q)
        if lq < best:
            p, best = q, lq
    # recherche en grille pour chaque membre (bras/jambe = 2 os), autour de la pose actuelle
    for a, b in (("uarm_f", "farm_f"), ("uarm_b", "farm_b"), ("thigh_f", "shin_f"), ("thigh_b", "shin_b")):
        base_a, base_b = p[a], p[b]
        for da in (-60, -40, -20, 0, 20, 40, 60):
            for db in (-60, -30, 0, 30, 60):
                if da == 0 and db == 0:
                    continue
                q = dict(p)
                q[a], q[b] = base_a + da, base_b + da + db
                lq = L(q)
                if lq < best:
                    p, best = q, lq
    keys = ["x", "y"] + ROLES
    for st_a, st_p, passes in ((24, 8, 1), (12, 4, 2), (6, 2, 2), (3, 1, 1), (1.5, 0.5, 1)):
        for _ in range(passes):
            improved = False
            for k in keys:
                s = st_p if k in ("x", "y") else st_a
                for sgn in (1, -1):
                    q = dict(p)
                    q[k] = p[k] + sgn * s
                    lq = L(q)
                    if lq < best - 1e-3:
                        p, best = q, lq
                        improved = True
                        break
            if not improved:
                break
    return p, best


res = {}
if OUT.exists():
    res = json.loads(OUT.read_text())
prev, prev_m = None, None
t0 = time.time()
for i in range(a0, a1):
    tgt, m = target(i)
    if m.sum() < 400:
        prev, prev_m = None, None
        continue
    p, lv = fit(tgt, m, prev, prev_m)
    for TP in ([] if TEMPLATE is None else (TEMPLATE if isinstance(TEMPLATE, list) else [TEMPLATE])):
        ys_, xs_ = np.nonzero(m)
        for fl in ((TP["flip"],) if "flip" in TP and not TP.get("_both") else (False, True)):
            tp = {k: v for k, v in TP.items() if not k.startswith("_")}
            tp["flip"] = fl
            tp["x"] = float(xs_.mean()) + TP.get("_dx", 0.0)
            tp["y"] = float(ys_.max()) - TP.get("_foot", 0.0)
            p2, l2 = fit(tgt, m, tp, None)
            if l2 < lv:
                p, lv = p2, l2
    p["loss"] = lv
    res[str(i)] = p
    prev, prev_m = {k: v for k, v in p.items() if k != "loss"}, m
    if i % 10 == 0:
        OUT.write_text(json.dumps(res))
        print(i, round(lv, 2), round(time.time() - t0), flush=True)
OUT.write_text(json.dumps(res))
print("fini", len(res))
