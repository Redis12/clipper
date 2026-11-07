"""Rendu final d'une recopie image par image (fit.py) : 9:16, notre décor, caméra qui suit Goku en douceur,
lissage léger des angles (médiane sur 3 images : enlève les tressautements du fit sans ralentir les gestes vifs).
python3 render_fit.py doc.json fit.json[,fit2.json] sortie.mp4 [nb_images_ref] [fps]
"""
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "punch"))
import pivot_render as pr  # noqa: E402
from scene import make_bg  # noqa: E402

W, H = 1080, 1920
GY = 1250
REF_SCALE = 640 / 768
SCALE = 2.6
K = SCALE / REF_SCALE                                     # px de sortie par px de la référence
REF_FEET = 329                                            # y des pieds au sol dans la référence
doc = json.load(open(sys.argv[1]))
R = {}
for f in sys.argv[2].split(","):
    R.update({int(k): v for k, v in json.load(open(f)).items()})
OUT = sys.argv[3]
# pieds de la réf (bas de la silhouette) : le sol de la réf est en perspective (plus loin = plus haut), donc on pose
# Goku sur NOTRE sol et on ne garde que la hauteur de saut = sol local (max glissant) − bas de la silhouette
FEET = {}
_ff = Path(sys.argv[2].split(",")[0]).with_suffix("").with_suffix(".feet.json")
if _ff.exists():
    FEET = {int(k): v for k, v in json.load(open(_ff)).items()}
N = int(sys.argv[4]) if len(sys.argv) > 4 else max(R) + 1
FPS = int(sys.argv[5]) if len(sys.argv) > 5 else 30
ROLES = ["hip", "spine", "chest", "neck", "head", "uarm_f", "farm_f", "uarm_b", "farm_b",
         "thigh_f", "shin_f", "thigh_b", "shin_b"]
import views  # noqa: E402
ACTORS = views.make_actors(doc, SCALE)
g = ACTORS[0]
BG = make_bg(GY)

ids = sorted(R)
# lissage : médiane sur 3 images (angles dépliés), positions comprises
sm = {}
for j, i in enumerate(ids):
    nb = [R[k] for k in ids[max(0, j - 1): j + 2] if abs(k - i) <= 1 and R[k]["flip"] == R[i]["flip"]
          and R[k].get("view", 0) == R[i].get("view", 0)]
    p = dict(R[i])
    for k in ROLES:
        base = R[i][k]
        vals = [base + ((q[k] - base + 180) % 360 - 180) for q in nb]
        p[k] = float(np.median(vals))
    for k in ("x", "y"):
        p[k] = float(np.median([q[k] for q in nb]))
    sm[i] = p

# caméra : suit le x de Goku, lissée
xs = {i: sm[i]["x"] for i in ids}
cam = {}
c = None
for i in range(N):
    if i in xs:
        c = xs[i] if c is None else c + (xs[i] - c) * 0.12
    cam[i] = c
first = ids[0]

tmp = Path("/tmp/fit/render")
tmp.mkdir(parents=True, exist_ok=True)
for f in tmp.glob("*.png"):
    f.unlink()
hist = []
for i in range(N):
    img = BG.copy()
    if i in sm:
        p = sm[i]
        cx = cam[i] if cam[i] is not None else p["x"]
        X = W / 2 + (p["x"] - cx) * K
        Y = None
        if FEET and i in FEET:
            floor = max(FEET[j] for j in range(i - 20, i + 21) if j in FEET)
            lift = max(0.0, floor - FEET[i] - 3) * K
        else:
            lift = 0.0
        g = ACTORS[p.get("view", 0)]
        g.flip = p["flip"]
        pose = {k: p[k] for k in ROLES}
        # traînée quand il bouge vite (comme le flou de mouvement de la réf)
        if hist:
            pp, PX, PY, pf, _ = hist[-1]
            if abs(X - PX) > 40:
                for jj, (hp, hx, hy, hf, hg) in enumerate(hist[-3:][::-1]):
                    gh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                    hg.flip = hf
                    hg.draw(gh, hp, hx, hy, record=False, alpha=0.32 - 0.09 * jj)
                    img.alpha_composite(gh)
                g.flip = p["flip"]
        info = g.draw(img, pose, X, 0, ground=GY + 8, lift=lift, shadow_y=GY + 6, record=False)
        hist.append((pose, X, info["y"], p["flip"], g))
    else:
        hist = []
    if i < 30:                                             # sort du noir (comme la réf)
        img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * (1 - i / 30)))))
    img.convert("RGB").save(tmp / f"{i:05d}.png")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-r", str(FPS), "-i", str(tmp / "%05d.png"), "-c:v", "libx264",
                "-pix_fmt", "yuv420p", "-crf", "20", OUT], check=True)
print(N)
