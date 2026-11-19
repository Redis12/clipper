"""« If you had Gojo's Infinity » v3 (19/11) : DA vectorielle plate « un peu stickman ».
Gojo / Sukuna = PNG détourés générés par l'utilisateur (ChatGPT Images, planche découpée dans
library/_explainer/gojo_infinity/flat/) animés à peine (respiration, léger balancement, entrée en pop) ;
tout le reste est dessiné (flat_assets : YOU, poing, Zénon, atome, horloge, pièce ; ici : orbes, lance, entailles…).
Aplats, pas de lueur ni de dégradé. Texte 3 mots en haut, compteur jaune à droite (hors des places du filigrane),
voix Kokoro am_adam, fin qui reboucle sur la 1re image, filigrane render.stamp_video.
python3 tools/explainer/flat_style.py tools/explainer/scripts/gojo_infinity_v3.json sortie.mp4 [--preview t1,t2,…]
"""
from __future__ import annotations

import json
import math
import random
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(Path(__file__).parent))
import flat_assets as fa  # noqa: E402

W, H, FPS = 1080, 1920, 30
FONTS = ROOT / "tools/money_sim/fonts"
HY = ROOT / "library/_sfx/Helton Yan's Old-School Shonen SFX"
INK, WHITE, YEL, CYAN, RED, PURP = fa.INK, fa.WHITE, fa.YEL, fa.CYAN, fa.RED, fa.PURP
BG, BG2 = fa.BG, fa.BG2
STAGE_Y = 930


@lru_cache(maxsize=None)
def F(name, sz):
    return ImageFont.truetype(str(FONTS / f"{name}.woff2"), int(sz))


def ease(k):
    k = min(1, max(0, k))
    return k * k * (3 - 2 * k)


def back(k):
    k = min(1, max(0, k))
    return 1 + 2.70158 * (k - 1) ** 3 + 1.70158 * (k - 1) ** 2


def make_bg(col=BG, grid=BG2):
    im = Image.new("RGB", (W, H), col)
    d = ImageDraw.Draw(im)
    for gx in range(0, W + 1, 90):
        d.line((gx, 0, gx, H), fill=grid, width=2)
    for gy in range(0, H + 1, 90):
        d.line((0, gy, W, gy), fill=grid, width=2)
    return im


class Assets:
    def __init__(self, base):
        self.base = base
        self.c = {}

    def get(self, key, fn):
        if key not in self.c:
            self.c[key] = fn()
        return self.c[key]

    def png(self, name):
        return self.get(("png", name), lambda: Image.open(self.base / f"{name}.png").convert("RGBA"))

    def scaled(self, name, h, flip=False):
        def f():
            im = self.png(name)
            s = h / im.height
            im = im.resize((int(im.width * s), int(h)), Image.LANCZOS)
            return im.transpose(Image.FLIP_LEFT_RIGHT) if flip else im
        return self.get(("sc", name, int(h), flip), f)

    def drawn(self, key, fn, s=1.0):
        def f():
            im = fn()
            return im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS) if s != 1 else im
        return self.get(("dr", key, s), f)


def paste(im, img, cx, cy, anchor="mm"):
    x = cx - img.width / 2
    y = cy - img.height / 2 if anchor == "mm" else cy - img.height
    im.paste(img, (int(round(x)), int(round(y))), img)          # toile RGB : paste avec masque = vrai mélange


def char(im, A, name, cx, bottom, h, t, k_in=1.0, flip=False, sway=1.0):
    """Perso PNG posé sur `bottom`, entrée en pop, respiration (étirement vertical) et léger balancement."""
    base = A.scaled(name, h, flip)
    s = 0.82 + 0.18 * back(k_in)
    br = 1 + 0.010 * math.sin(2 * math.pi * t / 3.1)
    img = base
    if abs(s - 1) > 1e-3 or abs(br - 1) > 1e-4:
        img = base.resize((max(1, int(base.width * s)), max(1, int(base.height * s * br))), Image.BILINEAR)
    ang = sway * 0.8 * math.sin(t * 0.9)
    if abs(ang) > 0.05:
        img = img.rotate(ang, resample=Image.BICUBIC, expand=True, center=(img.width / 2, img.height))
    a = min(1.0, k_in * 3)
    if a < 1:
        img = img.copy()
        img.putalpha(img.getchannel("A").point(lambda v: int(v * a)))
    paste(im, img, cx, bottom + 30 * (1 - ease(k_in)), "bottom")


