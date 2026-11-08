"""Recopie FINE d'une vidéo faite avec le même Goku Pivot (07–08/11, demandé : « un outil qui analyse tout, même
les petits détails »).

Différences avec fit.py :
- on ne recopie que les POSES DISTINCTES : la vidéo répète chaque pose 2–3 images (animation ~10 i/s) ; recalculer
  chaque image à part faisait trembler le perso. Chaque pose est tenue exactement le même nombre d'images que l'original.
- comparaison par CLASSES DE COULEUR (cheveux, orange clair/foncé = jambe avant/arrière, bleu, peau claire/foncée =
  bras avant/arrière, bottes, corde, rouge) : une pose fausse qui couvre « la même surface orange » ne passe plus.
- 2 étages : (A) squelette (place, sens, vue, 13 os) avec plusieurs départs, (B) CHAQUE MORCEAU du perso (97 :
  morceaux du pantalon, mains, pieds, mèches…) tourné en plus autour de son attache.
- carte des différences et score par pose (part des pixels du perso qui ne collent pas) pour contrôler.

python3 fit2.py doc.json dossier_images fond_vide.png sortie.json [début fin]
"""
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "punch"))
import stickanim as sa  # noqa: E402
import views  # noqa: E402

ROLES = ["hip", "spine", "chest", "neck", "head", "uarm_f", "farm_f", "uarm_b", "farm_b",
         "thigh_f", "shin_f", "thigh_b", "shin_b"]
# palette du Goku de base → classes (0 = fond)
PAL = [((24, 24, 24), 1), ((0, 0, 0), 1),
       ((238, 112, 60), 2), ((250, 111, 54), 2), ((228, 103, 52), 3),
       ((23, 68, 116), 4),
       ((251, 218, 188), 5), ((250, 211, 176), 6),
       ((2, 32, 66), 7), ((3, 29, 59), 7),
       ((198, 179, 120), 8), ((192, 169, 100), 8), ((164, 145, 87), 8),
       ((219, 40, 40), 9), ((209, 35, 35), 9)]
PCOL = np.array([c for c, _ in PAL], np.int16)
PCLS = np.array([k for _, k in PAL], np.int8)
FAMILY = {2: 2, 3: 2, 5: 5, 6: 5}                        # orange clair/foncé, peau claire/foncée = même famille
WEIGHT = {1: 1.5, 2: 1.0, 3: 1.0, 4: 1.5, 5: 3.0, 6: 3.0, 7: 5.0, 8: 2.0, 9: 3.0}   # bottes = repères forts


def labels(rgb, bg):
    """classe de chaque pixel : fond si proche du fond vide, sinon couleur de la palette la plus proche."""
    d = np.abs(rgb[:, :, None, :] - PCOL[None, None]).sum(3)
    lab = PCLS[d.argmin(2)]
    isbg = np.abs(rgb - bg).sum(2) < 45
    lab[isbg] = 0
    return lab


_wtab = np.ones(10, np.float32)
for k, w in WEIGHT.items():
    _wtab[k] = w
_fam = np.arange(10)
for k, f in FAMILY.items():
    _fam[k] = f


def mismatch(a, b):
    """coût : 0 si même classe, 0,4 si même famille (ex. orange clair/foncé), sinon poids de la classe."""
    diff = a != b
    same_fam = _fam[a] == _fam[b]
    w = np.maximum(_wtab[a], _wtab[b])
    return float((diff * np.where(same_fam, 0.4, 1.0) * w).sum())


def unique_poses(frames, bg, a0, a1, thr=0.6):
    """groupes d'images identiques (la même pose tenue) : [(image clé, [images…]), …]"""
    groups, prev = [], None
    for i in range(a0, a1):
        a = np.asarray(Image.open(frames[i]).convert("RGB")).astype(np.int16)
        if prev is not None and np.abs(a - prev).mean() < thr and groups:
            groups[-1][1].append(i)
        else:
            groups.append((i, [i]))
        prev = a
    return groups


