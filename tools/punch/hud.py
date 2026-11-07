"""Textes « faits main » pour les vidéos stickman (07/11, l'utilisateur : « le texte, on dirait de l'IA »).

Au lieu du titre centré Anton blanc/jaune + contour : polices cartoon (fontsource, OFL : Luckiest Guy, Bangers,
Lilita One, Titan One), ombre portée en relief, léger angle, cartouches. 3 styles : a (cartoon 3D), b (BD / manga),
c (HUD de jeu).
"""
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONTS = Path(__file__).resolve().parents[1] / "money_sim/fonts"
_cache = {}


def font(name, size):
    k = (name, size)
    if k not in _cache:
        _cache[k] = ImageFont.truetype(str(FONTS / name), size)
    return _cache[k]


def text3d(layer, xy, txt, f, fill, side=(40, 20, 60), depth=10, outline=(20, 10, 30), ow=6, anchor="mm"):
    """Texte avec relief (copies décalées) + contour, façon titre de cartoon."""
    d = ImageDraw.Draw(layer)
    x, y = xy
    for k in range(depth, 0, -1):
        d.text((x + k * 0.6, y + k), txt, font=f, fill=side, anchor=anchor, stroke_width=ow, stroke_fill=side)
    d.text((x, y), txt, font=f, fill=fill, anchor=anchor, stroke_width=ow, stroke_fill=outline)


def rotated(base, layer, angle, center):
    r = layer.rotate(angle, resample=Image.BICUBIC, center=center)
    base.alpha_composite(r)


def burst(d, cx, cy, rx, ry, n=18, fill=(255, 220, 40), outline=(20, 10, 10), w=8, seed=0):
    pts = []
    for i in range(n * 2):
        a = math.pi * i / n
        k = 1.0 if i % 2 == 0 else 0.78 + 0.06 * ((i * 7 + seed) % 3)
        pts.append((cx + math.cos(a) * rx * k, cy + math.sin(a) * ry * k))
    d.polygon(pts, fill=fill, outline=outline, width=w)


def draw(img, style, down, total=1000, title=("1 PUNCH", "VS 1000 STICKMEN"), pulse=1.0, sub="KO"):
    """img RGB → RGB avec le titre + compteur."""
    W = img.width
    base = img.convert("RGBA")
    L = Image.new("RGBA", base.size, (0, 0, 0, 0))
    col = (255, 255, 255) if down < total - 1 else ((255, 80, 80) if down == total - 1 else (110, 255, 140))
    if style == "a":                                   # cartoon 3D, un peu penché
        text3d(L, (W / 2, 120), title[0], font("luckiest-guy.woff2", 150), (255, 255, 255), side=(30, 60, 140),
               depth=12, outline=(20, 20, 50), ow=7)
        text3d(L, (W / 2, 240), title[1], font("luckiest-guy.woff2", 72), (255, 214, 50), side=(150, 70, 10),
               depth=8, outline=(40, 15, 5), ow=5)
        rotated(base, L, 3, (W / 2, 180))
        L = Image.new("RGBA", base.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(L)
        d.rounded_rectangle((W / 2 - 230, 318, W / 2 + 230, 450), 40, fill=(20, 22, 40, 225), outline=(255, 255, 255),
                            width=6)
        f = font("luckiest-guy.woff2", int(92 * pulse))
        d.text((W / 2 + 40, 388), f"{down}", font=f, fill=col, anchor="mm")
        d.text((W / 2 - 150, 390), sub, font=font("luckiest-guy.woff2", 54), fill=(255, 214, 50), anchor="mm")
        base.alpha_composite(L)
    elif style == "b":                                 # BD / manga : explosion jaune, Bangers
        d = ImageDraw.Draw(L)
        burst(d, W / 2, 175, 470, 165, n=20, fill=(255, 225, 40), w=9)
        f1 = font("bangers.woff2", 150)
        d.text((W / 2 + 8, 140 + 8), title[0], font=f1, fill=(20, 10, 10), anchor="mm")
        d.text((W / 2, 140), title[0], font=f1, fill=(230, 40, 40), anchor="mm", stroke_width=6, stroke_fill=(20, 10, 10))
        d.text((W / 2, 245), title[1], font=font("bangers.woff2", 74), fill=(20, 10, 10), anchor="mm")
        rotated(base, L, -4, (W / 2, 175))
        L = Image.new("RGBA", base.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(L)
        d.polygon([(W / 2 - 220, 360), (W / 2 + 240, 340), (W / 2 + 225, 470), (W / 2 - 235, 480)], fill=(255, 255, 255),
                  outline=(20, 10, 10), width=8)
        f = font("bangers.woff2", int(100 * pulse))
        c2 = (20, 10, 10) if down < total - 1 else col
        d.text((W / 2 + 4, 412), f"{down} / {total}", font=f, fill=c2, anchor="mm",
               stroke_width=3 if down >= total - 1 else 0, stroke_fill=(20, 10, 10))
        base.alpha_composite(L)
    else:                                              # HUD de jeu : cartouche en haut + score façon arcade
        d = ImageDraw.Draw(L)
        d.rounded_rectangle((60, 70, W - 60, 290), 34, fill=(255, 255, 255, 240))
        d.rounded_rectangle((60, 270, W - 60, 300), 14, fill=(0, 0, 0, 40))
        d.text((W / 2, 135), title[0], font=font("lilita-one.woff2", 118), fill=(235, 60, 50), anchor="mm")
        d.text((W / 2, 235), title[1], font=font("lilita-one.woff2", 68), fill=(30, 35, 60), anchor="mm")
        f = font("titan-one.woff2", int(110 * pulse))
        d.text((W / 2 + 6, 410 + 8), f"{down}", font=f, fill=(0, 0, 0, 90), anchor="mm")
        d.text((W / 2, 410), f"{down}", font=f, fill=col, anchor="mm", stroke_width=7, stroke_fill=(25, 25, 45))
        d.text((W / 2, 492), f"/ {total} KNOCKED OUT", font=font("lilita-one.woff2", 40), fill=(255, 255, 255),
               anchor="mm", stroke_width=4, stroke_fill=(25, 25, 45))
        base.alpha_composite(L)
    return base.convert("RGB")


def label(img, xy, txt, size=96, style="a", fill=(255, 80, 80), angle=0):
    """Gros mot isolé (« 1 LEFT... », « FLAWLESS ») dans le même style."""
    base = img.convert("RGBA")
    L = Image.new("RGBA", base.size, (0, 0, 0, 0))
    fname = {"a": "luckiest-guy.woff2", "b": "bangers.woff2"}.get(style, "titan-one.woff2")
    text3d(L, xy, txt, font(fname, size), fill, side=(60, 20, 20), depth=max(4, size // 14), outline=(20, 10, 10),
           ow=max(4, size // 22))
    if angle:
        L = L.rotate(angle, resample=Image.BICUBIC, center=xy)
    base.alpha_composite(L)
    return base.convert("RGB")
