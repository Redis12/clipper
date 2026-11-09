"""Facts n°2 (09/11) : « Could Saitama survive Beerus' Hakai? » — même moteur que facts.py (voix Adam, sous-titres,
fond néon). Beerus = capture du modèle Stick Nodes fournie par l'utilisateur (library/_sticknodes/Dragon Ball/
beerus_still.png, découpée sur fond en dégradé), regarde à gauche. Faits vérifiés : Hakai de Beerus sur Zamasu
(arc Future Trunks), Vegeta plus fort que l'énergie de destruction de Toppo (DBS ép. 126), Boros : Collapsing Star
Roaring Cannon annulé par le Serious Punch (OPM).
python3 beerus.py sortie.mp4
"""
import math
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import facts as F  # noqa: E402
from facts import W, YEL, RED, WHITE, CYAN, font, glow_text, pill, ease_out, back_out, rim  # noqa: E402

PUR = (190, 110, 255)
GRN = (110, 230, 140)

BEATS = [
    dict(say="Saitama has never been hurt. Not once. But Beerus doesn't need to hurt you. He erases you.",
         tag="ONE PUNCH vs HAKAI", title=("COULD SAITAMA", "SURVIVE HAKAI?"), col=(WHITE, PUR), vis="versus",
         sfx=[]),
    dict(say="Hakai is the signature move of a God of Destruction. One gesture, and the target is gone. Body and soul.",
         tag="WHAT IS HAKAI?", title=("BODY AND SOUL", "ERASED"), col=(WHITE, PUR), vis="hakai",
         sfx=[(1.6, "timestop", 0.25, 1), (2.0, "ko", 0.3, 2)]),
    dict(say="Beerus used it on Zamasu, a Supreme Kai in training. One second later, there was nothing left.",
         tag="IT ALREADY HAPPENED", title=("A GOD IN TRAINING", "GONE"), col=(GRN, WHITE), vis="zamasu",
         sfx=[(1.2, "ko", 0.3, 4)]),
    dict(say="But Hakai has a weakness. In the Tournament of Power, Toppo threw destruction energy at Vegeta, and Vegeta overpowered it with raw power.",
         tag="THE WEAKNESS", title=("HAKAI CAN BE", "OVERPOWERED"), col=(YEL, CYAN), vis="clash",
         sfx=[(0.4, "clash", 0.25, 1)]),
    dict(say="Now look at Saitama. He broke his limiter. His power has no ceiling.",
         tag="NO LIMITER", title=("NO CEILING", ""), col=(YEL, WHITE), vis="nolimit",
         sfx=[(0.3, "transform", 0.2, 3)]),
    dict(say="Boros fired a blast he said would wipe out the surface of the Earth. Saitama cancelled it with one serious punch.",
         tag="PROOF", title=("SERIOUS", "PUNCH"), col=(WHITE, YEL), vis="boros",
         sfx=[(0.2, "beam", 0.25, 2)]),
    dict(say="So the real question is this: is Hakai an unbreakable rule, or is it just energy? Because if it's energy, Saitama punches it away.",
         tag="THE REAL QUESTION", title=("RULE", "OR ENERGY?"), col=(PUR, YEL), vis="rule", sfx=[]),
    dict(say="So be honest. Does Hakai erase Saitama, or does he not even notice? Erased or unbothered? One word below.",
         tag="I'M WAITING", title=("ERASED OR", "UNBOTHERED?"), col=(PUR, YEL), vis="final", sfx=[]),
]


class Actors(F.Actors):
    def __init__(self):
        super().__init__()
        b = Image.open(F.LIB / "_sticknodes/Dragon Ball/beerus_still.png").convert("RGBA")
        k = 600 / b.height
        b = b.resize((round(b.width * k), round(b.height * k)), Image.LANCZOS)
        self.beerus = ([b], [b.height])
        self.vegeta = self.icon(F.LIB / "_fusion/Vegeta/5 SSJBLUE.jpg", 300, (90, 170, 255))


def aura(img, cx, cy, col, u, r=220):
    rim(img, cx, cy, r * 0.9, r * 1.5, col, 0.65 + 0.15 * math.sin(u * 5))


def sphere(img, cx, cy, r, col, u):
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.ellipse((cx - r * 1.6, cy - r * 1.6, cx + r * 1.6, cy + r * 1.6), fill=col + (120,))
    lay = lay.filter(ImageFilter.GaussianBlur(max(2, r * 0.5)))
    d = ImageDraw.Draw(lay)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col + (255,))
    d.ellipse((cx - r * 0.6, cy - r * 0.6, cx + r * 0.6, cy + r * 0.6), fill=(255, 240, 255, 255))
    rnd = random.Random(int(u * 24))
    for _ in range(6):
        a = rnd.uniform(0, 6.28)
        d.arc((cx - r * 1.25, cy - r * 1.25, cx + r * 1.25, cy + r * 1.25), math.degrees(a), math.degrees(a) + 40,
              fill=(255, 255, 255, 200), width=4)
    img.alpha_composite(lay)


