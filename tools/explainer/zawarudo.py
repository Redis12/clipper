"""« If you had ZA WARUDO » (19/11) — même moteur que Byakugan (infinity_v4) : DA bleu nuit + or, texte fin,
compteur, « 1 ou 2 », follow qui reboucle. Accent or/jaune (DIO). Le temps arrêté = le monde passe en négatif
(onde qui part de DIO) puis reste désaturé violet ; seuls DIO et Jotaro gardent leurs couleurs.
Persos = PNG Gemini détourés (fond vert, cœurs verts gardés) dans library/_explainer/zawarudo/simple/.
python3 tools/explainer/zawarudo.py tools/explainer/scripts/zawarudo_v1.json sortie.mp4 [--preview]
"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0, str(Path(__file__).parent))
import infinity_v4 as v  # noqa: E402
from infinity_v4 import GOLD, RED, WHITE, H, W, back, ease, flash, m  # noqa: E402

YEL = (255, 210, 70)
PURP = (190, 150, 255)


def stopped(im, k=1.0):
    """Look « temps arrêté » : désaturé + teinte violette (k = 0..1)."""
    if k <= 0:
        return im
    rgb = np.asarray(im.convert("RGB")).astype(np.float32)
    g = rgb.mean(-1, keepdims=True)
    tint = np.array([0.78, 0.70, 1.0], np.float32)
    st = g * tint * 0.9 + 10
    out = rgb * (1 - k) + st * k
    res = Image.fromarray(out.clip(0, 255).astype(np.uint8)).convert("RGBA")
    return res


def negative_wave(im, cx, cy, r):
    """Onde du ZA WARUDO : tout ce qui est dans le cercle passe en négatif."""
    if r <= 0:
        return im
    inv = ImageOps.invert(im.convert("RGB")).convert("RGBA")
    mk = Image.new("L", im.size, 0)
    ImageDraw.Draw(mk).ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
    out = im.copy()
    out.paste(inv, (0, 0), mk)
    ImageDraw.Draw(out).ellipse((cx - r, cy - r, cx + r, cy + r), outline=(255, 255, 255, 255), width=8)
    return out


def clock_img(size, minute):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = size / 2
    d.ellipse((4, 4, size - 4, size - 4), fill=(236, 232, 224), outline=(150, 130, 90), width=14)
    for k in range(12):
        a = math.radians(k * 30)
        r1, r2 = c * 0.72, c * 0.84
        d.line((c + r1 * math.sin(a), c - r1 * math.cos(a), c + r2 * math.sin(a), c - r2 * math.cos(a)), fill=(60, 50, 40), width=8 if k % 3 == 0 else 4)
    am = math.radians(minute * 6)
    ah = math.radians(10 * 30 + minute * 0.5)
    d.line((c, c, c + c * 0.45 * math.sin(ah), c - c * 0.45 * math.cos(ah)), fill=(40, 34, 30), width=14)
    d.line((c, c, c + c * 0.68 * math.sin(am), c - c * 0.68 * math.cos(am)), fill=(200, 40, 40), width=8)
    d.ellipse((c - 14, c - 14, c + 14, c + 14), fill=(40, 34, 30))
    return im


def knife(d, x, y, ang, L=150):
    ca, sa = math.cos(ang), math.sin(ang)

    def P(u, w):
        return (x + u * ca - w * sa, y + u * sa + w * ca)
    blade = [P(0, -12), P(L * 0.72, -14), P(L, 0), P(L * 0.72, 6), P(0, 10)]
    d.polygon(blade, fill=(214, 220, 232, 255))
    d.line([P(4, -2), P(L * 0.9, -2)], fill=(250, 252, 255, 255), width=3)
    d.rounded_rectangle([min(P(-60, -9)[0], P(0, 9)[0]), min(P(-60, -9)[1], P(0, 9)[1]),
                         max(P(-60, -9)[0], P(0, 9)[0]), max(P(-60, -9)[1], P(0, 9)[1])], radius=6, fill=(110, 70, 40, 255))
    d.line([P(0, -18), P(0, 18)], fill=(170, 150, 110, 255), width=8)


def bullet(d, x, y, s=1.0):
    d.rounded_rectangle((x - 40 * s, y - 13 * s, x + 20 * s, y + 13 * s), radius=int(12 * s), fill=(196, 150, 70, 255))
    d.ellipse((x + 4 * s, y - 13 * s, x + 44 * s, y + 13 * s), fill=(210, 170, 90, 255))
    for k in range(3):                                   # traits de vitesse figés
        d.line((x - 150 * s - k * 30, y - 8 + k * 8, x - 60 * s - k * 30, y - 8 + k * 8), fill=(255, 255, 255, 90), width=3)


class ZaWarudo(v.Show):
    boom_scenes = {"roller": 1.0, "clash": 0.8}
    scene_sounds = {
        "stop": [(0.25, "library/_sounds/jojo_villains/dio time stop.mp3", 0.55)],
        "walk": [(0.25 + 0.42 * i, "library/_sfx/Helton Yan's Old-School Shonen SFX/FGHTBf_Anime Land 3.ogg", 0.35) for i in range(6)],
        "ora": [(0.05 + 0.11 * i, "library/_sfx/Helton Yan's Old-School Shonen SFX/FGHTImpt_Anime Melee {}.ogg".format(1 + i % 7), 0.22) for i in range(18)],
        "moves": [(0.0, "library/_sfx/Helton Yan's Old-School Shonen SFX/FGHTImpt_Anime Melee 5.ogg", 0.3)],
    }

    def __init__(self, script):
        super().__init__(script)
        rnd = random.Random(5)
        self.drops = [(rnd.uniform(40, W - 40), rnd.uniform(380, 1560)) for _ in range(70)]
        self.knives = [(rnd.uniform(-0.4, 0.4)) for _ in range(9)]

    def pizza_parts(self):
        if "_pizza" not in self.cache:
            from scipy import ndimage
            pz = self.png("pizza", 900)
            a = np.asarray(pz.getchannel("A")) > 100
            lab, n = ndimage.label(a)
            parts = []
            for i, sl in enumerate(ndimage.find_objects(lab)):
                mk = Image.fromarray(((lab[sl] == i + 1) * 255).astype(np.uint8))
                piece = pz.crop((sl[1].start, sl[0].start, sl[1].stop, sl[0].stop))
                piece.putalpha(Image.fromarray(np.minimum(np.asarray(piece.getchannel("A")), np.asarray(mk))))
                ang = math.atan2((sl[0].start + sl[0].stop) / 2 - 450, (sl[1].start + sl[1].stop) / 2 - 450)
                parts.append((ang, piece, (sl[1].start, sl[0].start)))
            parts.sort(key=lambda p: p[0])
            self.cache["_pizza"] = [(p, b) for _, p, b in parts]
        return self.cache["_pizza"]

    def loop_counter(self):
        return ("TIME", "RUNNING", YEL)                  # = image 0 (boucle)

    # ------------------------------------------------------------------ scènes
    def scene(self, im, kind, q, t, tl, dur):
        d = ImageDraw.Draw(im, "RGBA")
        if kind in ("stop", "end"):
            ck = clock_img(520, 9 if kind == "end" else (9 + int(min(tl, 0.55) * 30)) % 60)
            im.alpha_composite(ck, (540 - 260, 760))
            band = self.png("dio_eyes", 1150).copy()
            band = band.crop((0, int(band.height * 0.30), band.width, int(band.height * 0.56)))
            mk = Image.new("L", band.size, 0)
            ImageDraw.Draw(mk).rounded_rectangle((30, 0, band.width - 30, band.height), radius=40, fill=255)
            band.putalpha(Image.fromarray(np.minimum(np.asarray(band.getchannel("A")), np.asarray(mk))))
            im.alpha_composite(band, (int(540 - band.width / 2), 400))
            if kind == "stop":                           # le temps s'arrête : onde en négatif puis monde figé
                t0 = 0.55
                if tl > t0:
                    k = (tl - t0) / 0.5
                    if k < 1:
                        out = negative_wave(im, 540, 1020, 1500 * ease(k))
                        im.paste(out)
                    else:
                        im.paste(stopped(im, min(1, (k - 1) * 2)))
                return ("TIME", "STOPPED" if tl > t0 else "RUNNING", YEL)
            im.paste(stopped(im, 1 - ease(q)))
            return None
        if kind == "late":                               # l'horloge bloquée à 8 h 59
            im.paste(stopped(im, 1))
            ck = clock_img(700, 59)
            im.alpha_composite(ck, (540 - 350, 640))
            return ("LATE", "NEVER", YEL)
        if kind == "pizza":                              # les 8 parts disparaissent une à une
            im.paste(stopped(im, 1))
            pz = self.pizza_parts()
            n = min(8, int(tl / max(0.2, (dur - 0.3) / 8)))
            for i, (part, box) in enumerate(pz):
                if i < n:
                    continue
                im.alpha_composite(part, (540 - 450 + box[0], 1000 - 450 + box[1]))
            if 0 < n <= 8:                               # petit « pop » sur la dernière mangée
                d.text((540, 480), "CHOMP!", font=m.P("Bold", 90), fill=YEL + (255,), anchor="mm", stroke_width=6, stroke_fill=(20, 14, 6))
            return ("SLICES LEFT", str(8 - n), YEL)
        if kind == "rain":                               # pluie figée (image Gemini), elle ne tombe pas
            im.paste(stopped(im, 1))
            r = self.png("raindrops", H - 420)                 # sous la zone du texte
            for x in range(-r.width // 2, W + r.width, r.width):
                im.alpha_composite(r, (int(x + 30 * math.sin(t * 0.3)), 420))
            return ("YOU GET WET", "0%", YEL)
        if kind == "bullet":
            im.paste(stopped(im, 1))
            if tl < 0.9:                                 # la balle ralentit puis s'arrête
                b = self.png("bullet", 330)
                x = -300 + 700 * (1 - (1 - min(1, tl / 0.9)) ** 3)
                im.alpha_composite(b, (int(x), 900))
                return ("BULLET SPEED", f"{int(1700 * (1 - min(1, tl / 0.9)) ** 2)} mph", YEL)
            hb = self.png("hand_bullet", 1000)
            k = back(min(1, (tl - 0.9) / 0.3))
            h2 = hb.resize((max(1, int(hb.width * k)), max(1, int(hb.height * k))), Image.BILINEAR)
            im.alpha_composite(h2, (int(540 - h2.width / 2), int(1000 - h2.height / 2)))
            return ("BULLET SPEED", "0 mph", YEL)
        if kind == "moves":                              # DIO choqué, l'écran tremble
            im.paste(stopped(im, 1))
            sh = 12 * math.exp(-tl * 3)
            self.char(im, "dio_shocked", 540 + sh * math.sin(t * 60), H + 60, 1400, t, tl / 0.15)
            return ("SOMEONE", "MOVED", RED)
        if kind == "walk":                               # Jotaro avance vers toi, pas lourds
            im.paste(stopped(im, 1))
            k = ease(min(1, tl / max(0.5, dur)))
            h = 1150 + 900 * k
            self.halo(im, 540, 1200, int(380 + 200 * k), (150, 110, 255), 80)
            jw = self.png("jotaro_walk", int(h))
            bob = 10 * abs(math.sin(tl * 5))
            im.alpha_composite(jw, (int(540 - jw.width / 2), int(H + 40 - h * 0.86 - bob)))
            return ("DISTANCE", f"{max(0.5, 6 * (1 - k)):.1f} m", PURP)
        if kind == "ora":                                # rafale de poings + ORA
            im.paste(stopped(im, 1))
            sp = self.png("star_platinum", 1350)
            rnd = random.Random(int(t * 20))
            fist = sp.crop((0, int(sp.height * 0.55), int(sp.width * 0.62), sp.height))
            for _ in range(7):                           # poings fantômes
                f2 = fist.copy()
                f2.putalpha(f2.getchannel("A").point(lambda a: int(a * 0.55)))
                im.alpha_composite(f2, (int(rnd.uniform(-120, 420)), int(rnd.uniform(650, 1250))))
            jx = rnd.uniform(-14, 14)
            im.alpha_composite(sp, (int(W - sp.width + 60 + jx), int(H + 60 - 1350 + rnd.uniform(-8, 8))))
            for i in range(5):
                x, y = rnd.uniform(120, 960), rnd.uniform(450, 1500)
                d.text((x, y), "ORA", font=m.P("Bold", int(rnd.uniform(70, 130))), fill=(235, 180, 255, 255), anchor="mm",
                       stroke_width=6, stroke_fill=(30, 10, 50))
            return ("HITS", f"{int(tl * 22)}", PURP)
        if kind == "five":
            im.paste(stopped(im, 1))
            self.char(im, "dio_face", 720, H + 60, 1200, t, tl / 0.3)
            left = max(0.0, 5.0 * (1 - tl / max(0.5, dur)))
            return ("TIME LEFT", f"{left:.1f} s", YEL)
        if kind == "frozen":
            for x, y in self.drops:                       # pluie figée
                d.line((x, y - 34, x, y), fill=(190, 210, 255, 220), width=5)
                d.ellipse((x - 6, y - 6, x + 6, y + 8), fill=(210, 230, 255, 240))
            bullet(d, 330, 760, 2.2)
            bullet(d, 760, 1020, 1.8)
            bullet(d, 460, 1260, 1.5)
            for i, a0 in enumerate(self.knives[:5]):
                knife(d, 160 + i * 180, 520 + (i % 2) * 110, math.pi / 2 + a0, 230)
            im.paste(stopped(im, 1))
            return ("MOVING", "0", YEL)
        if kind == "nobody":                              # couteaux en cercle autour de toi, figés
            im.paste(stopped(im, 1))
            k = ease(min(1, tl / 0.9))
            cx, cy = 540, 1000
            for i in range(12):
                a = i * math.pi / 6 + 0.2
                R = 460 - 60 * k
                x, y = cx + R * math.cos(a), cy + R * math.sin(a)
                knife(d, x, y, a + math.pi, 160)
            d.ellipse((cx - 70, cy - 70, cx + 70, cy + 70), outline=(255, 255, 255, 120), width=4)
            return ("WITNESSES", "0", YEL)
        if kind == "nine":
            im.paste(stopped(im, 1))
            self.halo(im, 700, 1150, 380, (200, 30, 40), 90)
            self.char(im, "dio_knives", 720, H + 60, 1200, t, tl / 0.3)
            n = 5 + 4 * ease(min(1, tl / 1.4))
            return ("TIME STOP", f"{n:.0f} s", RED if n > 8.5 else YEL)
        if kind == "roller":
            im.paste(stopped(im, 1))
            k = ease(min(1, tl / 1.0))
            rr = self.png("road_roller", 900)
            y = -600 + (1050 - -600) * k
            ang = -12 * (1 - k)
            r2 = rr.rotate(ang, resample=Image.BICUBIC, expand=True)
            im.alpha_composite(r2, (int(540 - r2.width / 2), int(y - r2.height / 2)))
            if tl > 1.0:
                f = m.P("Bold", 120)
                d.text((540, 560), "ROAD ROLLER!", font=f, fill=YEL + (255,), anchor="mm", stroke_width=8, stroke_fill=(20, 14, 6))
                if tl < 1.15:
                    flash(im, 255, 255, 255, int(160 * (1 - (tl - 1.0) / 0.15)))
            return ("WEIGHT", "HEAVY", YEL)
        if kind == "jotaro":                              # monde figé, Jotaro en couleur
            im.paste(stopped(im, 1))
            self.halo(im, 700, 1150, 400, (150, 110, 255), 90)
            self.char(im, "jotaro", 720, H + 60, 1250, t, tl / 0.3)
            return ("CAN MOVE", "JOTARO", PURP)
        if kind == "clash":
            im.paste(stopped(im, 1))
            k = ease(min(1, tl / 0.8))
            tw = self.png("the_world", 1250)
            sp = self.png("star_platinum", 1250, flip=True)
            im.alpha_composite(tw, (int(-tw.width * 0.45 + 300 * k), H + 60 - 1250))
            im.alpha_composite(sp, (int(W - sp.width * 0.55 - 300 * k), H + 60 - 1250))
            if tl > 0.8:
                hit = math.exp(-((tl - 0.85) / 0.08) ** 2)
                self.halo(im, 540, 900, int(120 + 80 * hit), (255, 220, 120), int(60 + 70 * hit))
                if hit > 0.05:
                    flash(im, 255, 255, 255, int(70 * hit))
            return ("STAND TYPE", "SAME", WHITE)
        if kind == "choice":
            for j, (x0, lab, col, name) in enumerate(((60, "DIO", YEL, "dio_face"), (560, "JOTARO", PURP, "jotaro"))):
                k = back(min(1, max(0, (tl - 0.15 * j) / 0.35)))
                if k <= 0:
                    continue
                pw, ph = 460, 820
                pm = Image.new("L", (pw, ph), 0)
                ImageDraw.Draw(pm).rounded_rectangle((0, 0, pw - 1, ph - 1), radius=44, fill=255)
                bgp = Image.new("RGBA", (pw, ph), (16, 26, 58, 255))
                e = self.png(name, 1500)
                yoff = -0.03
                bgp.alpha_composite(e, (int(pw / 2 - e.width / 2), int(e.height * yoff)))
                panel = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
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
        return super().scene(im, kind, q, t, tl, dur)


if __name__ == "__main__":
    a = sys.argv[1:]
    print(v.main(a[0], a[1], "--preview" in a, show_cls=ZaWarudo))
