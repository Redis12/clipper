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


def background(col, gy=GROUND):
    """mur dégradé (couleur, clair en haut) jusqu'à la ligne du sol gy, puis sol sombre"""
    y = np.arange(H, dtype=np.float32)[:, None]
    c = np.array(col, np.float32) / 255
    top = c * 0.95 + 0.05
    mid = c * 0.55
    k = np.clip(y / gy, 0, 1)
    sky = top[None, None] * (1 - k[..., None]) + mid[None, None] * k[..., None]
    floor = np.clip(1 - (y - gy) / 420, 0, 1)[..., None] * mid * 0.45 + 0.03
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


# --------------------------------------------------------------------------------------------- caméra 3D (orbite)
R_CIRC = 1.6          # rayon du cercle des persos (m)
CH_M = 1.8            # taille d'un perso (m)
F = 1370.0            # focale (px)
HORIZON = 973.0       # ligne d'horizon à l'écran


def project(px, pz, cam):
    """point au sol (px, pz) → (x écran, y écran des pieds, profondeur) ; cam = (angle, distance, hauteur)"""
    th, D, hgt = cam
    cx, cz = D * math.sin(th), -D * math.cos(th)                 # la caméra regarde le centre (0, 0)
    dx, dz = px - cx, pz - cz
    fx, fz = -math.sin(th), math.cos(th)                         # axe de visée
    rx, rz = math.cos(th), math.sin(th)                          # axe droit
    depth = dx * fx + dz * fz
    lat = dx * rx + dz * rz
    return W / 2 + F * lat / depth, HORIZON + F * hgt / depth, depth


def mix(c1, c2, k):
    return tuple(int(a + (b - a) * k) for a, b in zip(c1, c2))


def orbit_ease(p):
    """départ très rapide puis long ralenti (comme la référence)"""
    p = min(1.0, max(0.0, p))
    return 1 - (1 - p) ** 4


