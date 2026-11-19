"""Maquettes de DA « clean » (19/11) : même scène dans 3 styles, cadrage serré (sujet = 70-80 % de l'image).
python3 tools/explainer/da_mock.py sortie.png
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).parent))
import flat_assets as fa  # noqa: E402
from flat_style import F, W, H, ROOT  # noqa: E402

FLAT = ROOT / "library/_explainer/gojo_infinity/flat"
INK = fa.INK

STYLES = {
    "A · CLEAN CLAIR": dict(bg=(243, 240, 233), text=INK, accent=(30, 140, 235), hi=(30, 140, 235), sub=(120, 120, 135), dots=None),
    "B · NOIR MINIMAL": dict(bg=(11, 13, 22), text=(250, 250, 252), accent=(90, 200, 255), hi=(255, 205, 70), sub=(130, 140, 165), dots=None),
    "C · PAPIER MANGA": dict(bg=(250, 250, 248), text=INK, accent=INK, hi=(225, 50, 60), sub=(120, 120, 120), dots=(222, 222, 222)),
}


def png(name, h, flip=False):
    im = Image.open(FLAT / f"{name}.png").convert("RGBA")
    im = im.resize((int(im.width * h / im.height), int(h)), Image.LANCZOS)
    return im.transpose(Image.FLIP_LEFT_RIGHT) if flip else im


def scale(im, s):
    return im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)


def paste(base, im, cx, cy, anchor="mm"):
    y = cy - im.height / 2 if anchor == "mm" else cy - im.height
    base.paste(im, (int(cx - im.width / 2), int(y)), im)


def shadow(base, im, cx, cy, anchor, st, off=(18, 22)):
    """Ombre portée plate (silhouette décalée), pas de flou : c'est ce qui donne l'air « propre »."""
    a = im.getchannel("A").point(lambda v: 255 if v > 40 else 0)
    col = (0, 0, 0, 40) if st["bg"][0] > 128 else (0, 0, 0, 120)
    sh = Image.new("RGBA", im.size, col)
    sh.putalpha(a.point(lambda v: col[3] if v else 0))
    paste(base, sh, cx + off[0], cy + off[1], anchor)


def bg(st):
    im = Image.new("RGB", (W, H), st["bg"])
    if st["dots"]:
        d = ImageDraw.Draw(im)
        for y in range(0, H, 22):
            for x in range((y // 22) % 2 * 11, W, 22):
                d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=st["dots"])
    return im


def rings(d, cx, cy, st, n=4, r0=130, gap=48):
    for k in range(n - 1, -1, -1):
        r = r0 + gap * k
        if st["dots"]:
            d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=INK, width=6 if k == 0 else 4)
        else:
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=st["accent"] + (34 + 14 * (n - 1 - k),),
                      outline=st["accent"] + (255,), width=6)


def caption(d, st, words, hi_i, y=250):
    txt = " ".join(words)
    sz = 92
    while d.textlength(txt, font=F("mont900", sz)) > W - 110:
        sz -= 2
    f = F("mont900", sz)
    x = W / 2 - d.textlength(txt, font=f) / 2
    for i, w in enumerate(words):
        col = st["hi"] if i == hi_i else st["text"]
        d.text((x, y), w, font=f, fill=col, anchor="lm")
        x += d.textlength(w + " ", font=f)


def stat(d, st, label, value, y=1640):
    """Chiffre en gros, sans carte : étiquette fine au-dessus, valeur énorme."""
    d.text((W / 2, y - 70), label, font=F("mont800", 34), fill=st["sub"], anchor="mm")
    d.text((W / 2, y + 10), value, font=F("anton", 130), fill=st["hi"], anchor="mm")


def scene_palm(st):
    im = bg(st)
    d = ImageDraw.Draw(im, "RGBA")
    g = png("gojo_main", 1900)                         # Gojo remplit l'écran
    gx, gb = 470, H + 260
    shadow(im, g, gx, gb, "bottom", st)
    paste(im, g, gx, gb, "bottom")
    px, py = 175, 1230                                 # paume
    rings(d, px, py, st, n=4, r0=120, gap=46)
    fs = scale(fa.fist().transpose(Image.FLIP_LEFT_RIGHT), 1.35)
    fx = px + 120 + 3 * 46 + 70 + fs.width / 2
    shadow(im, fs, fx, py, "mm", st)
    paste(im, fs, fx, py)
    caption(d, st, ["ENDLESS", "SPACE", "BETWEEN"], 1)
    stat(d, st, "DISTANCE LEFT", "0.0000001 in")
    return im


def scene_you(st):
    im = bg(st)
    d = ImageDraw.Draw(im, "RGBA")
    cx, cy = 600, 1000
    rings(d, cx, cy, st, n=4, r0=260, gap=60)
    yu = scale(fa.you("smug"), 1.65)
    shadow(im, yu, cx, cy + 640, "bottom", st)
    paste(im, yu, cx, cy + 640, "bottom")
    fs = scale(fa.fist(), 1.35)
    fx = cx - 260 - 3 * 60 - 40 - fs.width / 2 + 120
    shadow(im, fs, fx, cy - 40, "mm", st)
    paste(im, fs, fx, cy - 40)
    caption(d, st, ["NEVER", "TOUCHES", "YOU"], 1)
    return im


def main(out):
    tiles = []
    for name, st in STYLES.items():
        for fn in (scene_you, scene_palm):
            t = fn(st).resize((540, 960), Image.LANCZOS)
            tiles.append((name, t))
    sheet = Image.new("RGB", (540 * 3 + 40 * 4, 960 * 2 + 150), (40, 40, 48))
    d = ImageDraw.Draw(sheet)
    for i, (name, t) in enumerate(tiles):
        c, r = i // 2, i % 2
        x, y = 40 + c * 580, 110 + r * 980
        sheet.paste(t, (x, y))
        if r == 0:
            d.text((x + 270, 60), name, font=F("anton", 52), fill=(255, 255, 255), anchor="mm")
    sheet.save(out)


if __name__ == "__main__":
    main(sys.argv[1])
