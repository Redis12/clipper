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
CAST = [                                         # 3 persos max (comme la référence)
    ("Dragon Ball/Goku (Hero Suit) Ssj3", "GOKU", (225, 85, 80), False),
    ("Luffy/LuffyOP(Gear5)", "LUFFY", (190, 90, 210), False),
    ("Naruto/naruto rikudou", "NARUTO", (80, 160, 230), True),
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


def background(col, gy=GROUND):
    """mur dégradé (couleur, clair en haut) jusqu'à la ligne du sol gy, puis sol sombre"""
    y = np.arange(H, dtype=np.float32)[:, None]
    c = np.array(col, np.float32) / 255
    top = c * 0.95 + 0.05
    mid = c * 0.55
    k = np.clip(y / gy, 0, 1)
    sky = top[None, None] * (1 - k[..., None]) + mid[None, None] * k[..., None]
    floor = np.clip(1 - (y - gy) / 700, 0, 1)[..., None] * mid * 0.6 + 0.03
    a = np.where(y[..., None] < gy, sky, floor)
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


# --------------------------------------------------------------------------------------------- caméra 3D (look-at)
R_CIRC = 1.25         # rayon du triangle des persos (m)
CH_M = 1.8            # taille d'un perso (m)
F = 1370.0            # focale (px)
YC = 1080.0           # où tombe le point visé (à 0,9 m du sol, au centre) à l'écran


class Cam:
    def __init__(self, th, D, hgt):
        self.C = np.array([D * math.sin(th), hgt, -D * math.cos(th)])
        f = np.array([0.0, 0.9, 0.0]) - self.C
        self.f = f / np.linalg.norm(f)
        r = np.cross([0.0, 1.0, 0.0], self.f)
        self.r = r / np.linalg.norm(r)
        self.u = np.cross(self.f, self.r)
        self.th = th

    def proj(self, P):
        v = np.asarray(P, float) - self.C
        z = v @ self.f
        return W / 2 + F * (v @ self.r) / z, YC - F * (v @ self.u) / z, z


def mix(c1, c2, k):
    return tuple(int(a + (b - a) * k) for a, b in zip(c1, c2))


def col_at(th, cols):
    """couleur du mur selon l'angle de la caméra (glisse en continu d'un perso au suivant)"""
    n = len(cols)
    x = (th / (2 * math.pi) * n) % n
    i = int(x)
    return mix(cols[i], cols[(i + 1) % n], x - i)


def orbit_ease(p):
    p = min(1.0, max(0.0, p))
    return 1 - (1 - p) ** 4


def render(out, music=LIB / "_music/Delirious.mp3", m_start=40.0):
    bt, per = beats(music, m_start, 10)
    step = 2 if per < 0.45 else 1
    INTRO = 0.55
    whips = [b for b in bt if b > INTRO + 0.4][::step][:3]          # 2 orbites vers les persos suivants + le recul final
    t_wide = whips[2]
    end = t_wide + 1.9
    n = len(CAST)
    sils = [silhouette(s, f) for s, _, _, f in CAST]
    cols = [c for _, _, c, _ in CAST]
    ang = [i * 2 * math.pi / n for i in range(n)]
    pos = [(R_CIRC * math.sin(a), -R_CIRC * math.cos(a)) for a in ang]
    MOVE, DRIFT, STEP = 0.8, 0.22, 2 * math.pi / n
    tmp = Path(tempfile.mkdtemp())
    events = [("whoosh", 0.0)]
    cache, bg_cache = {}, {}

    def theta(t):
        th = -1.1 * (1 - orbit_ease(t / INTRO)) + DRIFT * t        # l'intro tourne vite puis la dérive ne s'arrête jamais
        for w in whips[:2]:
            th += STEP * orbit_ease((t - w) / MOVE)
        return th

    def cam_at(t):
        e = orbit_ease(t / INTRO)
        D = 8.0 + (4.0 - 8.0) * e
        hgt = 6.5 + (1.05 - 6.5) * e
        th = theta(t)
        D += 0.35 * sum(math.sin(math.pi * min(1, max(0, (t - w) / MOVE))) for w in whips[:2])
        D -= 0.1 * t
        wide = 0.0
        if t >= t_wide:
            wide = orbit_ease((t - t_wide) / 0.9)
            D += 2.2 * wide
            hgt += 0.9 * wide
        return Cam(th, D, hgt), wide

    def sil_at(i, h):
        key = (i, int(h / 4))
        if key not in cache:
            s_ = sils[i]
            hh = max(4, key[1] * 4)
            cache[key] = s_.resize((max(1, round(s_.width * hh / s_.height)), hh), Image.BILINEAR)
        return cache[key]

    def bg(col, gy):
        key = tuple(v // 4 for v in col) + (int(gy // 6),)
        if key not in bg_cache:
            bg_cache[key] = Image.fromarray((background(col, max(1, key[-1] * 6)) * 255).astype(np.uint8)).convert("RGBA")
        return bg_cache[key].copy()

    prev = None
    for fi in range(int(end * FPS)):
        t = fi / FPS
        cam, wide = cam_at(t)
        th = cam.th
        col = col_at(th, cols)
        hf = np.array([-math.sin(th), 0, math.cos(th)])
        gy = cam.proj(hf * 9.0)[1]                                     # ligne mur / sol
        img = bg(col, min(H - 1, max(1, gy)))
        # triangle néon au sol + lumière blanche du départ
        lay = Image.new("RGBA", (W // 2, H // 2), (0, 0, 0, 0))
        dl = ImageDraw.Draw(lay)
        lite = tuple(min(255, int(v * 0.5 + 130)) for v in col)
        for rad, fill in ((1.9, lite + (210,)), (1.0, (255, 255, 255, 130))):
            pts = []
            for j in range(3):
                aa = math.pi / 3 + j * 2 * math.pi / 3
                x_, y_, _ = cam.proj((rad * math.sin(aa), 0.0, -rad * math.cos(aa)))
                pts.append((x_ / 2, y_ / 2))
            dl.polygon(pts, fill=fill)
        burst = max(0.0, 1 - t / 0.4)
        if burst > 0:
            x_, y_, z_ = cam.proj((0, 0.3, 0))
            r_ = 260 * burst / max(1.0, z_ / 4)
            dl.ellipse((x_ / 2 - r_, y_ / 2 - r_ * 0.6, x_ / 2 + r_, y_ / 2 + r_ * 0.6), fill=(255, 255, 255, int(255 * burst)))
        glow = lay.filter(ImageFilter.GaussianBlur(14)).resize((W, H), Image.BILINEAR)
        img.alpha_composite(glow)
        img.alpha_composite(glow)
        img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(2)).resize((W, H), Image.BILINEAR))
        dust(img, t, col, 5, vx=th * 900)
        # étincelles qui jaillissent du centre au départ
        if t < 0.9:
            d = ImageDraw.Draw(img, "RGBA")
            cx_, cy_, _ = cam.proj((0, 0.4, 0))
            rnd = random.Random(3)
            for _ in range(70):
                a_ = rnd.uniform(0, 2 * math.pi)
                sp_ = rnd.uniform(900, 2600)
                r0 = sp_ * t
                L = rnd.uniform(40, 140) * (1 - t / 0.9)
                al = int(230 * (1 - t / 0.9))
                d.line((cx_ + math.cos(a_) * r0, cy_ + math.sin(a_) * r0, cx_ + math.cos(a_) * (r0 + L),
                        cy_ + math.sin(a_) * (r0 + L)), fill=(255, 150, 90, al), width=3)
        # persos (billboards), du plus loin au plus proche
        items = []
        for i, (px, pz) in enumerate(pos):
            fx, fy, z = cam.proj((px, 0, pz))
            hx, hy, _ = cam.proj((px, CH_M, pz))
            if z < 0.5:
                continue
            items.append((z, i, fx, fy, fy - hy))
        for z, i, fx, fy, hpx in sorted(items, reverse=True):
            s_ = sil_at(i, hpx)
            x0, y0 = int(fx - s_.width / 2), int(fy - s_.height)
            if wide > 0.35:
                g, pad = rim(s_, (255, 150, 90), width=5)
                k_ = min(1.0, (wide - 0.35) / 0.4)
                g.putalpha(g.getchannel("A").point(lambda v: int(v * k_)))
                img.paste(g, (x0 - pad, y0 - pad), g)
            img.paste(s_, (x0, y0), s_)
        # flou de mouvement selon la vitesse de la caméra
        a = np.asarray(img.convert("RGB"), np.float32) / 255
        dth = abs(theta(t + 0.5 / FPS) - theta(t - 0.5 / FPS)) * FPS   # rad/s
        sp = min(1.0, max(0.0, (dth - 0.6) / 6)) * (min(1.0, t / 0.3) if t < 0.3 else 1.0)
        if sp > 0.02:
            a = hblur(a, 260 * sp)
            a = speed_lines(a, 22, 0.35 * sp, fi)
        if t < 0.12:                                                  # plongée : flou vertical
            k_ = int(30 * (1 - t / 0.12))
            if k_ > 2:
                c_ = np.cumsum(np.pad(a, ((k_, k_), (0, 0), (0, 0)), mode="edge"), axis=0)
                a = (c_[2 * k_:] - c_[:-2 * k_])[:H] / (2 * k_)
        if t > t_wide + 0.5:
            a = a + (1 - a) * 0.7 * math.exp(-(t - t_wide - 0.5) * 8)
        img = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
        name_text(img, "WHO WINS?", int(max(0, t - 0.45) / 0.06), H * 0.17, 150, glow=(255, 110, 70))
        for w in whips:
            if abs(t - w) < 0.5 / FPS:
                events.append(("whoosh", t))
        if abs(t - t_wide - 0.5) < 0.5 / FPS:
            events.append(("boom", t))
        img.convert("RGB").save(tmp / f"{fi:05d}.jpg", quality=92)

    # --- audio
    sr = 44100
    tot = int(end * sr) + sr
    mixb = np.zeros(tot, np.float32)

    def pcm(path, ss=0.0, dur=None, gain=1.0):
        cmd = ["ffmpeg", "-v", "error", "-ss", str(ss)] + (["-t", str(dur)] if dur else []) + \
              ["-i", str(path), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"]
        return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32) * gain

    def put(t, s_):
        a_ = int(t * sr)
        s_ = s_[:max(0, tot - a_)]
        mixb[a_:a_ + len(s_)] += s_

    put(0, pcm(music, m_start, end + 1, 0.55))
    rng = np.random.default_rng(1)
    Lw = int(0.5 * sr)
    env = np.exp(-np.linspace(0, 6, Lw)) * (1 - np.exp(-np.linspace(0, 60, Lw)))
    wh = np.convolve(rng.standard_normal(Lw).astype(np.float32), np.ones(14) / 14, "same") * env * 0.6
    for kind, t in events:
        if kind == "whoosh":
            put(t, wh)
        else:
            put(t, pcm(SFX / "low_frequency_explosion_000.ogg", gain=0.5))
            put(t, pcm(SFX / "impact_punch_heavy_000.ogg", gain=0.4))
    put(0.0, pcm(SFX / "impact_punch_heavy_000.ogg", gain=0.35))
    mixb = np.tanh(mixb * 1.1) * 0.9
    wav = tmp / "a.wav"
    with wave.open(str(wav), "wb") as w_:
        w_.setnchannels(1)
        w_.setsampwidth(2)
        w_.setframerate(sr)
        w_.writeframes((mixb[:int(end * sr)] * 32767).astype(np.int16).tobytes())
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", str(tmp / "%05d.jpg"), "-i", str(wav),
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", str(out)], check=True)
    from clipper.slides import render as R
    R.stamp_video(Path(out))
    print(out, round(end, 2), "s", "whips", [round(w, 2) for w in whips])


if __name__ == "__main__":
    render(sys.argv[1])