def dust(img, x0, x1, ycut, u, seed, col=PUR, n=40):
    """particules qui s'envolent de la ligne d'effacement"""
    d = ImageDraw.Draw(img, "RGBA")
    rnd = random.Random(seed)
    for _ in range(n):
        x = rnd.uniform(x0, x1)
        age = (u * 1.6 + rnd.random()) % 1.0
        y = ycut - age * rnd.uniform(120, 320)
        x += math.sin(age * 6 + x) * 18
        r = rnd.uniform(3, 8) * (1 - age)
        d.rectangle((x - r, y - r, x + r, y + r), fill=col + (int(255 * (1 - age)),))


def erase(img, im, x, ground, frac, u, seed, col=PUR):
    """`im` effacé de haut en bas (frac 0 → 1), particules au bord"""
    if frac >= 1:
        return
    im = im.copy()
    h = im.height
    ycut = int(h * frac)
    a = im.getchannel("A")
    ImageDraw.Draw(a).rectangle((0, 0, im.width, ycut), fill=0)
    im.putalpha(a)
    ox, oy = int(x - im.width / 2), int(ground - h)
    img.alpha_composite(im, (ox, oy))
    if frac > 0:
        lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(lay).rectangle((ox, oy + ycut - 6, ox + im.width, oy + ycut + 6), fill=col + (230,))
        img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(6)))
        dust(img, ox + 20, ox + im.width - 20, oy + ycut, u, seed, col)


# ------------------------------------------------------------------------------------------------- visuels
def vis_versus(img, A, u, f, dur=0):
    rim(img, 300, 1100, 200, 330, (255, 180, 40), 0.7)
    aura(img, 790, 1050, PUR, u)
    s = ease_out(u / 0.4)
    A.put(img, A.sai["saitama_debout"], f, 300 - 200 * (1 - s))
    A.put(img, A.beerus, 0, 800 + 200 * (1 - s))
    if u > 0.25:
        sc = back_out((u - 0.25) / 0.3)
        glow_text(img, (W / 2, 1000), "VS", font("anton.woff2", int(150 * max(0.01, sc))), WHITE, glow=(255, 60, 120))


def vis_hakai(img, A, u, f, dur):
    aura(img, 300, 1050, PUR, u)
    A.put(img, A.beerus, 0, 300)
    t_g = dur * 0.3                                                       # le geste : sphère au bout de la main
    if u > t_g:
        k = ease_out((u - t_g) / 0.4)
        sphere(img, 440, 800, 36 * k + 4 * math.sin(u * 20), PUR, u)
    # la cible : une silhouette grise effacée de haut en bas
    tgt = A.gok["debout_regarde"]
    fr = tgt[0][f % len(tgt[0])]
    sil = Image.new("RGBA", fr.size, (70, 70, 90, 0))
    sil.putalpha(fr.getchannel("A"))
    t_e = dur * 0.42
    frac = ease_out((u - t_e) / 1.3) if u > t_e else 0
    erase(img, sil, 780, 1310, frac, u, 7)
    if u < t_e:
        pill(img, 780, 620, "TARGET", (200, 200, 220))
    if frac >= 1:
        glow_text(img, (780, 1050), "GONE", font("anton.woff2", int(140 * back_out((u - t_e - 1.3) / 0.3) + 1)), PUR,
                  glow=(120, 40, 200))


