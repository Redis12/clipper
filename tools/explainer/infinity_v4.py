"""« If you had Gojo's Infinity » v4 (19/11), DA validée par l'utilisateur : bleu nuit + or, vue à la 1re personne.
Le poing fonce vers TOI (la caméra) et bute sur la barrière dorée ; Gojo / Sukuna = PNG ChatGPT de l'utilisateur
(library/_explainer/gojo_infinity/flat/) ; texte fin Poppins (mots entre *astérisques* = gras), compteur doré,
fin « Follow for more If you had... » sur le plan du poing : le bouton redevient le compteur → boucle parfaite.
Script volontairement différent de la vidéo de référence (pas de Zénon, angle « toi »).
python3 tools/explainer/infinity_v4.py <script.json> <sortie.mp4> [--preview]
"""
from __future__ import annotations

import json
import math
import os
import random
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(Path(__file__).parent))
import da_v4_mock as m  # noqa: E402

W, H, FPS = m.W, m.H, 30
GOLD, WHITE, SUB = m.GOLD, m.WHITE, m.SUB
CYAN, RED, PURP = (110, 200, 255), (255, 84, 84), (176, 110, 255)
HY = ROOT / "library/_sfx/Helton Yan's Old-School Shonen SFX"
FCX, FCY = 540, 1000                                     # centre du plan « poing »
GAP0, GAP_MIN = 330, 26                                  # écart poing-nez : image 0 (en plein vol) / après le choc
NOSE = (690, 1060)


def ease(k):
    k = min(1, max(0, k))
    return k * k * (3 - 2 * k)


def back(k):
    k = min(1, max(0, k))
    return 1 + 2.70158 * (k - 1) ** 3 + 1.70158 * (k - 1) ** 2


def tinted_bg(c0, c1, center=(0.5, 0.5), seed=1):
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((x - W * center[0]) / W) ** 2 + ((y - H * center[1]) / H * 0.75) ** 2) / 0.62
    px = np.array(c0, np.float32) + (np.array(c1, np.float32) - np.array(c0, np.float32)) * np.clip(r, 0, 1)[..., None] ** 0.9
    im = Image.fromarray(px.astype(np.uint8)).convert("RGBA")
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    rnd = random.Random(seed)
    for _ in range(90):
        sx, sy, s = rnd.uniform(0, W), rnd.uniform(0, H), rnd.choice((1.5, 2, 2, 3))
        d.ellipse((sx - s, sy - s, sx + s, sy + s), fill=(220, 220, 255, rnd.randint(40, 120)))
    im.alpha_composite(lay)
    return im


def vignette_layer():
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((x - W / 2) / W) ** 2 + ((y - H / 2) / H) ** 2) / 0.72
    a = (np.clip(r - 0.55, 0, 1) * 320).clip(0, 150).astype(np.uint8)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    lay.putalpha(Image.fromarray(a))
    return lay


