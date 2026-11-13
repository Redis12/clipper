"""Intro « néon » (13/11, vidéo de référence de l'utilisateur) : persos dessinés en traits lumineux (contour + lignes
intérieures de l'image officielle, une couleur par perso) debout en cercle sur une grille au sol, dans un ciel étoilé noir.
La caméra arrive de très loin et de haut en tournant, puis tourne sans jamais s'arrêter et passe d'un perso à l'autre sur
les temps de la musique ; le perso devant la caméra s'allume (plus de lueur), les autres restent plus sombres ; fin sur le
héros : son nom en lettres-boîtes + sous-titre.
Images en pied sur fond blanc : library/_neon/<Perso>.png|jpg (détourées ici).
python3 tools/edit/neonring.py sortie.mp4
"""
import math
import random
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage as ndi

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from camedit import beats, hblur, SFX, W, H, FPS  # noqa: E402

LIB = ROOT / "library"
NEON = LIB / "_neon"
ANTON = str(ROOT / "tools/money_sim/fonts/anton.woff2")

# (fichier, nom affiché, sous-titre, couleur néon)
CAST = [
    ("Goku", "GOKU", "Son", (255, 140, 60)),
    ("Vegeta", "VEGETA", "Prince", (70, 140, 255)),
    ("Gohan", "GOHAN", "Son", (200, 90, 255)),
    ("Piccolo", "PICCOLO", "Namekian", (80, 255, 140)),
]
HERO = 0                                   # le plan final se pose sur lui

R_CIRC = 1.5                               # rayon du cercle des persos (m)
CH_M = 1.8                                 # taille d'un perso (m)
FOC = 1500.0                               # focale (px)
YC = 1150.0                                # où tombe le point visé à l'écran


# ------------------------------------------------------------------------------------------- persos en néon
def cutout(path):
    """fond blanc (ou faux damier clair) relié au bord → transparent"""
    im = Image.open(path).convert("RGBA")
    a = np.asarray(im, np.float32)
    rgb = a[..., :3]
    bg = (rgb.min(-1) > 205) & ((rgb.max(-1) - rgb.min(-1)) < 30)
    if im.mode == "RGBA":
        bg |= a[..., 3] < 20
    lab, _ = ndi.label(bg)
    edge = set(np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]])) - {0}
    m = ~np.isin(lab, list(edge))
    m = ndi.binary_opening(m, iterations=1)
    lab2, n = ndi.label(m)                                     # garde le plus gros morceau (le perso)
    if n > 1:
        sizes = ndi.sum(m, lab2, range(1, n + 1))
        m = lab2 == (1 + int(np.argmax(sizes)))
    m = ndi.binary_fill_holes(m)
    ys, xs = np.nonzero(m)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    return rgb[y0:y1, x0:x1], m[y0:y1, x0:x1]


def neon_sprite(path, col, h=1100):
    """RGBA : intérieur noir presque opaque, contour épais + traits intérieurs de la couleur, cœur clair, lueur."""
    rgb, m = cutout(path)
    k = h / m.shape[0]
    size = (max(1, int(m.shape[1] * k)), h)
    g = Image.fromarray(np.uint8(rgb.mean(-1))).resize(size, Image.LANCZOS)
    m = np.asarray(Image.fromarray(np.uint8(m * 255)).resize(size, Image.LANCZOS)) > 127
    ga = np.asarray(g, np.float32)
    # traits intérieurs : les lignes sombres du dessin (encre) = gris local - gris
    loc = ndi.uniform_filter(ga, 9)
    ink = np.clip((loc - ga - 8) / 40, 0, 1) * m
    ink = ndi.grey_dilation(ink, size=2)
    # contour de la silhouette
    er = ndi.binary_erosion(m, iterations=3)
    rim = (m & ~er).astype(np.float32)
    line = np.maximum(rim, ink * 0.9)
    pad = 60
    L = np.zeros((h + 2 * pad, size[0] + 2 * pad), np.float32)
    L[pad:-pad, pad:-pad] = line
    M = np.zeros_like(L)
    M[pad:-pad, pad:-pad] = m
    glow = ndi.gaussian_filter(L, 8) * 1.8 + ndi.gaussian_filter(L, 26) * 1.6
    glow *= 1 - ndi.gaussian_filter(M, 6) * 0.7                # intérieur sombre : la lueur sort surtout autour
    c = np.array(col, np.float32) / 255
    core = np.clip(L, 0, 1)[..., None]
    rgbo = c * np.clip(L * 1.3 + glow, 0, 1)[..., None] + (1 - c) * core * 0.3   # cœur des traits plus clair
    alpha = np.clip(np.maximum(M * 0.88, np.clip(L * 1.3 + glow, 0, 1)), 0, 1)
    out = np.concatenate([np.clip(rgbo, 0, 1), alpha[..., None]], -1)
    return Image.fromarray(np.uint8(out * 255), "RGBA"), pad