def rings(d, cx, cy, t, col=CYAN, n=5, r0=150, gap=42, alpha=55, broken=0.0):
    """Anneaux plats : aplats translucides + trait net qui ondule à peine. broken>0 = les anneaux éclatent."""
    for k in range(n - 1, -1, -1):
        r = r0 + gap * k + 5 * math.sin(t * 2.2 + k * 0.9)
        if broken > 0:
            r += broken * (120 + 60 * k)
        a = int(max(0, (alpha + 18 * (n - 1 - k)) * (1 - broken)))
        la = int(255 * (1 - broken))
        if la <= 0:
            continue
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col + (a,))
        if broken > 0:
            for j in range(6):                          # morceaux d'anneau
                a0 = j * 60 + k * 17
                d.arc((cx - r, cy - r, cx + r, cy + r), a0, a0 + 38, fill=col + (la,), width=5)
        else:
            d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=col + (la,), width=5)


def card(d, label, value, col=YEL, y=1385, right=1010):
    """Compteur plat : carte bleu foncé, contour encre, valeur en Anton. Calé à droite (filigrane à gauche/centre-bas)."""
    f1, f2 = F("mont800", 26), F("anton", 84)
    tw = max(d.textlength(value, font=f2), d.textlength(label, font=f1)) + 64
    x0 = right - tw
    d.rounded_rectangle((x0 + 8, y - 72, right + 8, y + 78), radius=20, fill=(10, 14, 30, 255))      # ombre plate
    d.rounded_rectangle((x0, y - 80, right, y + 70), radius=20, fill=(16, 24, 52, 255), outline=INK, width=6)
    d.text((x0 + 32, y - 46), label, font=f1, fill=(160, 180, 220), anchor="lm")
    d.text((x0 + 32, y + 16), value, font=f2, fill=col, anchor="lm")


def orb(d, cx, cy, r, col, t):
    d.ellipse((cx - r * 1.35, cy - r * 1.35, cx + r * 1.35, cy + r * 1.35), fill=col + (60,))
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col + (255,), outline=INK, width=6)
    d.ellipse((cx - r * 0.55, cy - r * 0.55, cx + r * 0.55, cy + r * 0.55), fill=(255, 255, 255, 230))
    for k in range(3):                                   # éclats qui tournent
        a = t * 3 + k * 2.09
        x, y = cx + r * 0.78 * math.cos(a), cy + r * 0.78 * math.sin(a)
        d.ellipse((x - r * 0.12, y - r * 0.12, x + r * 0.12, y + r * 0.12), fill=(255, 255, 255, 255))


def spear(d, x, y, ang, L=760):
    """Lance plate originale : manche + lame à 3 pointes (dessin générique)."""
    ca, sa = math.cos(ang), math.sin(ang)

    def P(u, v):
        return (x + u * ca - v * sa, y + u * sa + v * ca)
    d.line([P(-L, 0), P(0, 0)], fill=INK, width=22)
    d.line([P(-L, 0), P(0, 0)], fill=(120, 90, 60), width=12)
    for v, l in ((0, 130), (-34, 80), (34, 80)):
        pts = [P(0, v - 12), P(l, v), P(0, v + 12)]
        d.polygon(pts, fill=(220, 225, 235), outline=INK)
        d.line(pts + [pts[0]], fill=INK, width=5)
    guard = [P(-12, -40), P(12, -40), P(12, 40), P(-12, 40)]       # garde rouge
    d.polygon(guard, fill=(170, 40, 50))
    d.line(guard + [guard[0]], fill=INK, width=5)


