"""Présentation de persos en silhouettes (11/11, début de la vidéo de référence de l'utilisateur) : stickmen Stick Nodes
en noir (parties blanches gardées : cheveux de Gear 5, cape…), alignés sur un sol sombre ; la caméra se pose sur chacun
(fond d'une couleur par perso, lumière néon au sol, particules, lente avancée) puis file au suivant (whip pan : flou de
mouvement + traits de vitesse) sur les temps de la musique ; plan large final : contours lumineux + « WHO WINS? ».
python3 tools/edit/stickline.py sortie.mp4
"""
import json
import math
import random
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage as ndi

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools/punch"))
sys.path.insert(0, str(HERE))
import sticknodes as sn  # noqa: E402
from camedit import beats, hblur, speed_lines, name_text, ease, SFX, W, H, FPS  # noqa: E402

LIB = ROOT / "library"
SNL = LIB / "_sticknodes"
GROUND = 1500                      # y du sol à l'écran
CHAR_H = 900                       # hauteur d'un perso au zoom 1
GAP = 560                          # écart entre deux persos (px monde)

# (source, nom, couleur du fond, miroir)
CAST = [
    ("png:Saitama/saitama_still.png", "SAITAMA", (225, 85, 80), False),
    ("Dragon Ball/Goku (Hero Suit) Ssj3", "GOKU", (175, 95, 225), False),
    ("Dragon Ball/Vegeta (Armour)", "VEGETA", (150, 150, 175), True),
    ("Luffy/LuffyOP(Gear5)", "LUFFY", (80, 200, 150), False),
    ("Naruto/naruto rikudou", "NARUTO", (80, 170, 220), True),
    ("Ichigo/_Ichigo-Bankai-Arlando", "ICHIGO", (235, 120, 60), False),
]


def silhouette(src, flip):
    if src.startswith("png:"):
        im = Image.open(SNL / src[4:]).convert("RGBA")
    else:
        im, _, _ = sn.render(json.load(open(SNL / f"{src}.json")), scale=3.0)
    a = np.asarray(im).astype(np.float32)
    al = a[..., 3]
    ys, xs = np.nonzero(al > 20)
    a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    rgb, al = a[..., :3], a[..., 3]
    lum = rgb @ np.array([0.299, 0.587, 0.114])
    sat = rgb.max(2) - rgb.min(2)
    white = (lum > 215) & (sat < 40) & (al > 128)
    out = np.zeros_like(a)
    out[..., :3] = np.array([10, 9, 16])
    out[white, :3] = 238
    out[..., 3] = al
    im = Image.fromarray(out.astype(np.uint8))
    if flip:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    k = CHAR_H / im.height
    return im.resize((max(1, round(im.width * k)), CHAR_H), Image.LANCZOS)


def rim(sil, col, width=7, strength=1.0):
    """contour lumineux de la couleur `col` autour de la silhouette (dessiné derrière)"""
    al = np.asarray(sil)[..., 3] > 100
    pad = width * 3
    big = np.pad(al, pad)
    ring = ndi.binary_dilation(big, iterations=width) & ~big
    lay = np.zeros(big.shape + (4,), np.uint8)
    lay[ring] = list(col) + [int(255 * strength)]
    g = Image.fromarray(lay).filter(ImageFilter.GaussianBlur(width * 0.8))
    return g, pad


def background(col):
    """dégradé : clair en haut (couleur), sombre vers le sol, sol presque noir"""
    y = np.arange(H, dtype=np.float32)[:, None]
    c = np.array(col, np.float32) / 255
    top = c * 0.95 + 0.05
    mid = c * 0.55
    k = np.clip(y / GROUND, 0, 1)
    sky = top[None, None] * (1 - k[..., None]) + mid[None, None] * k[..., None]
    floor = np.clip(1 - (y - GROUND) / 260, 0, 1)[..., None] * mid * 0.5 + 0.03
    a = np.where(y[..., None] < GROUND, sky, floor)
    a = np.broadcast_to(a, (H, W, 3)).copy()
    xx = np.arange(W, dtype=np.float32)[None, :]
    v = 1 - 0.35 * ((xx / W - 0.5) * 2) ** 2
    return a * v[..., None]


