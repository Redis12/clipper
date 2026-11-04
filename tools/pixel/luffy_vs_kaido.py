"""Domain War #6 — Luffy vs Kaido, version « vrais sprites pixel-art » (scénario de l'utilisateur, 04/11).

Luffy (base) se bat avec ses bras élastiques, Kaido (dragon) le domine et le met K.O. (Boro Breath) ;
silence, tambours de la libération, cinématique Gear 5 (clips de l'utilisateur), Luffy Gear 5 revient,
Zoro perdu passe sous l'arène puis vient trancher Kaido, et Bajrang Gun → FINISH.
Le terrain (cases) = la part de chaque camp, il bouge à chaque coup.

python tools/pixel/luffy_vs_kaido.py <sortie.mp4>
Sprites : library/_domain/fx/_luffy_sheet/ (base + gear5_sheet.png) et _kaido_sheet/ (dragon).
"""
from __future__ import annotations

import json
import math
import random
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from clipper.slides import render, vfxgen, mugen  # noqa: E402

LIB = ROOT / "library"
LS = LIB / "_domain/fx/_luffy_sheet"
KS = LIB / "_domain/fx/_kaido_sheet"
SFX = LIB / "_sfx/One Piece/One Piece SFX"
MCH = LIB / "One Piece/one-piece-mugen/One Piece MUGEN/chars"
W, H, FPS = 1080, 1920, 30
TITLE = "DOMAIN WAR #6"

# ------------------------------------------------------------------ sprites

def key_green(a: np.ndarray, tol=(10, 12, 45)) -> np.ndarray:
    r, g, b = a[..., 0].astype(int), a[..., 1].astype(int), a[..., 2].astype(int)
    return (abs(r - 17) < tol[0]) & (abs(g - 136) < tol[1]) & (b < tol[2])


def scale(im: Image.Image, s: float) -> Image.Image:
    return im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.NEAREST)


def trim(im: Image.Image) -> Image.Image:
    bb = im.getchannel("A").getbbox()
    return im.crop(bb) if bb else im


# Luffy base (planche Jump Ultimate Stars, fond violet)
def _base_frames():
    im = np.array(Image.open(LS / "sheet.png").convert("RGB")).astype(int)
    bg = (abs(im[..., 0] - 128) < 12) & (abs(im[..., 1] - 128) < 12) & (abs(im[..., 2] - 255) < 12)
    rgba = Image.fromarray(np.dstack([im, (~bg) * 255]).astype(np.uint8))
    boxes = json.loads((LS / "arms/base_boxes.json").read_text())
    return {k: rgba.crop((x0, y0, x1, y1)) for k, (y0, y1, x0, x1) in boxes.items()}


def _g5_frames():
    im = np.array(Image.open(LS / "gear5_sheet.png").convert("RGB"))
    bg = key_green(im)
    rgba = Image.fromarray(np.dstack([im, (~bg) * 255]).astype(np.uint8))
    boxes = json.loads((LS / "gear5_boxes.json").read_text())
    out = {}
    for k, (y0, y1, x0, x1) in boxes.items():
        out[k] = trim(rgba.crop((x0, y0, x1, y1)))
    return out


def _clean_kaido(p: Path, s: float) -> Image.Image:
    a = np.array(Image.open(p).convert("RGBA")).astype(int)
    r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    al[((g > r + 25) & (g > b + 25)) & (g > 120)] = 0
    a[..., 1] = np.minimum(g, np.maximum(r, b) + 10)
    a[..., 3] = ndimage.binary_erosion(al > 0, iterations=1) * 255
    return scale(Image.fromarray(a.astype(np.uint8)), s)


def load_sprites():
    B = _base_frames()
    G = _g5_frames()
    S = {}
    S["l_idle"] = [scale(B[str(k)], 4) for k in (0, 1, 2, 3)]
    S["l_punch"], S["l_gat"], S["l_charge"], S["l_dead"] = (scale(B[str(k)], 4) for k in (79, 89, 94, 30))
    S["l_run"] = [scale(B[str(k)], 4) for k in (4, 5, 6, 7, 8, 9, 10, 11)]
    S["l_jump"] = [scale(B[str(k)], 4) for k in (17, 18, 19, 20)]
    S["l_hurt"] = [scale(B[str(k)], 4) for k in (25, 26, 27)]
    S["l_fly"] = [scale(B[str(k)], 4) for k in (28, 29)]
    S["g_walk"] = [scale(G[f"w{k}"], 2.4) for k in range(10, 18)]
    S["g_jump"] = [scale(G[f"j{k}"], 2.4) for k in range(20, 26)]
    S["g_run"] = [scale(G[f"r{k}"], 2.4) for k in (26, 27, 28, 29)]
    S["g_hurt"] = [scale(G[f"h{k}"], 2.4) for k in (228, 229, 231)]
    S["g_idle"] = [scale(G[k], 2.4) for k in ("idle1", "idle2", "idle3", "idle4", "idle5", "idle6")]
    S["g_punch"] = [scale(G[k], 2.4) for k in ("p79", "p80", "p87")]
    S["g_giant"] = scale(G["g157"], 2.4)
    S["g_head"] = [scale(G[k], 1.6) for k in ("h194", "h196")]
    S["g_bajrang"] = [scale(G[k], 1.5) for k in ("b219", "b220")]
    S["g_rayo"] = [scale(G[k], 2.4) for k in ("r47", "r48", "r49")]
    gif = Image.open(KS / "dragon_idle.gif")
    S["k_idle"] = []
    tmp = Path("/tmp") / "kaido_idle"
    tmp.mkdir(exist_ok=True)
    for i in range(gif.n_frames):
        gif.seek(i)
        gif.convert("RGBA").save(tmp / f"{i}.png")
        S["k_idle"].append(ImageOps.mirror(_clean_kaido(tmp / f"{i}.png", 2.5)))
    fr = KS / "frames"
    S["k_breath"] = [ImageOps.mirror(_clean_kaido(fr / f"f{k:02d}.png", 2.5)) for k in range(4, 15)]
    S["k_fly"] = [_clean_kaido(fr / f"f{k:02d}.png", 2.5) for k in range(15, 27)]
    S["k_bolt"] = [_clean_kaido(fr / f"f{k:02d}.png", 3) for k in range(30, 37)]
    arm = Image.open(LS / "arms/1476.png")
    S["fist"] = scale(arm.crop((arm.width - 16, 0, arm.width, arm.height)), 5)
    S["seg"] = arm.crop((20, 0, 50, arm.height))
    giant = scale(Image.open(LS / "arms/1573.png"), 8)
    S["kkg"] = haki(giant)
    zoro = Image.open(LIB / "_fusion/Luffy/7 Zoro.jpeg").convert("RGB")
    S["zoro"] = zoro
    S["slash"] = [trim(Image.open(p).convert("RGBA")) for p in sorted((LIB / "_domain/_effets_jaunes").glob("slash_*.png"))]
    S["mL"] = mugen.Char(MCH / "G6_Luffy", "Luffy")
    S["mZ"] = mugen.Char(MCH / "G6_Zoro", "Zoro")
    return S