def brain(d, cx, cy, heat, t):
    col = (255, int(170 - 110 * heat), int(190 - 150 * heat))
    d.ellipse((cx - 230, cy - 160, cx + 230, cy + 150), fill=col, outline=INK, width=7)
    d.line((cx, cy - 150, cx, cy + 140), fill=INK, width=6)
    for k in range(4):
        d.arc((cx - 200 + 100 * k, cy - 110, cx - 90 + 100 * k, cy + 10), 200, 340, fill=INK, width=6)
        d.arc((cx - 190 + 100 * k, cy - 10, cx - 80 + 100 * k, cy + 110), 20, 160, fill=INK, width=6)
    for k in range(6):                                   # fumée plate
        tt = (t * 0.7 + k / 6) % 1
        x, y = cx - 200 + 80 * k + 20 * math.sin(tt * 6 + k), cy - 170 - 240 * tt
        r = 26 + 46 * tt
        a = int(230 * (1 - tt) * heat)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(210, 210, 225, a), outline=INK + (a,), width=4)


class Show:
    def __init__(self, script):
        self.s = script
        self.A = Assets(ROOT / script["dir"])
        self.bg = make_bg()
        self.void_bg = self._void()
        rnd = random.Random(7)
        self.parts = [(rnd.uniform(0, 2 * math.pi), rnd.uniform(0, 1), rnd.uniform(6, 14)) for _ in range(34)]

    def _void(self):
        im = Image.new("RGB", (W, H), (8, 8, 20))
        d = ImageDraw.Draw(im)
        rnd = random.Random(3)
        for _ in range(260):
            x, y, r = rnd.uniform(0, W), rnd.uniform(0, H), rnd.choice((2, 2, 3, 4, 6))
            d.ellipse((x - r, y - r, x + r, y + r), fill=(235, 235, 255))
        return im

    # ------------------------------------------------------------------ scènes
    def scene(self, im, kind, q, t, tl, line_i):
        A = self.A
        d = ImageDraw.Draw(im, "RGBA")
        cx = W / 2
        if kind == "punch":
            yx, yfeet = 650, 1300
            rings(d, yx, 980, t, n=5, r0=170)
            yu = A.drawn(("you", "smug" if q < 0.8 else "calm"), lambda: fa.you("smug" if q < 0.8 else "calm"), 0.95)
            paste(im, yu, yx, yfeet, "bottom")
            gap = 110 * math.exp(-3.2 * q) + 14             # poing entier visible dès l'image 0
            fs = A.drawn("fist", fa.fist, 0.95)
            edge = yx - 172 - 5 * 42 + 40                # bord de l'anneau extérieur
            paste(im, fs, edge - gap - fs.width / 2 + 40, 980 + 6 * math.sin(t * 9))
            v = 0.002 * math.exp(-5 * q) * (0.5 ** (tl * 4))
            card(d, "DISTANCE LEFT", f"{v:.9f} in")
        elif kind == "palm":
            char(im, A, "gojo_main", 400, H + 10, 1250, t, tl / 0.35)
            px_, py_ = 185, 1190                         # paume de gojo_main
            rings(d, px_, py_, t, n=4, r0=90, gap=38, alpha=40)
            gap = 240 * math.exp(-3 * q) + 10
            fs = A.drawn("fist_l", lambda: fa.fist().transpose(Image.FLIP_LEFT_RIGHT), 0.85)
            paste(im, fs, px_ + 90 + 3 * 38 + gap + fs.width / 2 - 30, py_ + 5 * math.sin(t * 9))
            card(d, "SPACE BETWEEN", "ENDLESS", CYAN)
        elif kind in ("zeno", "zeno_talk"):
            z = A.drawn(("zeno", "point"), lambda: fa.zeno("point"), 0.82)
            if kind == "zeno_talk" and int(t * 2.3) % 7 == 0:
                z = A.drawn(("zeno", "point_b"), lambda: fa.zeno("point", blink=True), 0.82)
            paste(im, z, 230, 1330, "bottom")
            x0, x1, y = 400, 1000, 860
            d.line((x0, y, x1, y), fill=WHITE, width=6)
            d.rectangle((x1 - 6, y - 90, x1, y), fill=WHITE)
            d.polygon([(x1, y - 90), (x1 - 70, y - 70), (x1, y - 50)], fill=YEL, outline=INK)
            n = int(1 + q * 7) if kind == "zeno" else 8
            pos, labels = 0.0, []
            for i in range(n):
                pos += (1 - pos) / 2
                labels.append(pos)
            px = x0
            for i, p in enumerate(labels):
                xx = x0 + (x1 - x0) * p
                d.line((xx, y - 22, xx, y + 22), fill=YEL, width=5)
                if i < 4:
                    d.text((xx, y + 60), f"1/{2 ** (i + 1)}", font=F("anton", 46 - i * 6), fill=YEL, anchor="mm")
                px = xx
            # la balle saute de repère en repère
            prev = x0 + (x1 - x0) * (labels[-2] if len(labels) > 1 else 0)
            jt = (q * 7) % 1 if kind == "zeno" else 1
            bx = prev + (px - prev) * ease(jt * 1.4)
            by = y - 40 - 90 * math.sin(math.pi * min(1, jt * 1.4))
            d.ellipse((bx - 26, by - 26, bx + 26, by + 26), fill=RED, outline=INK, width=6)
            if kind == "zeno_talk":
                d.rounded_rectangle((380, 470, 1010, 640), radius=40, fill=WHITE, outline=INK, width=6)
                d.polygon([(470, 636), (420, 720), (540, 636)], fill=WHITE)
                d.line([(470, 638), (420, 720), (540, 638)], fill=INK, width=6)
                d.text((695, 555), "~450 BC", font=F("anton", 88), fill=INK, anchor="mm")
                card(d, "IDEA AGE", "2,400+ YRS")
            else:
                card(d, "STEPS", f"{n}")
        elif kind == "series":
            terms = ["1/2", "1/4", "1/8", "1/16", "1/32", "..."]
            n = int(1 + q * 7)
            x = 90
            for i, tm in enumerate(terms[:n]):
                f = F("anton", 100 - i * 10)
                d.text((x, 760), tm, font=f, fill=WHITE, anchor="lm", stroke_width=5, stroke_fill=INK)
                x += d.textlength(tm, font=f) + 14
                if i < n - 1 and i < len(terms) - 1:
                    d.text((x, 760), "+", font=F("anton", 70), fill=CYAN, anchor="lm")
                    x += 46
            tot = sum(0.5 ** (i + 1) for i in range(min(n, 30)))
            bw = 880
            d.rounded_rectangle((100, 900, 100 + bw, 990), radius=22, fill=(16, 24, 52), outline=INK, width=6)
            d.rounded_rectangle((110, 910, 110 + (bw - 20) * tot, 980), radius=16, fill=YEL)
            d.line((100 + bw - 8, 870, 100 + bw - 8, 1020), fill=RED, width=8)
            d.text((100 + bw - 8, 1060), "1", font=F("anton", 60), fill=RED, anchor="mm")
            z = A.drawn(("zeno", "idle"), lambda: fa.zeno("idle"), 0.55)
            paste(im, z, 200, 1520, "bottom")
            card(d, "TOTAL", f"{tot:.4f}...")
        elif kind == "slow":
            yx = 820
            rings(d, yx, 980, t, n=5, r0=110, gap=34)
            yu = A.drawn(("you", "calm", 0.6), lambda: fa.you("calm"), 0.62)
            paste(im, yu, yx, 1210, "bottom")
            speeds = [182, 91, 45, 22, 11, 5.6, 2.8, 1.4, 0.7]
            k = min(len(speeds) - 1, int(q * len(speeds)))
            for j, (fn, key, yy, sc) in enumerate(((lambda: fa.coin("heads"), "coin", 720, 0.45),
                                                   (lambda: fa.atom(t=0), "atom", 980, 0.5),
                                                   (lambda: fa.coin("edge"), "coin_e", 1230, 0.45))):
                ob = A.drawn(key, fn, sc)
                x = 120 + 420 * (1 - 0.5 ** (q * 6 + j * 0.4))
                for s_ in range(4):                      # traits de vitesse qui raccourcissent
                    ln = 70 * (1 - q) + 10
                    d.line((x - ob.width / 2 - 20 - 36 * s_ - ln, yy, x - ob.width / 2 - 20 - 36 * s_, yy),
                           fill=(255, 255, 255, 170 - 35 * s_), width=6)
                paste(im, ob, x, yy)
            card(d, "SPEED", f"{speeds[k]:g} mph")
        elif kind == "clock":
            ck = fa.clock(10, int(tl * 40) % 60).resize((300, 300), Image.LANCZOS)
            paste(im, ck, 270, 760)
            rings(d, 720, 1080, t, n=4, r0=110, gap=34)
            yu = A.drawn(("you", "calm", 0.55), lambda: fa.you("calm"), 0.55)
            paste(im, yu, 720, 1290, "bottom")
            cn = A.drawn("coin", lambda: fa.coin("heads"), 0.4)
            paste(im, cn, 720 - 110 - 3 * 34 - 60, 1060 + 3 * math.sin(t * 2))
            card(d, "COIN SPEED", "0.0000001")
        elif kind == "brain":
            heat = min(1, q * 1.3)
            brain(d, cx, 700, heat, t)
            yu = A.drawn(("you", "shock", "up"), lambda: fa.you("shock", "arms_up"), 0.7)
            paste(im, yu, cx, 1420 + 8 * math.sin(t * 30) * heat, "bottom")
            card(d, "BRAIN LOAD", f"{int(100 + 9900 * heat):,}%", RED)
        elif kind == "eyes":
            z = 1.0 + 0.12 * ease(q)
            char(im, A, "gojo_yeux", cx + 40, H + 20, 1500 * z, t, tl / 0.3, sway=0.3)
            card(d, "PRECISION", "PERFECT", CYAN)
        elif kind in ("blue", "red"):
            char(im, A, "gojo_face", 330, H + 10, 1150, t, tl / 0.35)
            col = CYAN if kind == "blue" else RED
            ox, oy = 740, 760
            for a0, r0, sz in self.parts:
                a = a0 + t * 1.6
                if kind == "blue":
                    r = (1 - ((q * 1.8 + r0) % 1)) * 460 + 90
                else:
                    r = ((q * 1.8 + r0) % 1) * 520 + 110
                x, y = ox + r * math.cos(a), oy + r * math.sin(a)
                d.ellipse((x - sz, y - sz, x + sz, y + sz), fill=col + (255,), outline=INK, width=3)
            orb(d, ox, oy, 110 + 6 * math.sin(t * 7), col, t)
            card(d, "FORCE", "INWARD" if kind == "blue" else "OUTWARD", col)
        elif kind == "purple":
            char(im, A, "gojo_profil", 230, H + 10, 1100, t, tl / 0.35, flip=True)
            k = min(1.0, q / 0.4)
            ox, oy = 640, 820
            if k < 1:
                for sx, col in ((-1, CYAN), (1, RED)):
                    orb(d, ox + sx * 260 * (1 - ease(k)), oy, 80, col, t)
            else:
                g = ease(min(1.0, (q - 0.4) / 0.35))
                for j in range(5):                       # débris qui disparaissent quand le cercle les touche
                    bx, by = 420 + 130 * j, 380 + (j % 2) * 120
                    if math.hypot(bx - ox, by - oy) > 90 + 520 * g:
                        d.rounded_rectangle((bx - 40, by - 30, bx + 40, by + 30), radius=10, fill=(130, 120, 150), outline=INK, width=5)
                r = 90 + 520 * g
                d.ellipse((ox - r * 1.15, oy - r * 1.15, ox + r * 1.15, oy + r * 1.15), fill=PURP + (70,))
                d.ellipse((ox - r, oy - r, ox + r, oy + r), fill=PURP + (255,), outline=INK, width=7)
                d.ellipse((ox - r * 0.5, oy - r * 0.5, ox + r * 0.5, oy + r * 0.5), fill=(255, 255, 255, 235))
            card(d, "MASS", "IMAGINARY", PURP)
        elif kind == "void":
            im.paste(self.void_bg)
            rings(d, cx, 820, t * 0.6, col=(200, 200, 255), n=6, r0=160, gap=60, alpha=18)
            char(im, A, "gojo_face", cx, H + 10, 1100, t, tl / 0.35)
            yu = A.drawn(("you", "shock", "s"), lambda: fa.you("shock"), 0.42)
            paste(im, yu, 860, 780, "bottom")
            rnd = random.Random(int(t * 12))
            for _ in range(18):                          # « informations » qui pleuvent sur YOU
                x, y = 860 + rnd.uniform(-170, 170), 470 + rnd.uniform(0, 320)
                d.text((x, y), rnd.choice("01"), font=F("anton", 34),
                       fill=(255, 255, 255, 200), anchor="mm")
            card(d, "INFORMATION", "INFINITE", PURP)
        elif kind == "warning":
            k = ease(tl / 0.25)
            d.rectangle((0, 560, W, 560 + 120 * k), fill=RED + (255,))
            d.text((cx, 620), "BUT...", font=F("anton", 100), fill=WHITE, anchor="mm", stroke_width=6, stroke_fill=INK)
            char(im, A, "sukuna_visage", cx, H + 10, 1150, t, tl / 0.3, sway=0.4)
        elif kind == "spear":
            yx, yy = 700, 1000
            hit = 0.45
            br = 0.0 if q < hit else ease((q - hit) / 0.3)
            rings(d, yx, yy, t, n=5, r0=120, gap=36, broken=br)
            yu = A.drawn(("you", "shock", 0.7), lambda: fa.you("shock"), 0.7)
            paste(im, yu, yx, 1290, "bottom")
            tip = -200 + (yx - 80 + 200) * ease(min(1, q / hit))
            spear(d, tip, yy - 30, 0.0)
            if q >= hit and q < hit + 0.12:
                d.rectangle((0, 0, W, H), fill=(255, 255, 255, int(200 * (1 - (q - hit) / 0.12))))
            card(d, "INFINITY", "CANCELLED" if q >= hit else "ACTIVE", RED if q >= hit else CYAN)
        elif kind == "slash":
            rings(d, 260, 1000, t, n=4, r0=200, gap=44, alpha=30)
            char(im, A, "gojo_profil", 260, H + 10, 1000, t, 1.0, flip=True)
            char(im, A, "sukuna_main", 790, H + 10, 1050, t, tl / 0.3)
            for k in range(3):
                tk = (tl - 0.6) * 3 - k * 0.45
                if tk > 0:
                    p = min(1, tk * 2.2)
                    x0, y0, x1, y1 = -60 + 120 * k, 380 + 260 * k, 1140, 820 + 240 * k
                    xe, ye = x0 + (x1 - x0) * p, y0 + (y1 - y0) * p
                    d.line((x0, y0, xe, ye), fill=INK, width=26)
                    d.line((x0, y0, xe, ye), fill=RED, width=16)
                    d.line((x0, y0, xe, ye), fill=WHITE, width=5)
            card(d, "SPACE", "CUT", RED)

    def caption(self, im, words, t, top=330):
        cur = [i for i, (w, a, b) in enumerate(words) if a - 0.05 <= t]
        if not cur or t > words[-1][2] + 0.4:
            return
        i = cur[-1]
        g0 = (i // 3) * 3
        chunk = words[g0:g0 + 3]
        d = ImageDraw.Draw(im, "RGBA")
        f = F("mont900", 66)
        txt = " ".join(w for w, a, b in chunk)
        tw = d.textlength(txt, font=f)
        if tw > W - 80:
            f = F("mont900", int(66 * (W - 80) / tw))
            tw = d.textlength(txt, font=f)
        x = W / 2 - tw / 2
        for j, (w, a, b) in enumerate(chunk):
            on = t >= a - 0.05
            col = (YEL if g0 + j == i else WHITE) + ((255,) if on else (0,))
            if on:
                d.text((x, top), w, font=f, fill=col, anchor="lm", stroke_width=6, stroke_fill=INK)
            x += d.textlength(w + " ", font=f)

    def title(self, im, t):
        d = ImageDraw.Draw(im, "RGBA")
        a, b = self.s["title"]
        d.text((W / 2, 200), a, font=F("anton", 90), fill=WHITE, anchor="mm", stroke_width=7, stroke_fill=INK)
        d.text((W / 2, 310), b, font=F("anton", 118), fill=YEL, anchor="mm", stroke_width=8, stroke_fill=INK)


def timeline(lines):
    import tts
    from explainer import word_times
    vbuf, segs = tts.lines([l["text"] for l in lines], gap=0.25, start=0.1)
    words = [word_times(l["text"], a, b) for l, (a, b) in zip(lines, segs)]
    return vbuf, segs, words, segs[-1][1] + 0.6


def frame(sh, lines, segs, words, total, t, first=None):
    idx = max([i for i, (a, b) in enumerate(segs) if t >= a - 0.1] or [0])
    a, b = segs[idx]
    nxt = segs[idx + 1][0] if idx + 1 < len(segs) else total
    q = min(1.0, max(0.0, (t - a) / max(0.4, nxt - a)))
    im = sh.bg.copy()
    sh.scene(im, lines[idx]["scene"], q, t, t - a, idx)
    if idx == 0:
        sh.title(im, t)
        sh.caption(im, words[idx], t, top=470)
    else:
        sh.caption(im, words[idx], t)
    if t > total - 0.45 and first is not None:             # boucle : retour à la 1re image
        im = Image.blend(im, first, (t - (total - 0.45)) / 0.45)
    return im


def main(script_path, out, preview=None):
    import os
    out = Path(out).resolve()
    script_path = Path(script_path).resolve()
    os.chdir(ROOT)                                       # config.yaml (filigrane) est lu depuis le dossier du projet
    sys.path.insert(0, str(ROOT / "tools"))
    from clipper.slides import fusion, render
    script = json.loads(Path(script_path).read_text())
    lines = script["lines"]
    vbuf, segs, words, total = timeline(lines)
    sh = Show(script)
    out = Path(out)
    if preview:
        for t in preview:
            frame(sh, lines, segs, words, total, t).save(out.parent / f"{out.stem}_t{t:05.2f}.png")
        return [round(a, 2) for a, b in segs], total
    first = frame(sh, lines, segs, words, total, 0.0)
    tmp = out.with_suffix(".raw.mp4")
    ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                           "-pix_fmt", "yuv420p", str(tmp)], stdin=subprocess.PIPE)
    for fi in range(int(total * FPS)):
        ff.stdin.write(frame(sh, lines, segs, words, total, fi / FPS, first).convert("RGB").tobytes())
    ff.stdin.close()
    ff.wait()
    RATE = fusion.RATE
    buf = np.zeros(int(total * RATE) + RATE, np.float32)

    def add(s, t, g):
        i = int(t * RATE)
        n = min(len(s), len(buf) - i)
        if n > 0 and i >= 0:
            buf[i:i + n] += s[:n] * g
    whoosh = fusion.load_sound(HY / "FGHTClth_Anime Swing 2.ogg")
    boom = fusion.load_sound(HY / "EXPLDsgn_Anime Explosion 3.ogg")
    tt = np.arange(len(buf)) / RATE
    buf += (np.sin(2 * math.pi * 55 * tt) * 0.04 + np.sin(2 * math.pi * 82.5 * tt) * 0.025).astype(np.float32)
    for ln, (a, b) in zip(lines, segs):
        add(whoosh, max(0, a - 0.1), 0.18)
        if ln["scene"] == "purple":
            add(boom, a + 0.4 * (b - a + 0.25), 0.35)
        elif ln["scene"] == "spear":
            add(boom, a + 0.45 * (b - a + 0.25), 0.3)
        elif ln["scene"] == "slash":
            add(boom, a + 0.7, 0.3)
    n = min(len(buf), len(vbuf))
    buf[:n] += vbuf[:n]
    wav = out.with_suffix(".wav")
    fusion.write_wav(wav, np.tanh(buf * 0.9))
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(tmp), "-i", str(wav), "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", str(out)], check=True)
    tmp.unlink()
    wav.unlink()
    render.stamp_video(out)
    return out, total


if __name__ == "__main__":
    args = sys.argv[1:]
    pv = None
    if "--preview" in args:
        i = args.index("--preview")
        pv = [float(x) for x in args[i + 1].split(",")]
        args = args[:i] + args[i + 2:]
    print(main(args[0], args[1], pv))