# ------------------------------------------------------------------------------------------- caméra
class Cam:
    def __init__(self, th, D, hgt, look_y=0.95):
        self.C = np.array([D * math.sin(th), hgt, -D * math.cos(th)])
        f = np.array([0.0, look_y, 0.0]) - self.C
        self.f = f / np.linalg.norm(f)
        r = np.cross([0.0, 1.0, 0.0], self.f)
        self.r = r / np.linalg.norm(r)
        self.u = np.cross(self.f, self.r)
        self.th = th

    def proj(self, P):
        v = np.asarray(P, float) - self.C
        z = v @ self.f
        return W / 2 + FOC * (v @ self.r) / z, YC - FOC * (v @ self.u) / z, z


def ease_out(p, k=3):
    p = min(1.0, max(0.0, p))
    return 1 - (1 - p) ** k


def ease_io(p):
    p = min(1.0, max(0.0, p))
    return p * p * (3 - 2 * p)


# ------------------------------------------------------------------------------------------- décor
rnd = np.random.default_rng(7)
STARS = np.c_[rnd.uniform(-30, 30, 1400), rnd.uniform(-8, 30, 1400), rnd.uniform(-30, 30, 1400)]
STAR_C = rnd.choice(np.array([[255, 255, 255], [150, 200, 255], [255, 170, 230], [120, 255, 230]]), 1400, p=[.6, .2, .1, .1])


def draw_stars(img, cam, prev):
    d = ImageDraw.Draw(img, "RGBA")
    for P, c in zip(STARS, STAR_C):
        x, y, z = cam.proj(P)
        if z < 0.5 or not (-40 < x < W + 40 and -40 < y < H + 40):
            continue
        b = int(min(255, 90 + 2600 / z))
        r = max(0.7, 9 / z)
        if prev is not None:                                    # traînée quand la caméra file
            px, py, pz = prev.proj(P)
            if pz > 0.5 and math.hypot(px - x, py - y) > 3:
                d.line((px, py, x, y), fill=tuple(int(v) for v in c) + (int(b * 0.6),), width=max(1, int(r)))
                continue
        d.ellipse((x - r, y - r, x + r, y + r), fill=tuple(int(v) for v in c) + (b,))


def draw_grid(cam, alpha):
    """grille au sol (lignes tous les 0,35 m, disque de rayon 3,6 m qui s'efface au bord), à mi-résolution"""
    lay = Image.new("RGBA", (W // 2, H // 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    Rg, st = 3.6, 0.35
    n = int(Rg / st)
    for i in range(-n, n + 1):
        v = i * st
        h_ = math.sqrt(max(0.0, Rg * Rg - v * v))
        for a_, b_ in (((v, -h_), (v, h_)), ((-h_, v), (h_, v))):
            seg = 10
            for s in range(seg):
                p0 = np.array([a_[0] + (b_[0] - a_[0]) * s / seg, 0, a_[1] + (b_[1] - a_[1]) * s / seg])
                p1 = np.array([a_[0] + (b_[0] - a_[0]) * (s + 1) / seg, 0, a_[1] + (b_[1] - a_[1]) * (s + 1) / seg])
                x0, y0, z0 = cam.proj(p0)
                x1, y1, z1 = cam.proj(p1)
                if z0 < 0.3 or z1 < 0.3:
                    continue
                rr = np.linalg.norm((p0 + p1) / 2) / Rg
                al = int(alpha * 170 * max(0.0, 1 - rr ** 3))
                d.line((x0 / 2, y0 / 2, x1 / 2, y1 / 2), fill=(185, 195, 215, al), width=1)
    return lay


def box_text(img, s, y, size, n_letters, col=(255, 255, 255)):
    """nom en lettres « boîtes » (comme la référence) : texte épais blanc + cadre, lettres qui apparaissent une à une"""
    if n_letters <= 0:
        return
    f = ImageFont.truetype(ANTON, size)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    full = f.getlength(s) + size * 0.16 * (len(s) - 1)
    x = W / 2 - full / 2
    for ch in s[:n_letters]:
        w = f.getlength(ch)
        d.rectangle((x - 6, y - size * 0.62, x + w + 6, y + size * 0.62), outline=col + (255,), width=6)
        d.text((x + w / 2, y), ch, font=f, fill=col + (255,), anchor="mm")
        x += w + size * 0.16
    g = lay.filter(ImageFilter.GaussianBlur(10))
    img.alpha_composite(g)
    img.alpha_composite(lay)


def sub_text(img, s, y, size, a, col):
    if a <= 0:
        return
    f = ImageFont.truetype(ANTON, size)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(lay).text((W / 2, y), s, font=f, fill=col + (int(255 * a),), anchor="mm")
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(8)))
    img.alpha_composite(lay)