def haki(im: Image.Image) -> Image.Image:
    r, g, b, a = im.convert("RGBA").split()
    lum = Image.merge("RGB", (r, g, b)).convert("L")
    return Image.merge("RGBA", (lum.point(lambda v: int(v * 0.30 + 30)), lum.point(lambda v: int(v * 0.10)),
                                lum.point(lambda v: int(v * 0.22 + 14)), a))


# ------------------------------------------------------------------ scène

LX, LY = 300, 1030          # Luffy (pieds)
KX, KY = 790, 960           # Kaido (centre)
GX0, GY0, CELL, NX, NY = 43, 260, 38, 26, 33
RED, PURPLE = (214, 52, 52), (122, 70, 200)


def tile(c, flash=0.0):
    t = Image.new("RGBA", (CELL, CELL), (0, 0, 0, 0))
    d = ImageDraw.Draw(t)
    c2 = tuple(min(255, int(v + (255 - v) * flash)) for v in c)
    d.rectangle((1, 1, CELL - 2, CELL - 2), fill=c2)
    d.line((1, 1, CELL - 2, 1), fill=tuple(min(255, v + 45) for v in c2))
    d.line((1, CELL - 2, CELL - 2, CELL - 2), fill=tuple(int(v * 0.7) for v in c2))
    return t


TILES = {RED: tile(RED), PURPLE: tile(PURPLE)}


def paste_c(img, im, x, y, alpha=1.0):
    if im is None:
        return
    if alpha < 1:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda v: int(v * max(0.0, alpha))))
    img.alpha_composite(im, (int(x - im.width / 2), int(y - im.height / 2)))


def paste_foot(img, im, x, y):
    img.alpha_composite(im, (int(x - im.width / 2), int(y - im.height)))


