"""Mouvement d'une vidéo → poses du moteur stickman (07/11, essai).
Squelette détecté par YOLO-pose (17 points COCO) → angles des rôles (hip, spine, chest, neck, head, uarm/farm, thigh/shin),
points peu sûrs = trous comblés dans le temps, lissage léger. python3 retarget.py kp.json frames_dir out.mp4 [couleur=red|blue]"""
import json, math, sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "punch"))
ROLES_SRC = {  # rôle : (point de départ, point d'arrivée) ; -1 = milieu des hanches, -2 = milieu des épaules
    "hip": (-1, -2), "spine": (-1, -2), "chest": (-1, -2), "neck": (-2, 0), "head": (-2, 0),
    "uarm_f": (5, 7), "farm_f": (7, 9), "uarm_b": (6, 8), "farm_b": (8, 10),
    "thigh_f": (11, 13), "shin_f": (13, 15), "thigh_b": (12, 14), "shin_b": (14, 16)}


def pt(kp, i, cmin=0.25):
    if i == -1:
        a, b = pt(kp, 11, cmin), pt(kp, 12, cmin)
    elif i == -2:
        a, b = pt(kp, 5, cmin), pt(kp, 6, cmin)
    else:
        x, y, c = kp[i]
        return (x, y) if c >= cmin else None
    if a and b:
        return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    return a or b


def pick(dets, frame, want):
    """le combattant de la couleur voulue (couleur moyenne autour de ses points)."""
    best, bs = None, -1e9
    for d in dets:
        px = [frame[int(min(frame.shape[0] - 1, max(0, y))), int(min(frame.shape[1] - 1, max(0, x)))]
              for x, y, c in d["kp"] if c > 0.2]
        if not px:
            continue
        m = np.mean(px, 0).astype(float)
        score = (m[0] - m[2]) if want == "red" else (m[2] - m[0])
        if score > bs:
            best, bs = d, score
    return best if bs > 10 else None


def extract(kpjson, frames, want="red"):
    data = json.load(open(kpjson))
    files = sorted(Path(frames).glob("*.png"))
    rows = []
    for dets, f in zip(data, files):
        fr = np.asarray(Image.open(f).convert("RGB"))
        d = pick(dets, fr, want)
        row = {}
        if d:
            kp = d["kp"]
            nose, ms = pt(kp, 0), pt(kp, -2)
            facing = 1 if (nose and ms and nose[0] >= ms[0]) else -1
            for role, (a, b) in ROLES_SRC.items():
                A, B = pt(kp, a), pt(kp, b)
                if A and B and (A != B):
                    ang = math.degrees(math.atan2(-(B[1] - A[1]), B[0] - A[0]))
                    if facing < 0:
                        ang = 180 - ang
                    row[role] = ang % 360
            hp = pt(kp, -1)
            anks = [p for p in (pt(kp, 15), pt(kp, 16)) if p]
            row["_x"] = hp[0] if hp else None
            row["_foot"] = max(p[1] for p in anks) if anks else None
            row["_facing"] = facing
        rows.append(row)
    return rows


def fill(rows, key, circ=True):
    """comble les trous par interpolation (angles : chemin le plus court), puis lisse."""
    idx = [i for i, r in enumerate(rows) if r.get(key) is not None]
    if not idx:
        return [None] * len(rows)
    out = [None] * len(rows)
    for i in range(len(rows)):
        if i <= idx[0]:
            out[i] = rows[idx[0]][key]
        elif i >= idx[-1]:
            out[i] = rows[idx[-1]][key]
    for a, b in zip(idx, idx[1:]):
        va, vb = rows[a][key], rows[b][key]
        d = ((vb - va + 180) % 360 - 180) if circ else (vb - va)
        for i in range(a, b + 1):
            out[i] = va + d * (i - a) / max(1, b - a)
    # lissage (moyenne glissante 3, en dépliant les angles)
    if circ:
        un = np.unwrap(np.radians(out))
        sm = np.convolve(np.pad(un, 1, mode="edge"), np.ones(3) / 3, "valid")
        return list(np.degrees(sm) % 360)
    return list(np.convolve(np.pad(np.array(out, float), 1, mode="edge"), np.ones(3) / 3, "valid"))


def poses(rows):
    keys = list(ROLES_SRC)
    cols = {k: fill(rows, k) for k in keys}
    xs = fill(rows, "_x", circ=False)
    ft = fill(rows, "_foot", circ=False)
    fc = [r.get("_facing") for r in rows]
    last = 1
    for i, f in enumerate(fc):
        fc[i] = f if f else last
        last = fc[i]
    return [({k: cols[k][i] for k in keys}, xs[i], ft[i], fc[i]) for i in range(len(rows))]