# ------------------------------------------------------------------------------------------- montage
def render(out, music=LIB / "_music/Delirious.mp3", m_start=40.0):
    n = len(CAST)
    bt, per = beats(music, m_start, 12)
    step = 2 if per < 0.45 else 1
    INTRO = 1.4                                                 # arrivée de loin, en tournant
    whips = [b for b in bt if b > INTRO + 0.3][::step][:n]      # un passage par perso (le dernier = le héros)
    land = whips[-1]
    end = land + 2.4
    sprites = [neon_sprite(next(NEON.glob(f"{f}.*")), c) for f, _, _, c in CAST]
    STEP = 2 * math.pi / n
    pos = [(R_CIRC * math.sin(i * STEP), -R_CIRC * math.cos(i * STEP)) for i in range(n)]
    # ordre de passage : on finit sur le héros
    order = [(HERO + 1 + k) % n for k in range(n)]
    MOVE = 0.55

    def theta(t):
        th = order[0] * STEP - 4.2 * (1 - ease_out(t / INTRO, 3))   # tour rapide à l'arrivée
        th += 0.16 * t                                          # dérive continue : jamais figé
        for k, w in enumerate(whips[1:], 1):
            d_ = ((order[k] - order[k - 1]) % n) * STEP
            th += d_ * ease_io((t - w + MOVE * 0.5) / MOVE)
        return th

    def cam_at(t):
        e = ease_out(t / INTRO, 3)
        D = 16.0 + (4.6 - 16.0) * e
        hgt = 9.0 + (1.25 - 9.0) * e
        for w in whips[1:]:                                     # petit recul pendant chaque passage
            D += 0.6 * math.sin(math.pi * min(1.0, max(0.0, (t - w + MOVE * 0.5) / MOVE)))
        D -= 0.12 * max(0.0, t - INTRO)
        if t > land:                                            # plan final : on s'approche du héros
            q = ease_out((t - land) / 1.2, 3)
            D -= 1.6 * q
            hgt += 0.35 * q
        th = theta(t)
        # on vise un peu le perso actif (pas le centre exact)
        return Cam(th, D, hgt, look_y=1.0)

    tmp = Path(tempfile.mkdtemp())
    cache = {}
    events = [("rise", 0.0)] + [("whoosh", w - MOVE * 0.5) for w in whips[1:]] + [("hit", land)]
    prev = None
    for fi in range(int(end * FPS)):
        t = fi / FPS
        cam = cam_at(t)
        img = Image.new("RGBA", (W, H), (4, 4, 8, 255))
        draw_stars(img, cam, prev)
        grid = draw_grid(cam, min(1.0, t / 0.8)).resize((W, H), Image.BILINEAR)
        img.alpha_composite(grid.filter(ImageFilter.GaussianBlur(5)))
        img.alpha_composite(grid)
        # perso actif = le plus en face de la caméra
        items = []
        for i, (px, pz) in enumerate(pos):
            fx, fy, z = cam.proj((px, 0, pz))
            _, hy, _ = cam.proj((px, CH_M, pz))
            if z < 0.6:
                continue
            items.append((z, i, fx, fy, fy - hy))
        front = min(items, key=lambda it: abs(it[2] - W / 2) + it[0] * 40)[1] if items else -1
        for z, i, fx, fy, hpx in sorted(items, reverse=True):
            spr, pad = sprites[i]
            hh = max(8, int(hpx / 4) * 4)
            act = i == front
            key = (i, hh, act)
            if key not in cache:
                k = hh / (spr.height - 2 * pad)
                s_ = spr.resize((max(1, int(spr.width * k)), max(1, int(spr.height * k))), Image.BILINEAR)
                if not act:                                     # les autres : plus sombres
                    a = np.asarray(s_, np.float32)
                    a[..., :3] *= 0.55
                    s_ = Image.fromarray(np.uint8(a), "RGBA")
                else:                                           # le perso devant : lueur en plus
                    gl = s_.filter(ImageFilter.GaussianBlur(max(2, hh * 0.02)))
                    base = Image.new("RGBA", s_.size, (0, 0, 0, 0))
                    base.alpha_composite(gl)
                    base.alpha_composite(s_)
                    s_ = base
                cache[key] = (s_, k)
            s_, k = cache[key]
            img.alpha_composite(s_, (int(fx - s_.width / 2), int(fy - s_.height + pad * k)))
        a = np.asarray(img.convert("RGB"), np.float32) / 255
        dth = abs(theta(t + 0.5 / FPS) - theta(t - 0.5 / FPS)) * FPS
        sp = min(1.0, max(0.0, (dth - 2.0) / 9))
        if sp > 0.03:
            a = hblur(a, 70 * sp)
        if abs(t - land) < 0.25:                                # flash léger à l'arrivée sur le héros
            a = a + (1 - a) * 0.35 * (1 - abs(t - land) / 0.25)
        img = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
        if t > land:
            _, name, sub, col = CAST[HERO]
            box_text(img, name, H * 0.2, 120, int((t - land) / 0.07) + 1)
            sub_text(img, sub, H * 0.2 + 115, 60, min(1.0, (t - land - 0.35) / 0.3), col)
        img.convert("RGB").save(tmp / f"{fi:05d}.jpg", quality=92)
        prev = cam

    # --- audio
    sr = 44100
    tot = int(end * sr) + sr
    mixb = np.zeros(tot, np.float32)

    def pcm(path, ss=0.0, dur=None, gain=1.0):
        cmd = ["ffmpeg", "-v", "error", "-ss", str(ss)] + (["-t", str(dur)] if dur else []) + \
              ["-i", str(path), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"]
        return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32) * gain

    def put(t, s_):
        a_ = int(max(0.0, t) * sr)
        s_ = s_[:max(0, tot - a_)]
        mixb[a_:a_ + len(s_)] += s_

    put(0, pcm(music, m_start, end + 1, 0.55))
    rng = np.random.default_rng(1)
    Lw = int(0.5 * sr)
    env = np.exp(-np.linspace(0, 6, Lw)) * (1 - np.exp(-np.linspace(0, 60, Lw)))
    wh = np.convolve(rng.standard_normal(Lw).astype(np.float32), np.ones(14) / 14, "same") * env * 0.45
    for kind, t in events:
        if kind == "whoosh":
            put(t, wh)
        elif kind == "rise":
            Lr = int(INTRO * sr)
            put(0, np.convolve(rng.standard_normal(Lr).astype(np.float32), np.ones(30) / 30, "same")
                * np.linspace(0, 0.5, Lr) ** 2)
        else:
            put(t, pcm(SFX / "impact_punch_heavy_000.ogg", gain=0.35))
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
    if len(sys.argv) > 2 and sys.argv[1] == "--sprites":
        tiles = [neon_sprite(next(NEON.glob(f"{f}.*")), c, 700)[0] for f, _, _, c in CAST]
        sheet = Image.new("RGB", (sum(t.width for t in tiles), max(t.height for t in tiles)), (4, 4, 8))
        x = 0
        for t_ in tiles:
            sheet.paste(t_, (x, 0), t_)
            x += t_.width
        sheet.save(sys.argv[2])
    else:
        render(sys.argv[1])
