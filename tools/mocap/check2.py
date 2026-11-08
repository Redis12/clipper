"""Contrôle d'une recopie fit2 : pour chaque pose, la référence, la recopie et la carte des différences (rouge = pixel
du perso mal recopié). Score = part des pixels du perso qui ne collent pas. Planche des pires poses + vidéo
comparative (référence | recopie | différences) image par image.
python3 check2.py doc.json fit.json dossier_images fond.png sortie_dossier [nb_pires]
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fit2  # noqa: E402

doc = json.load(open(sys.argv[1]))
R = {int(k): v for k, v in json.load(open(sys.argv[2])).items()}
FR = sorted(Path(sys.argv[3]).glob("*.png"))
BGI = Image.open(sys.argv[4])
OUT = Path(sys.argv[5])
OUT.mkdir(parents=True, exist_ok=True)
NW = int(sys.argv[6]) if len(sys.argv) > 6 else 12
F = fit2.Fitter(doc, BGI)
full = (0, 0, BGI.width, BGI.height)


def panel(key):
    p = R[key]
    ref = np.asarray(Image.open(FR[key]).convert("RGB")).astype(np.int16)
    cop = F.render(p, full)
    lr, lc = fit2.labels(ref, F.bga), fit2.labels(cop, F.bga)
    bad = (lr != lc) & ((lr > 0) | (lc > 0)) & (fit2._fam[lr] != fit2._fam[lc])
    char = (lr > 0) | (lc > 0)
    score = bad.sum() / max(1, char.sum())
    dm = np.full(ref.shape, 235, np.uint8)
    dm[char] = (150, 150, 150)
    dm[bad] = (230, 30, 30)
    return ref.astype(np.uint8), cop.astype(np.uint8), dm, float(score)


scores = {}
frames_out = OUT / "cmp"
frames_out.mkdir(exist_ok=True)
for f in frames_out.glob("*.png"):
    f.unlink()
cache = {}
for key in sorted(R):
    a, b, d, s = panel(key)
    scores[key] = s
    cache[key] = (a, b, d)
# vidéo comparative : chaque image de la source montre la pose de son groupe
owner = {}
for key, p in R.items():
    for i in p["frames"]:
        owner[i] = key
n = 0
for i in range(min(owner), max(owner) + 1):
    if i not in owner:
        continue
    k = owner[i]
    ref = np.asarray(Image.open(FR[i]).convert("RGB"))
    _, b, d = cache[k]
    W = ref.shape[1]
    im = Image.new("RGB", (W, ref.shape[0] * 3 + 60), (20, 20, 20))
    im.paste(Image.fromarray(ref), (0, 0))
    im.paste(Image.fromarray(b), (0, ref.shape[0] + 30))
    im.paste(Image.fromarray(d), (0, 2 * ref.shape[0] + 60))
    dr = ImageDraw.Draw(im)
    dr.text((6, ref.shape[0] + 8), f"REFERENCE / RECOPIE  image {i}  pose {k}  vue {R[k].get('view', 0)}", fill=(255, 255, 255))
    dr.text((6, 2 * ref.shape[0] + 38), f"DIFFERENCES (rouge)  {scores[k] * 100:.1f} % du perso", fill=(255, 120, 120))
    im.save(frames_out / f"{n:05d}.png")
    n += 1
subprocess.run(["ffmpeg", "-v", "error", "-y", "-r", "30", "-i", str(frames_out / "%05d.png"), "-c:v", "libx264",
                "-pix_fmt", "yuv420p", "-crf", "22", str(OUT / "comparaison.mp4")], check=True)
worst = sorted(scores, key=lambda k: -scores[k])[:NW]
cells = []
for k in worst:
    a, b, d = cache[k]
    m = np.abs(a.astype(int) - F.bga).sum(2) >= 45
    m |= np.abs(b.astype(int) - F.bga).sum(2) >= 45
    ys, xs = np.nonzero(m)
    box = (max(0, xs.min() - 20), max(0, ys.min() - 20), min(a.shape[1], xs.max() + 20), min(a.shape[0], ys.max() + 20))
    trip = [Image.fromarray(x).crop(box) for x in (a, b, d)]
    w, h = trip[0].size
    c = Image.new("RGB", (w * 3, h + 18), (255, 255, 255))
    for j, t in enumerate(trip):
        c.paste(t, (j * w, 18))
    ImageDraw.Draw(c).text((4, 3), f"pose {k} : {scores[k] * 100:.1f} %", fill=(200, 0, 0))
    c.thumbnail((600, 260))
    cells.append(c)
H = sum(c.height for c in cells)
S = Image.new("RGB", (600, H), (255, 255, 255))
y = 0
for c in cells:
    S.paste(c, (0, y))
    y += c.height
S.save(OUT / "pires.png")
json.dump({str(k): round(v, 4) for k, v in scores.items()}, open(OUT / "scores.json", "w"))
v = np.array(list(scores.values()))
print("poses", len(v), "moyenne %.1f %%" % (v.mean() * 100), "médiane %.1f %%" % (np.median(v) * 100),
      "pire %.1f %%" % (v.max() * 100), "> 15 %%: %d" % (v > 0.15).sum())
