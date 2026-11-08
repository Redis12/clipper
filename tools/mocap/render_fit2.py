"""Rendu d'une recopie fine (fit2) : chaque pose tenue exactement le nombre d'images de l'original (pas de
tremblement), effets d'apparition recopiés (fantôme, flou, téléportation en tranches), 2 sorties :
- comparaison à l'échelle de la référence : référence | recopie | différences (rouge), image par image ;
- vidéo finale 9:16 sur notre décor, caméra qui suit, sauts = sol local − bas de la silhouette.
python3 render_fit2.py doc.json fit.json decoupage.json dossier_images fond.png comparaison.mp4 finale.mp4
"""
import json
import random
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "punch"))
import fit2  # noqa: E402
import views  # noqa: E402
from scene import make_bg  # noqa: E402

doc = json.load(open(sys.argv[1]))
R = {int(k): v for k, v in json.load(open(sys.argv[2])).items()}
CUT = json.load(open(sys.argv[3]))
FR = sorted(Path(sys.argv[4]).glob("*.png"))
BGI = Image.open(sys.argv[5]).convert("RGBA")
OUT_CMP, OUT_FIN = sys.argv[6], sys.argv[7]
FX = {int(k): v for k, v in CUT.get("effects", {}).items()}     # pose → {"fx": ghost|blur|glitch|sparse, "pose": clé}
ROLES = fit2.ROLES
N = len(FR)
owner = {}
for k, p in R.items():
    for i in p["frames"]:
        owner[i] = k
FEET = {}
bga = np.asarray(BGI.convert("RGB")).astype(np.int16)
for i in owner:
    a = np.asarray(Image.open(FR[i]).convert("RGB")).astype(np.int16)
    m = np.abs(a - bga).sum(2) >= 45
    if m.any():
        FEET[i] = int(np.nonzero(m)[0].max())


def pose_of(k):
    src = FX.get(k, {}).get("pose", k)
    return R[src] if src in R else R[k]


def draw_actor(A, canvas, p, x, y=None, ground=None, lift=0.0, alpha=1.0, shadow=None):
    g = A[p.get("view", 0)]
    g.flip = p["flip"]
    g.extra = {int(s): v for s, v in p.get("ex", {}).items()}
    g.lscale = {g.roles[k]: f for k, f in p.get("ls", {}).items()}
    g.fmirror = [int(q) for q in p.get("fm", [])]
    if ground is None:
        info = g.draw(canvas, {r: p[r] for r in ROLES}, x, y, record=False, alpha=alpha)
    else:
        info = g.draw(canvas, {r: p[r] for r in ROLES}, x, 0, ground=ground, lift=lift, record=False, alpha=alpha,
                      shadow_y=shadow)
    g.extra, g.lscale, g.fmirror = {}, {}, []
    return info


def apply_fx(layer, kind, seed):
    """effets d'apparition de la référence, appliqués à la couche du perso (RGBA)."""
    if not kind:
        return layer
    r = random.Random(seed)
    if kind == "ghost":
        a = layer.getchannel("A").point(lambda v: int(v * 0.35))
        layer.putalpha(a)
        return layer.filter(ImageFilter.GaussianBlur(1.5))
    if kind == "blur":
        out = Image.new("RGBA", layer.size, (0, 0, 0, 0))
        for dy in range(-18, 19, 3):
            sh = layer.copy()
            sh.putalpha(sh.getchannel("A").point(lambda v: int(v * 0.12)))
            out.alpha_composite(sh, (r.randint(-3, 3), dy))
        return out
    # téléportation : tranches horizontales décalées, une partie qui manque
    keep = 0.95 if kind == "glitch" else 0.22
    out = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    y = 0
    H = layer.height
    while y < H:
        h = r.randint(2, 6)
        if r.random() < keep:
            strip = layer.crop((0, y, layer.width, min(H, y + h)))
            out.alpha_composite(strip, (r.randint(-10, 10), y))
        y += h
    return out


# ---------------------------------------------------------------- 1) comparaison à l'échelle de la référence
A_ref = views.make_actors(doc, 640 / 768)
tmp = Path("/tmp/fit/r2cmp")
tmp.mkdir(parents=True, exist_ok=True)
for f in tmp.glob("*.png"):
    f.unlink()