def vis_zamasu(img, A, u, f, dur):
    aura(img, 790, 1050, PUR, u)
    A.put(img, A.beerus, 0, 800)
    t_e = dur * 0.25
    frac = ease_out((u - t_e) / 1.0) if u > t_e else 0
    card = Image.new("RGBA", (440, 300), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle((4, 4, 436, 296), radius=30, fill=(14, 30, 22, 235), outline=GRN + (255,), width=6)
    d.text((220, 110), "ZAMASU", font=font("anton.woff2", 96), fill=GRN, anchor="mm")
    d.text((220, 200), "SUPREME KAI", font=font("mont900.woff2", 34), fill=(220, 240, 225), anchor="mm")
    d.text((220, 245), "IN TRAINING", font=font("mont900.woff2", 34), fill=(220, 240, 225), anchor="mm")
    erase(img, card, 300, 1150, frac, u, 3, GRN)
    if frac >= 1:
        glow_text(img, (300, 1000), "0", font("anton.woff2", int(200 * back_out((u - t_e - 1.0) / 0.3) + 1)), PUR,
                  glow=(120, 40, 200))
        ImageDraw.Draw(img).text((300, 1130), "LEFT", font=font("anton.woff2", 60), fill=PUR, anchor="mm",
                                 stroke_width=5, stroke_fill=(10, 6, 20))


def vis_clash(img, A, u, f, dur):
    vx, tx, y = 230, 900, 900
    ic = A.vegeta
    rim(img, vx, y, 200, 200, (60, 140, 255), 0.7)
    img.alpha_composite(ic, (vx - ic.width // 2, y - ic.height // 2))
    # point de contact : d'abord au milieu, puis repoussé vers Toppo
    p = 0.5 + 0.08 * math.sin(u * 7) * (1 - ease_out(u / (dur * 0.5)))
    if u > dur * 0.5:
        p = 0.5 + 0.38 * ease_out((u - dur * 0.5) / (dur * 0.35))
    cxp = vx + (tx - vx) * p
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rectangle((vx + 120, y - 46, cxp, y + 46), fill=(80, 170, 255, 230))
    d.rectangle((cxp, y - 40, tx, y + 40), fill=PUR + (230,))
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(10)))
    ImageDraw.Draw(img).rectangle((vx + 120, y - 14, cxp, y + 14), fill=(230, 245, 255))
    sphere(img, cxp, y, 70, (150, 120, 255), u)
    sphere(img, tx, y, 60, PUR, u)
    d = ImageDraw.Draw(img, "RGBA")
    d.text((vx, y + 210), "VEGETA", font=font("anton.woff2", 60), fill=(120, 190, 255), anchor="mm", stroke_width=5,
           stroke_fill=(10, 6, 20))
    d.text((tx, y + 210), "TOPPO", font=font("anton.woff2", 60), fill=PUR, anchor="mm", stroke_width=5,
           stroke_fill=(10, 6, 20))
    d.text((W / 2 + 60, y - 210), "RAW POWER  vs  DESTRUCTION", font=font("mont900.woff2", 34), fill=WHITE, anchor="mm")
    if u > dur * 0.85:
        glow_text(img, (W / 2, 1220), "OVERPOWERED", font("anton.woff2", int(110 * back_out((u - dur * 0.85) / 0.3) + 1)),
                  CYAN, glow=(40, 120, 255))


def vis_nolimit(img, A, u, f, dur):
    rim(img, 330, 1100, 200, 330, (255, 180, 40), 0.8)
    A.put(img, A.sai["saitama_debout"], f, 330)
    d = ImageDraw.Draw(img, "RGBA")
    bx, y0, y1 = 700, 640, 1260
    fill = ease_out(u / max(0.8, dur * 0.55))
    d.rounded_rectangle((bx, y0, bx + 90, y1), radius=45, outline=YEL + (255,), width=6, fill=(10, 8, 24, 200))
    d.rounded_rectangle((bx + 12, y1 - 12 - (y1 - y0 - 24) * fill, bx + 78, y1 - 12), radius=33, fill=YEL + (255,))
    lim = y0 + (y1 - y0) * 0.45                                           # le « plafond » qui casse
    if fill < 0.55:
        d.line((bx - 40, lim, bx + 130, lim), fill=RED + (255,), width=8)
        d.text((bx + 150, lim), "LIMIT", font=font("anton.woff2", 50), fill=RED, anchor="lm", stroke_width=4,
               stroke_fill=(10, 6, 20))
    else:
        k = ease_out((fill - 0.55) / 0.2)
        for s_ in (-1, 1):
            d.line((bx - 40 - 30 * k, lim + s_ * 40 * k, bx + 40, lim), fill=RED + (int(255 * (1 - k)),), width=8)
        glow_text(img, (bx + 45, y0 - 70), "∞", F.ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                                                                      int(130 * max(0.05, k))), YEL, glow=(255, 160, 0))