def wrap(d):
    return (d + 180) % 360 - 180


LIMITS = [("thigh_f", "shin_f", -170, 5), ("thigh_b", "shin_b", -170, 5),
          ("uarm_f", "farm_f", -5, 170), ("uarm_b", "farm_b", -5, 170),
          ("hip", "spine", -40, 40), ("spine", "chest", -40, 40),
          ("chest", "neck", -45, 45), ("neck", "head", -40, 40)]


def anat(p):
    pen = 0.0
    for a, b, lo, hi in LIMITS:
        d = wrap(p[b] - p[a])
        pen += max(0.0, lo - d) + max(0.0, d - hi)
    pen += sum(max(0.0, abs(v) - 35) for v in p.get("ex", {}).values())   # un morceau ne se tord pas de 90°
    pen += sum(40 * max(0.0, 0.45 - f) + 40 * max(0.0, f - 1.15) for f in p.get("ls", {}).values())
    return pen


class Fitter:
    def __init__(self, doc, bg_img, scale=640 / 768):
        self.A = views.make_actors(doc, scale)
        self.BG = bg_img.convert("RGBA")
        self.bga = np.asarray(self.BG.convert("RGB")).astype(np.int16)

    def render(self, p, box):
        x0, y0, x1, y1 = box
        c = self.BG.crop(box).copy()
        g = self.A[p.get("view", 0)]
        g.flip = p["flip"]
        g.extra = {int(k): v for k, v in p.get("ex", {}).items()}
        g.lscale = {g.roles[r]: f for r, f in p.get("ls", {}).items()}
        g.draw(c, {r: p[r] for r in ROLES}, p["x"] - x0, p["y"] - y0, record=False)
        g.extra, g.lscale = {}, {}
        return np.asarray(c.convert("RGB")).astype(np.int16)

    def cost(self, p, tl, box, bgc):
        lab = labels(self.render(p, box), bgc)
        return mismatch(lab, tl) / 100.0 + 0.6 * anat(p)

    def fit(self, rgb, prev, starts, inits=()):
        bgl = self.bga
        m = np.abs(rgb - bgl).sum(2) >= 45
        ys, xs = np.nonzero(m)
        box = (max(0, int(xs.min()) - 30), max(0, int(ys.min()) - 30), min(rgb.shape[1], int(xs.max()) + 30),
               min(rgb.shape[0], int(ys.max()) + 25))
        crop = rgb[box[1]:box[3], box[0]:box[2]]
        bgc = bgl[box[1]:box[3], box[0]:box[2]]
        tl = labels(crop, bgc)
        C = lambda q: self.cost(q, tl, box, bgc)  # noqa: E731
        cx, foot = float(xs.mean()), float(ys.max())
        cands = []
        if prev:
            q = dict(prev)
            q["x"] += cx - prev["_cx"]
            q["y"] += foot - prev["_foot"]
            cands.append(q)
        for tp in starts:
            for v in (0, 2, 3, 6) if not prev else (prev.get("view", 0),):
                for fl in (False, True):
                    q = {k: tp[k] for k in ROLES}
                    q.update(flip=fl, view=v, x=cx, y=foot - tp.get("_foot", 120.0), ex={})
                    cands.append(q)
        for q0 in inits:                                         # poses d'un recopiage précédent
            q = {k: q0[k] for k in ROLES}
            q.update(flip=q0["flip"], view=q0.get("view", 0), x=q0["x"], y=q0["y"], ex=dict(q0.get("ex", {})))
            cands.append(q)
        scored = sorted(((C(q), j, q) for j, q in enumerate(cands)), key=lambda t: t[0])
        best_all = None
        for c0, _, q in scored[:2]:                              # on affine les 3 meilleurs départs
            q, c = self.stage_a(q, C, c0)
            if best_all is None or c < best_all[0]:
                best_all = (c, q)
        c, p = best_all
        p, c = self.stage_c(p, C, c)
        p, c = self.stage_b(p, C, c)
        p, c = self.stage_a(p, C, c, coarse=False)
        p["_cx"], p["_foot"] = cx, foot
        n_char = int((tl > 0).sum())
        return p, c, n_char, box

    def stage_a(self, p, C, best, coarse=True):
        # changement de vue / sens / échange avant-arrière
        alts = [dict(p, flip=not p["flip"])]
        for v in range(len(self.A)):
            if v != p.get("view", 0):
                alts.append(dict(p, view=v, ex={}))
        q = dict(p)
        for a, b in (("uarm_f", "uarm_b"), ("farm_f", "farm_b")):
            q[a], q[b] = p[b], p[a]
        alts.append(q)
        q = dict(p)
        for a, b in (("thigh_f", "thigh_b"), ("shin_f", "shin_b")):
            q[a], q[b] = p[b], p[a]
        alts.append(q)
        for q in alts:
            c = C(q)
            if c < best:
                p, best = q, c
        if coarse:
            # configurations complètes de jambes / bras (sauts absolus : sort des minimums « jambes repliées »)
            LEGS = [(270, 270, 270, 270), (280, 270, 262, 270), (295, 268, 248, 272), (310, 262, 232, 276),
                    (330, 268, 215, 262), (300, 240, 250, 285), (5, 275, 270, 270), (270, 270, 5, 275)]
            ARMS = [(275, 270, 268, 265), (300, 30, 290, 40), (285, 80, 280, 90), (250, 300, 240, 290),
                    (330, 10, 310, 20), (200, 250, 210, 250)]
            for lg in LEGS:
                for sw in (False, True):
                    q = dict(p)
                    a = lg if not sw else (lg[2], lg[3], lg[0], lg[1])
                    q["thigh_f"], q["shin_f"], q["thigh_b"], q["shin_b"] = [v + (0 if True else 0) for v in a]
                    c = C(q)
                    if c < best:
                        p, best = q, c
            for am in ARMS:
                q = dict(p)
                q["uarm_f"], q["farm_f"], q["uarm_b"], q["farm_b"] = am
                c = C(q)
                if c < best:
                    p, best = q, c
            for dr in (-60, -30, 30, 60):                        # tout le buste
                q = dict(p)
                for k in ("hip", "spine", "chest", "neck", "head"):
                    q[k] = p[k] + dr
                c = C(q)
                if c < best:
                    p, best = q, c
            for a, b in (("uarm_f", "farm_f"), ("uarm_b", "farm_b"), ("thigh_f", "shin_f"), ("thigh_b", "shin_b")):
                ba, bb = p[a], p[b]
                for da in (-60, -30, 0, 30, 60):
                    for db in (-60, -30, 0, 30, 60):
                        if da == db == 0:
                            continue
                        q = dict(p)
                        q[a], q[b] = ba + da, bb + da + db
                        c = C(q)
                        if c < best:
                            p, best = q, c
        keys = ["x", "y"] + ROLES
        steps = ((16, 6), (8, 3), (4, 1.5), (2, 0.75), (1, 0.4)) if coarse else ((4, 1.5), (2, 0.75), (1, 0.4))
        for sa_, sp in steps:
            for _ in range(3):
                imp = False
                for k in keys:
                    s = sp if k in ("x", "y") else sa_
                    for sg in (1, -1):
                        q = dict(p)
                        q[k] = p[k] + sg * s
                        c = C(q)
                        if c < best - 1e-4:
                            p, best, imp = q, c, True
                            break
                if not imp:
                    break
        return p, best

    def stage_c(self, p, C, best):
        """raccourci des membres (cuisse, tibia, bras, avant-bras vus de face) : longueur × 0,45–1,15."""
        limbs = ["thigh_f", "shin_f", "thigh_b", "shin_b", "uarm_f", "farm_f", "uarm_b", "farm_b"]
        for st in (0.25, 0.1, 0.05):
            for r in limbs:
                for sg in (-1, 1):
                    q = dict(p)
                    ls = dict(p.get("ls", {}))
                    ls[r] = round(ls.get(r, 1.0) + sg * st, 3)
                    q["ls"] = ls
                    c = C(q)
                    if c < best - 1e-4:
                        p, best = q, c
                        break
        # avec un raccourci, réessayer l'angle du membre et la hauteur
        for r in limbs:
            if abs(p.get("ls", {}).get(r, 1.0) - 1) > 0.05:
                for da in (-40, -20, 20, 40):
                    q = dict(p)
                    q[r] = p[r] + da
                    c = C(q)
                    if c < best:
                        p, best = q, c
        return p, best

    def stage_b(self, p, C, best):
        """chaque morceau tourné autour de son attache (pantalon, mains, pieds, mèches…)."""
        g = self.A[p.get("view", 0)]
        role_slots = set(g.roles.values())
        slots = [s for s in g.tree if s not in role_slots and s != g.root]
        for st in (20, 8, 3):
            for s in slots:
                for sg in (1, -1):
                    q = dict(p)
                    ex = dict(p.get("ex", {}))
                    ex[s] = ex.get(s, 0.0) + sg * st
                    q["ex"] = ex
                    c = C(q)
                    if c < best - 1e-4:
                        p, best = q, c
                        break
        p["ex"] = {s: round(v, 2) for s, v in p.get("ex", {}).items() if abs(v) > 0.5}
        return p, best


