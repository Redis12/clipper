"""Éléments dessinés en code pour l'explainer Gojo v3 (19/11), DA vectorielle plate « un peu stickman » :
aplats, contour encre épais et régulier, pas de lueur ni de dégradé. Tout est original (aucun perso existant).
Chaque fonction rend une image RGBA (dessinée à ×SS puis réduite pour des bords lisses).
  you(expr, pose)  bonhomme « YOU » : tête ronde, corps en traits ; expr = calm | smug | shock ; pose = idle | arms_up | point
  fist()           poing de profil, manche
  rings(n)         anneaux de l'Infini (cercles pleins concentriques, pas de lueur)
  zeno(pose)       philosophe grec original (barbe, toge, bâton) ; pose = idle | point
  atom()           atome (noyau + 3 orbites)
  clock(h, m)      horloge murale
  coin(face)       pièce (face = heads | tails | edge)
python3 tools/explainer/flat_assets.py sheet.png   → planche d'aperçu
"""
from __future__ import annotations

import math
import sys

from PIL import Image, ImageDraw, ImageFont

SS = 3
INK = (28, 24, 44)          # même encre que les PNG de ChatGPT (traits fins)
WHITE = (250, 250, 252)
BG = (24, 34, 66)          # bleu nuit plat
BG2 = (32, 46, 88)
YEL = (255, 205, 70)
CYAN = (110, 200, 255)
RED = (240, 80, 80)
PURP = (160, 100, 245)
SKIN = (250, 214, 180)
SKIN_D = (226, 180, 146)
YOU_COL = (255, 205, 70)   # le « YOU » porte le jaune de la chaîne
TOGA = (240, 236, 222)
TOGA_D = (206, 198, 178)
BEARD = (190, 190, 200)
GOLD = (245, 190, 60)
GOLD_D = (200, 145, 30)


