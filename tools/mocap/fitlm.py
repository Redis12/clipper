"""Recopie fine guidée par repères (08/11) : fit2 + écart entre les repères du corps (landmarks.py : bottes, tête,
ceinture, poignets) de la référence et de la recopie. Pour les grands gestes (sprint, fente, coup de poing) où fit2
seul s'enfermait dans des poses compactes fausses. Départs en plus : course, fente-coup de poing.
python3 fitlm.py doc.json dossier_images fond_vide.png sortie.json début fin [init.json] [poids_repères]
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fit2  # noqa: E402
import landmarks as L  # noqa: E402

RUN = dict(hip=95, spine=75, chest=70, neck=70, head=60, uarm_f=300, farm_f=30, uarm_b=250, farm_b=330,
           thigh_f=320, shin_f=250, thigh_b=250, shin_b=200, _foot=95.0)
LUNGE_PUNCH = dict(hip=100, spine=60, chest=55, neck=50, head=40, uarm_f=10, farm_f=5, uarm_b=220, farm_b=150,
                   thigh_f=330, shin_f=270, thigh_b=200, shin_b=190, _foot=75.0)
SPRINT_BACK = dict(hip=100, spine=70, chest=65, neck=60, head=50, uarm_f=320, farm_f=40, uarm_b=200, farm_b=250,
                   thigh_f=0, shin_f=260, thigh_b=210, shin_b=190, _foot=85.0)


def starts():
    T = fit2.templates()
    for t in (RUN, LUNGE_PUNCH, SPRINT_BACK):
        T.append(dict(t))
        sw = dict(t)                                  # jambes inversées
        sw["thigh_f"], sw["thigh_b"], sw["shin_f"], sw["shin_b"] = t["thigh_b"], t["thigh_f"], t["shin_b"], t["shin_f"]
        T.append(sw)
    return T


class LMFitter(fit2.Fitter):
    W = 0.35

    def cost(self, p, tl, box, bgc):
        key = id(tl)
        if getattr(self, "_rk", None) != key:
            self._rk, self._rl = key, L.find(tl)
        lab = fit2.labels(self.render(p, box), bgc)
        return fit2.mismatch(lab, tl) / 100.0 + 0.6 * fit2.anat(p) + self.W * L.dist(self._rl, L.find(lab))


if __name__ == "__main__":
    doc = json.load(open(sys.argv[1]))
    FR = sorted(Path(sys.argv[2]).glob("*.png"))
    BGI = Image.open(sys.argv[3])
    OUT = Path(sys.argv[4])
    a0, a1 = int(sys.argv[5]), int(sys.argv[6])
    F = LMFitter(doc, BGI)
    if len(sys.argv) > 8:
        LMFitter.W = float(sys.argv[8])
    INIT = {}
    if len(sys.argv) > 7 and sys.argv[7] != "-":
        for f in sys.argv[7].split(","):
            INIT.update({int(k): v for k, v in json.load(open(f)).items()})
    groups = fit2.unique_poses(FR, F.bga, a0, a1)
    res = json.loads(OUT.read_text()) if OUT.exists() else {}
    prev, t0 = None, time.time()
    for key, members in groups:
        rgb = np.asarray(Image.open(FR[key]).convert("RGB")).astype(np.int16)
        if (np.abs(rgb - F.bga).sum(2) >= 45).sum() < 300:
            prev = None
            continue
        inits = [INIT[i] for i in members if i in INIT][:3]
        p, c, n, box = F.fit(rgb, prev, starts(), inits)
        res[str(key)] = dict(p, cost=round(c, 3), n=n, frames=members)
        prev = p
        OUT.write_text(json.dumps(res))
        print(key, len(members), round(c, 2), n, round(time.time() - t0), flush=True)
    print("fini", len(res), flush=True)
