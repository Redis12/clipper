"""Maquette DA v4 (19/11) « bleu nuit + or », vue à la 1re personne : le poing fonce vers TOI (la caméra).
Inspirée des qualités de « The math behind Gojo's Infinity » (plans serrés, un plan fil rouge, texte fin, or),
sans reprendre ses dessins : poing de face, barrière dorée devant l'écran, Gojo = PNG ChatGPT de l'utilisateur.
python3 tools/explainer/da_v4_mock.py <dossier_sortie>
"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
FLAT = ROOT / "library/_explainer/gojo_infinity/flat"
GF = Path("/usr/share/fonts/truetype/google-fonts")
W, H = 1080, 1920
GOLD = (255, 196, 84)
GOLD_L = (255, 228, 150)
WHITE = (245, 246, 250)
SUB = (150, 160, 190)
SK, SK_L, SK_D, SK_DD = (236, 186, 146), (252, 214, 178), (208, 154, 116), (176, 122, 90)


def P(w, sz):
    return ImageFont.truetype(str(GF / f"Poppins-{w}.ttf"), int(sz))


def background(seed=1, center=(0.5, 0.48)):
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((x - W * center[0]) / W) ** 2 + ((y - H * center[1]) / H * 0.75) ** 2) / 0.62
    c0, c1 = np.array([26, 42, 86], np.float32), np.array([5, 8, 20], np.float32)
    px = c0 + (c1 - c0) * np.clip(r, 0, 1)[..., None] ** 0.9
    im = Image.fromarray(px.astype(np.uint8)).convert("RGBA")
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    rnd = random.Random(seed)
    for _ in range(90):                                  # poussière d'étoiles très discrète
        sx, sy, s = rnd.uniform(0, W), rnd.uniform(0, H), rnd.choice((1.5, 2, 2, 3))
        d.ellipse((sx - s, sy - s, sx + s, sy + s), fill=(200, 210, 255, rnd.randint(40, 120)))
    im.alpha_composite(lay)
    return im


def grad_fill(size, top, bot, mask):
    """Remplit `mask` (L) d'un dégradé vertical top→bot (ombrage doux)."""
    h = size[1]
    t = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    g = np.array(top, np.float32) * (1 - t) + np.array(bot, np.float32) * t
    g = np.repeat(g, size[0], axis=1)
    im = Image.fromarray(g.astype(np.uint8)).convert("RGBA")
    im.putalpha(mask)
    return im


