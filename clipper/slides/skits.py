"""Sketches du Gauntlet (20/11, « Joseph vs every anime » : un gag par adversaire).

Un adversaire `{"skit": "<nom>", "lines": [(début, fin, "hero"|"foe", texte)…]}` : pendant son gag, `pose()`
déplace / tourne les persos et `draw()` ajoute les accessoires (Death Note, lettre, lunettes, table, volcan…).
Les temps sont en secondes depuis le début du gag ; `dur` = durée du gag (après : état final, pendant le K.O.)."""
from __future__ import annotations

import math
import random

from PIL import Image, ImageDraw, ImageOps

from . import render


def _ease(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def _back(x: float) -> float:
    x = min(1.0, max(0.0, x))
    c = 1.70158
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def _seg(age: float, a: float, b: float) -> float:
    return min(1.0, max(0.0, (age - a) / max(1e-6, b - a)))


def pose(name: str, age: float, dur: float, ctx: dict) -> dict:
    """Décalages d'affichage : fdx, fdy, frot, fflip, fhide, keep (garder le perso pendant le K.O.), hdx, hdy,
    hhide, goggles (0–1), hbob."""
    k, S = ctx["k"], ctx["S"]
    p = dict(fdx=0.0, fdy=0.0, frot=0.0, fflip=False, fhide=False, keep=False, hdx=0.0, hdy=0.0, hhide=False,
             goggles=0.0, hbob=0.0, hscale=1.0)
    if age < dur:                                               # Joseph en plus gros pendant le sketch (lisible)
        p["hscale"] = 1 + 0.45 * _ease(_seg(age, 0.0, 0.25)) * (1 - _ease(_seg(age, dur - 0.3, dur)))
    fx, fy, R, hx, hy = ctx["fx"], ctx["fy"], ctx["R"], ctx["hx"], ctx["hy"]
    if name == "deathnote" and dur - 0.45 < age < dur:
        p["fdx"] = 9 * k * math.sin(age * 70)                       # crise cardiaque
    elif name == "lost":
        q = _seg(age, 1.5, dur)
        p["fdx"] = -(fx - ctx["ox"] + R * 1.3) * q * q
        if 0 < q < 1:
            p["fdy"] = -abs(math.sin(age * 16)) * 10 * k
        p["fhide"] = age >= dur
    elif name == "letter":
        q = _seg(age, 2.0, 2.45)
        p["frot"] = 88 * _ease(q)
        p["fdy"] = R * 0.55 * _ease(q)
        p["keep"] = True
    elif name == "copy":
        q = _seg(age, 1.45, dur)
        p["fdx"] = -(fx - ctx["ox"] + R * 1.3) * q * q
        if age < dur:
            p["hdx"] = (ctx["ox"] + S * 1.35 - hx) * q * q
        if 0 < q < 1:
            p["fdy"] = p["hdy"] = -abs(math.sin(age * 20)) * 10 * k
        p["fhide"] = age >= dur
    elif name == "goggles":
        p["goggles"] = _ease(_seg(age, 0.55, 0.9))
    elif name == "crying":
        if 0.6 < age < dur:
            p["hbob"] = -abs(math.sin(age * math.pi * 2.6)) * 12 * k
    elif name == "eat":
        p["keep"] = True
        if age > 1.9:
            p["fdy"] = math.sin(age * 22) * 6 * k
    elif name == "lookbehind":
        p["fflip"] = age >= 0.7
        q = _ease(_seg(age, 1.45, 1.8))
        if age < dur:
            tx, ty = fx + R + ctx["rh"], fy
            p["hdx"], p["hdy"] = (tx - hx) * q, (ty - hy) * q
    elif name == "zawarudo":
        if 1.0 < age < 2.6:
            p["fflip"] = int((age - 1.0) / 0.38) % 2 == 1
        out_ = _ease(_seg(age, 0.3, 0.75))
        back = _ease(_seg(age, 2.7, dur - 0.08))
        tx, ty = fx + R + ctx["rh"], fy
        off_x = ctx["ox"] + S * 1.35
        if age < dur:
            if back <= 0:
                p["hdx"] = (off_x - hx) * out_ * out_
            else:
                p["hdx"] = (off_x + (tx - off_x) * back) - hx
                p["hdy"] = (ty - hy) * back
    return p


def _bubble_lines(name, age, dur, foe):
    return [(a, b, who, txt) for (a, b, who, txt) in foe.get("lines", []) if a <= age < b]


def _book(img, cx, cy, k, open_q, text, nch, font):
    d = ImageDraw.Draw(img, "RGBA")
    if open_q <= 0:
        w, h = 120 * k, 165 * k
        d.rounded_rectangle((cx - w / 2 + 6 * k, cy - h / 2 + 8 * k, cx + w / 2 + 6 * k, cy + h / 2 + 8 * k),
                            radius=int(8 * k), fill=(0, 0, 0, 120))
        d.rounded_rectangle((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), radius=int(8 * k), fill=(18, 18, 20),
                            outline=(200, 200, 210), width=int(3 * k))
        f_ = font(max(6, int(24 * k)))
        d.text((cx, cy - 20 * k), "DEATH", font=f_, anchor="mm", fill=(235, 235, 240))
        d.text((cx, cy + 12 * k), "NOTE", font=f_, anchor="mm", fill=(235, 235, 240))
        return
    pw, ph = 150 * k, 200 * k
    d.rounded_rectangle((cx - pw + 8 * k, cy - ph / 2 + 10 * k, cx + pw + 8 * k, cy + ph / 2 + 10 * k),
                        radius=int(8 * k), fill=(0, 0, 0, 120))
    d.rounded_rectangle((cx - pw - 8 * k, cy - ph / 2 - 6 * k, cx + pw + 8 * k, cy + ph / 2 + 6 * k),
                        radius=int(10 * k), fill=(18, 18, 20))
    for sx in (-1, 1):
        x0, x1 = (cx - pw, cx - 3 * k) if sx < 0 else (cx + 3 * k, cx + pw)
        d.rectangle((x0, cy - ph / 2, x1, cy + ph / 2), fill=(246, 244, 236))
        for j in range(7):
            yy = cy - ph / 2 + 30 * k + j * 24 * k
            d.line((x0 + 10 * k, yy, x1 - 10 * k, yy), fill=(190, 200, 215), width=max(1, int(2 * k)))
    f_ = font(int(30 * k))
    words = text.split()
    shown = text[:nch]
    parts = shown.split(" ") if shown else []
    for j, w_ in enumerate(parts):
        d.text((cx + pw / 2 + 2 * k, cy - 28 * k + j * 42 * k), w_, font=f_, anchor="mm", fill=(25, 20, 30))
    _ = words


def _heart(d, x, y, s, col):
    d.ellipse((x - s, y - s * 0.6, x, y + s * 0.4), fill=col)
    d.ellipse((x, y - s * 0.6, x + s, y + s * 0.4), fill=col)
    d.polygon([(x - s * 0.98, y), (x + s * 0.98, y), (x, y + s * 1.15)], fill=col)


def _envelope(img, cx, cy, k, rot=0.0):
    w, h = 130 * k, 88 * k
    e = Image.new("RGBA", (int(w + 20 * k), int(h + 20 * k)), (0, 0, 0, 0))
    d = ImageDraw.Draw(e)
    o = 10 * k
    d.rounded_rectangle((o, o, o + w, o + h), radius=int(8 * k), fill=(255, 196, 214), outline=(120, 30, 60),
                        width=int(3 * k))
    d.line((o, o, o + w / 2, o + h * 0.55, o + w, o), fill=(120, 30, 60), width=int(3 * k))
    _heart(d, o + w / 2, o + h * 0.52, 17 * k, (230, 30, 70))
    if rot:
        e = e.rotate(rot, resample=Image.BICUBIC, expand=True)
    img.alpha_composite(e, (int(cx - e.width / 2), int(cy - e.height / 2)))


def _goggles(img, hx, hy, hs, k, q):
    """Lunettes d'aviateur de Joseph : descendent du front sur les yeux."""
    if q <= 0:
        return
    ey = hy - hs * 0.06 - (1 - q) * hs * 0.32
    cx = hx - hs * 0.04
    r = hs * 0.15
    d = ImageDraw.Draw(img, "RGBA")
    d.line((hx - hs * 0.47, ey, hx + hs * 0.45, ey), fill=(70, 45, 25, 255), width=int(9 * k))
    for sx in (-1, 1):
        x = cx + sx * r * 1.08
        d.ellipse((x - r * 1.12, ey - r * 1.12, x + r * 1.12, ey + r * 1.12), fill=(120, 80, 40, 255))
        d.ellipse((x - r, ey - r, x + r, ey + r), fill=(110, 200, 255, 215))
        d.ellipse((x - r * 0.55, ey - r * 0.7, x - r * 0.1, ey - r * 0.3), fill=(255, 255, 255, 200))
    d.rectangle((cx - r * 0.25, ey - r * 0.2, cx + r * 0.25, ey + r * 0.2), fill=(120, 80, 40, 255))


def _speedlines(d, x, y, R, k, side, age):
    rnd = random.Random(int(age * 12))
    for j in range(5):
        yy = y + (j - 2) * R * 0.35
        ln = R * rnd.uniform(0.6, 1.3)
        x0 = x - side * R * 1.05
        d.line((x0, yy, x0 - side * ln, yy), fill=(255, 255, 255, 200), width=int(5 * k))


def _dust(d, x, y, k, q, seed):
    rnd = random.Random(seed)
    for j in range(6):
        rr = (14 + 26 * q) * k * rnd.uniform(0.7, 1.3)
        xx = x + rnd.uniform(-40, 40) * k
        yy = y + rnd.uniform(-12, 12) * k - 30 * k * q
        a = int(200 * (1 - q))
        d.ellipse((xx - rr, yy - rr, xx + rr, yy + rr), fill=(230, 225, 215, a))


def draw(name: str, age: float, dur: float, ctx: dict, img: Image.Image) -> None:
    """Accessoires du sketch (dessinés après les persos, avant les bulles)."""
    k, font = ctx["k"], ctx["font"]
    fx, fy, R, hx, hy, hs = ctx["fx"], ctx["fy"], ctx["R"], ctx["hx"], ctx["hy"], ctx["hs"]
    d = ImageDraw.Draw(img, "RGBA")
    if name == "deathnote":
        txt = ctx["foe"].get("note_text", "Light Yagami")
        sx, sy = fx + R * 1.15, fy + R * 0.25
        tx, ty = hx - hs * 1.85, hy + hs * 0.2
        if age < 0.9:
            s_ = 1.0 if age < 0.2 else _back(_seg(age, 0.2, 0.35))   # visible dès l'image 0
            if s_ > 0.05:
                _book(img, sx, sy, k * s_, 0, "", 0, font)
        elif age < 1.3:
            q = _ease(_seg(age, 0.9, 1.3))
            _book(img, sx + (tx - sx) * q, sy + (ty - sy) * q - math.sin(q * math.pi) * 90 * k, k, 0, "", 0, font)
        else:
            nch = int(len(txt) * _seg(age, 1.4, 2.2))
            _book(img, tx, ty, k, 1, txt, nch, font)
            if age < 2.25:                                        # le stylo qui écrit
                px = tx + 150 * k / 2 + 2 * k + (nch % 6 - 3) * 10 * k
                py = ty - 28 * k + (1 if nch > 5 else 0) * 42 * k
                d.line((px + 8 * k, py - 6 * k, px + 50 * k, py - 52 * k), fill=(30, 30, 40), width=int(8 * k))
                d.polygon([(px, py), (px + 12 * k, py - 4 * k), (px + 8 * k, py - 12 * k)], fill=(30, 30, 40))
    elif name == "lost":
        q = _back(_seg(age, 0.2, 0.45))
        if age < dur and q > 0:                                    # grosse flèche jaune vers la sortie
            ax, ay = hx - hs * 0.9, hy - hs * 0.05
            L_, T_ = 170 * k * q, 46 * k * q
            blink = 1.0 if int(age * 6) % 2 == 0 or age > 1.4 else 0.75
            col = (255, 214, 10, int(255 * blink))
            d.rectangle((ax - L_ + 60 * k * q, ay - T_ / 2, ax, ay + T_ / 2), fill=col, outline=(0, 0, 0), width=int(4 * k))
            d.polygon([(ax - L_, ay), (ax - L_ + 70 * k * q, ay - 62 * k * q), (ax - L_ + 70 * k * q, ay + 62 * k * q)],
                      fill=col, outline=(0, 0, 0))
        if 1.5 < age < dur:
            _dust(d, fx + R * 0.9, fy + R * 0.9, k, (age * 3) % 1, int(age * 3))
    elif name == "letter":
        if 0.15 < age < 0.95:
            q = _ease(_seg(age, 0.15, 0.9))
            ex = hx + (fx + R * 0.95 - hx) * q
            ey = hy - hs * 0.4 + (fy + R * 0.75 - hy + hs * 0.4) * q - math.sin(q * math.pi) * 160 * k
            _envelope(img, ex, ey, k, rot=20 * math.sin(age * 10))
        elif age >= 0.95 and age < 2.0:
            _envelope(img, fx + R * 0.95, fy + R * 0.75, k, rot=-12)
        if 0.95 < age:
            rnd = random.Random(3)
            for j in range(9):                                    # cœurs qui montent
                ph = (age * 0.8 + j / 9) % 1
                xx = fx + rnd.uniform(-1.1, 1.1) * R
                yy = fy - R * 0.4 - ph * R * 1.3
                s_ = (16 + 10 * rnd.random()) * k * (1 - ph * 0.4)
                _heart(d, xx, yy, s_, (255, 70 + int(60 * rnd.random()), 140, int(255 * (1 - ph))))
        if age > 1.55:                                            # saignement de nez : 2 jets en fontaine
            q = _seg(age, 1.55, 1.8)
            rot = math.radians(ctx["pose"]["frot"])
            ox_, oy_ = -0.06 * R, 0.12 * R
            nx_ = fx + ox_ * math.cos(rot) + oy_ * math.sin(rot)
            ny_ = fy + ctx["pose"]["fdy"] - ox_ * math.sin(rot) + oy_ * math.cos(rot)
            for sx, spread in ((-1, 0.55), (1, 0.75)):
                pts = []
                for j in range(12):
                    u = j / 11 * q
                    pts.append((nx_ + sx * u * R * spread, ny_ - u * R * 0.75 + u * u * R * 1.1))
                d.line(pts, fill=(215, 15, 25, 255), width=int(9 * k), joint="curve")
            rnd = random.Random(int(age * 14))
            for j in range(8):                                    # gouttes
                xx = nx_ + rnd.uniform(-0.8, 0.8) * R
                yy = ny_ + rnd.uniform(0.1, 0.9) * R
                r_ = rnd.uniform(4, 8) * k
                d.ellipse((xx - r_, yy - r_ * 1.3, xx + r_, yy + r_ * 1.3), fill=(215, 15, 25, 230))
            if age > 2.3:                                         # petite flaque
                pq = _ease(_seg(age, 2.3, 2.9))
                pw = R * 0.85 * pq
                py = fy + ctx["pose"]["fdy"] + R * 0.95
                d.ellipse((fx - pw, py - pw * 0.16, fx + pw, py + pw * 0.16), fill=(170, 0, 15, 220))
    elif name == "copy":
        q = _seg(age, 1.45, dur)
        if 0 < q < 1:
            _speedlines(d, fx + ctx["pose"]["fdx"], fy, R, k, -1, age)
            _speedlines(d, hx + ctx["pose"]["hdx"], hy, hs / 2, k, 1, age)
            _dust(d, fx + ctx["pose"]["fdx"] + R, fy + R * 0.8, k, (age * 4) % 1, int(age * 4))
            _dust(d, hx + ctx["pose"]["hdx"] - hs / 2, hy + hs * 0.4, k, (age * 4 + 0.5) % 1, int(age * 4) + 9)
    elif name == "goggles":
        if age < 1.25:                                            # Tsukuyomi : anneaux rouges
            a = int(150 * min(1.0, age / 0.2) * (1 - _seg(age, 0.9, 1.25)))
            for j in range(4):
                rr = R * (1.08 + 0.16 * j + 0.05 * math.sin(age * 9 + j))
                d.ellipse((fx - rr, fy - rr, fx + rr, fy + rr), outline=(230, 20, 30, a), width=int(7 * k))
            img.alpha_composite(Image.new("RGBA", img.size, (150, 0, 0, a // 2)))
        if 0.9 < age < 1.6:                                       # « tink » : le genjutsu rebondit sur les verres
            q = _seg(age, 0.9, 1.6)
            for j in range(8):
                an = j * math.pi / 4
                r0, r1 = hs * (0.35 + 0.4 * q), hs * (0.5 + 0.55 * q)
                d.line((hx + math.cos(an) * r0, hy - hs * 0.06 + math.sin(an) * r0,
                        hx + math.cos(an) * r1, hy - hs * 0.06 + math.sin(an) * r1),
                       fill=(255, 255, 255, int(255 * (1 - q))), width=int(5 * k))
    elif name == "crying":
        if age < dur:
            for sx in (-1, 1):                                    # torrents de larmes
                ex, ey = fx + sx * R * 0.24, fy - R * 0.02
                ln = R * (0.9 + 0.3 * math.sin(age * 6 + sx))
                pts = [(ex + sx * (j / 10) * R * 0.25 + math.sin(age * 25 + j) * 3 * k, ey + j / 10 * ln) for j in range(11)]
                d.line(pts, fill=(90, 180, 255, 230), width=int(16 * k), joint="curve")
                rnd = random.Random(int(age * 10) + sx)
                for j in range(4):
                    yy = ey + ln + rnd.uniform(0, R * 0.5)
                    xx = ex + sx * R * 0.25 + rnd.uniform(-20, 20) * k
                    d.ellipse((xx - 7 * k, yy - 9 * k, xx + 7 * k, yy + 9 * k), fill=(120, 200, 255, 220))
            if age > 0.6:                                         # Joseph tape du pied
                step = int((age - 0.6) * 2.6)
                if (age - 0.6) * 2.6 % 1 < 0.45:
                    f_ = font(int(34 * k))
                    tx = hx + (1 if step % 2 else -1) * hs * 0.45
                    d.text((tx, hy + hs * 0.62), "tap", font=f_, anchor="mm", fill=(255, 255, 255),
                           stroke_width=int(3 * k), stroke_fill=(0, 0, 0))
    elif name == "eat":
        q = _back(_seg(age, 1.0, 1.3))
        if q > 0:
            ty = fy + R * 1.02
            tw = R * 1.5 * q
            d.rectangle((fx - tw, ty, fx + tw, ty + 26 * k), fill=(150, 85, 40), outline=(60, 30, 10), width=int(4 * k))
            d.rectangle((fx - tw * 0.85, ty + 26 * k, fx - tw * 0.75, ty + 80 * k), fill=(110, 60, 25))
            d.rectangle((fx + tw * 0.75, ty + 26 * k, fx + tw * 0.85, ty + 80 * k), fill=(110, 60, 25))
            nb = int(min(14, max(0, (age - 1.7) * 7)))
            for j in range(nb):                                   # bols vides empilés
                col_, row = divmod(j, 7)
                bx_ = fx + tw * (0.62 if col_ == 0 else -0.62)
                by_ = ty - 2 * k - row * 22 * k
                d.chord((bx_ - 34 * k, by_ - 34 * k, bx_ + 34 * k, by_ + 14 * k), 0, 180, fill=(245, 245, 250),
                        outline=(40, 40, 60), width=int(3 * k))
                d.line((bx_ - 30 * k, by_ - 10 * k, bx_ + 30 * k, by_ - 10 * k), fill=(220, 60, 60), width=int(3 * k))
            if 1.3 < age:                                         # bol fumant devant lui
                for j in range(3):
                    sx_ = fx + (j - 1) * 22 * k
                    pts = [(sx_ + math.sin(age * 5 + j + u) * 8 * k, ty - 50 * k - u * 14 * k) for u in range(6)]
                    d.line(pts, fill=(255, 255, 255, 150), width=int(4 * k), joint="curve")
    elif name == "lookbehind":
        if 1.45 < age < 1.85:
            q = _seg(age, 1.45, 1.85)
            cx_, cy_ = hx + ctx["pose"]["hdx"], hy + ctx["pose"]["hdy"]
            for j in range(4):                                    # traînée du coup en traître
                u = j / 4
                d.line((cx_, cy_, cx_ + (hx - cx_) * (0.3 + u * 0.7), cy_ + (hy - cy_) * (0.3 + u * 0.7)),
                       fill=(255, 255, 255, int(150 * (1 - q))), width=int((30 - j * 6) * k))
    elif name == "zawarudo":
        if 0.3 < age < 0.9:                                       # il file avant que le temps s'arrête
            _dust(d, hx, hy + hs * 0.4, k, _seg(age, 0.3, 0.9), 7)
        if 0.55 < age < 2.75:
            f_ = font(int(46 * k))
            ImageDraw.Draw(img).text((hx, hy), "NIGERUNDAYO!", font=f_, anchor="mm", fill=(255, 214, 10),
                                     stroke_width=int(5 * k), stroke_fill=(0, 0, 0))
            sp_ = font(int(30 * k))
            ImageDraw.Draw(img).text((hx, hy + 48 * k), "(he ran away)", font=sp_, anchor="mm", fill=(255, 255, 255),
                                     stroke_width=int(3 * k), stroke_fill=(0, 0, 0))


def post(name: str, age: float, dur: float, img: Image.Image) -> Image.Image:
    """Effets plein écran (ZA WARUDO : le monde passe en négatif pendant que le temps est arrêté)."""
    if name == "zawarudo" and 0.85 < age < 2.7:
        a = min(1.0, (age - 0.85) / 0.15, (2.7 - age) / 0.12)
        rgb = img.convert("RGB")
        g = ImageOps.grayscale(rgb)
        lut = lambda c0, c1: [int(c0 + (c1 - c0) * (v / 255) ** 0.8) for v in range(256)]   # noqa: E731
        duo = Image.merge("RGB", [g.point(lut(40, 255)), g.point(lut(8, 235)), g.point(lut(70, 90))])
        if age < 1.0:                                             # flash négatif au moment de l'arrêt
            duo = ImageOps.invert(duo)
        return Image.blend(rgb, duo, a).convert("RGBA")
    return img


def volcano(img: Image.Image, a: float, ctx: dict, icon: Image.Image, kx: float, ky: float, kR: float) -> None:
    """Fin de Kars (comme dans l'anime) : le volcan entre en éruption et l'envoie dans l'espace."""
    k, ox, oy, S = ctx["k"], ctx["ox"], ctx["oy"], ctx["S"]
    d = ImageDraw.Draw(img, "RGBA")
    sky = _ease(_seg(a, 0.2, 0.5))
    if sky > 0:                                                   # le haut de la boîte devient l'espace
        sp = Image.new("RGBA", (int(S), int(S * 0.5)), (6, 4, 20, int(235 * sky)))
        ds = ImageDraw.Draw(sp)
        rnd = random.Random(5)
        for j in range(60):
            x, y = rnd.uniform(0, S), rnd.uniform(0, S * 0.5)
            r = rnd.uniform(1, 3) * k
            ds.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, int(220 * sky * rnd.uniform(0.4, 1))))
        img.alpha_composite(sp, (int(ox), int(oy)))
    rise = _ease(_seg(a, 0.0, 0.22))
    vx, vb = ox + S * 0.5, oy + S
    vh = S * 0.32 * rise
    vw = S * 0.36
    d.polygon([(vx - vw, vb), (vx - vw * 0.28, vb - vh), (vx + vw * 0.28, vb - vh), (vx + vw, vb)], fill=(70, 40, 35))
    d.polygon([(vx - vw * 0.28, vb - vh), (vx - vw * 0.12, vb - vh + 40 * k), (vx + vw * 0.05, vb - vh + 18 * k),
               (vx + vw * 0.28, vb - vh)], fill=(255, 110, 20))
    erupt = _seg(a, 0.18, 0.75)
    if 0 < erupt < 1:
        rnd = random.Random(int(a * 40))
        for j in range(26):                                       # lave qui jaillit
            u = rnd.random()
            x = vx + rnd.uniform(-1, 1) * vw * 0.35 * u
            y = vb - vh - u * S * 0.6 * erupt
            r = rnd.uniform(10, 26) * k
            d.ellipse((x - r, y - r, x + r, y + r), fill=(255, rnd.randint(80, 200), 20, 230))
    fly = _seg(a, 0.22, 0.72)                                     # Kars propulsé vers les étoiles
    if 0 < fly < 1:
        sz = max(8, int(kR * 2 * (1 - 0.88 * fly)))
        x = kx + (vx - kx) * min(1.0, fly * 3)
        y = (vb - vh) + (oy + S * 0.06 - (vb - vh)) * _ease(fly)
        d.line((x, y + sz * 0.5, x, min(vb - vh, y + sz * 2.5)), fill=(255, 160, 40, 200), width=max(4, sz // 3))
        img.alpha_composite(icon.resize((sz, sz)).rotate(fly * 720), (int(x - sz / 2), int(y - sz / 2)))
    elif fly >= 1:                                                # petit « ding » d'étoile
        tw = _seg(a, 0.72, 0.85)
        if tw < 1:
            r = 40 * k * math.sin(tw * math.pi)
            x, y = vx, oy + S * 0.06
            d.polygon([(x, y - r), (x + r * 0.25, y - r * 0.25), (x + r, y), (x + r * 0.25, y + r * 0.25), (x, y + r),
                       (x - r * 0.25, y + r * 0.25), (x - r, y), (x - r * 0.25, y - r * 0.25)], fill=(255, 255, 255))


def ora(img: Image.Image, e: float, x: float, y: float, k: float, font, box=None) -> None:
    """Défaite : « ORA ORA ORA » partout autour du perso (dans la boîte)."""
    rnd = random.Random(11)
    for j in range(18):
        t0 = j * 0.055
        if e < t0:
            break
        age = e - t0
        s_ = 1 + 0.5 * max(0.0, 1 - age / 0.1)
        ang = rnd.uniform(0, 2 * math.pi)
        dd = rnd.uniform(120, 330) * k
        f_ = font(int(rnd.uniform(64, 100) * k * s_))
        px, py = x + math.cos(ang) * dd, y + math.sin(ang) * dd * 0.8
        if box:
            px = min(max(px, box[0] + 80 * k), box[2] - 80 * k)
            py = min(max(py, box[1] + 50 * k), box[3] - 50 * k)
        ImageDraw.Draw(img).text((px, py), "ORA", font=f_, anchor="mm",
                                 fill=(170, 80, 255), stroke_width=int(5 * k), stroke_fill=(255, 255, 255))


__all__ = ["pose", "draw", "post", "volcano", "ora", "render"]