def floor_light(col, w=620):
    """lumière néon au sol (quadrilatère en perspective : étroit aux pieds, large vers la caméra)"""
    lay = Image.new("RGBA", (w * 2, 340), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    cx = w
    c2 = tuple(min(255, int(v * 0.55 + 120)) for v in col)
    d.polygon([(cx - w * 0.35, 40), (cx + w * 0.45, 40), (cx + w * 0.95, 250), (cx - w * 0.9, 250)], fill=c2 + (150,))
    d.polygon([(cx - w * 0.2, 40), (cx + w * 0.25, 40), (cx + w * 0.55, 200), (cx - w * 0.5, 200)], fill=(255, 255, 255, 80))
    glow = lay.filter(ImageFilter.GaussianBlur(26))
    out = Image.new("RGBA", lay.size, (0, 0, 0, 0))
    out.alpha_composite(glow)
    out.alpha_composite(glow)
    out.alpha_composite(lay.filter(ImageFilter.GaussianBlur(3)))
    return out


def dust(img, t, col, seed, vx=0.0):
    d = ImageDraw.Draw(img, "RGBA")
    rnd = random.Random(seed)
    c = tuple(min(255, int(v * 0.4 + 150)) for v in col)
    for _ in range(90):
        x0, y0 = rnd.uniform(0, W), rnd.uniform(0, GROUND)
        x = (x0 + t * rnd.uniform(-30, 30) - vx) % W
        y = (y0 - t * rnd.uniform(10, 40)) % GROUND
        L = rnd.uniform(6, 26)
        d.line((x, y, x + L, y + rnd.uniform(-3, 3)), fill=c + (int(rnd.uniform(60, 170)),), width=2)


def render(out, music=LIB / "_music/Delirious.mp3", m_start=40.0):
    bt, per = beats(music, m_start, 12)
    bt = [b for b in bt if b > 0.3]
    step = 2 if per < 0.45 else 1
    n = len(CAST)
    cuts = [0.0] + [bt[i * step] for i in range(1, n + 1)]      # cuts[n] = début du plan large
    t_wide = cuts[n]
    end = t_wide + per * step * 3.2
    sils = [silhouette(s, f) for s, _, _, f in CAST]
    rims = {}
    bgs = [background(c) for _, _, c, _ in CAST]
    lights = [floor_light(c) for _, _, c, _ in CAST]
    xs = [i * GAP for i in range(n)]
    WH = 0.22
    tmp = Path(tempfile.mkdtemp())
    whips = []
    cache = {}

    def scaled(i, z):
        key = (i, round(z, 2))
        if key not in cache:
            s = sils[i]
            cache[key] = s.resize((max(1, round(s.width * key[1])), max(1, round(s.height * key[1]))), Image.BILINEAR)
        return cache[key]

    def draw_cast(img, cam_x, z, focus, glow_col=None, gk=0.0, squeeze=1.0):
        mid = sum(xs) / n
        for i in range(n):
            sx = W / 2 + (mid + (xs[i] - mid) * squeeze - cam_x) * z
            s = scaled(i, z)
            if sx + s.width < -50 or sx - s.width > W + 50:
                continue
            x0, y0 = int(sx - s.width / 2), int(GROUND - s.height + 8 * z)
            if glow_col is not None and gk > 0:
                key = (i, round(z, 2), "rim")
                if key not in rims:
                    rims[key] = rim(s, (255, 150, 90))
                g, pad = rims[key]
                ga = g.copy()
                ga.putalpha(ga.getchannel("A").point(lambda v: int(v * gk)))
                img.alpha_composite(ga, (x0 - pad, y0 - pad)) if x0 - pad >= 0 and y0 - pad >= 0 else img.paste(ga, (x0 - pad, y0 - pad), ga)
            if x0 >= 0 and y0 >= 0 and x0 + s.width <= W:
                img.alpha_composite(s, (x0, y0))
            else:
                img.paste(s, (x0, y0), s)

    for fi in range(int(end * FPS)):
        t = fi / FPS
        k = max(j for j in range(n + 1) if cuts[j] <= t + 1e-6)
        whip = next((j for j in range(1, n + 1) if abs(t - cuts[j]) < WH / 2), None)
        if whip is not None and whip < n:
            j = whip
            p = (t - (cuts[j] - WH / 2)) / WH
            cam = xs[j - 1] + (xs[j] - xs[j - 1]) * (p * p * (3 - 2 * p))
            z = 1.0 + 0.06 * (cuts[j] - cuts[j - 1])
            ci = j - 1 if p < 0.5 else j
            a = bgs[ci].copy()
            img = Image.fromarray((a * 255).astype(np.uint8)).convert("RGBA")
            draw_cast(img, cam, z, ci)
            sp = math.sin(p * math.pi)
            a = np.asarray(img.convert("RGB"), np.float32) / 255
            a = hblur(a, 320 * sp)
            a = speed_lines(a, 30, 0.45 * sp, fi)
            img = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
            if abs(p - 0.5) <= 0.5 / (WH * FPS):
                whips.append(t)
        elif k < n:
            u = t - cuts[k]
            z = 1.0 + 0.06 * u                                        # lente avancée
            cam = xs[k] - 25 * u + (8 * math.sin(u * 2))
            img = Image.fromarray((bgs[k] * 255).astype(np.uint8)).convert("RGBA")
            L = lights[k]
            img.paste(L, (int(W / 2 - L.width / 2 + (xs[k] - cam) * z), GROUND - 40), L)
            dust(img, t, CAST[k][2], k, vx=cam * 0.3)
            draw_cast(img, cam, z, k)
            name_text(img, CAST[k][1], int(u / 0.05), H * 0.86, 104, glow=CAST[k][2])
        else:
            # plan large : la caméra recule, tout le monde, contours lumineux, « WHO WINS? »
            u = t - t_wide
            e = ease(u / 0.5)
            z = 1.0 - 0.47 * e
            sq = 1.0 - 0.5 * e
            mid = sum(xs) / n
            cam = (mid + (xs[n - 1] - mid) * sq) * (1 - e) + mid * e
            col = (230, 95, 80)
            img = Image.fromarray((background(col) * 255).astype(np.uint8)).convert("RGBA") if "wbg" not in cache else cache["wbg"].copy()
            cache.setdefault("wbg", img.copy())
            L = lights[0]
            L2 = L.resize((int(L.width * 1.4), L.height))
            img.paste(L2, (int(W / 2 - L2.width / 2), GROUND - 40), L2)
            dust(img, t, col, 77)
            draw_cast(img, cam, z, -1, glow_col=True, gk=min(1.0, max(0.0, (u - 0.35) / 0.3)), squeeze=sq)
            a = np.asarray(img.convert("RGB"), np.float32) / 255
            if u < 0.5:
                a = hblur(a, 160 * (1 - e))
            fl = math.exp(-max(0, u - 0.35) * 8) if u > 0.35 else 0
            a = a + (1 - a) * 0.7 * fl
            img = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
            name_text(img, "WHO WINS?", int(max(0, u - 0.45) / 0.06), H * 0.2, 150, glow=(255, 110, 70))
            if abs(u - 0.35) < 0.5 / FPS:
                whips.append(-t)                                      # impact
        img.convert("RGB").save(tmp / f"{fi:05d}.jpg", quality=92)

    # --- audio
    sr = 44100
    tot = int(end * sr) + sr
    mix = np.zeros(tot, np.float32)

    def pcm(path, ss=0.0, dur=None, gain=1.0):
        cmd = ["ffmpeg", "-v", "error", "-ss", str(ss)] + (["-t", str(dur)] if dur else []) + \
              ["-i", str(path), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"]
        return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32) * gain

    def put(t, s):
        a = int(t * sr)
        s = s[:max(0, tot - a)]
        mix[a:a + len(s)] += s

    put(0, pcm(music, m_start, end + 1, 0.55))
    rng = np.random.default_rng(1)
    Lw = int(0.35 * sr)
    env = np.sin(np.linspace(0, math.pi, Lw)) ** 2
    wh = np.convolve(rng.standard_normal(Lw).astype(np.float32), np.ones(18) / 18, "same") * env * 0.5
    for t in whips:
        if t >= 0:
            put(max(0, t - 0.17), wh)
        else:
            put(-t, pcm(SFX / "low_frequency_explosion_000.ogg", gain=0.5))
            put(-t, pcm(SFX / "impact_punch_heavy_000.ogg", gain=0.4))
    mix = np.tanh(mix * 1.1) * 0.9
    wav = tmp / "a.wav"
    with wave.open(str(wav), "wb") as w_:
        w_.setnchannels(1)
        w_.setsampwidth(2)
        w_.setframerate(sr)
        w_.writeframes((mix[:int(end * sr)] * 32767).astype(np.int16).tobytes())
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", str(tmp / "%05d.jpg"), "-i", str(wav),
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", str(out)], check=True)
    from clipper.slides import render as R
    R.stamp_video(Path(out))
    print(out, round(end, 2), "s", [round(c, 2) for c in cuts])


if __name__ == "__main__":
    render(sys.argv[1])