def render(out, music=LIB / "_music/Delirious.mp3", m_start=40.0):
    bt, per = beats(music, m_start, 12)
    bt = [b for b in bt if b > 0.3]
    step = 2 if per < 0.45 else 1
    n = len(CAST)
    cuts = [0.0] + [bt[i * step] for i in range(1, n + 1)]          # cuts[n] = début du plan large
    t_wide = cuts[n]
    end = t_wide + per * step * 3.4
    sils = [silhouette(s, f) for s, _, _, f in CAST]
    cols = [c for _, _, c, _ in CAST]
    # persos en cercle ; la caméra « devant » le perso k a l'angle ang[k]
    ang = [-i * 2 * math.pi / n for i in range(n)]
    pos = [(R_CIRC * math.sin(a), -R_CIRC * math.cos(a)) for a in ang]
    MOVE = 0.75                                                       # durée d'une orbite d'un perso au suivant
    tmp = Path(tempfile.mkdtemp())
    events = []
    cache = {}
    bg_cache = {}
    prev_th = None

    def sil_at(i, h):
        key = (i, int(h / 4))
        if key not in cache:
            s = sils[i]
            hh = max(4, key[1] * 4)
            cache[key] = s.resize((max(1, round(s.width * hh / s.height)), hh), Image.BILINEAR)
        return cache[key]

    def bg(col, gy):
        key = tuple(v // 4 for v in col) + (int(gy // 6),)
        if key not in bg_cache:
            bg_cache[key] = Image.fromarray((background(col, key[-1] * 6) * 255).astype(np.uint8)).convert("RGBA")
        return bg_cache[key].copy()

    def camera(t):
        """(angle, distance, hauteur, couleur, perso en focus, vitesse 0-1, glow, plan large 0-1)"""
        k = max(j for j in range(n + 1) if cuts[j] <= t + 1e-6)
        if k == 0:
            u = t
            return ang[0] - 0.05 * u, 4.2 - 0.12 * u, 1.0, cols[0], 0, 0.0, 0.0
        u = t - cuts[k]
        a0 = ang[k - 1] - 0.05 * (cuts[k] - cuts[k - 1])
        if k < n:
            e = orbit_ease(u / MOVE)
            th = a0 + (ang[k] - a0) * e - 0.05 * max(0.0, u - MOVE * 0.6)
            D = 4.2 - 0.12 * max(0.0, u - 0.2) + 0.5 * math.sin(math.pi * min(1, u / MOVE))
            sp = 1.5 * (1 - min(1, u / MOVE)) ** 5
            return th, D, 1.0, mix(cols[k - 1], cols[k], min(1, u / (MOVE * 0.5))), k, min(1.0, sp), 0.0
        # plan large : la caméra recule et monte, tourne encore un peu
        e = orbit_ease(u / 0.9)
        th = a0 - 0.6 * e
        D = 4.2 + 3.6 * e
        return th, D, 1.0 + 0.6 * e, mix(cols[-1], (230, 95, 80), min(1, u / 0.5)), -1, min(1.0, 3 * (1 - min(1, u / 0.9)) ** 3), e

    for fi in range(int(end * FPS)):
        t = fi / FPS
        th, D, hgt, col, focus, sp, wide = camera(t)
        img = bg(col, HORIZON + F * hgt / (D + 5.0))
        cam = (th, D, hgt)
        # triangle de lumière au sol (tourne avec la caméra)
        lay = Image.new("RGBA", (W // 2, H // 2), (0, 0, 0, 0))
        dl = ImageDraw.Draw(lay)
        lite = tuple(min(255, int(v * 0.5 + 130)) for v in col)
        for rad, a_ in ((2.3, 210), (1.25, 140)):
            pts = []
            for j in range(3):
                aa = 0.35 + j * 2 * math.pi / 3
                x_, y_, d_ = project(rad * math.sin(aa), -rad * math.cos(aa), cam)
                pts.append((x_ / 2, y_ / 2))
            dl.polygon(pts, fill=(lite if rad > 2 else (255, 255, 255)) + (a_,))
        glow = lay.filter(ImageFilter.GaussianBlur(14)).resize((W, H), Image.BILINEAR)
        img.alpha_composite(glow)
        img.alpha_composite(glow)
        img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(2)).resize((W, H), Image.BILINEAR))
        dust(img, t, col, 5, vx=th * 900)
        # persos, du plus loin au plus proche
        items = []
        for i, (px, pz) in enumerate(pos):
            sx, fy, dep = project(px, pz, cam)
            if dep < 0.6:
                continue
            items.append((dep, i, sx, fy, F * CH_M / dep))
        for dep, i, sx, fy, hpx in sorted(items, reverse=True):
            s = sil_at(i, hpx)
            x0, y0 = int(sx - s.width / 2), int(fy - s.height)
            if x0 > W or x0 + s.width < 0:
                continue
            if wide > 0.4:
                g, pad = rim(s, (255, 150, 90), width=5)
                ga = g.copy()
                ga.putalpha(ga.getchannel("A").point(lambda v, k_=min(1.0, (wide - 0.4) / 0.4): int(v * k_)))
                img.paste(ga, (x0 - pad, y0 - pad), ga)
            img.paste(s, (x0, y0), s)
        a = np.asarray(img.convert("RGB"), np.float32) / 255
        if sp > 0.05:
            a = hblur(a, 230 * sp)
            a = speed_lines(a, 24, 0.35 * sp, fi)
        if wide > 0:                                                  # flash à l'arrivée du plan large
            u = t - t_wide
            if 0.55 < u:
                a = a + (1 - a) * 0.7 * math.exp(-(u - 0.55) * 8)
        img = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
        if focus >= 0:
            u = t - cuts[focus]
            if focus == 0 or u > MOVE * 0.35:
                name_text(img, CAST[focus][1], int((u - (0 if focus == 0 else MOVE * 0.35)) / 0.05), H * 0.86, 104,
                          glow=cols[focus])
        else:
            u = t - t_wide
            name_text(img, "WHO WINS?", int(max(0, u - 0.6) / 0.06), H * 0.2, 150, glow=(255, 110, 70))
        for j in range(1, n + 1):
            if abs(t - cuts[j]) < 0.5 / FPS:
                events.append(("whoosh", t))
        if abs(t - t_wide - 0.55) < 0.5 / FPS:
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
    print(out, round(end, 2), "s", [round(c, 2) for c in cuts])


if __name__ == "__main__":
    render(sys.argv[1])