class Fight:
    def __init__(self, S):
        self.S = S
        self.fnt = render.font(62)
        self.big = render.font(150)
        self.mid = render.font(84)
        self.sm = render.font(44)
        self.expl = vfxgen.frames("explosion", 300, (255, 190, 90))
        self.hit = vfxgen.frames("hit", 180, (255, 240, 200))
        self.ring = vfxgen.frames("ring", 400, (255, 255, 255))
        self.bolt_red = vfxgen.frames("lightning", 320, (255, 30, 30), hot=0.4)
        self.rows_noise = [random.Random(j).uniform(-1.2, 1.2) for j in range(NY)]
        self.keys = []          # (t, share Luffy)
        self.sounds = []        # (t, fichier, volume)
        self.events = []
        self.cine = []

    # part de Luffy dans le terrain, interpolée
    def share(self, t):
        k = self.keys
        if t <= k[0][0]:
            return k[0][1]
        for (t0, a), (t1, b) in zip(k, k[1:]):
            if t0 <= t <= t1:
                q = (t - t0) / max(1e-6, t1 - t0)
                q = q * q * (3 - 2 * q)
                return a + (b - a) * q
        return k[-1][1]

    def grid(self, img, t, dark=0.0):
        s = self.share(t)
        for j in range(NY):
            front = s * NX + self.rows_noise[j] * (1 - abs(s - 0.5) * 1.6)
            for i in range(NX):
                c = RED if i + 0.5 < front else PURPLE
                img.alpha_composite(TILES[c], (GX0 + i * CELL, GY0 + j * CELL))
        if dark:
            img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * dark))))
        # barre de part en bas
        y = GY0 + NY * CELL + 40
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((GX0, y, W - GX0, y + 46), 20, fill=PURPLE)
        d.rounded_rectangle((GX0, y, GX0 + (W - 2 * GX0) * s, y + 46), 20, fill=RED)
        d.text((GX0 + 18, y + 23), f"{round(s * 100)}%", font=self.sm, anchor="lm", fill=(255, 255, 255),
               stroke_width=4, stroke_fill=(0, 0, 0))
        d.text((W - GX0 - 18, y + 23), f"{round((1 - s) * 100)}%", font=self.sm, anchor="rm", fill=(255, 255, 255),
               stroke_width=4, stroke_fill=(0, 0, 0))
        d.text((GX0, y + 70), "LUFFY", font=self.sm, anchor="lm", fill=(255, 140, 140), stroke_width=4,
               stroke_fill=(0, 0, 0))
        d.text((W - GX0, y + 70), "KAIDO", font=self.sm, anchor="rm", fill=(200, 170, 255), stroke_width=4,
               stroke_fill=(0, 0, 0))

    def header(self, img):
        d = ImageDraw.Draw(img)
        d.text((W / 2, 95), TITLE, font=self.mid, anchor="mm", fill=(255, 255, 255), stroke_width=6,
               stroke_fill=(0, 0, 0))
        d.text((W / 2 - 60, 175), "LUFFY", font=self.sm, anchor="rm", fill=(255, 120, 120), stroke_width=4,
               stroke_fill=(0, 0, 0))
        d.text((W / 2, 175), " VS ", font=self.sm, anchor="mm", fill=(255, 255, 255), stroke_width=4,
               stroke_fill=(0, 0, 0))
        d.text((W / 2 + 60, 175), "KAIDO", font=self.sm, anchor="lm", fill=(190, 160, 255), stroke_width=4,
               stroke_fill=(0, 0, 0))

    def label(self, img, who, move, col, big=False, age=0.0):
        d = ImageDraw.Draw(img)
        if big:
            pop = 1 + 0.4 * max(0.0, 1 - age / 0.2)
            f = render.font(int(110 * pop))
            d.text((W / 2, 880), move, font=f, anchor="mm", fill=(255, 225, 90), stroke_width=9, stroke_fill=(0, 0, 0))
            d.text((W / 2, 780), who, font=self.fnt, anchor="mm", fill=col, stroke_width=6, stroke_fill=(0, 0, 0))
        else:
            d.text((W / 2, 300), f"{who} · {move}", font=self.sm, anchor="mm", fill=col, stroke_width=5,
                   stroke_fill=(0, 0, 0))

    # bras élastique
    def arm(self, img, x1, y1, x2, y2, t, thick=1.0, wob=1.0):
        L = math.hypot(x2 - x1, y2 - y1)
        S = self.S
        if L < 20:
            return
        fist = scale(S["fist"], thick)
        h = int(S["seg"].height * 5 * thick)
        body = S["seg"].resize((max(4, int(L - fist.width * 0.6)), h), Image.NEAREST)
        strip = Image.new("RGBA", (body.width + fist.width, max(h, fist.height) + 40), (0, 0, 0, 0))
        yy = (strip.height - h) // 2
        for cx in range(0, body.width, 4):
            off = int(math.sin(cx / 38.0 + t * 30) * 8 * wob * (1 - cx / body.width))
            strip.alpha_composite(body.crop((cx, 0, min(body.width, cx + 4), h)), (cx, yy + off))
        strip.alpha_composite(fist, (body.width, (strip.height - fist.height) // 2))
        rs = strip.rotate(-math.degrees(math.atan2(y2 - y1, x2 - x1)), expand=True, resample=Image.NEAREST)
        img.alpha_composite(rs, (int((x1 + x2) / 2 - rs.width / 2), int((y1 + y2) / 2 - rs.height / 2)))


def ease_punch(a, out=0.16, hold=0.10, back=0.18):
    if a < 0 or a > out + hold + back:
        return None
    if a < out:
        return 1 - (1 - a / out) ** 3, False
    if a < out + hold:
        return 1.0, True
    return 1 - ((a - out - hold) / back) ** 2, False


# ------------------------------------------------------------------ scénario

def build(F: Fight):
    """Clés de la part du terrain + sons ; renvoie la durée totale."""
    K = F.keys
    snd = F.sounds
    K += [(0.0, 0.5), (1.6, 0.5)]
    # Phase 1 : Luffy base
    K += [(2.3, 0.55), (3.6, 0.45), (5.4, 0.53), (6.9, 0.42), (9.4, 0.42), (9.9, 0.53), (11.2, 0.40), (12.6, 0.30)]
    K += [(13.4, 0.30), (14.6, 0.08), (25.0, 0.08)]
    # Phase 2 : Gear 5 (après la cinématique, 25.0 → 31.0)
    K += [(32.0, 0.08), (33.4, 0.22), (35.4, 0.32), (36.8, 0.27), (38.6, 0.44), (40.2, 0.40), (42.0, 0.58),
          (43.2, 0.55), (45.0, 1.0), (47.5, 1.0)]
    s = lambda t, n, v=1.0: snd.append((t, n, v))
    s(0.15, "Whoosh hit.mp3"); s(0.35, "big punch.mp3", 0.7)
    s(1.9, "luffys arm stretch.mp3"); s(2.08, "fist.mp3")                       # Jet Pistol
    s(3.0, "explosion with debris.mp3", 0.8)                                   # Boro Breath 1
    s(4.6, "consecutive attacks.mp3")                                          # Jet Gatling
    s(6.3, "explosion.mp3", 0.8)                                               # Thunder Bagua
    s(7.2, "Armament Haki (Busoshoku Haki ) v1.mp3"); s(9.45, "big punch.mp3"); s(9.55, "Big explosion.mp3", 0.8)
    s(10.3, "Terror.mp3", 0.6)                                                   # Kaido vole
    s(11.9, "explosion with debris.mp3"); s(13.4, "explosion with debris.mp3")  # Boro Breath final
    s(14.2, "at death's door.mp3")
    s(16.3, "Gear 5 drums.mp3", 1.1)                                           # tambours (8,5 s)
    s(24.6, "conqueror's haki (Haoshoku Haki) v2.mp3", 0.8)
    s(31.2, "gomu gomu no rocket!.mp3"); s(32.5, "big punch.mp3")              # Gear 5 : coup élastique
    s(34.0, "explosion with debris.mp3", 0.7)                                  # Kaido : foudre
    s(34.9, "WTF sound v3 (most popular).mp3", 0.8)                            # Gear 5 : attrape la foudre
    s(36.3, "Zoro's run gait.mp3", 0.8)                                        # Zoro perdu
    s(38.2, "big sword cutting.mp3")                                           # Zoro : Asura
    s(39.6, "explosion with debris.mp3", 0.7)
    s(41.2, "big punch.mp3"); s(41.6, "Big explosion.mp3", 0.6)               # poings géants
    s(43.0, "conqueror's Haki (Haoshoku Haki) v1.mp3", 0.6)
    s(44.3, "big punch.mp3"); s(44.6, "Big explosion.mp3"); s(45.2, "explosion with debris.mp3")  # Bajrang Gun
    L = F.S["mL"]
    tmp = Path("/tmp/mugen_snd")
    tmp.mkdir(exist_ok=True)
    def ms(t, g, n, v=1.0):
        w = L.sounds.get((g, n))
        if w:
            f = tmp / f"L_{g}_{n}.wav"
            f.write_bytes(w)
            snd.append((t, str(f), v))
    ms(7.2, 4, 18); ms(7.2 + 35 / 60, 4, 4, 0.8); ms(7.2 + 40 / 60, 4, 17); ms(7.2 + 90 / 60, 4, 16)   # Gear 4
    ms(8.87, 4, 21); ms(8.87 + 30 / 60, 4, 4, 0.8); ms(8.87 + 70 / 60, 4, 19)                           # King Kong Gun
    return 49.0



# ------------------------------------------------------------------ mouvements et coups encaissés

def lerp(a, b, q):
    return a + (b - a) * q


def smooth(q):
    q = max(0.0, min(1.0, q))
    return q * q * (3 - 2 * q)


# Luffy : (t0, t1, x0, x1, mode) — mode = run / jump / back / still
L_MOVES = [(1.6, 1.9, 300, 430, "run"), (2.4, 2.7, 430, 400, "still"), (4.0, 4.5, 400, 480, "run"),
           (5.9, 6.2, 480, 360, "back"), (10.3, 11.0, 360, 470, "jump"), (11.0, 11.7, 470, 330, "jump"),
           (13.5, 13.95, 330, 230, "fly"),
           (31.6, 32.0, 260, 330, "run"), (33.0, 33.6, 330, 420, "jump"), (36.0, 36.4, 420, 330, "jump"),
           (39.4, 40.2, 330, 380, "run"), (42.2, 42.9, 380, 300, "jump")]
# coups reçus : (t, force)
HITS_K = [(2.06, 1.0)] + [(4.62 + i * 0.08, 0.35) for i in range(16)] + [(9.5, 2.2), (31.7, 1.8), (35.3, 1.6),
                                                                        (38.4, 2.0), (40.8, 1.4), (41.3, 1.6), (44.3, 3.0)]
HITS_L = [(3.1, 1.0), (6.4, 1.0), (12.3, 1.3), (13.5, 1.8), (34.2, 0.8)]
DMG_K = {2.06: "-5%", 9.5: "-9%", 31.7: "-14%", 35.3: "-10%", 38.4: "-12%", 40.8: "-8%", 41.3: "-10%", 44.3: "-45%"}
DMG_L = {3.1: "-10%", 6.4: "-11%", 12.3: "-8%", 13.5: "-22%"}


def luffy_pos(t):
    """x du perso + mode de déplacement en cours."""
    x, mode, q = 300, None, 0.0
    for t0, t1, x0, x1, m in L_MOVES:
        if t >= t1:
            x = x1
        elif t >= t0:
            q = (t - t0) / (t1 - t0)
            x, mode = lerp(x0, x1, smooth(q)), m
            break
        else:
            break
    if t >= 25.0 and t < 31.6:
        x = 260
    if 13.95 <= t < 31.6:
        x = 230 if t < 25.0 else 260
    return x, mode, q


def recent(hits, t, win=0.45):
    best = None
    for th, f in hits:
        if 0 <= t - th < win:
            best = (t - th, f)
    return best


def render_frame(F: Fight, t: float, cine_frames) -> Image.Image:
    global LX, KX
    S = F.S
    img = Image.new("RGBA", (W, H), (12, 10, 22, 255))
    energy = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shake = 0
    rr = random.Random(int(t * 1000))

    # ---------- accroche (0 → 1,6 s) : les 2 persos + VS + WHO WINS?
    if t < 1.6:
        d = ImageDraw.Draw(img)
        d.polygon(((0, 0), (W * 0.62, 0), (W * 0.38, H), (0, H)), fill=(120, 24, 24))
        d.polygon(((W * 0.62, 0), (W, 0), (W, H), (W * 0.38, H)), fill=(54, 28, 96))
        for i in range(40):
            y = rr.uniform(0, H)
            d.line((0, y, W, y - 300), fill=(255, 255, 255, 40), width=3)
        a = min(1.0, t / 0.3)
        paste_foot(img, scale(S["l_idle"][int(t * 8) % 4], 1.25), 300 - (1 - a) * 300, 1150)
        paste_c(img, scale(S["k_idle"][int(t * 8) % 4], 1.15), 760 + (1 - a) * 300, 900)
        d = ImageDraw.Draw(img)
        d.text((W / 2, 300), "WHO WINS?", font=F.big, anchor="mm", fill=(255, 255, 255), stroke_width=10,
               stroke_fill=(0, 0, 0))
        d.text((W / 2, 980), "VS", font=render.font(200), anchor="mm", fill=(255, 215, 40), stroke_width=12,
               stroke_fill=(0, 0, 0))
        d.text((300, 1230), "LUFFY", font=F.mid, anchor="mm", fill=(255, 140, 140), stroke_width=7, stroke_fill=(0, 0, 0))
        d.text((780, 1230), "KAIDO", font=F.mid, anchor="mm", fill=(200, 170, 255), stroke_width=7, stroke_fill=(0, 0, 0))
        d.text((W / 2, 140), TITLE, font=F.mid, anchor="mm", fill=(255, 255, 255), stroke_width=6, stroke_fill=(0, 0, 0))
        render.draw_rich(img, (W / 2, 1420), "Comment your pick 👇", render.font(62), (255, 255, 255), anchor="ma",
                         stroke_width=5, stroke_fill=(0, 0, 0))
        render.like_follow(img, W / 2, 1540, min(1.0, t / 0.4))
        if t < 0.12:
            shake = 14
        return finish(img, energy, shake, t)

    # ---------- cinématique Gear 5 (25,0 → 31,0)
    if 25.0 <= t < 31.0:
        img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        fr = cine_frames[min(len(cine_frames) - 1, int((t - 25.0) * 24))]
        band = fr.resize((W, int(fr.height * W / fr.width)), Image.LANCZOS)
        img.alpha_composite(band, (0, int(H * 0.42 - band.height / 2)))
        d = ImageDraw.Draw(img)
        d.text((W / 2, H * 0.42 + band.height / 2 + 120), "GEAR 5", font=render.font(160), anchor="mm",
               fill=(255, 255, 255), stroke_width=10, stroke_fill=(0, 0, 0))
        d.text((W / 2, H * 0.42 - band.height / 2 - 90), "THE DRUMS OF LIBERATION", font=F.fnt, anchor="mm",
               fill=(255, 230, 150), stroke_width=6, stroke_fill=(0, 0, 0))
        if t < 25.15 or 30.85 < t:
            img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, 220)))
        return finish(img, energy, 0, t)

    # ---------- arène
    LX, mode, mq = luffy_pos(t)
    hk = recent(HITS_K, t)
    KX = 790 + (45 * hk[1] * math.exp(-hk[0] * 7) * (1 - math.exp(-hk[0] * 40)) if hk else 0) + math.sin(t * 0.9) * 25
    dark = 0.0
    if 14.6 <= t < 25.0:
        dark = min(0.78, (t - 14.6) / 1.2 * 0.78)
    F.grid(img, t, dark)
    F.header(img)
    gear5 = t >= 31.0
    lpose, lx_off = None, 0
    kpose, kx, ky = S["k_idle"][int(t * 8) % len(S["k_idle"])], KX, KY + math.sin(t * 3) * 22
    hide_luffy = False
    mact = None
    lab = None

    if t < 14.6:                                                     # ---- phase 1 (Luffy MUGEN)
        if 1.9 <= t < 2.4:                                           # Jet Pistol
            mact = (491, t - 1.9, False)
            if 2.02 < t < 2.2:
                paste_c(energy, F.hit[int((t - 2.0) * 30) % 10], KX - 150, KY - 30)
                shake = 12
            lab = ("LUFFY", "JET PISTOL", (255, 150, 150))
        if 2.7 <= t < 4.0:                                           # Boro Breath 1
            a = t - 2.7
            kpose = S["k_breath"][min(4, int(a / 0.4 * 5))] if a < 0.4 else S["k_breath"][5 + int(a * 12) % 4]
            if 0.4 < a:
                paste_c(energy, F.expl[int(a * 24) % 10], LX, LY - 110, 0.8)
                shake = 8
            lab = ("KAIDO", "BORO BREATH", (200, 170, 255))
        if 4.5 <= t < 5.9:                                           # Jet Gatling
            a = t - 4.5
            mact = (400, a, False) if a < 0.5 else ((402, a - 0.5, True) if a < 1.15 else (401, a - 1.15, False))
            if 0.1 < a < 1.3 and int(a * 25) % 2 == 0:
                r2 = random.Random(int(a * 25))
                paste_c(energy, F.hit[int(a * 30) % 10].resize((120, 120)), KX - 170 + r2.uniform(-30, 30), KY - 30 + r2.uniform(-90, 90))
                shake = 6
            lab = ("LUFFY", "JET GATLING", (255, 150, 150))
        if 6.1 <= t < 7.2:                                           # Thunder Bagua
            a = t - 6.1
            for k in range(3):
                bx = LX - 120 + k * 120 + random.Random(int(a * 6) + k).uniform(-30, 30)
                b_ = S["k_bolt"][(int(a * 14) + k) % len(S["k_bolt"])]
                paste_c(energy, b_, bx, 300 + b_.height / 2)
                paste_c(energy, F.expl[int(a * 24 + k * 3) % 10].resize((170, 170)), bx, 300 + b_.height)
            shake = 10
            lab = ("KAIDO", "THUNDER BAGUA", (200, 170, 255))
        if 7.2 <= t < 8.87:                                          # Gear 4
            mact = (3201, t - 7.2, False)
            lab = ("LUFFY", "GEAR 4 · BOUNDMAN", (255, 150, 150))
            if int(t * 20) % 3 == 0:
                paste_c(energy, F.bolt_red[int(t * 24) % 10].resize((300, 300)), LX, LY - 200, 0.6)
        if 8.87 <= t < 10.3:                                         # King Kong Gun
            mact = (3202, t - 8.87, False)
            lab = ("LUFFY", "KING KONG GUN", (255, 150, 150))
            if t >= 9.5:
                b = t - 9.5
                paste_c(energy, F.expl[min(9, int(b * 18))].resize((640, 640)), KX - 40, KY)
                paste_c(energy, F.bolt_red[int(b * 24) % 10].resize((520, 520)), KX - 40, KY, max(0, 1 - b))
                shake = int(30 * max(0, 1 - b / 0.7))
        if 10.3 <= t < 11.7:                                         # Kaido s'envole
            a = t - 10.3
            kpose = S["k_fly"][int(a * 10) % len(S["k_fly"])]
            ox, oy = 540 + math.cos(a * 1.8 + 1.0) * 270, 980 + math.sin(a * 2.2) * 330
            w_in = smooth(a / 0.45) * smooth((11.7 - t) / 0.45)
            kx, ky = lerp(KX, ox, w_in), lerp(KY, oy, w_in)
            lab = ("KAIDO", "DRAGON TWISTER", (200, 170, 255))
        if 11.7 <= t < 13.9:                                         # Boro Breath final
            a = t - 11.7
            kpose = S["k_breath"][min(4, int(a / 0.5 * 5))] if a < 0.5 else S["k_breath"][5 + int(a * 12) % 4]
            if a > 0.5:
                paste_c(energy, F.expl[int(a * 24) % 10].resize((420, 420)), LX, LY - 110, 0.9)
                shake = 14
            lab = ("KAIDO", "BORO BREATH", (200, 170, 255))
        if 13.9 <= t and t < 14.3:
            paste_c(energy, F.expl[min(9, int((t - 13.9) * 24))].resize((600, 600)), LX, LY - 60)
            shake = 20
    elif t < 25.0:                                                   # ---- Luffy à terre, tambours
        mact = (5110, 0, False)
        d = ImageDraw.Draw(img)
        if t < 16.3:
            d.text((W / 2, 760), "LUFFY IS DOWN...", font=F.mid, anchor="mm", fill=(255, 255, 255), stroke_width=7,
                   stroke_fill=(0, 0, 0))
        else:
            a = t - 16.3
            beat = (a % 1.08) / 1.08                                  # battement des tambours
            R = 120 + 220 * beat
            ring = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(ring).ellipse((LX - R, LY - 40 - R, LX + R, LY - 40 + R), outline=(255, 255, 255, int(220 * (1 - beat))), width=10)
            energy.alpha_composite(ring)
            if a > 3.5:
                d.text((W / 2, 760), "DON DON DON...", font=F.mid, anchor="mm", fill=(255, 240, 200), stroke_width=7,
                       stroke_fill=(0, 0, 0))
            if a > 6.5 and int(t * 10) % 2 == 0:
                img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, 90)))
    else:                                                            # ---- phase 3 : Gear 5
        lpose = None
        if t < 31.6:
            paste_c(energy, F.ring[min(9, int((t - 31.0) * 18))].resize((700, 700)), LX, LY - 120)
            F.label(img, "LUFFY", "GEAR 5", (255, 255, 255), big=True, age=t - 31.0)
        # coup élastique Gear 5 (31,2 → 33,0)
        if 31.2 <= t < 33.0:
            a = t - 31.2
            lpose = S["g_punch"][min(2, int(a / 0.25))] if a < 1.3 else S["g_idle"][0]
            if 0.5 < a < 1.3:
                paste_c(energy, F.hit[int(a * 30) % 10].resize((260, 260)), KX - 150, KY)
                shake = 12
            lab = ("LUFFY", "GOMU GOMU NO DAWN WHIP", (255, 255, 255))
        # Kaido foudre → Luffy l'attrape (33,8 → 36,0)
        if 33.8 <= t < 36.0:
            a = t - 33.8
            if a < 1.0:
                for k in range(2):
                    b_ = S["k_bolt"][(int(a * 14) + k) % 7]
                    paste_c(energy, b_, LX - 40 + k * 90, 300 + b_.height / 2)
                lab = ("KAIDO", "THUNDER BAGUA", (200, 170, 255))
            else:
                lpose = S["g_rayo"][min(2, int((a - 1.0) * 4))]
                lab = ("LUFFY", "GRABS THE LIGHTNING!", (255, 255, 255))
        # Zoro perdu (36,2 → 38,0) : il marche sous l'arène dans le mauvais sens, puis Sanzen Sekai (38,0 → 39,4)
        if 36.2 <= t < 39.4:
            a = t - 36.2
            Z = S["mZ"]
            if a < 1.8:
                x = W + 60 - a * 380
                yb = GY0 + NY * CELL + 330
                Z.draw(img, 20, a, x, yb, scale=1.5, facing=-1, loop=True)
                render.draw_rich(img, (x - 60, yb - 330), "Where am I? 🗺️", render.font(46), (255, 255, 255),
                                 anchor="ma", stroke_width=4, stroke_fill=(0, 0, 0))
            else:
                b = a - 1.8
                act, tb = (3200, b) if b < 0.57 else (3201, b - 0.57)
                Z.draw(img, act, tb, KX - 230, LY, scale=1.7, facing=1, loop=False)
                if b > 0.35:
                    for k, sp in enumerate(S["slash"][:3]):
                        paste_c(energy, scale(sp, 0.9), KX - 40 + k * 30, KY - 40 + k * 40, max(0, 1 - (b - 0.35) * 0.9))
                    shake = 12
                lab = ("ZORO", "SANTORYU · SANZEN SEKAI", (130, 230, 130))
        # poings géants (40,4 → 42,2)
        if 40.4 <= t < 42.2:
            a = t - 40.4
            g = S["g_giant"]
            rev = int(g.width * (0.25 + 0.75 * smooth(a / 0.35)))
            img.alpha_composite(g.crop((0, 0, rev, g.height)), (int(LX - 70), int(LY - g.height + 10)))
            hide_luffy = True
            if a > 0.4:
                paste_c(energy, F.expl[int(a * 24) % 10].resize((380, 380)), KX - 60, KY)
                shake = 10
            lab = ("LUFFY", "GOMU GOMU NO GIANT", (255, 255, 255))
        # Bajrang Gun (43,0 → 47,0) : coup de grâce
        if 43.0 <= t:
            a = t - 43.0
            F.label(img, "LUFFY", "BAJRANG GUN", (255, 255, 255), big=a < 1.4, age=a)
            fr = S["g_bajrang"][int(t * 8) % 2]
            hide_luffy = a < 2.2
            if a < 1.3:
                rev = int(fr.width * (0.18 + 0.82 * smooth(a / 1.2)))
                img.alpha_composite(fr.crop((0, 0, rev, fr.height)), (int(LX - 110), int(KY - fr.height / 2 - 20)))
                shake = int(6 + 10 * a)
            elif a < 3.0:
                b = a - 1.3
                f2 = fr.copy()
                f2.putalpha(f2.getchannel("A").point(lambda v: int(v * max(0, 1 - b * 1.2))))
                img.alpha_composite(f2, (int(LX - 110), int(KY - fr.height / 2 - 20)))
                paste_c(energy, F.expl[min(9, int(b * 14))].resize((900, 900)), KX, KY)
                paste_c(energy, F.bolt_red[int(b * 24) % 10].resize((700, 700)), KX, KY, max(0, 1 - b))
                shake = int(36 * max(0, 1 - b / 1.0))
                kpose = None if b > 0.6 else kpose
            if a >= 3.0:
                kpose = None
            if a > 1.6:
                pop = 1 + 0.4 * max(0.0, 1 - (a - 1.6) / 0.2)
                ImageDraw.Draw(img).text((W / 2, 1100), "FINISH!", font=render.font(int(190 * pop)), anchor="mm",
                                         fill=(255, 225, 60), stroke_width=12, stroke_fill=(0, 0, 0))
            if a > 4.5:                                             # écran WINNER
                return winner(F, img, t)

    # dessin des persos : Kaido encaisse (flash blanc, recul, il se tord), Luffy bouge en permanence
    if kpose is not None:
        if hk and t < 44.0:                                            # il se tord sous le coup (inclinaison)
            ang = 9 * hk[1] * math.exp(-hk[0] * 6) * math.sin(hk[0] * 25)
            kpose = kpose.rotate(ang, expand=True, resample=Image.NEAREST)
        if hk and hk[0] < 0.09:
            kpose = whiten(kpose)
        paste_c(img, kpose, kx, ky + (12 * math.sin(hk[0] * 40) * (1 - hk[0] / 0.45) if hk else 0))
    hl = recent(HITS_L, t, 0.5)
    if not gear5 and not hide_luffy and lpose is None:                # Luffy MUGEN (vraies animations du jeu)
        if mact is None:
            if 13.95 <= t:
                mact = (5110, 0, False)
            elif hl and hl[0] < 0.45:
                mact = (5002, hl[0], False)
            elif mode == "run":
                mact = (100, t, True)
            elif mode == "back":
                mact = (105, t, True)
            elif mode == "jump":
                mact = (50, mq * 0.67, False)
            elif mode == "fly":
                mact = (5050, mq * 0.3, False)
            else:
                mact = (0, t, True)
        kx_ = -int(40 * hl[1] * (1 - hl[0] / 0.5)) if hl else 0
        tint = (255, 255, 255) if hl and hl[0] < 0.08 else None
        S["mL"].draw(img, mact[0], mact[1], LX + kx_, LY, scale=1.7, facing=1, loop=mact[2], tint=tint)
        lpose = "mugen"
    elif lpose is None and not hide_luffy:
        if hl and hl[0] < 0.5:
            lpose = S["g_hurt"][min(2, int(hl[0] * 6))]
        elif mode == "run":
            lpose = S["g_run"][int(t * 16) % 4]
        elif mode == "jump":
            lpose = S["g_jump"][min(5, int(mq * 6))]
        else:
            lpose = S["g_idle"][int(t * 8) % 6]
    if lpose is not None and lpose != "mugen" and not hide_luffy:
        jy = -math.sin(mq * math.pi) * 160 if mode == "jump" else 0
        kx_ = -int(40 * hl[1] * (1 - hl[0] / 0.5)) if hl else 0
        if hl and hl[0] < 0.09:
            lpose = whiten(lpose)
        paste_foot(img, lpose, LX + kx_, LY + jy + (60 if lpose is S["l_dead"] else 0))
    for th, txt in list(DMG_K.items()) + list(DMG_L.items()):
        a_ = t - th
        if 0 <= a_ < 0.9:
            onK = th in DMG_K
            x_, y_ = (KX - 40, KY - 230) if onK else (LX, LY - 330)
            ImageDraw.Draw(img).text((x_, y_ - a_ * 120), txt, font=render.font(int(70 * (1 + 0.3 * max(0, 1 - a_ / 0.15)))),
                                     anchor="mm", fill=(255, 70, 70) if onK else (190, 150, 255), stroke_width=6,
                                     stroke_fill=(0, 0, 0))
    if lab and not (t >= 43.0):
        F.label(img, *lab)
    return finish(img, energy, shake, t)


