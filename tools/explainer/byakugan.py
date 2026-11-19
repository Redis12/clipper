"""« If you had the Byakugan » (#2 de la série, 19/11) — même DA que Gojo v6 (bleu nuit, texte fin, compteur doré),
accent lavande pour le Byakugan. Réutilise le moteur infinity_v4 (texte, compteur, badge, « 1 ou 2 », follow qui
reboucle) ; ici seulement les scènes propres à l'épisode. Persos = PNG Gemini sur fond vert détourés dans
library/_explainer/byakugan/simple/ (hinata_face, neji_face, neji_palm, neji_back, byakugan_eye) ; si une image
manque, une silhouette grise la remplace (aperçus avant réception).
python3 tools/explainer/byakugan.py tools/explainer/scripts/byakugan_v1.json sortie.mp4 [--preview]
"""
from __future__ import annotations

import math
import random

import numpy as np
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).parent))
import infinity_v4 as v  # noqa: E402
from infinity_v4 import GOLD, RED, WHITE, H, W, back, ease, flash, m  # noqa: E402

LAV = (196, 186, 255)
LAV_D = (120, 104, 220)
DARK = (14, 18, 40)


def brick_wall(w, h, seed=2):
    """Mur de briques, ombrage doux (dégradé par brique), dessin original."""
    im = Image.new("RGBA", (w, h), (60, 44, 52, 255))
    d = ImageDraw.Draw(im)
    rnd = random.Random(seed)
    bw, bh = 180, 78
    for r, y in enumerate(range(-20, h, bh)):
        off = (bw // 2) * (r % 2)
        for x in range(-bw + off, w, bw):
            base = rnd.randint(-10, 10)
            top = (150 + base, 84 + base // 2, 70 + base // 2)
            bot = (118 + base, 62 + base // 2, 54 + base // 2)
            mk = Image.new("L", (bw - 10, bh - 10), 0)
            ImageDraw.Draw(mk).rounded_rectangle((0, 0, bw - 11, bh - 11), radius=10, fill=255)
            im.alpha_composite(m.grad_fill((bw - 10, bh - 10), top, bot, mk), (x + 5, y + 5))
    return im


def body_points(seed=11, n=361):
    """Silhouette humaine générique + réseau de chakra (points le long de lignes), coordonnées 0..1."""
    rnd = random.Random(seed)
    paths = [[(0.5, 0.13), (0.5, 0.55)], [(0.5, 0.24), (0.27, 0.48), (0.2, 0.62)], [(0.5, 0.24), (0.73, 0.48), (0.8, 0.62)],
             [(0.5, 0.55), (0.4, 0.78), (0.38, 0.97)], [(0.5, 0.55), (0.6, 0.78), (0.62, 0.97)],
             [(0.5, 0.3), (0.36, 0.38)], [(0.5, 0.3), (0.64, 0.38)], [(0.5, 0.42), (0.38, 0.5)], [(0.5, 0.42), (0.62, 0.5)]]
    pts = []
    for i in range(n):
        pth = paths[i % len(paths)]
        seg = rnd.randrange(len(pth) - 1)
        u = rnd.random()
        (x0, y0), (x1, y1) = pth[seg], pth[seg + 1]
        pts.append((x0 + (x1 - x0) * u + rnd.uniform(-0.035, 0.035), y0 + (y1 - y0) * u + rnd.uniform(-0.012, 0.012)))
    pts.sort(key=lambda p: p[1])
    return paths, pts


def silhouette(w, h, col=(26, 34, 70)):
    """Corps générique (tête ronde, membres arrondis) : pas un perso existant."""
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    S = lambda x, y: (x * w, y * h)  # noqa: E731
    d.ellipse((*S(0.41, 0.0), *S(0.59, 0.12)), fill=col)
    d.rounded_rectangle((*S(0.34, 0.14), *S(0.66, 0.58)), radius=int(0.08 * w), fill=col)
    for pts in (((0.36, 0.18), (0.22, 0.46), (0.18, 0.64)), ((0.64, 0.18), (0.78, 0.46), (0.82, 0.64)),
                ((0.44, 0.55), (0.4, 0.78), (0.38, 0.98)), ((0.56, 0.55), (0.6, 0.78), (0.62, 0.98))):
        d.line([S(*p) for p in pts], fill=col, width=int(0.1 * w), joint="curve")
        for p in (pts[0], pts[-1]):
            x, y = S(*p)
            r = 0.05 * w
            d.ellipse((x - r, y - r, x + r, y + r), fill=col)
    return im


class ByakuganShow(v.Show):
    boom_scenes = {"palm": 0.55, "arrow": 0.9}

    def __init__(self, script):
        super().__init__(script)
        self.wall = brick_wall(W, H)
        dark = Image.new("RGBA", (W, H), (8, 10, 24, 120))            # mur assombri : texte lisible
        self.wall.alpha_composite(dark)
        grad = Image.new("L", (1, H), 0)                                # dégradé sombre derrière le texte (haut)
        for y in range(H):
            grad.putpixel((0, y), int(230 * max(0.0, 1 - y / 520) ** 1.4))
        top = Image.new("RGBA", (W, H), (6, 8, 20, 255))
        top.putalpha(grad.resize((W, H)))
        self.wall.alpha_composite(top)
        self.paths, self.pts = body_points()
        self.sil = silhouette(520, 1100)
        self.hidden = silhouette(300, 640, (10, 12, 26))

    def loop_counter(self):
        return ("HIDDEN FROM YOU", "NOTHING", LAV)

    def png(self, name, h, flip=False):
        key = (name, int(h), flip)
        if key not in self.cache and not (self.base / f"{name}.png").exists():
            ph = silhouette(int(h * 0.6), int(h), (70, 76, 110))          # en attendant l'image Gemini
            ImageDraw.Draw(ph).text((ph.width / 2, ph.height * 0.3), name, font=m.P("Bold", 40), fill=WHITE, anchor="mm")
            self.cache[key] = ph
        return super().png(name, h, flip)

    # ------------------------------------------------------------------ éléments
    def lens(self, im, cx, cy, r, t):
        """Loupe Byakugan : le mur devient transparent dans le cercle → on voit l'ennemi caché et son chakra."""
        behind = self.bg.copy()
        self.halo(behind, cx, cy, int(r * 0.9), LAV_D, 70)
        hid = self.png("body_on", int(r * 1.75))
        behind.alpha_composite(hid, (int(cx - hid.width / 2), int(cy - hid.height / 2 + r * 0.12)))
        mk = Image.new("L", (W, H), 0)
        ImageDraw.Draw(mk).ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
        im.paste(behind, (0, 0), mk)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(lay).ellipse((cx - r, cy - r, cx + r, cy + r), outline=LAV + (255,), width=7)
        im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(10)))
        im.alpha_composite(lay)

    def topdown(self, im, cx, cy, sweep, t, blind_col=None, arrow=None):
        """Vue de dessus : toi au centre, cône de vision lavande sur `sweep` degrés ; l'angle mort est derrière."""
        d = ImageDraw.Draw(im, "RGBA")
        R = 430
        start = 90 + 6                                        # l'angle mort (12°) est en bas = derrière toi
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dl = ImageDraw.Draw(lay)
        dl.pieslice((cx - R, cy - R, cx + R, cy + R), start, start + sweep, fill=LAV + (70,))
        for k in range(1, 4):
            rr = R * k / 3
            dl.arc((cx - rr, cy - rr, cx + rr, cy + rr), start, start + sweep, fill=LAV + (150,), width=3)
        im.alpha_composite(lay)
        if blind_col:
            d.pieslice((cx - R, cy - R, cx + R, cy + R), 84, 96, fill=blind_col + (200,))
        top = self.png("neji_top", 300)                                     # Neji vu du dessus (avant = en haut)
        im.alpha_composite(top, (int(cx - top.width / 2), int(cy - top.height / 2)))
        if arrow is not None:
            ax, ay = arrow
            d.line((ax, ay + 160, ax, ay), fill=(150, 110, 70, 255), width=12)
            d.polygon([(ax - 22, ay), (ax + 22, ay), (ax, ay - 46)], fill=(220, 225, 235, 255))
            for s in (-1, 1):
                d.polygon([(ax, ay + 150), (ax + s * 26, ay + 182), (ax, ay + 170)], fill=RED + (255,))

    def chakra_body(self, im, cx, top, h, reveal=1.0, off=0.0, t=0.0):
        """Corps Gemini (body_on / body_off). reveal : le chakra s'allume de la tête aux pieds (0→1) ;
        off : il s'éteint en cercle depuis la poitrine (0→1)."""
        on, dark = self.png("body_on", h), self.png("body_off", h)
        x0, y0 = int(cx - on.width / 2), int(top)
        im.alpha_composite(dark, (x0, y0))
        mk = Image.new("L", on.size, 0)
        dm = ImageDraw.Draw(mk)
        if reveal > 0:
            yy = on.height * reveal
            dm.rectangle((0, 0, on.width, yy), fill=255)
            for k in range(12):                              # bord adouci
                dm.rectangle((0, yy + k * 3, on.width, yy + k * 3 + 3), fill=255 - 20 * k)
        if off > 0:
            r = off * on.height * 1.1
            ccx, ccy = on.width / 2, on.height * 0.28
            dm.ellipse((ccx - r, ccy - r, ccx + r, ccy + r), fill=0)
        lit = on.copy()
        lit.putalpha(Image.fromarray(np.minimum(np.asarray(on.getchannel("A")), np.asarray(mk))))
        im.alpha_composite(lit, (x0, y0))

    # ------------------------------------------------------------------ scènes
    def scene(self, im, kind, q, t, tl, dur):
        d = ImageDraw.Draw(im, "RGBA")
        if kind in ("wall", "end"):
            im.alpha_composite(self.wall)
            k = ease(q) if kind == "wall" else 1 - ease(q)
            r = 250 + 90 * k + 6 * math.sin(t * 4)
            self.lens(im, 540, 1000, r, t)
            band = self.png("byakugan_eye", 300).copy()          # bandeau des yeux (le perso dès l'image 0)
            mk = Image.new("L", band.size, 0)
            ImageDraw.Draw(mk).rounded_rectangle((30, 0, band.width - 30, band.height), radius=40, fill=255)
            band.putalpha(Image.fromarray(np.minimum(np.asarray(band.getchannel("A")), np.asarray(mk))))
            im.alpha_composite(band, (int(540 - band.width / 2), 380))
            return ("HIDDEN FROM YOU", "NOTHING", LAV) if kind == "wall" else None
        if kind == "fov":
            sweep = 348 * ease(min(1, tl / 1.6))
            self.topdown(im, 540, 1000, sweep, t)
            return ("FIELD OF VIEW", f"{int(sweep)}°" if sweep < 347 else "≈ 360°", LAV)
        if kind == "range":
            im.paste(self.bg_gojo)
            self.char(im, "hinata_face", 790, H + 60, 1200, t, tl / 0.3)
            k = ease(min(1, tl / 2.2))
            dist = 10 * k
            d.line((80, 560, 1000, 560), fill=LAV + (200,), width=4)                      # règle de distance
            for i in range(11):
                x = 80 + i * 92
                d.line((x, 546, x, 574), fill=LAV + (200,), width=4)
                if i % 5 == 0:
                    d.text((x, 610), f"{i} km", font=m.P("Medium", 30), fill=LAV, anchor="mm")
            x = 80 + 920 * k
            self.halo(im, x, 560, 60, LAV_D, 110)
            d.ellipse((x - 18, 542, x + 18, 578), fill=LAV + (255,))
            return ("VISION RANGE", f"{dist:.1f} km", GOLD)
        if kind == "body":
            k = ease(min(1, tl / 2.0))
            n = int(361 * k)
            self.halo(im, 540, 1020, 380, LAV_D, 60)
            self.chakra_body(im, 540, 440, 1180, reveal=k, t=t)
            return ("CHAKRA POINTS", f"{n}", LAV)
        if kind == "needle":
            z = ease(min(1, tl / 0.8))
            cx, cy = 560, 1000
            self.halo(im, cx, cy, int(160 + 120 * z), LAV_D, 90)
            r = 10 + 34 * z                                     # le point grossit (zoom)
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=LAV + (255,))
            L = 900                                             # aiguille : sa pointe est plus grosse que le point
            tipx = cx - r - 30
            d.polygon([(tipx, cy), (tipx - L, cy - 26 - 40 * z), (tipx - L, cy + 26 + 40 * z)], fill=(200, 205, 220, 255))
            d.line((tipx, cy, tipx - L, cy - 26 - 40 * z), fill=(150, 156, 175, 255), width=4)
            return ("SIZE", "< NEEDLE TIP", LAV)
        if kind == "palm":
            self.chakra_body(im, 810, 560, 1250, reveal=1.0, off=ease(max(0, (tl - 0.55) / 0.7)), t=t)
            self.char(im, "neji_palm", 380, H + 60, 1350, t, tl / 0.3)
            hit = math.exp(-((tl - 0.55) / 0.07) ** 2)
            if hit > 0.05:
                flash(im, 255, 255, 255, int(80 * hit))
            return ("CHAKRA", "OFF" if tl > 0.7 else "ON", RED if tl > 0.7 else LAV)
        if kind == "blind" and not (self.base / "neji_back.png").exists():
            # pas d'image de Neji de dos : vue de dessus, l'angle mort (derrière la nuque) clignote en rouge
            pulse = 0.5 + 0.5 * math.sin(t * 8)
            self.char(im, "neji_close", 540, H + 330, 1050, t, tl / 0.3)
            self.topdown(im, 540, 720, 348, t, blind_col=(255, int(60 + 60 * pulse), int(60 + 60 * pulse)))
            return ("BLIND SPOT", "BACK OF NECK", RED)
        if kind == "blind":
            h = 1400
            self.char(im, "neji_back", 540, H + 80, h, t, tl / 0.3)
            nx, ny = 540, H + 80 - h + 0.555 * h              # nuque : juste au-dessus du nœud de la queue de cheval
            pulse = 0.5 + 0.5 * math.sin(t * 8)
            for k in range(3):
                rr = 40 + 30 * k + 14 * pulse
                d.ellipse((nx - rr, ny - rr, nx + rr, ny + rr), outline=RED + (int(230 - 60 * k),), width=6)
            d.ellipse((nx - 16, ny - 16, nx + 16, ny + 16), fill=RED + (255,))
            f = m.P("Bold", 44)
            tw = d.textlength("BLIND SPOT", font=f) + 50
            d.rounded_rectangle((nx - tw / 2, ny - 210, nx + tw / 2, ny - 140), radius=35, fill=RED + (255,))
            d.text((nx, ny - 175), "BLIND SPOT", font=f, fill=WHITE, anchor="mm")
            return None
        if kind == "arrow" and tl < 1.1:                 # Kidomaru vise
            im.paste(self.bg_red)
            self.char(im, "kidomaru", 540, H + 60, 1500, t, tl / 0.25)
            return ("TARGET", "BLIND SPOT", WHITE)
        if kind == "arrow":
            tl -= 1.1
            ay = 1000 + 70 + 700 * (1 - ease(min(1, tl / 0.9)))
            self.topdown(im, 540, 1000, 348, t, blind_col=RED, arrow=(540, ay))
            if tl > 0.9:
                k = tl - 0.9
                if k < 0.15:
                    flash(im, 255, 80, 80, int(160 * (1 - k / 0.15)))
            return ("BLIND SPOT", "FOUND", RED)
        if kind == "choice":
            for j, (x0, lab, col) in enumerate(((60, "BYAKUGAN", LAV), (560, "SHARINGAN", RED))):
                k = back(min(1, max(0, (tl - 0.15 * j) / 0.35)))
                if k <= 0:
                    continue
                pw, ph = 460, 820
                pm = Image.new("L", (pw, ph), 0)
                ImageDraw.Draw(pm).rounded_rectangle((0, 0, pw - 1, ph - 1), radius=44, fill=255)
                bgp = Image.new("RGBA", (pw, ph), (16, 26, 58, 255))
                if j == 0:
                    e = self.png("hinata_close", 1150)
                    bgp.alpha_composite(e, (int(pw / 2 - e.width / 2), int(ph / 2 - e.height * 0.62)))
                else:
                    e = self.png("sasuke_close", 1150)
                    bgp.alpha_composite(e, (int(pw / 2 - e.width / 2), int(ph / 2 - e.height * 0.55)))
                panel = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
                panel.paste(bgp, (0, 0), pm)
                dd = ImageDraw.Draw(panel)
                dd.rounded_rectangle((0, 0, pw - 1, ph - 1), radius=44, outline=col + (255,), width=6)
                dd.ellipse((pw / 2 - 52, 30, pw / 2 + 52, 134), fill=col + (255,))
                dd.text((pw / 2, 82), str(j + 1), font=m.P("Bold", 70), fill=(14, 16, 30), anchor="mm")
                dd.text((pw / 2, ph - 70), lab, font=m.P("Bold", 52), fill=WHITE, anchor="mm", stroke_width=3, stroke_fill=(8, 12, 30))
                if k != 1:
                    panel = panel.resize((max(1, int(pw * k)), max(1, int(ph * k))), Image.BILINEAR)
                im.alpha_composite(panel, (int(x0 + pw / 2 - panel.width / 2), int(1000 - panel.height / 2)))
            return None
        return super().scene(im, kind, q, t, tl, dur)


if __name__ == "__main__":
    a = sys.argv[1:]
    print(v.main(a[0], a[1], "--preview" in a, show_cls=ByakuganShow))