def soft_part(canvas, box, radius, top, bot, rim=None, hl=None):
    """Partie arrondie avec dégradé, liseré sombre fin et reflet clair flou (rendu « vectoriel doux »)."""
    m = Image.new("L", canvas.size, 0)
    ImageDraw.Draw(m).rounded_rectangle(box, radius=radius, fill=255)
    canvas.alpha_composite(grad_fill(canvas.size, top, bot, m))
    if hl:
        hm = Image.new("L", canvas.size, 0)
        x0, y0, x1, y1 = box
        ImageDraw.Draw(hm).rounded_rectangle((x0 + (x1 - x0) * 0.2, y0 + 10, x1 - (x1 - x0) * 0.2, y0 + (y1 - y0) * 0.32),
                                             radius=radius // 2, fill=110)
        hm = hm.filter(ImageFilter.GaussianBlur(10))
        hm = Image.fromarray(np.minimum(np.asarray(hm), np.asarray(m)))
        lay = Image.new("RGBA", canvas.size, hl + (0,))
        lay.putalpha(hm)
        canvas.alpha_composite(lay)
    if rim:
        ImageDraw.Draw(canvas).rounded_rectangle(box, radius=radius, outline=rim + (255,), width=5)


def ell_part(canvas, box, top, bot, rim=None, hl=None):
    m = Image.new("L", canvas.size, 0)
    ImageDraw.Draw(m).ellipse(box, fill=255)
    canvas.alpha_composite(grad_fill(canvas.size, top, bot, m))
    if hl:
        x0, y0, x1, y1 = box
        hm = Image.new("L", canvas.size, 0)
        ImageDraw.Draw(hm).ellipse((x0 + (x1 - x0) * 0.25, y0 + (y1 - y0) * 0.12, x1 - (x1 - x0) * 0.25, y0 + (y1 - y0) * 0.45), fill=120)
        hm = hm.filter(ImageFilter.GaussianBlur(8))
        lay = Image.new("RGBA", canvas.size, hl + (0,))
        lay.putalpha(Image.fromarray(np.minimum(np.asarray(hm), np.asarray(m))))
        canvas.alpha_composite(lay)
    if rim:
        ImageDraw.Draw(canvas).ellipse(box, outline=rim + (255,), width=4)


def fist_front(size=900):
    """Poing vu de face (jointures vers la caméra), dessin original : rangée de doigts repliés, bosses des
    jointures au-dessus, pouce replié en travers, ombrage doux, liseré fin couleur peau foncée (pas de noir)."""
    c = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    k = size / 900
    R = lambda *v: tuple(int(a * k) for a in v)  # noqa: E731
    soft_part(c, R(250, 640, 650, 900), int(50 * k), (34, 40, 70), (14, 16, 30))             # manche (au loin)
    soft_part(c, R(230, 470, 680, 720), int(110 * k), SK_D, SK_DD)                           # talon de la main
    soft_part(c, R(170, 210, 740, 420), int(100 * k), SK_L, SK, rim=SK_D)                    # dos de la main (haut)
    fx = [(180, 300, 150, 250), (325, 290, 150, 270), (470, 295, 148, 262), (612, 318, 130, 222)]
    for x, y, w, h in fx:                                                                    # doigts repliés (2es phalanges)
        soft_part(c, R(x, y, x + w, y + h), int(62 * k), SK, SK_D, rim=SK_DD, hl=(255, 236, 214))
        ImageDraw.Draw(c).arc(R(x + 24, y + h * 0.48, x + w - 24, y + h * 0.48 + 40), 200, 340, fill=SK_DD + (200,), width=max(2, int(4 * k)))
    for x, y, w, h in fx:                                                                    # jointures (bosses)
        ell_part(c, R(x + 14, y - 46, x + w - 14, y + 44), SK_L, SK, rim=SK_D, hl=(255, 244, 228))
    # pouce : part de la gauche et passe devant l'index et le majeur
    th = Image.new("RGBA", c.size, (0, 0, 0, 0))
    soft_part(th, R(120, 470, 520, 610), int(70 * k), SK_L, SK_D, rim=SK_DD, hl=(255, 236, 214))
    soft_part(th, R(410, 492, 505, 588), int(34 * k), (255, 226, 212), (236, 196, 182), rim=SK_D)  # ongle
    th = th.rotate(-8, resample=Image.BICUBIC, center=(320 * k, 540 * k))
    c.alpha_composite(th)
    return c


def fist_side(w=900):
    """Poing de profil qui vise la DROITE, dessin original, même ombrage doux que fist_front."""
    k = w / 900
    c = Image.new("RGBA", (w, int(600 * k)), (0, 0, 0, 0))
    R = lambda *v: tuple(int(a * k) for a in v)  # noqa: E731
    soft_part(c, R(0, 175, 360, 435), int(40 * k), (70, 74, 104), (34, 36, 56))           # manche
    soft_part(c, R(300, 130, 700, 475), int(140 * k), SK, SK_D)                            # dos de la main
    for i in range(4):                                                                     # doigts repliés empilés
        y = 128 + i * 86
        soft_part(c, R(585, y, 800 - (i == 3) * 30, y + 92), int(44 * k), SK_L, SK_D, rim=SK_D, hl=(255, 238, 218))
    soft_part(c, R(420, 350, 730, 470), int(58 * k), SK_L, SK_D, rim=SK_DD, hl=(255, 236, 214))  # pouce
    soft_part(c, R(655, 372, 722, 448), int(26 * k), (255, 226, 212), (236, 196, 182), rim=SK_D)  # ongle
    return c


def barrier(canvas, cx, cy, r, t=0.0, n=4):
    """L'Infini en vue 1re personne : fins anneaux dorés lumineux juste devant l'écran."""
    lay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for i in range(n):
        rr = r + i * 26 + 6 * math.sin(t * 3 + i)
        a = 230 - 45 * i
        for j in range(5):                                 # anneau en tirets (ondes)
            a0 = j * 72 + t * 30 + i * 18
            d.arc((cx - rr, cy - rr * 0.98, cx + rr, cy + rr * 0.98), a0, a0 + 52, fill=GOLD + (a,), width=6 - i)
    glow = lay.filter(ImageFilter.GaussianBlur(14))
    canvas.alpha_composite(glow)
    canvas.alpha_composite(glow)
    canvas.alpha_composite(lay)


def speed_lines(canvas, cx, cy, seed=4):
    lay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    rnd = random.Random(seed)
    for _ in range(40):
        a = rnd.uniform(0, 2 * math.pi)
        r0 = rnd.uniform(560, 700)
        r1 = r0 + rnd.uniform(120, 380)
        if cy + r1 * math.sin(a) < 460:                  # pas de traits sous le texte
            continue
        d.line((cx + r0 * math.cos(a), cy + r0 * math.sin(a), cx + r1 * math.cos(a), cy + r1 * math.sin(a)),
               fill=(170, 190, 240, rnd.randint(40, 110)), width=3)
    canvas.alpha_composite(lay)


def caption(canvas, parts, y=270):
    """Texte fin blanc centré, un mot en gras : parts = [("If you had", False), ("Infinity", True)]."""
    d = ImageDraw.Draw(canvas)
    fl, fb = P("Light", 62), P("Bold", 62)
    tw = sum(d.textlength(s + " ", font=fb if b else fl) for s, b in parts)
    x = W / 2 - tw / 2
    for s, b in parts:
        f = fb if b else fl
        d.text((x, y), s, font=f, fill=WHITE, anchor="lm")
        x += d.textlength(s + " ", font=f)


def counter(canvas, label, value, y=1500):
    d = ImageDraw.Draw(canvas)
    lab = " ".join(label)                                  # lettres espacées
    d.text((80, y - 66), lab, font=P("Medium", 30), fill=SUB, anchor="lm")
    d.text((76, y), value, font=P("Bold", 92), fill=GOLD, anchor="lm")


def follow_pill(canvas, handle="@ANIMELOREHQ", y=1480):
    d = ImageDraw.Draw(canvas)
    f1, f2 = P("Medium", 28), P("Bold", 62)
    tw = max(d.textlength(handle, font=f2), 300) + 110
    x0 = W / 2 - tw / 2
    d.rounded_rectangle((x0, y - 70, x0 + tw, y + 74), radius=30, fill=GOLD + (255,))
    d.text((W / 2, y - 30), "F O L L O W", font=f1, fill=(60, 40, 10), anchor="mm")
    d.text((W / 2, y + 26), handle, font=f2, fill=(30, 22, 10), anchor="mm")


def vignette(canvas):
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((x - W / 2) / W) ** 2 + ((y - H / 2) / H) ** 2) / 0.72
    a = (np.clip(r - 0.55, 0, 1) * 320).clip(0, 150).astype(np.uint8)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    lay.putalpha(Image.fromarray(a))
    canvas.alpha_composite(lay)