def winner(F, img, t):
    S = F.S
    img = Image.new("RGBA", (W, H), (60, 12, 12, 255))
    d = ImageDraw.Draw(img)
    for i in range(24):
        an = i / 24 * 2 * math.pi + t
        d.polygon(((W / 2, 900), (W / 2 + math.cos(an) * 1400, 900 + math.sin(an) * 1400),
                   (W / 2 + math.cos(an + 0.12) * 1400, 900 + math.sin(an + 0.12) * 1400)), fill=(110, 24, 24))
    paste_foot(img, scale(S["g_idle"][int(t * 8) % 6], 1.5), W / 2, 1150)
    d.text((W / 2, 420), "WINNER", font=render.font(170), anchor="mm", fill=(255, 225, 60), stroke_width=10,
           stroke_fill=(0, 0, 0))
    d.text((W / 2, 1260), "LUFFY", font=render.font(120), anchor="mm", fill=(255, 255, 255), stroke_width=8,
           stroke_fill=(0, 0, 0))
    render.draw_rich(img, (W / 2, 1420), "Who should fight next? Comment 👇", render.font(46), (255, 255, 255),
                     anchor="ma", stroke_width=5, stroke_fill=(0, 0, 0))
    return img.convert("RGB")


def whiten(im):
    w = Image.new("RGBA", im.size, (255, 255, 255, 255))
    w.putalpha(im.getchannel("A"))
    return Image.blend(im, w, 0.75)