def vis_boros(img, A, u, f, dur):
    rim(img, 300, 1100, 200, 330, (255, 180, 40), 0.7)
    armer, tendu = A.sai["saitama_poing_armer"], A.sai["saitama_poing_tendu"]
    t_hit = dur * 0.62
    by = 1010
    # le rayon de Boros arrive de la droite
    head = W + 20 - (W + 20 - 470) * ease_out(u / t_hit)
    if u < t_hit + 0.05:
        lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        wdt = 70 + 10 * math.sin(u * 30)
        d.rectangle((head, by - wdt, W + 50, by + wdt), fill=(90, 160, 255, 220))
        d.ellipse((head - wdt, by - wdt, head + wdt, by + wdt), fill=(90, 160, 255, 220))
        img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(14)))
        ImageDraw.Draw(img).rectangle((head, by - 22, W + 50, by + 22), fill=(230, 245, 255))
        pill(img, 820, 760, "BOROS: EARTH-ENDING BLAST", (120, 180, 255), font("mont900.woff2", 28))
        A.put(img, armer, int(min(1, u / t_hit) * (len(armer[0]) - 1)), 300)
    else:
        A.put(img, tendu, min(len(tendu[0]) - 1, int((u - t_hit) * 24)), 330)
        k = (u - t_hit) / 0.6
        if k < 1:                                                         # le rayon se disperse
            lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            d = ImageDraw.Draw(lay)
            rnd = random.Random(5)
            for _ in range(40):
                a = rnd.uniform(-0.9, 0.9)
                L = rnd.uniform(200, 700) * ease_out(k)
                d.line((500, by, 500 + math.cos(a) * L, by + math.sin(a) * L), fill=(150, 200, 255, int(255 * (1 - k))),
                       width=6)
            img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(3)))
            img.alpha_composite(Image.new("RGBA", img.size, (255, 255, 255, int(200 * max(0, 1 - k * 3)))))
        glow_text(img, (760, 1180), "CANCELLED", font("anton.woff2", int(110 * back_out((u - t_hit) / 0.3) + 1)), YEL,
                  glow=(255, 150, 0))


def vis_rule(img, A, u, f, dur):
    d = ImageDraw.Draw(img, "RGBA")
    cards = [(270, PUR, "RULE", ("SAITAMA", "ERASED")), (810, YEL, "ENERGY", ("ONE PUNCH", "IT'S OVER"))]
    for i, (cx, col, h, (l1, l2)) in enumerate(cards):
        a = ease_out((u - i * dur * 0.45) / 0.35)
        if a <= 0:
            continue
        y = 900 + 60 * (1 - a)
        d.rounded_rectangle((cx - 230, y - 260, cx + 230, y + 260), radius=34, fill=(12, 8, 26, int(230 * a)),
                            outline=col + (int(255 * a),), width=7)
        d.text((cx, y - 170), "IF HAKAI IS", font=font("mont900.woff2", 32), fill=(200, 200, 225, int(255 * a)), anchor="mm")
        d.text((cx, y - 90), h, font=font("anton.woff2", 110), fill=col + (int(255 * a),), anchor="mm")
        d.line((cx, y - 20, cx, y + 40), fill=(220, 220, 240, int(200 * a)), width=6)
        d.polygon([(cx - 20, y + 30), (cx + 20, y + 30), (cx, y + 60)], fill=(220, 220, 240, int(200 * a)))
        d.text((cx, y + 120), l1, font=font("anton.woff2", 66), fill=WHITE + (int(255 * a),), anchor="mm")
        d.text((cx, y + 195), l2, font=font("anton.woff2", 66), fill=col + (int(255 * a),), anchor="mm")
    glow_text(img, (W / 2, 900), "?", font("anton.woff2", 120), WHITE, glow=(140, 60, 255))


def vis_final(img, A, u, f, dur):
    rim(img, 300, 1100, 200, 330, (255, 180, 40), 0.7)
    aura(img, 790, 1050, PUR, u)
    A.put(img, A.sai["saitama_debout"], f, 300)
    A.put(img, A.beerus, 0, 800)
    d = ImageDraw.Draw(img, "RGBA")
    for (bx, col, lab) in ((80, YEL, "ONE PUNCH"), (W - 150, PUR, "HAKAI")):
        d.rounded_rectangle((bx, 720, bx + 70, 1260), radius=35, outline=col + (255,), width=6, fill=(10, 8, 24, 200))
        h = 520 * (0.92 + 0.06 * math.sin(u * 5 + bx))
        d.rounded_rectangle((bx + 10, 1250 - h, bx + 60, 1250), radius=25, fill=col + (255,))
        d.text((bx + 35, 1300), lab, font=font("mont900.woff2", 26), fill=col, anchor="mm")
    rnd = random.Random(int(u * 20))
    pts = [(400, 980)] + [(400 + i * 36, 980 + rnd.uniform(-40, 40)) for i in range(1, 9)] + [(690, 980)]
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).line(pts, fill=(220, 190, 255, 255), width=8)
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(5)))
    ImageDraw.Draw(img).line(pts, fill=WHITE, width=3)
    if u > dur * 0.55:
        pill(img, W / 2, 1390, "ONE WORD", YEL, font("mont900.woff2", 34), ease_out((u - dur * 0.55) / 0.3))


VIS = dict(versus=vis_versus, hakai=vis_hakai, zamasu=vis_zamasu, clash=vis_clash, nolimit=vis_nolimit, boros=vis_boros,
           rule=vis_rule, final=vis_final)

if __name__ == "__main__":
    F.render(sys.argv[1], BEATS, VIS, Actors, music_start=40)