def shot_punch(end=False):
    im = background()
    cx, cy = 540, 1000
    speed_lines(im, cx, cy)
    barrier(im, cx, cy - 20, 455, t=0.4)
    f = fist_front(1000)
    im.alpha_composite(f, (int(cx - f.width / 2), int(cy - f.height / 2 + 40)))
    vignette(im)
    if end:
        caption(im, [("Follow for more", False), ("If you had...", True)])
        follow_pill(im)
    else:
        caption(im, [("If you had", False), ("Gojo's Infinity,", True)])
        caption(im, [("this punch would never touch you.", False)], y=350)
        counter(im, "DISTANCE LEFT", "0.000000561 in")
    return im


def shot_eyes():
    im = background(seed=2, center=(0.5, 0.62))
    g = Image.open(FLAT / "gojo_yeux.png").convert("RGBA")
    h = 1520
    g = g.resize((int(g.width * h / g.height), h), Image.LANCZOS)
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0))     # halo bleu derrière (pas de cadre)
    ImageDraw.Draw(lay).ellipse((140, 700, 940, 1500), fill=(90, 170, 255, 90))
    im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(120)))
    im.alpha_composite(g, (int(W / 2 - g.width / 2 + 40), H - h + 60))
    vignette(im)
    caption(im, [("That's why he needs the", False)])
    caption(im, [("Six Eyes.", True)], y=350)
    counter(im, "PRECISION", "100%", y=1640)
    return im


def main(outdir):
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    shots = [shot_punch(), shot_eyes(), shot_punch(end=True)]
    for i, s in enumerate(shots):
        s.convert("RGB").save(out / f"da_v4_{i + 1}.png")
    strip = Image.new("RGB", (540 * 3 + 40, 960), (30, 30, 36))
    for i, s in enumerate(shots):
        strip.paste(s.convert("RGB").resize((540, 960), Image.LANCZOS), (i * 560, 0))
    strip.save(out / "da_v4_maquette.png")


if __name__ == "__main__":
    main(sys.argv[1])