def finish(img, energy, shake, t):
    img.alpha_composite(energy.filter(ImageFilter.GaussianBlur(14)))
    img.alpha_composite(energy)
    if shake:
        rs = random.Random(int(t * 1000))
        img = img.transform(img.size, Image.AFFINE, (1, 0, rs.uniform(-shake, shake), 0, 1, rs.uniform(-shake, shake)))
    return img.convert("RGB")


def cine_frames():
    """Clips Gear 5 de l'utilisateur : transformation 2 puis attaque (filigrane du bas rogné)."""
    out = []
    for name in ("Gear 5 transformation 2.webp", "Gear 5 attaque.webp"):
        im = Image.open(LIB / "_domain/ulti_src/Luffy" / name)
        for i in range(im.n_frames):
            im.seek(i)
            fr = im.convert("RGBA")
            out.append(fr.crop((0, 0, fr.width, int(fr.height * 0.9))))
    # 6 s à 24 i/s = 144 images : on étire un peu si besoin
    if len(out) < 144:
        out = [out[int(i * len(out) / 144)] for i in range(144)]
    return out


def main(out: Path):
    S = load_sprites()
    F = Fight(S)
    dur = build(F)
    cf = cine_frames()
    vid = out.with_suffix(".noaudio.mp4")
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
                          "-pix_fmt", "yuv420p", str(vid)], stdin=subprocess.PIPE)
    for f in range(int(dur * FPS)):
        p.stdin.write(render_frame(F, f / FPS, cf).tobytes())
    p.stdin.close()
    p.wait()
    # son : bruitages One Piece + tambours
    args = ["ffmpeg", "-v", "error", "-y", "-i", str(vid)]
    filt = []
    n = 0
    for t, name, v in F.sounds:
        path = Path(name) if name.startswith("/") else SFX / name
        if not path.is_file():
            path = LIB / "_sounds/domain" / name
        if not path.is_file():
            continue
        args += ["-i", str(path)]
        n += 1
        lim = 9 if "drums" in name else 3
        filt.append(f"[{n}:a]atrim=0:{lim},volume={v},adelay={int(t * 1000)}|{int(t * 1000)}[a{n}]")
    filt.append("".join(f"[a{i}]" for i in range(1, n + 1)) +
                f"amix=inputs={n}:normalize=0,atrim=0:{dur},loudnorm=I=-20:TP=-3[o]")
    args += ["-filter_complex", ";".join(filt), "-map", "0:v", "-map", "[o]", "-c:v", "copy", "-c:a", "aac",
             "-b:a", "160k", str(out)]
    subprocess.run(args, check=True)
    vid.unlink(missing_ok=True)
    try:
        render.stamp_video(out)
    except Exception as e:
        print("filigrane ignoré :", e)
    print(out, dur)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