def templates():
    P = sa.P
    T = [dict(P["idle"], _foot=120.0), dict(P["stance"], _foot=115.0), dict(P["crouch"], _foot=90.0)]
    T.append(dict(P["idle"], hip=82, spine=86, chest=90, neck=88, head=88, thigh_b=200, shin_b=268, thigh_f=345,
                  shin_f=345, uarm_f=262, farm_f=300, uarm_b=250, farm_b=290, _foot=70.0))           # fente latérale
    T.append(dict(P["idle"], hip=10, spine=350, chest=335, neck=320, head=305, thigh_f=272, shin_f=270,
                  thigh_b=268, shin_b=270, uarm_f=272, farm_f=268, uarm_b=268, farm_b=265, _foot=100.0))  # penché
    T.append(dict(P["idle"], thigh_f=10, shin_f=275, _foot=120.0))                                   # genou levé
    return T


if __name__ == "__main__":
    doc = json.load(open(sys.argv[1]))
    FR = sorted(Path(sys.argv[2]).glob("*.png"))
    BGI = Image.open(sys.argv[3])
    OUT = Path(sys.argv[4])
    a0 = int(sys.argv[5]) if len(sys.argv) > 5 else 0
    a1 = int(sys.argv[6]) if len(sys.argv) > 6 else len(FR)
    F = Fitter(doc, BGI)
    INIT = {}
    if len(sys.argv) > 7:                                         # recopie(s) précédente(s) comme points de départ
        for f in sys.argv[7].split(","):
            INIT.update({int(k): v for k, v in json.load(open(f)).items()})
    groups = unique_poses(FR, F.bga, a0, a1)
    res = json.loads(OUT.read_text()) if OUT.exists() else {}
    prev = None
    t0 = time.time()
    ONLY = set(int(x) for x in sys.argv[8].split(",")) if len(sys.argv) > 8 else None
    for key, members in groups:
        if ONLY is not None and key not in ONLY:
            continue
        rgb = np.asarray(Image.open(FR[key]).convert("RGB")).astype(np.int16)
        if (np.abs(rgb - F.bga).sum(2) >= 45).sum() < 300:
            prev = None
            continue
        inits = [INIT[i] for i in members if i in INIT][:3]
        p, c, n, box = F.fit(rgb, prev, templates(), inits)
        res[str(key)] = dict(p, cost=round(c, 3), n=n, frames=members)
        prev = p
        OUT.write_text(json.dumps(res))
        print(key, len(members), round(c, 2), n, p.get("view"), len(p.get("ex", {})), round(time.time() - t0), flush=True)
    print("fini", len(res), flush=True)