def barrier(canvas, cx, cy, r, t, glow=1.0, col=GOLD, n=4):
    """Barrière dorée (anneaux en tirets qui tournent), flou calculé sur un carré autour seulement (rapide)."""
    R = int(r + n * 26 + 60)
    lay = Image.new("RGBA", (2 * R, 2 * R), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for i in range(n):
        rr = r + i * 26 + 6 * math.sin(t * 3 + i)
        a = int(min(255, (230 - 45 * i) * (0.75 + 0.25 * glow)))
        for j in range(5):
            a0 = j * 72 + t * 30 * (1 if i % 2 == 0 else -1) + i * 18
            d.arc((R - rr, R - rr, R + rr, R + rr), a0, a0 + 52, fill=col + (a,), width=max(2, 6 - i))
    g = lay.filter(ImageFilter.GaussianBlur(14))
    pos = (int(cx - R), int(cy - R))
    for _ in range(1 + int(glow > 1.3)):
        canvas.alpha_composite(g, pos)
    canvas.alpha_composite(g, pos)
    canvas.alpha_composite(lay, pos)


def parse(text):
    """« a *b c* d » → [(a, False), (b, True), (c, True), (d, False)] ; texte pour la voix sans astérisques."""
    out, bold = [], False
    for tok in re.findall(r"\*|[^\s*]+", text):
        if tok == "*":
            bold = not bold
        else:
            out.append((tok, bold))
    return out, text.replace("*", "")


def word_times(words, a, b):
    wts = [len(re.sub(r"\W", "", w)) + 2 for w, _ in words]
    tot = sum(wts)
    out, t = [], a
    for (w, bo), k in zip(words, wts):
        dd = (b - a) * k / tot
        out.append((w, bo, t, t + dd))
        t += dd
    return out


class Show:
    def __init__(self, script):
        self.s = script
        self.base = ROOT / script["dir"]
        self.bg = tinted_bg((26, 42, 86), (5, 8, 20), (0.5, 0.48))
        self.bg_gojo = tinted_bg((26, 42, 86), (5, 8, 20), (0.5, 0.62), seed=2)
        self.bg_red = tinted_bg((120, 18, 26), (20, 2, 6), (0.5, 0.55), seed=3)
        self.bg_void = tinted_bg((40, 24, 80), (4, 2, 12), (0.5, 0.45), seed=5)
        self.vig = vignette_layer()
        self.fist = m.fist_front(1000)
        self.cache = {}
        rnd = random.Random(9)
        self.drops = [(rnd.uniform(60, W - 60), rnd.uniform(0, 1), rnd.uniform(0.7, 1.3)) for _ in range(46)]
        self.parts = [(rnd.uniform(0, 2 * math.pi), rnd.uniform(0, 1), rnd.uniform(6, 13)) for _ in range(40)]
        self.atoms = [(rnd.uniform(80, W - 80), rnd.uniform(520, 1500), rnd.uniform(0, 6)) for _ in range(22)]

    boom_scenes: dict = {}
    scene_sounds: dict = {}                               # scène → [(décalage s, fichier, volume)]

    def loop_counter(self):
        """Compteur affiché à l'image 0 (la fin le remet à l'identique pour que la boucle ne se voie pas)."""
        return ("DISTANCE LEFT", f"{0.0000012:.9f} in", GOLD)

    def anchor(self, name, key, default):
        """Repères mesurés au détourage (library/.../anchors.json), ex. le bout du nez de gojo_profil."""
        if "_anchors" not in self.cache:
            f = self.base / "anchors.json"
            self.cache["_anchors"] = json.loads(f.read_text()) if f.exists() else {}
        return tuple(self.cache["_anchors"].get(name, {}).get(key, default))

    def png(self, name, h, flip=False):
        key = (name, int(h), flip)
        if key not in self.cache:
            im = Image.open(self.base / f"{name}.png").convert("RGBA")
            im = im.resize((int(im.width * h / im.height), int(h)), Image.LANCZOS)
            self.cache[key] = im.transpose(Image.FLIP_LEFT_RIGHT) if flip else im
        return self.cache[key]

    def char(self, im, name, cx, bottom, h, t, k_in, flip=False):
        base = self.png(name, h, flip)
        s = 0.86 + 0.14 * back(k_in)
        br = 1 + 0.009 * math.sin(2 * math.pi * t / 3.1)
        img = base.resize((max(1, int(base.width * s)), max(1, int(base.height * s * br))), Image.BILINEAR)
        a = min(1.0, k_in * 3)
        if a < 1:
            img.putalpha(img.getchannel("A").point(lambda v: int(v * a)))
        im.alpha_composite(img, (int(cx - img.width / 2), int(bottom - img.height + 40 * (1 - ease(k_in)))))

    def halo(self, im, cx, cy, r, col, a=90):
        R = int(r * 1.6)
        lay = Image.new("RGBA", (2 * R, 2 * R), (0, 0, 0, 0))
        ImageDraw.Draw(lay).ellipse((R - r, R - r, R + r, R + r), fill=col + (a,))
        im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(r * 0.35)), (int(cx - R), int(cy - R)))

    def punch_plate(self, im, gap, t, glow=1.0, shake=0.0):
        """Plan fil rouge : Gojo de profil (tourné vers la gauche), le poing arrive par la gauche et n'atteint
        jamais son visage ; entre les deux, des ondes dorées (l'Infini)."""
        gh = 1650
        g = self.png("gojo_profil", gh, flip=True)
        nose_x, nose_y = NOSE
        fx_, fy_ = self.anchor("gojo_profil", "nose", (0.97, 0.45))   # repère mesuré sur l'image (tournée vers la droite)
        gx = nose_x - (1 - fx_) * g.width                 # image retournée : le nez passe à gauche
        gy = nose_y - fy_ * gh
        br = 1 + 0.006 * math.sin(2 * math.pi * t / 3.1)
        im.alpha_composite(g, (int(gx), int(gy + (1 - br) * 200)))
        if "fist_side" not in self.cache:
            self.cache["fist_side"] = m.fist_side(720)
        f = self.cache["fist_side"]
        jx, jy = (3 + 14 * shake) * math.sin(t * 47), (3 + 10 * shake) * math.cos(t * 39)
        fx = nose_x - 30 - gap - f.width + 20 * (1 - 0.5)
        im.alpha_composite(f, (int(fx + jx), int(nose_y - f.height * 0.52 + jy)))
        self.waves(im, nose_x - 36 - gap * 0.45, nose_y, t, glow)
        for kk in range(7):                               # traits de vitesse derrière le poing
            yy = nose_y - 170 + kk * 55
            ln = 140 + 60 * math.sin(kk * 1.7)
            ImageDraw.Draw(im, "RGBA").line((fx - 40 - ln, yy, fx - 40, yy), fill=(170, 190, 240, 70), width=3)

    def waves(self, im, x, y, t, glow=1.0):
        """Ondes dorées verticales « ))) » entre le poing et le visage, flou sur une petite zone."""
        Wd, Hd = 360, 640
        lay = Image.new("RGBA", (Wd, Hd), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        for i in range(5):
            r = 210 + i * 22
            cxw = Wd / 2 - r + 40 + i * 18
            a = int(min(255, (235 - 38 * i) * (0.8 + 0.2 * glow) * (0.85 + 0.15 * math.sin(t * 8 + i))))
            d.arc((cxw - r, Hd / 2 - r, cxw + r, Hd / 2 + r), -38, 38, fill=GOLD + (a,), width=max(2, 6 - i))
        gl = lay.filter(ImageFilter.GaussianBlur(12))
        pos = (int(x - Wd / 2), int(y - Hd / 2))
        im.alpha_composite(gl, pos)
        im.alpha_composite(gl, pos)
        im.alpha_composite(lay, pos)

    # ------------------------------------------------------------------ scènes
    def scene(self, im, kind, q, t, tl, dur):
        d = ImageDraw.Draw(im, "RGBA")
        if kind == "punch":                             # le poing fonce, freine net sur les ondes, puis rampe
            gap = GAP_MIN + (GAP0 - GAP_MIN) * math.exp(-6.5 * tl)
            hit = math.exp(-((tl - 0.38) / 0.09) ** 2)   # le choc contre la barrière
            self.punch_plate(im, gap, t, 1.0 + 1.2 * hit + 0.4 * q, shake=hit)
            v = 0.0000012 * math.exp(-2.2 * tl)
            return ("DISTANCE LEFT", f"{v:.9f} in", GOLD)
        if kind == "end":                               # le poing recule jusqu'à la pose de l'image 0 (boucle)
            self.punch_plate(im, GAP_MIN + (GAP0 - GAP_MIN) * ease(q), t, 1.0)
            return None
        if kind == "slow":                              # il avance toujours… de moins en moins (zoom sur l'écart)
            gap = 6 + (GAP_MIN - 6) * 0.5 ** (tl * 2.2)
            self.punch_plate(im, gap, t, 1.5)
            sp = 120 * 0.5 ** (tl * 2.6)
            return ("FIST SPEED", f"{sp:.4f} mph" if sp < 1 else f"{sp:.1f} mph", GOLD)
        if kind == "rain":
            cx, cy, r = 540, 1150, 470                    # la pluie s'arrête sur la bulle autour de Gojo
            self.char(im, "gojo_face", 540, H + 60, 1250, t, 1.0)
            barrier(im, cx, cy, r - 60, t, 1.0, n=3)
            for x, ph, sp in self.drops:
                y = -80 + ((tl * 900 * sp + ph * 1900) % 2100)
                dy = abs(x - cx)
                stop = cy - math.sqrt(max(0, (r + 30) ** 2 - dy * dy)) if dy < r + 30 else None
                if stop is not None and y > stop - 40:  # la goutte ralentit puis reste suspendue
                    y = stop - 40 * math.exp(-(y - stop + 40) / 60)
                    ln = 10
                else:
                    ln = 46
                d.line((x, y - ln, x, y), fill=(170, 210, 255, 210), width=6)
                d.ellipse((x - 7, y - 7, x + 7, y + 9), fill=(200, 230, 255, 235))
            return ("DROPS ON HIM", "0", GOLD)
        if kind == "brain":
            heat = min(1, q * 1.2)
            for x, y, ph in self.atoms:                   # atomes qui tournent autour
                rr = 22
                for kk in range(2):
                    ang = t * 2 + ph + kk * 1.57
                    d.ellipse((x - rr * 1.9, y - rr * 0.7, x + rr * 1.9, y + rr * 0.7), outline=CYAN + (120,), width=3)
                    ex, ey = x + rr * 1.9 * math.cos(ang), y + rr * 0.7 * math.sin(ang)
                    d.ellipse((ex - 5, ey - 5, ex + 5, ey + 5), fill=GOLD + (230,))
                d.ellipse((x - 9, y - 9, x + 9, y + 9), fill=(255, 120, 120, 230))
            self.halo(im, 540, 1000, 300, (255, int(120 - 80 * heat), 80), int(60 + 80 * heat))
            br = self.cache.get("brain")
            if br is None:
                br = self.cache["brain"] = brain_img()
            s = 1 + 0.03 * math.sin(t * 20) * heat
            b2 = br.resize((int(br.width * s), int(br.height * s)), Image.BILINEAR)
            im.alpha_composite(b2, (int(540 - b2.width / 2), int(1000 - b2.height / 2)))
            n = int(10 ** (3 + 9 * heat))
            return ("CALCULATIONS / SEC", f"{n:,}", RED if heat > 0.7 else GOLD)
        if kind == "eyes":
            im.paste(self.bg_gojo)
            self.halo(im, 540, 1100, 400, (90, 170, 255), 90)
            self.char(im, "gojo_yeux", 580, H + 60, 1520 * (1 + 0.06 * ease(q)), t, tl / 0.3)
            return ("PRECISION", "100%", CYAN)
        if kind in ("blue", "red"):
            im.paste(self.bg_gojo)
            col = CYAN if kind == "blue" else RED
            ox, oy = 700, 760
            self.char(im, "gojo_face", 360, H + 60, 1250, t, tl / 0.3)
            self.halo(im, ox, oy, 260, col, 110)
            for a0, r0, sz in self.parts:
                a = a0 + t * 1.5
                r = (1 - ((q * 1.8 + r0) % 1)) * 440 + 90 if kind == "blue" else ((q * 1.8 + r0) % 1) * 520 + 120
                x, y = ox + r * math.cos(a), oy + r * math.sin(a)
                d.ellipse((x - sz, y - sz, x + sz, y + sz), fill=col + (235,))
            orb(im, ox, oy, 105 + 6 * math.sin(t * 7), col, t)
            return ("FORCE", "INWARD" if kind == "blue" else "OUTWARD", col)
        if kind == "purple":                            # Blue et Red se forment au-dessus de la paume, puis Purple part de la main
            im.paste(self.bg_void)
            gh = 1500
            gimg = self.png("gojo_main", gh)
            gcx = 600
            self.char(im, "gojo_main", gcx, H + 60, gh, t, 1.0)
            px = gcx - gimg.width / 2 + 0.20 * gimg.width
            py = H + 60 - gh + 0.50 * gh
            ox, oy = px, py - 330
            k = min(1.0, q / 0.4)
            if k < 1:
                for sx, col in ((-1, CYAN), (1, RED)):
                    x = ox + sx * 230 * (1 - ease(k))
                    rr = 40 + 45 * ease(min(1, q / 0.15))
                    self.halo(im, x, oy, int(rr * 2), col, 110)
                    orb(im, x, oy, rr, col, t)
            else:
                g = ease(min(1.0, (q - 0.4) / 0.25))
                r = 85 + 150 * g
                x = ox + 700 * ease(max(0, (q - 0.72) / 0.28))  # le Purple part vers la droite
                self.halo(im, x, oy, int(r * 1.5), PURP, 130)
                d.ellipse((x - r, oy - r, x + r, oy + r), fill=PURP + (240,))
                d.ellipse((x - r * 0.55, oy - r * 0.55, x + r * 0.55, oy + r * 0.55), fill=(250, 240, 255, 245))
            return ("MASS", "IMAGINARY", (215, 180, 255))
        if kind == "choice":                            # « 1 ou 2 ? » écrit dans la vidéo : commenter = un seul mot
            for j, (x0, lab, col) in enumerate(((60, "INFINITY", GOLD), (560, "SIX EYES", CYAN))):
                k = back(min(1, max(0, (tl - 0.15 * j) / 0.35)))
                if k <= 0:
                    continue
                pw, ph = 460, 820
                panel = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
                pm = Image.new("L", (pw, ph), 0)
                ImageDraw.Draw(pm).rounded_rectangle((0, 0, pw - 1, ph - 1), radius=44, fill=255)
                bgp = Image.new("RGBA", (pw, ph), (16, 26, 58, 255))
                if j == 0:
                    self.waves(bgp, pw / 2 + 60, ph / 2 - 40, t, 1.6)
                    fs = self.cache.get("fist_small") or self.cache.setdefault("fist_small", m.fist_side(340))
                    bgp.alpha_composite(fs, (int(pw / 2 - fs.width + 20), int(ph / 2 - 40 - fs.height / 2)))
                else:
                    gy = self.png("gojo_yeux", 900)
                    bgp.alpha_composite(gy, (int(pw / 2 - gy.width / 2), ph - gy.height + 60))
                panel.paste(bgp, (0, 0), pm)
                dd = ImageDraw.Draw(panel)
                dd.rounded_rectangle((0, 0, pw - 1, ph - 1), radius=44, outline=col + (255,), width=6)
                dd.ellipse((pw / 2 - 52, 30, pw / 2 + 52, 134), fill=col + (255,))
                dd.text((pw / 2, 82), str(j + 1), font=m.P("Bold", 70), fill=(14, 16, 30), anchor="mm")
                dd.text((pw / 2, ph - 70), lab, font=m.P("Bold", 56), fill=WHITE, anchor="mm", stroke_width=3, stroke_fill=(8, 12, 30))
                if k != 1:
                    panel = panel.resize((max(1, int(pw * k)), max(1, int(ph * k))), Image.BILINEAR)
                im.alpha_composite(panel, (int(x0 + pw / 2 - panel.width / 2), int(1000 - panel.height / 2)))
            return None
        if kind == "warning":
            im.paste(self.bg_red)
            m.speed_lines(im, 540, 1100, seed=8)
            self.char(im, "sukuna_visage", 540, H + 60, 1350, t, tl / 0.3)
            return None
        if kind == "slash":
            im.paste(self.bg_red)
            self.char(im, "sukuna_slash", 560, H + 60, 1350, t, tl / 0.3)
            return ("SPACE", "CUT", WHITE)
        return None

    def caption(self, im, words, t):
        cur = [i for i, (w, b, a, e) in enumerate(words) if a - 0.05 <= t]
        hook = words is self.first and t < words[3][2]  # image 0 : « If you had Gojo's » déjà écrit (accroche)
        if hook:
            cur = [3]
        if not cur or t > words[-1][3] + 0.35:
            return
        i = cur[-1]
        g0 = (i // 4) * 4                                # 4 mots max à la fois
        chunk = words[g0:g0 + 4]
        d = ImageDraw.Draw(im)
        sz = 66
        while True:                                      # trop large → le texte rétrécit (jamais hors champ)
            fl, fb = m.P("Light", sz), m.P("Bold", sz)
            tw = sum(d.textlength(w + " ", font=fb if b else fl) for w, b, a, e in chunk)
            if tw <= W - 120 or sz <= 40:
                break
            sz -= 2
        x = W / 2 - tw / 2
        for w, b, a, e in chunk:
            f = fb if b else fl
            if t >= a - 0.05 or hook:
                d.text((x, 290), w, font=f, fill=WHITE, anchor="lm", stroke_width=3, stroke_fill=(8, 12, 30))
            x += d.textlength(w + " ", font=f)


def flash(im, r, g, b, a):
    """Voile plein écran MÉLANGÉ (un rectangle RGBA dessiné sur une toile RGBA remplace les pixels au lieu de
    les mélanger : bug des flashs tout blancs du 19/11)."""
    if a > 0:
        im.alpha_composite(Image.new("RGBA", im.size, (r, g, b, int(min(255, a)))))


def orb(im, cx, cy, r, col, t):
    d = ImageDraw.Draw(im, "RGBA")
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col + (255,))
    d.ellipse((cx - r * 0.62, cy - r * 0.62, cx + r * 0.62, cy + r * 0.62), fill=(255, 255, 255, 235))
    for k in range(3):
        a = t * 3 + k * 2.09
        x, y = cx + r * 0.8 * math.cos(a), cy + r * 0.8 * math.sin(a)
        d.ellipse((x - r * 0.1, y - r * 0.1, x + r * 0.1, y + r * 0.1), fill=(255, 255, 255, 255))


def brain_img():
    """Cerveau original, ombrage doux (dégradé + liseré fin), sans contour noir."""
    S = 640
    c = Image.new("RGBA", (S, int(S * 0.8)), (0, 0, 0, 0))
    top, bot, rim = (255, 186, 200), (222, 120, 150), (190, 90, 120)
    for box in ((40, 80, 330, 470), (300, 80, 600, 470), (90, 30, 330, 300), (300, 30, 550, 300)):
        mk = Image.new("L", c.size, 0)
        ImageDraw.Draw(mk).ellipse(box, fill=255)
        c.alpha_composite(m.grad_fill(c.size, top, bot, mk))
    d = ImageDraw.Draw(c)
    d.line((320, 40, 320, 470), fill=rim, width=6)
    for k in range(3):
        d.arc((70 + 80 * k, 120, 190 + 80 * k, 260), 200, 340, fill=rim, width=6)
        d.arc((340 + 80 * k, 120, 460 + 80 * k, 260), 200, 340, fill=rim, width=6)
        d.arc((80 + 80 * k, 270, 200 + 80 * k, 400), 20, 160, fill=rim, width=6)
        d.arc((350 + 80 * k, 270, 470 + 80 * k, 400), 20, 160, fill=rim, width=6)
    return c


def counter(im, spec, t_on):
    if not spec:
        return
    label, value, col = spec
    d = ImageDraw.Draw(im)
    d.text((80, 1344), " ".join(label), font=m.P("Medium", 30), fill=SUB, anchor="lm")
    d.text((76, 1410), value, font=m.P("Bold", 92), fill=col, anchor="lm")


def slash_cut(im, tl, d0=0.9):
    """Sukuna coupe l'ESPACE : l'image entière se fend en diagonale et les deux moitiés glissent."""
    k = tl - d0
    if k <= 0:
        return im
    p = min(1, k / 0.18)
    sep = 34 * ease(min(1, k / 0.35))
    x0, y0, x1, y1 = -40, 600, W + 40, 1500
    msk = Image.new("L", (W, H), 0)
    ImageDraw.Draw(msk).polygon([(x0, y0), (x1, y1), (W, H), (0, H)], fill=255)
    if sep > 0:
        nx, ny = -(y1 - y0), (x1 - x0)
        nl = math.hypot(nx, ny)
        dx, dy = nx / nl * sep, ny / nl * sep
        out = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        top = im.copy()
        top.putalpha(Image.eval(msk, lambda v: 255 - v))
        bot = im.copy()
        bot.putalpha(msk)
        out.alpha_composite(top, (int(-dx / 2), int(-dy / 2)))
        out.alpha_composite(bot, (int(dx / 2), int(dy / 2)))
        im = out
    d = ImageDraw.Draw(im, "RGBA")
    xe, ye = x0 + (x1 - x0) * p, y0 + (y1 - y0) * p
    d.line((x0, y0, xe, ye), fill=(255, 60, 60, 200), width=26)
    d.line((x0, y0, xe, ye), fill=(255, 255, 255, 255), width=8)
    if k < 0.12:
        flash(im, 255, 255, 255, int(170 * (1 - k / 0.12)))
    return im


def series_badge(im, txt):
    """Petite pilule de série en haut à gauche : la chaîne a SA série (la vidéo de référence n'en a pas)."""
    d = ImageDraw.Draw(im)
    f = m.P("Bold", 30)
    w = d.textlength(txt, font=f) + 44
    d.rounded_rectangle((60, 130, 60 + w, 184), radius=27, fill=(255, 196, 84))
    d.text((60 + w / 2, 157), txt, font=f, fill=(20, 16, 8), anchor="mm")


def follow(im, k):
    """Bouton FOLLOW qui arrive en pop à la place du compteur."""
    if k <= 0:
        return
    s = back(min(1, k))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    m.follow_pill(lay, y=1390)
    if s != 1:
        bb = lay.getbbox()
        if bb:
            part = lay.crop(bb)
            part = part.resize((max(1, int(part.width * s)), max(1, int(part.height * s))), Image.BILINEAR)
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
            lay.alpha_composite(part, (int(cx - part.width / 2), int(cy - part.height / 2)))
    im.alpha_composite(lay)


def build(script):
    import tts
    lines = script["lines"]
    parsed = [parse(l["text"]) for l in lines]
    vbuf, segs = tts.lines([p[1] for p in parsed], gap=0.22, start=0.08)
    words = [word_times(p[0], a, b) for p, (a, b) in zip(parsed, segs)]
    total = segs[-1][1] + 1.0
    return lines, vbuf, segs, words, total


def frame(sh, lines, segs, words, total, t):
    idx = max([i for i, (a, b) in enumerate(segs) if t >= a - 0.08] or [0])
    a, b = segs[idx]
    nxt = segs[idx + 1][0] if idx + 1 < len(segs) else total
    dur = max(0.4, nxt - a)
    tl = max(0.0, t - a)
    q = min(1.0, tl / dur)
    kind = lines[idx]["scene"]
    im = sh.bg.copy()
    # caméra : lente avancée sur chaque plan
    spec = sh.scene(im, kind, q, t, tl, dur)
    im.alpha_composite(sh.vig)
    z = 1 + 0.035 * ease(q)
    if kind == "slow":                                  # zoom sur l'espace entre les jointures et le nez
        z = 1 + 0.9 * ease(min(1, tl / 1.2))
        fx_, fy_ = NOSE[0] - 60, NOSE[1]
        cw, ch = W / z, H / z
        x0 = min(max(0, fx_ - cw / 2), W - cw)
        y0 = min(max(0, fy_ - ch / 2), H - ch)
        im = im.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((W, H), Image.BILINEAR)
    elif kind not in ("punch", "end"):                  # le plan poing reste fixe (boucle exacte)
        cw, ch = W / z, H / z
        im = im.crop((int((W - cw) / 2), int((H - ch) / 2), int((W + cw) / 2), int((H + ch) / 2))).resize((W, H), Image.BILINEAR)
    if kind == "slash":
        im = slash_cut(im, tl)
    if kind == "end":
        te = total - t                                   # temps restant
        if te > 0.55:
            follow(im, tl / 0.3)
        else:                                            # le bouton redevient le compteur de l'image 0
            counter(im, sh.loop_counter(), 0)
    else:
        counter(im, spec, tl)
    if sh.s.get("series") and (idx == 0 or kind == "end"):
        series_badge(im, sh.s["series"])
    sh.caption(im, words[idx], t)
    if idx + 1 < len(segs) and nxt - t < 0.12:          # petit flash blanc entre deux plans
        flash(im, 255, 255, 255, int(110 * (1 - (nxt - t) / 0.12)))
    return im.convert("RGB")


def main(script_path, out, preview=False, show_cls=None):
    out = Path(out).resolve()
    script = json.loads(Path(script_path).resolve().read_text())
    os.chdir(ROOT)
    from clipper.slides import fusion, render
    lines, vbuf, segs, words, total = build(script)
    sh = (show_cls or Show)(script)
    sh.first = words[0]
    if preview:
        tiles = []
        for (a, b) in segs:
            for f in (0.2, 0.8):
                tiles.append(frame(sh, lines, segs, words, total, a + f * (b - a)).resize((270, 480)))
        tiles.append(frame(sh, lines, segs, words, total, total - 0.2).resize((270, 480)))
        tiles.append(frame(sh, lines, segs, words, total, 0.0).resize((270, 480)))
        cols = 8
        sheet = Image.new("RGB", (cols * 270, ((len(tiles) + cols - 1) // cols) * 480))
        for i, tm in enumerate(tiles):
            sheet.paste(tm, ((i % cols) * 270, (i // cols) * 480))
        sheet.save(out.with_suffix(".png"))
        return [round(a, 2) for a, b in segs], round(total, 2)
    tmp = out.with_suffix(".raw.mp4")
    ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
                           "-pix_fmt", "yuv420p", str(tmp)], stdin=subprocess.PIPE)
    for fi in range(int(total * FPS)):
        ff.stdin.write(frame(sh, lines, segs, words, total, fi / FPS).tobytes())
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
    hum = np.sin(2 * math.pi * 55 * tt) * 0.035 + np.sin(2 * math.pi * 82.5 * tt) * 0.022 + np.sin(2 * math.pi * 110 * tt) * 0.012
    buf += hum.astype(np.float32)
    for ln, (a, b) in zip(lines, segs):
        add(whoosh, max(0, a - 0.12), 0.16)
        if ln["scene"] in sh.boom_scenes:
            add(boom, a + sh.boom_scenes[ln["scene"]], 0.33)
        for off, path, g in sh.scene_sounds.get(ln["scene"], []):
            f = ROOT / path
            if f.exists():
                add(fusion.load_sound(f), a + off, g)
        if ln["scene"] == "purple":
            add(boom, a + 0.35 * (b - a), 0.35)
        elif ln["scene"] == "slash":
            add(boom, a + 0.9, 0.35)
    n = min(len(buf), len(vbuf))
    buf[:n] += vbuf[:n]
    fade = min(len(buf), int(0.5 * RATE))               # fondu de l'ambiance au début/à la fin (boucle douce)
    buf[:fade] *= np.linspace(0.4, 1, fade)
    wav = out.with_suffix(".wav")
    fusion.write_wav(wav, np.tanh(buf * 0.9))
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(tmp), "-i", str(wav), "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", str(out)], check=True)
    tmp.unlink()
    wav.unlink()
    render.stamp_video(out)
    return out, round(total, 2)


if __name__ == "__main__":
    a = sys.argv[1:]
    print(main(a[0], a[1], "--preview" in a))