class Pen:
    """Dessin à l'échelle ×SS avec un trait d'encre constant."""

    def __init__(self, w, h, lw=5):
        self.im = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)
        self.lw = lw * SS

    def _p(self, pts):
        return [(x * SS, y * SS) for x, y in pts]

    def line(self, pts, col=INK, w=None):
        w = self.lw if w is None else w * SS
        p = self._p(pts)
        self.d.line(p, fill=col, width=w, joint="curve")
        for x, y in (p[0], p[-1]):                      # bouts ronds
            self.d.ellipse((x - w / 2, y - w / 2, x + w / 2, y + w / 2), fill=col)

    def ell(self, cx, cy, rx, ry=None, fill=WHITE, outline=INK, w=None):
        ry = rx if ry is None else ry
        w = self.lw if w is None else w * SS
        self.d.ellipse(((cx - rx) * SS, (cy - ry) * SS, (cx + rx) * SS, (cy + ry) * SS), fill=fill,
                       outline=outline, width=w if outline else 0)

    def poly(self, pts, fill, outline=INK, w=None):
        w = self.lw if w is None else w * SS
        p = self._p(pts)
        self.d.polygon(p, fill=fill)
        if outline:
            self.d.line(p + [p[0]], fill=outline, width=w, joint="curve")

    def rrect(self, x0, y0, x1, y1, r, fill, outline=INK, w=None):
        w = self.lw if w is None else w * SS
        self.d.rounded_rectangle((x0 * SS, y0 * SS, x1 * SS, y1 * SS), radius=r * SS, fill=fill,
                                 outline=outline, width=w if outline else 0)

    def arc(self, cx, cy, r, a0, a1, col=INK, w=None):
        w = self.lw if w is None else w * SS
        self.d.arc(((cx - r) * SS, (cy - r) * SS, (cx + r) * SS, (cy + r) * SS), a0, a1, fill=col, width=w)

    def done(self):
        return self.im.resize((self.im.width // SS, self.im.height // SS), Image.LANCZOS)


def _limb(p, a, b, length, ang1, ang2, w=14):
    """Membre en 2 segments (épaule → coude → main), angles en degrés (0 = droite, 90 = bas)."""
    x1 = a + length * math.cos(math.radians(ang1))
    y1 = b + length * math.sin(math.radians(ang1))
    x2 = x1 + length * math.cos(math.radians(ang2))
    y2 = y1 + length * math.sin(math.radians(ang2))
    p.line([(a, b), (x1, y1), (x2, y2)], w=w)
    return x2, y2


def face(p, cx, cy, r, expr, look=0.0):
    """Yeux en points + bouche, communs au YOU et à Zénon."""
    ex = r * 0.34
    ey = cy - r * 0.08
    lx = look * r * 0.12
    if expr == "shock":
        for s in (-1, 1):
            p.ell(cx + s * ex + lx, ey, r * 0.16, fill=WHITE, w=5)
            p.ell(cx + s * ex + lx, ey, r * 0.06, fill=INK, outline=None)
        p.ell(cx + lx, cy + r * 0.45, r * 0.14, r * 0.18, fill=INK, outline=None)
    else:
        for s in (-1, 1):
            p.ell(cx + s * ex + lx, ey, r * 0.085, r * 0.11, fill=INK, outline=None)
        if expr == "smug":
            p.line([(cx - r * 0.28 + lx, cy + r * 0.40), (cx + r * 0.05 + lx, cy + r * 0.46),
                    (cx + r * 0.32 + lx, cy + r * 0.30)], w=6)
            for s in (-1, 1):                           # paupières mi-closes
                p.line([(cx + s * ex - r * 0.14 + lx, ey - r * 0.06), (cx + s * ex + r * 0.14 + lx, ey - r * 0.06)], w=6)
        else:
            p.arc(cx + lx, cy + r * 0.18, r * 0.30, 30, 150, w=6)


def you(expr="calm", pose="idle", blink=False):
    """Le « YOU » : tête ronde blanche, sweat jaune (le seul aplat de couleur), membres en traits."""
    W0, H0 = 420, 760
    p = Pen(W0, H0)
    cx = W0 / 2
    hy, hr = 150, 98
    sy, hip = 300, 520
    if pose == "arms_up":
        _limb(p, cx - 52, sy + 10, 105, 220, 250)
        _limb(p, cx + 52, sy + 10, 105, -40, -70)
    elif pose == "point":
        _limb(p, cx - 52, sy + 10, 110, 110, 95)
        _limb(p, cx + 52, sy + 10, 120, -10, -15)
    else:
        _limb(p, cx - 52, sy + 10, 110, 115, 95)
        _limb(p, cx + 52, sy + 10, 110, 65, 85)
    _limb(p, cx - 26, hip, 120, 100, 95)               # jambes
    _limb(p, cx + 26, hip, 120, 80, 85)
    p.rrect(cx - 72, sy - 22, cx + 72, hip + 18, 46, YOU_COL)   # sweat
    p.d.text((cx * SS, (sy + 120) * SS), "YOU", fill=INK, anchor="mm",
             font=ImageFont.truetype(_font("anton"), 46 * SS))
    p.ell(cx, hy, hr, fill=WHITE)                       # tête
    if blink:
        for s in (-1, 1):
            p.line([(cx + s * hr * 0.34 - 10, hy - 8), (cx + s * hr * 0.34 + 10, hy - 8)], w=6)
        p.arc(cx, hy + hr * 0.18, hr * 0.30, 30, 150, w=6)
    else:
        face(p, cx, hy, hr, expr)
    return p.done()


def fist(sleeve=RED):
    """Poing de profil qui vise la droite, manche colorée. Formes simples, contour constant."""
    W0, H0 = 520, 300
    p = Pen(W0, H0)
    p.rrect(10, 95, 230, 215, 24, sleeve)                # manche
    p.line([(70, 100), (70, 210)], w=6)
    p.rrect(200, 60, 420, 250, 70, SKIN)                 # paume
    for k in range(4):                                   # doigts repliés
        y = 66 + k * 46
        p.rrect(370, y, 470, y + 48, 24, SKIN)
    p.rrect(300, 190, 410, 250, 30, SKIN)                # pouce
    p.line([(330, 205), (395, 205)], col=SKIN_D, w=6)
    return p.done()


def rings(n=5, col=CYAN, r0=60, gap=34):
    """Anneaux de l'Infini : cercles concentriques en aplat translucide + trait net (pas de lueur)."""
    R = r0 + gap * n + 10
    p = Pen(2 * R, 2 * R, lw=5)
    for k in range(n - 1, -1, -1):
        r = r0 + gap * k
        a = 40 + 25 * (n - 1 - k)
        p.ell(R, R, r, fill=col + (a,), outline=col, w=5)
    return p.done()


def zeno(pose="idle", blink=False):
    """Philosophe grec ORIGINAL (« Zeno ») : tête ronde chauve, barbe grise, toge, bâton."""
    W0, H0 = 460, 800
    p = Pen(W0, H0)
    cx = 220
    hy, hr = 160, 92
    sy, hip = 300, 560
    p.line([(370, 220), (370, 760)], col=(150, 110, 70), w=16)      # bâton
    p.line([(370, 220), (370, 760)], w=4)
    if pose == "point":
        _limb(p, cx - 50, sy + 20, 115, 200, 195)
    else:
        _limb(p, cx - 50, sy + 20, 115, 110, 95)
    _limb(p, cx - 28, hip, 110, 98, 92)
    _limb(p, cx + 28, hip, 110, 82, 88)
    p.poly([(cx - 85, sy - 10), (cx + 85, sy - 10), (cx + 105, hip + 40), (cx - 105, hip + 40)], TOGA)
    p.poly([(cx - 80, sy - 6), (cx + 30, hip + 36), (cx + 70, hip + 36), (cx - 40, sy - 6)], TOGA_D, outline=None)
    p.line([(cx - 80, sy - 6), (cx + 50, hip + 36)], w=5)
    hx, hyy = _limb(p, cx + 55, sy + 20, 100, 30, -20)              # main sur le bâton
    p.ell(370, hyy, 16, fill=SKIN, w=5)
    p.ell(cx, hy, hr, fill=SKIN)
    p.poly([(cx - hr * 0.97, hy + 8), (cx - hr * 0.7, hy + 30), (cx - 30, hy + 42), (cx + 30, hy + 42),
            (cx + hr * 0.7, hy + 30), (cx + hr * 0.97, hy + 8), (cx + hr * 0.75, hy + hr * 1.3),
            (cx, hy + hr * 1.75), (cx - hr * 0.75, hy + hr * 1.3)], BEARD)  # barbe (sous le nez, favoris)
    p.ell(cx, hy + 66, 22, 12, fill=(150, 70, 70), w=5)                    # bouche dans la barbe
    p.line([(cx - 26, hy + 36), (cx, hy + 28), (cx + 26, hy + 36)], col=BEARD, w=12)  # moustache
    p.line([(cx - 4, hy - 2), (cx + 8, hy + 18)], col=SKIN_D, w=6)          # nez
    for s in (-1, 1):
        p.line([(cx + s * 30 - 18, hy - 42), (cx + s * 30 + 18, hy - 36 - s * 0)], col=BEARD, w=10)  # sourcils
        if blink:
            p.line([(cx + s * 30 - 9, hy - 10), (cx + s * 30 + 9, hy - 10)], w=6)
        else:
            p.ell(cx + s * 30, hy - 10, 8, 10, fill=INK, outline=None)
    for k in range(7):                                               # couronne de laurier : feuilles
        a = math.radians(195 + k * 25)
        lx, ly = cx + (hr + 4) * math.cos(a), hy - 18 + (hr + 4) * math.sin(a)
        p.ell(lx, ly, 15, 9, fill=(120, 175, 90), w=4)
    return p.done()


def atom(col=CYAN, t=0.0):
    W0 = 420
    p = Pen(W0, W0, lw=6)
    c = W0 / 2
    for k in range(3):
        a = math.radians(k * 60 + t * 40)
        pts = []
        for i in range(73):
            u = 2 * math.pi * i / 72
            x, y = 180 * math.cos(u), 62 * math.sin(u)
            pts.append((c + x * math.cos(a) - y * math.sin(a), c + x * math.sin(a) + y * math.cos(a)))
        p.line(pts, col=col, w=6)
        u = t * 3 + k * 2.1                              # électron
        x, y = 180 * math.cos(u), 62 * math.sin(u)
        p.ell(c + x * math.cos(a) - y * math.sin(a), c + x * math.sin(a) + y * math.cos(a), 14, fill=YEL, w=4)
    p.ell(c, c, 40, fill=RED)
    p.ell(c - 12, c - 10, 14, fill=(255, 140, 140), outline=None)
    return p.done()


def clock(h=10, m=10):
    W0 = 400
    p = Pen(W0, W0)
    c = W0 / 2
    p.ell(c, c, 180, fill=WHITE)
    p.ell(c, c, 150, fill=WHITE, w=4)
    for k in range(12):
        a = math.radians(k * 30)
        r1 = 128 if k % 3 else 112
        p.line([(c + r1 * math.sin(a), c - r1 * math.cos(a)), (c + 140 * math.sin(a), c - 140 * math.cos(a))], w=6 if k % 3 else 10)
    am = math.radians(m * 6)
    ah = math.radians((h % 12) * 30 + m * 0.5)
    p.line([(c, c), (c + 75 * math.sin(ah), c - 75 * math.cos(ah))], w=14)
    p.line([(c, c), (c + 115 * math.sin(am), c - 115 * math.cos(am))], col=RED, w=9)
    p.ell(c, c, 14, fill=INK, outline=None)
    return p.done()


def coin(face="heads"):
    W0 = 360
    p = Pen(W0, W0)
    c = W0 / 2
    if face == "edge":
        p.rrect(c - 160, c - 26, c + 160, c + 26, 26, GOLD)
        for k in range(-6, 7):
            p.line([(c + k * 22, c - 16), (c + k * 22, c + 16)], col=GOLD_D, w=5)
        return p.done()
    p.ell(c, c, 160, fill=GOLD)
    p.ell(c, c, 124, fill=GOLD, outline=GOLD_D, w=8)
    if face == "heads":                                  # symbole ∞ dessiné (la police n'a pas le glyphe)
        pts = [(c + 95 * math.cos(u) / (1 + math.sin(u) ** 2), c + 95 * math.sin(u) * math.cos(u) / (1 + math.sin(u) ** 2))
               for u in [2 * math.pi * i / 120 for i in range(121)]]
        p.line(pts, col=GOLD_D, w=16)
    else:
        p.d.text((c * SS, (c - 6) * SS), "1", fill=GOLD_D, anchor="mm", font=ImageFont.truetype(_font("anton"), 150 * SS))
    return p.done()


def _font(name):
    from pathlib import Path
    return str(Path(__file__).resolve().parents[2] / f"tools/money_sim/fonts/{name}.woff2")


def sheet(out):
    W, H = 1080, 1920
    im = Image.new("RGBA", (W, H), BG)
    d = ImageDraw.Draw(im)
    for gx in range(0, W, 90):
        d.line((gx, 0, gx, H), fill=BG2, width=2)
    for gy in range(0, H, 90):
        d.line((0, gy, W, gy), fill=BG2, width=2)
    lab = ImageFont.truetype(_font("mont800"), 30)

    def put(img, x, y, s, name):
        img = img.resize((int(img.width * s), int(img.height * s)), Image.LANCZOS)
        im.alpha_composite(img, (int(x - img.width / 2), int(y - img.height / 2)))
        d.text((x, y + img.height / 2 + 26), name, font=lab, fill=WHITE, anchor="mm")

    rg = rings()
    put(rg, 270, 330, 0.95, "")
    put(you("smug"), 270, 330, 0.55, "YOU + Infinity")
    put(fist(), 760, 300, 0.85, "fist")
    put(you("shock", "arms_up"), 180, 900, 0.6, "YOU (shock)")
    put(zeno("point"), 520, 900, 0.6, "Zeno (original)")
    put(atom(t=0.6), 860, 860, 0.6, "atom")
    put(clock(), 200, 1450, 0.7, "clock")
    put(coin("heads"), 540, 1450, 0.7, "coin")
    put(coin("edge"), 860, 1450, 0.7, "coin (edge)")
    d.text((W / 2, 1820), "DA v3 · aperçu des éléments dessinés", font=lab, fill=YEL, anchor="mm")
    im.convert("RGB").save(out)


if __name__ == "__main__":
    sheet(sys.argv[1] if len(sys.argv) > 1 else "sheet.png")
