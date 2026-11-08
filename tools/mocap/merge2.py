"""Fusionne plusieurs recopies fit2 : pour chaque pose, garde celle dont la carte des différences est la plus propre.
python3 merge2.py doc.json dossier_images fond.png sortie.json a.json b.json …"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fit2  # noqa: E402

doc = json.load(open(sys.argv[1]))
FR = sorted(Path(sys.argv[2]).glob("*.png"))
F = fit2.Fitter(doc, Image.open(sys.argv[3]))
full = (0, 0, F.BG.width, F.BG.height)


def score(key, p):
    ref = np.asarray(Image.open(FR[key]).convert("RGB")).astype(np.int16)
    lr, lc = fit2.labels(ref, F.bga), fit2.labels(F.render(p, full), F.bga)
    bad = (lr != lc) & ((lr > 0) | (lc > 0)) & (fit2._fam[lr] != fit2._fam[lc])
    return bad.sum() / max(1, ((lr > 0) | (lc > 0)).sum())


best = {}
for f in sys.argv[5:]:
    for k, p in json.load(open(f)).items():
        s = score(int(k), p)
        if k not in best or s < best[k][0]:
            best[k] = (s, p)
json.dump({k: v[1] for k, v in best.items()}, open(sys.argv[4], "w"))
print(len(best), "poses ; moyenne %.1f %%" % (100 * np.mean([v[0] for v in best.values()])))