first, last = min(owner), max(owner)
n = 0
for i in range(0, N):
    ref = Image.open(FR[i]).convert("RGB")
    cop = BGI.copy()
    if i in owner:
        k = owner[i]
        p = dict(pose_of(k))
        if FX.get(k, {}).get("pose") is not None:
            p["x"], p["y"] = R[k]["x"], R[k]["y"]
        lay = Image.new("RGBA", cop.size, (0, 0, 0, 0))
        draw_actor(A_ref, lay, p, p["x"], p["y"])
        cop.alpha_composite(apply_fx(lay, FX.get(k, {}).get("fx"), k))
    cop = cop.convert("RGB")
    lr = fit2.labels(np.asarray(ref).astype(np.int16), bga)
    lc = fit2.labels(np.asarray(cop).astype(np.int16), bga)
    bad = (lr != lc) & ((lr > 0) | (lc > 0)) & (fit2._fam[lr] != fit2._fam[lc])
    char = (lr > 0) | (lc > 0)
    dm = np.full((*lr.shape, 3), 235, np.uint8)
    dm[char] = (150, 150, 150)
    dm[bad] = (230, 30, 30)
    W, Hh = ref.size
    im = Image.new("RGB", (W, Hh * 3 + 60), (20, 20, 20))
    im.paste(ref, (0, 0))
    im.paste(cop, (0, Hh + 30))
    im.paste(Image.fromarray(dm), (0, 2 * Hh + 60))
    d = ImageDraw.Draw(im)
    d.text((6, Hh + 8), f"REFERENCE (haut) / RECOPIE (milieu)   image {i}", fill=(255, 255, 255))
    sc = 100 * bad.sum() / max(1, char.sum())
    d.text((6, 2 * Hh + 38), f"DIFFERENCES (rouge) : {sc:.0f} % du perso" if char.any() else "", fill=(255, 130, 130))
    im.save(tmp / f"{n:05d}.png")
    n += 1
subprocess.run(["ffmpeg", "-v", "error", "-y", "-r", "30", "-i", str(tmp / "%05d.png"), "-c:v", "libx264",
                "-pix_fmt", "yuv420p", "-crf", "20", OUT_CMP], check=True)

# ---------------------------------------------------------------- 2) vidéo finale 9:16
W, H, GY, SCALE = 1080, 1920, 1250, 2.6
K = SCALE / (640 / 768)
A = views.make_actors(doc, SCALE)
BG = make_bg(GY)
# caméra : moyenne centrée sur ±12 images (suit les grands déplacements, fente du coup de poing, sans retard)
cam, c = {}, None
for i in range(N):
    xs_ = [R[owner[j]]["x"] for j in range(i - 12, i + 13) if j in owner]
    if xs_:
        c = sum(xs_) / len(xs_)
    cam[i] = c
tmp2 = Path("/tmp/fit/r2fin")
tmp2.mkdir(parents=True, exist_ok=True)
for f in tmp2.glob("*.png"):
    f.unlink()
for i in range(N):
    img = BG.copy()
    if i in owner:
        k = owner[i]
        p = dict(pose_of(k))
        X = W / 2 + (R[k]["x"] - cam[i]) * K
        lift = 0.0
        grounded = any(a <= i <= b for a, b in CUT.get("ground", []))   # au sol : jamais de saut (la perspective trompe)
        if i in FEET and not grounded:
            floor = max(FEET[j] for j in range(i - 20, i + 21) if j in FEET)
            lift = max(0.0, floor - FEET[i] - 3) * K
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        fx = FX.get(k, {}).get("fx")
        info = draw_actor(A, lay, p, X, ground=GY + 8, lift=lift, shadow=None)
        if not fx:
            bx = info["box"]
            X = X if bx is None else (bx[0] + bx[2]) / 2           # ombre centrée sous le corps, pas sous la hanche
            sh = ImageDraw.Draw(img, "RGBA")
            hh = max(0.15, 1 - lift / 900)
            sh.ellipse((X - 80 * hh, GY + 6 - 11 * hh, X + 80 * hh, GY + 6 + 11 * hh), fill=(0, 0, 0, int(70 * hh)))
        img.alpha_composite(apply_fx(lay, fx, k))
    nf = min(30, max(6, N // 10))                                # fondu d'ouverture (court si le passage est court)
    if i < nf:
        img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * (1 - i / nf)))))
    img.convert("RGB").save(tmp2 / f"{i:05d}.png")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-r", "30", "-i", str(tmp2 / "%05d.png"), "-c:v", "libx264",
                "-pix_fmt", "yuv420p", "-crf", "20", OUT_FIN], check=True)
print("ok", n)
