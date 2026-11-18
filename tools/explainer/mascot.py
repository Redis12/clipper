"""Mascotte ORIGINALE de la chaîne (18/11) : « Lore », un garçon en sweat bleu canard avec un casque autour du cou.
Dessinée en code (formes simples, contour noir, aplats), style cartoon plat. Ce n'est la copie d'aucun perso.
mascot(expr, arm) → image RGBA ; expr = neutral | smug | shocked | scared | happy | wink ; arm = down | point | up
"""
from __future__ import annotations

from functools import lru_cache

from PIL import Image, ImageDraw

S = 2                                   # dessin à ×2 puis réduit (bords lisses)
W0, H0 = 520, 940
INK = (22, 20, 28)
SKIN = (255, 214, 178)
SKIN_D = (236, 184, 148)
HAIR = (34, 30, 44)
HOOD = (22, 160, 170)
HOOD_D = (14, 120, 130)
PANTS = (52, 56, 78)
SHOE = (245, 245, 250)
PHONES = (250, 250, 255)
ACC = (255, 200, 40)


def _r(v):
    return [int(x * S) for x in v]


@lru_cache(maxsize=64)
def mascot(expr: str = "neutral", arm: str = "down") -> Image.Image:
    im = Image.new("RGBA", (W0 * S, H0 * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    lw = 7 * S

    def poly(pts, fill):
        d.polygon([(x * S, y * S) for x, y in pts], fill=fill, outline=INK)
        d.line([(x * S, y * S) for x, y in pts + [pts[0]]], fill=INK, width=lw, joint="curve")

    def ell(box, fill):
        d.ellipse(_r(box), fill=fill, outline=INK, width=lw)

    def rrect(box, rad, fill):
        d.rounded_rectangle(_r(box), radius=rad * S, fill=fill, outline=INK, width=lw)

    # jambes + chaussures
    rrect((175, 700, 248, 880), 22, PANTS)
    rrect((272, 700, 345, 880), 22, PANTS)
    rrect((150, 860, 252, 915), 24, SHOE)
    rrect((268, 860, 370, 915), 24, SHOE)
    # bras (derrière le corps quand baissés)
    if arm == "down":
        rrect((108, 470, 168, 720), 28, HOOD_D)
        rrect((352, 470, 412, 720), 28, HOOD_D)
        ell((104, 690, 172, 758), SKIN)
        ell((348, 690, 416, 758), SKIN)
    # corps (sweat)
    rrect((140, 440, 380, 730), 70, HOOD)
    poly([(190, 600), (330, 600), (318, 690), (202, 690)], HOOD_D)          # poche ventrale
    d.line(_r((232, 470, 226, 560)), fill=INK, width=5 * S)                  # cordons
    d.line(_r((288, 470, 294, 560)), fill=INK, width=5 * S)
    ell((218, 552, 236, 570), PHONES)
    ell((284, 552, 302, 570), PHONES)
    if arm == "point":                                                        # bras droit tendu vers la droite
        rrect((108, 470, 168, 720), 28, HOOD_D)
        ell((104, 690, 172, 758), SKIN)
        poly([(352, 470), (500, 410), (514, 456), (372, 540)], HOOD_D)
        ell((484, 396, 540, 452), SKIN)
    elif arm == "up":                                                         # les deux bras en l'air (panique)
        poly([(150, 480), (70, 330), (112, 312), (186, 470)], HOOD_D)
        poly([(370, 480), (450, 330), (408, 312), (334, 470)], HOOD_D)
        ell((52, 276, 116, 340), SKIN)
        ell((404, 276, 468, 340), SKIN)
    # casque autour du cou
    d.arc(_r((150, 380, 370, 500)), 200, 340, fill=INK, width=24 * S)
    d.arc(_r((150, 380, 370, 500)), 200, 340, fill=PHONES, width=14 * S)
    ell((132, 420, 186, 486), PHONES)
    ell((334, 420, 388, 486), PHONES)
    # cou + tête
    rrect((226, 390, 294, 460), 14, SKIN_D)
    ell((120, 90, 400, 420), SKIN)
    ell((104, 230, 146, 300), SKIN)                                           # oreilles
    ell((374, 230, 416, 300), SKIN)
    # cheveux (mèches arrondies, pas de pointes)
    hair = [(122, 230), (118, 160), (150, 108), (210, 76), (290, 72), (352, 100), (396, 150), (400, 232),
            (370, 196), (338, 168), (300, 186), (262, 150), (226, 184), (186, 160), (150, 200)]
    poly(hair, HAIR)
    # visage
    ex = {"neutral": "open", "smug": "half", "shocked": "big", "scared": "big", "happy": "smile", "wink": "wink"}[expr]
    for k, cx in enumerate((205, 315)):
        if ex == "big":
            ell((cx - 34, 218, cx + 34, 292), (255, 255, 255))
            ell((cx - 12, 240, cx + 12, 266), INK)
        elif ex == "half":
            ell((cx - 26, 232, cx + 26, 282), (255, 255, 255))
            ell((cx - 10, 246, cx + 10, 270), INK)
            d.rectangle(_r((cx - 32, 222, cx + 32, 252)), fill=SKIN)
            d.line(_r((cx - 30, 252, cx + 30, 252)), fill=INK, width=6 * S)
        elif ex == "smile" or (ex == "wink" and k == 1):
            d.arc(_r((cx - 26, 236, cx + 26, 278)), 200, 340, fill=INK, width=8 * S)
        else:
            ell((cx - 24, 230, cx + 24, 284), (255, 255, 255))
            ell((cx - 10, 246, cx + 10, 270), INK)
        if expr in ("smug", "shocked", "scared", "neutral", "wink"):        # sourcils
            dy = {"smug": -8, "shocked": -26, "scared": -20, "neutral": -12, "wink": -14}[expr]
            tilt = {"smug": (10, -6), "scared": (-10, 10)}.get(expr, (0, 0))
            a, b = (tilt if k == 0 else tilt[::-1])
            d.line(_r((cx - 28, 214 + dy + a, cx + 28, 214 + dy + b)), fill=HAIR, width=10 * S)
    # bouche
    if expr in ("shocked", "scared"):
        ell((232, 322, 288, 374), (120, 30, 40))
    elif expr == "smug":
        d.arc(_r((228, 300, 300, 350)), 10, 120, fill=INK, width=7 * S)
    elif expr in ("happy", "wink"):
        d.chord(_r((214, 296, 306, 366)), 0, 180, fill=(120, 30, 40), outline=INK, width=6 * S)
    else:
        d.line(_r((238, 334, 282, 334)), fill=INK, width=7 * S)
    if expr == "scared":                                                       # goutte de sueur
        poly([(392, 180), (380, 214), (404, 214)], (140, 200, 255))
    ell((176, 300, 206, 322), (255, 170, 160))                                 # joues
    ell((314, 300, 344, 322), (255, 170, 160))
    out = im.resize((W0, H0), Image.LANCZOS)
    return out


if __name__ == "__main__":
    import sys
    exprs = ["neutral", "smug", "shocked", "scared", "happy", "wink"]
    arms = ["down", "point", "down", "up", "down", "point"]
    sheet = Image.new("RGBA", (W0 * 6, H0), (60, 60, 70, 255))
    for i, (e, a) in enumerate(zip(exprs, arms)):
        m = mascot(e, a)
        sheet.paste(m, (i * W0, 0), m)
    sheet.convert("RGB").save(sys.argv[1] if len(sys.argv) > 1 else "mascot_sheet.png")
