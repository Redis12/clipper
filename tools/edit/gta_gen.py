"""Carrousel « V vs VI » (12/11, tendance GTA 6, idée de l'utilisateur d'après un post du FC Bayern) : en haut l'ancienne
génération (Naruto), en bas son « équivalent » de la nouvelle (JJK). 4 paires choisies par l'utilisateur. Grille 2×2 par slide (1080×1350, 4:5) :
chiffre romain | perso. Logos GTA V / VI fournis par l'utilisateur (library/_brand/gta/, détourés du faux damier), sinon chiffres à notre style : « V » sur une ville au
crépuscule, « VI » sur un coucher de soleil rose/violet. Têtes recadrées par faces.head_square.
python3 tools/edit/gta_gen.py dossier_sortie
"""
import math
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from clipper.slides import faces  # noqa: E402

L = ROOT / "library"
N, J = L / "Naruto", L / "Jujutsu Kaisen"
ANTON = str(ROOT / "tools/money_sim/fonts/anton.woff2")
W, H = 1080, 1350
GAP, RAD = 14, 26
PW, PH = (W - 3 * GAP) // 2, (H - 3 * GAP) // 2

PAIRS = [
    ("Naruto", L / "_fusion/Naruto/3 Base.jpg", "Yuji", J / "Yuji Itadori/Yuji.jpg"),
    ("Sasuke", N / "Sasuke/Sasuke.jpg", "Megumi", J / "Megumi Fushiguro/megumi.jpg"),
    ("Kakashi", N / "Kakashi/Kakashi.jpg", "Gojo", J / "Satoru Gojo/gojo.png"),
    ("Sakura", N / "Sakura/Sakura.jpg", "Nobara", J / "Nobara Kugisaki/nobara.png"),
]


def grad(w, h, stops):
    """dégradé vertical (liste de (position 0-1, couleur))"""
    im = Image.new("RGB", (w, h))
    px = im.load()
    for y in range(h):
        t = y / (h - 1)
        for i in range(len(stops) - 1):
            if stops[i][0] <= t <= stops[i + 1][0]:
                a, ca = stops[i]
                b, cb = stops[i + 1]
                k = (t - a) / (b - a or 1)
                c = tuple(int(ca[j] + (cb[j] - ca[j]) * k) for j in range(3))
                break
        for x in range(w):
            px[x, y] = c
    return im


def panel_v():
    """ville au crépuscule (silhouettes d'immeubles dessinées) + « V » blanc"""
    im = grad(PW, PH, [(0, (232, 150, 120)), (0.45, (190, 110, 120)), (0.75, (80, 60, 90)), (1, (30, 28, 45))])
    d = ImageDraw.Draw(im)
    rnd = random.Random(5)
    x = 0
    while x < PW:
        bw = rnd.randint(22, 60)
        bh = rnd.randint(90, 300) if abs(x - PW * 0.35) > 60 else rnd.randint(260, 380)
        d.rectangle((x, PH - bh, x + bw, PH), fill=(28, 26, 40))
        for wy in range(PH - bh + 10, PH - 10, 18):
            for wx in range(x + 5, x + bw - 6, 11):
                if rnd.random() < 0.25:
                    d.rectangle((wx, wy, wx + 4, wy + 6), fill=(255, 200, 120))
        x += bw + rnd.randint(0, 6)
    logo(im, "gta5") or numeral(im, "V", (255, 255, 255), (20, 20, 30))
    return im


def panel_vi():
    """coucher de soleil rose/violet + palmiers en silhouette + « VI »"""
    im = grad(PW, PH, [(0, (150, 110, 220)), (0.5, (235, 130, 190)), (1, (255, 180, 150))])
    d = ImageDraw.Draw(im, "RGBA")
    d.ellipse((PW * 0.25, PH * 0.55, PW * 0.75, PH * 1.05), fill=(255, 220, 170, 150))
    for bx, s in ((PW * 0.08, 1.0), (PW * 0.9, 0.8)):
        top = (bx + 30 * s, PH * 0.25)
        d.line([(bx, PH), (bx + 15 * s, PH * 0.6), top], fill=(120, 60, 110, 230), width=int(16 * s))
        for a in range(0, 360, 40):
            r = math.radians(a)
            d.line([top, (top[0] + math.cos(r) * 120 * s, top[1] + math.sin(r) * 50 * s + 30 * s)],
                   fill=(120, 60, 110, 230), width=int(14 * s))
    logo(im, "gta6") or numeral(im, "VI", (255, 255, 255), (90, 30, 90))
    return im


def logo(im, name):
    """logo fourni par l'utilisateur (library/_brand/gta/<name>.png, détouré) ; False s'il n'existe pas"""
    p = L / "_brand/gta" / f"{name}.png"
    if not p.is_file():
        return False
    lg = Image.open(p).convert("RGBA")
    k = PW * 0.88 / lg.width
    lg = lg.resize((int(lg.width * k), int(lg.height * k)), Image.LANCZOS)
    x, y = (PW - lg.width) // 2, int(PH * 0.45 - lg.height / 2)
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sh.paste((0, 0, 0, 255), (x + 6, y + 10), lg.getchannel("A"))
    sh = sh.filter(ImageFilter.GaussianBlur(10))
    sh.putalpha(sh.getchannel("A").point(lambda v: int(v * 0.5)))
    im.paste(sh, (0, 0), sh)
    im.paste(lg, (x, y), lg)
    return True


def numeral(im, s, fill, stroke):
    f = ImageFont.truetype(ANTON, 300)
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).text((PW / 2, PH * 0.45), s, font=f, fill=fill + (255,), anchor="mm", stroke_width=14,
                             stroke_fill=stroke + (255,))
    sh = lay.filter(ImageFilter.GaussianBlur(10))
    im.paste((0, 0, 0), (0, 0), sh.getchannel("A").point(lambda v: int(v * 0.5)))
    im.paste(lay, (0, 0), lay)


def portrait(path, name):
    src = Image.open(path).convert("RGB")
    sq = faces.head_square(src, path)
    sq = sq.resize((PH, PH), Image.LANCZOS)
    x0 = (PH - PW) // 2
    im = sq.crop((x0, 0, x0 + PW, PH))
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(ANTON, 54)
    d.text((PW / 2, PH - 50), name.upper(), font=f, fill=(255, 255, 255), anchor="mm", stroke_width=6,
           stroke_fill=(10, 10, 14))
    return im


def rounded(im):
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, im.width - 1, im.height - 1), radius=RAD, fill=255)
    out = im.convert("RGBA")
    out.putalpha(m)
    return out


def slide(a, pa, b, pb):
    img = Image.new("RGBA", (W, H), (12, 12, 16, 255))
    for (im, col, row) in ((PV, 0, 0), (portrait(pa, a), 1, 0), (PVI, 0, 1), (portrait(pb, b), 1, 1)):
        r = rounded(im)
        img.alpha_composite(r, (GAP + col * (PW + GAP), GAP + row * (PH + GAP)))
    from clipper.slides import render as R
    return R.watermark(img.convert("RGB"), vertical=False)


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    PV, PVI = panel_v(), panel_vi()
    for i, (a, pa, b, pb) in enumerate(PAIRS, 1):
        slide(a, pa, b, pb).save(out / f"{i:02d}_{a}_vs_{b}.jpg", quality=93)
        print(i, a, b)
