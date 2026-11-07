"""Perso plat animable (07/11) : Goku dessiné en code, style « stickman plat » (aplats, petite lueur blanche).

Vue de profil, tourné vers la droite. Une pose = angles en degrés (0 = vers le bas pour les membres) :
    lean (buste), sh_f / el_f (épaule / coude du bras avant), sh_b / el_b (bras arrière),
    hip_f / kn_f (cuisse / genou jambe avant), hip_b / kn_b (jambe arrière), head (tête), crouch (px).
`draw(pose, form, scale)` -> image RGBA. Les formes changent les cheveux, les yeux et l'aura.
"""
import math
import random

from PIL import Image, ImageChops, ImageDraw, ImageFilter

SKIN, GI, GI_D, BLUE, BLUE_D, BOOT = (255, 214, 170), (255, 128, 30), (225, 95, 15), (40, 70, 170), (25, 45, 120), (30, 40, 90)
FORMS = {
    "base": dict(hair=(25, 25, 35), eye=(30, 30, 30), aura=None, spikes="base"),
    "ssj": dict(hair=(255, 225, 60), eye=(40, 170, 140), aura=(255, 220, 60), spikes="up"),
    "ssj3": dict(hair=(255, 225, 60), eye=(40, 170, 140), aura=(255, 220, 60), spikes="long"),
    "god": dict(hair=(220, 40, 60), eye=(200, 30, 50), aura=(255, 90, 40), spikes="base"),
    "blue": dict(hair=(60, 200, 255), eye=(40, 140, 220), aura=(80, 200, 255), spikes="up"),
    "ui": dict(hair=(220, 225, 240), eye=(190, 200, 230), aura=(200, 210, 255), spikes="base"),
}
IDLE = dict(lean=8, sh_f=30, el_f=-80, sh_b=-20, el_b=-70, hip_f=-25, kn_f=30, hip_b=20, kn_b=25, head=0, crouch=0)
WINDUP = dict(lean=-12, sh_f=-30, el_f=-110, sh_b=-60, el_b=-60, hip_f=-40, kn_f=55, hip_b=35, kn_b=10, head=-5, crouch=18)
PUNCH = dict(lean=22, sh_f=95, el_f=0, sh_b=-40, el_b=-90, hip_f=-45, kn_f=20, hip_b=45, kn_b=5, head=8, crouch=10)


def lerp_pose(a, b, t):
    return {k: a[k] + (b[k] - a[k]) * t for k in a}


def _pt(o, ang, ln):
    a = math.radians(ang)
    return (o[0] + math.sin(a) * ln, o[1] + math.cos(a) * ln)


def _limb(d, a, b, w, col):
    d.line((a, b), fill=col, width=int(w))
    for p in (a, b):
        d.ellipse((p[0] - w / 2, p[1] - w / 2, p[0] + w / 2, p[1] + w / 2), fill=col)


# Coiffure de Goku dessinée à la main (07/11, d'après la référence) : repère de la tête, rayon 1, x vers l'avant
# (droite), y vers le bas. Grosses mèches vers le haut et l'arrière, mèches devant sur le front.
GOKU_HAIR = [(0.78, -0.30), (1.50, -0.52), (0.95, -0.72), (1.35, -1.40), (0.55, -1.02), (0.30, -2.05), (0.02, -1.15),
             (-0.70, -1.85), (-0.48, -0.98), (-1.95, -1.20), (-0.98, -0.52), (-2.15, -0.30), (-1.02, -0.06),
             (-1.75, 0.42), (-0.90, 0.30), (-0.72, 0.66), (-0.30, 0.22), (0.12, -0.12), (0.50, -0.26)]
BANG = [(0.48, -0.40), (0.98, 0.10), (0.80, -0.38), (1.10, -0.20), (0.92, -0.50)]


def _hair(d, c, r, spikes, col, tilt):
    import math as m
    pts = list(GOKU_HAIR)
    if spikes in ("up", "long"):                          # Super Saiyan : mèches dressées vers le haut
        q = []
        for x, y in pts:
            if y < -0.4:
                a = m.radians(28)
                x, y = x * m.cos(a) + y * m.sin(a), -x * m.sin(a) + y * m.cos(a)
                x, y = x * 1.08, y * 1.15
            q.append((x, y))
        pts = q
    t = m.radians(tilt)

    def P(x, y):
        x, y = x * m.cos(t) - y * m.sin(t), x * m.sin(t) + y * m.cos(t)
        return (c[0] + x * r, c[1] + y * r)
    if spikes == "long":                                  # SSJ3 : crinière jusqu'au bas du dos
        mane = [(-0.6, -0.8), (-1.6, 0.2), (-1.2, 0.5), (-2.0, 1.4), (-1.4, 1.5), (-2.1, 2.7), (-1.3, 2.4),
                (-1.7, 3.6), (-0.9, 2.9), (-0.8, 3.8), (-0.4, 2.2), (-0.2, 0.4)]
        d.polygon([P(x, y) for x, y in mane], fill=col)
    d.polygon([P(x, y) for x, y in pts], fill=col)
    d.polygon([P(x, y) for x, y in BANG], fill=col)


def draw(pose, form="base", scale=1.0, aura_phase=0.0):
    f = FORMS[form]
    s = 2 * scale                                         # suréchantillonnage x2
    Wc, Hc = int(420 * s), int(520 * s)
    im = Image.new("RGBA", (Wc, Hc), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    hip = (Wc * 0.45, Hc * 0.58 + pose["crouch"] * s)
    th, sh_l, ar_l, fo_l = 70 * s, 100 * s, 62 * s, 58 * s
    neck = _pt(hip, 180 + pose["lean"], sh_l)
    shoulder = _pt(hip, 180 + pose["lean"], sh_l * 0.86)
    # jambe arrière
    kb = _pt(hip, pose["hip_b"], th)
    fb = _pt(kb, pose["hip_b"] - pose["kn_b"], th)
    _limb(d, hip, kb, 34 * s, GI_D)
    _limb(d, kb, fb, 30 * s, GI_D)
    d.rounded_rectangle((fb[0] - 18 * s, fb[1] - 8 * s, fb[0] + 22 * s, fb[1] + 14 * s), 8 * s, fill=BOOT)
    # bras arrière
    eb = _pt(shoulder, pose["sh_b"], ar_l)
    hb = _pt(eb, pose["sh_b"] + pose["el_b"], fo_l)
    _limb(d, shoulder, eb, 22 * s, tuple(int(c * .85) for c in SKIN))
    _limb(d, eb, hb, 20 * s, tuple(int(c * .85) for c in SKIN))
    d.ellipse((hb[0] - 13 * s, hb[1] - 13 * s, hb[0] + 13 * s, hb[1] + 13 * s), fill=BLUE_D)
    # buste (gi)
    nx, ny = neck[0] - hip[0], neck[1] - hip[1]
    L = math.hypot(nx, ny)
    px, py = -ny / L, nx / L
    tw, bw = 40 * s, 30 * s
    torso = [(hip[0] + px * bw, hip[1] + py * bw), (neck[0] + px * tw, neck[1] + py * tw),
             (neck[0] - px * tw, neck[1] - py * tw), (hip[0] - px * bw, hip[1] - py * bw)]
    d.polygon(torso, fill=GI)
    d.polygon([neck, (neck[0] + px * 16 * s - nx * .25, neck[1] + py * 16 * s - ny * .25),
               (neck[0] - nx * .32, neck[1] - ny * .32), (neck[0] - px * 16 * s - nx * .25, neck[1] - py * 16 * s - ny * .25)],
              fill=BLUE)
    belt_a = (hip[0] + nx * .12, hip[1] + ny * .12)
    d.line(((belt_a[0] + px * 34 * s, belt_a[1] + py * 34 * s), (belt_a[0] - px * 34 * s, belt_a[1] - py * 34 * s)),
           fill=BLUE, width=int(14 * s))
    # jambe avant
    kf = _pt(hip, pose["hip_f"], th)
    ff = _pt(kf, pose["hip_f"] - pose["kn_f"], th)
    _limb(d, hip, kf, 36 * s, GI)
    _limb(d, kf, ff, 32 * s, GI)
    d.rounded_rectangle((ff[0] - 18 * s, ff[1] - 8 * s, ff[0] + 24 * s, ff[1] + 14 * s), 8 * s, fill=BOOT)
    # tête
    hr = 44 * s
    hc = _pt(neck, 180 + pose["lean"] + pose["head"], hr * 0.95)
    d.ellipse((hc[0] - hr, hc[1] - hr, hc[0] + hr, hc[1] + hr), fill=SKIN)
    d.ellipse((hc[0] - hr * 0.15, hc[1] - hr * 0.05, hc[0] + hr * 0.12, hc[1] + hr * 0.3), fill=tuple(int(c * .9) for c in SKIN))
    _hair(d, hc, hr, f["spikes"], f["hair"], pose["lean"] * 0.5 + pose["head"])
    ex, ey = hc[0] + hr * 0.5, hc[1] + hr * 0.05
    d.polygon([(ex - 9 * s, ey - 4 * s), (ex + 9 * s, ey - 7 * s), (ex + 7 * s, ey + 5 * s), (ex - 8 * s, ey + 4 * s)], fill="white")
    d.ellipse((ex + 0 * s, ey - 5 * s, ex + 8 * s, ey + 4 * s), fill=f["eye"])
    d.line(((ex - 12 * s, ey - 11 * s), (ex + 11 * s, ey - 14 * s)), fill=(30, 30, 30), width=int(4 * s))
    # bras avant (par-dessus)
    ef = _pt(shoulder, pose["sh_f"], ar_l)
    hf = _pt(ef, pose["sh_f"] + pose["el_f"], fo_l)
    _limb(d, shoulder, ef, 24 * s, SKIN)
    _limb(d, ef, hf, 22 * s, SKIN)
    wr = _pt(ef, pose["sh_f"] + pose["el_f"], fo_l * 0.72)
    _limb(d, wr, hf, 24 * s, BLUE)
    d.ellipse((hf[0] - 15 * s, hf[1] - 15 * s, hf[0] + 15 * s, hf[1] + 15 * s), fill=SKIN)
    # liseré blanc lumineux autour du perso (comme la référence)
    a = im.getchannel("A")
    halo = a.filter(ImageFilter.MaxFilter(int(7 * s) | 1)).filter(ImageFilter.GaussianBlur(3 * s))
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    if f["aura"]:
        au = a.filter(ImageFilter.MaxFilter(int(31 * s) | 1)).filter(ImageFilter.GaussianBlur(14 * s))
        flick = 0.75 + 0.25 * math.sin(aura_phase * 9)
        au = au.point(lambda v: int(v * 0.85 * flick))
        out.paste(Image.new("RGBA", im.size, f["aura"] + (255,)), (0, 0), au)
    white = Image.new("RGBA", im.size, (255, 255, 255, 255))
    hl = Image.new("RGBA", im.size, (0, 0, 0, 0))
    hl.paste(white, (0, 0), halo.point(lambda v: int(v * 0.8)))
    out.alpha_composite(hl)
    out.alpha_composite(im)
    return out.resize((int(Wc / 2), int(Hc / 2)), Image.LANCZOS), (hf[0] / 2, hf[1] / 2)


if __name__ == "__main__":
    import sys
    tiles = [(IDLE, "base"), (WINDUP, "ssj"), (PUNCH, "ssj"), (WINDUP, "ssj3"), (PUNCH, "god"), (PUNCH, "blue"), (IDLE, "ui")]
    sheet = Image.new("RGBA", (420 * len(tiles), 520), (60, 40, 110, 255))
    for i, (p, fm) in enumerate(tiles):
        img, _ = draw(p, fm)
        sheet.alpha_composite(img, (i * 420, 0))
    sheet.save(sys.argv[1] if len(sys.argv) > 1 else "/tmp/rig.png")


# ---------------------------------------------------------------- style « animation flash » (07/11, référence YouTube)
PANTS, PANTS_D, NAVY, SKIN2 = (240, 120, 40), (205, 95, 30), (28, 36, 80), (246, 205, 170)
SHIRT = (40, 70, 160)


def _quad(d, a, b, wa, wb, col, bulge=0.0):
    """Segment épais en polygone (largeur wa au départ, wb à l'arrivée, ventre au milieu)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy) or 1
    px, py = -dy / L, dx / L
    m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    wm = (wa + wb) / 2 * (1 + bulge)
    pts = [(a[0] + px * wa / 2, a[1] + py * wa / 2), (m[0] + px * wm / 2, m[1] + py * wm / 2),
           (b[0] + px * wb / 2, b[1] + py * wb / 2), (b[0] - px * wb / 2, b[1] - py * wb / 2),
           (m[0] - px * wm / 2, m[1] - py * wm / 2), (a[0] - px * wa / 2, a[1] - py * wa / 2)]
    d.polygon(pts, fill=col)
    for p, w in ((a, wa), (b, wb)):
        d.ellipse((p[0] - w / 2, p[1] - w / 2, p[0] + w / 2, p[1] + w / 2), fill=col)


def aura_poly(cx, cy, rx, ry, phase, n=26, seed=0):
    r = random.Random(seed)
    pts = []
    for i in range(n):
        a = i / n * math.tau
        up = max(0.0, -math.cos(a))                      # flammes plus hautes en haut
        k = 1 + (0.25 + 0.55 * up) * (0.5 + 0.5 * math.sin(phase * 7 + i * 1.9 + r.random() * 6)) * (i % 2)
        pts.append((cx + math.sin(a) * rx * (k if i % 2 else 0.85), cy - math.cos(a) * ry * (k if i % 2 else 0.85)))
    return pts


def draw_flat(pose, form="base", phase=0.0, aura=None):
    """Goku plat façon animation flash : fin, pantalon bouffant, pas de visage, grosses mèches."""
    f = FORMS[form]
    s = 2.0
    Wc, Hc = int(560 * s), int(720 * s)
    im = Image.new("RGBA", (Wc, Hc), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    hip = (Wc * 0.45, Hc * 0.62 + pose["crouch"] * s)
    th, tl, ua, fa = 92 * s, 128 * s, 72 * s, 66 * s
    neck = _pt(hip, 180 + pose["lean"], tl)
    sh = _pt(hip, 180 + pose["lean"], tl * 0.88)
    aura_col = aura if aura is not None else f["aura"]
    if aura_col:                                         # aura en flammes derrière le perso
        cx, cy = hip[0], hip[1] - 70 * s
        for scl, alpha, mix in ((1.25, 150, 0.0), (1.0, 200, 0.45)):
            col = tuple(int(c + (255 - c) * mix) for c in aura_col)
            lay = Image.new("RGBA", (Wc, Hc), (0, 0, 0, 0))
            ImageDraw.Draw(lay).polygon(aura_poly(cx, cy, 120 * s * scl, 230 * s * scl, phase + scl, seed=int(scl * 10)),
                                        fill=col + (alpha,))
            im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(2 * s)))
    # jambe arrière
    for hp, kn, col, boot in ((pose["hip_b"], pose["kn_b"], PANTS_D, NAVY), ):
        k_ = _pt(hip, hp, th)
        a_ = _pt(k_, hp - kn, th)
        _quad(d, hip, k_, 44 * s, 40 * s, col, 0.15)
        _quad(d, k_, a_, 40 * s, 24 * s, col, 0.25)
        d.ellipse((a_[0] - 13 * s, a_[1] - 9 * s, a_[0] + 13 * s, a_[1] + 9 * s), fill=SHIRT)
        d.rounded_rectangle((a_[0] - 14 * s, a_[1] + 2 * s, a_[0] + 30 * s, a_[1] + 22 * s), 9 * s, fill=boot)
    # bras arrière
    e_ = _pt(sh, pose["sh_b"], ua)
    h_ = _pt(e_, pose["sh_b"] + pose["el_b"], fa)
    _quad(d, sh, e_, 15 * s, 13 * s, tuple(int(c * .88) for c in SKIN2))
    _quad(d, e_, h_, 13 * s, 12 * s, tuple(int(c * .88) for c in SKIN2))
    w_ = _pt(e_, pose["sh_b"] + pose["el_b"], fa * 0.78)
    _quad(d, w_, h_, 17 * s, 17 * s, (30, 50, 120))
    d.ellipse((h_[0] - 10 * s, h_[1] - 10 * s, h_[0] + 10 * s, h_[1] + 10 * s), fill=tuple(int(c * .88) for c in SKIN2))
    # buste : maillot bleu dessous, kimono orange par-dessus, ceinture
    _quad(d, hip, neck, 38 * s, 44 * s, SHIRT)
    mid = ((hip[0] * 0.35 + neck[0] * 0.65), (hip[1] * 0.35 + neck[1] * 0.65))
    _quad(d, hip, mid, 40 * s, 40 * s, PANTS)
    _quad(d, mid, _pt(mid, 180 + pose["lean"], 26 * s), 40 * s, 26 * s, PANTS)
    b0 = _pt(hip, 180 + pose["lean"], 12 * s)
    _quad(d, _pt(b0, 90 + pose["lean"], -22 * s), _pt(b0, 90 + pose["lean"], 22 * s), 12 * s, 12 * s, SHIRT)
    # jambe avant
    k_ = _pt(hip, pose["hip_f"], th)
    a_ = _pt(k_, pose["hip_f"] - pose["kn_f"], th)
    _quad(d, hip, k_, 46 * s, 42 * s, PANTS, 0.15)
    _quad(d, k_, a_, 42 * s, 25 * s, PANTS, 0.25)
    d.ellipse((a_[0] - 13 * s, a_[1] - 9 * s, a_[0] + 13 * s, a_[1] + 9 * s), fill=SHIRT)
    d.rounded_rectangle((a_[0] - 14 * s, a_[1] + 2 * s, a_[0] + 32 * s, a_[1] + 22 * s), 9 * s, fill=NAVY)
    # tête (sans visage) + cheveux
    hr = 27 * s
    hc = _pt(neck, 180 + pose["lean"] + pose["head"], hr * 1.05)
    _quad(d, neck, hc, 14 * s, 14 * s, SKIN2)
    d.ellipse((hc[0] - hr * .92, hc[1] - hr, hc[0] + hr * .92, hc[1] + hr), fill=SKIN2)
    _hair_sprite(im, hc, hr, f, pose["lean"] * 0.5 + pose["head"])
    # bras avant
    e_ = _pt(sh, pose["sh_f"], ua)
    h_ = _pt(e_, pose["sh_f"] + pose["el_f"], fa)
    _quad(d, sh, e_, 16 * s, 14 * s, SKIN2)
    _quad(d, e_, h_, 14 * s, 13 * s, SKIN2)
    w_ = _pt(e_, pose["sh_f"] + pose["el_f"], fa * 0.78)
    _quad(d, w_, h_, 18 * s, 18 * s, SHIRT)
    d.ellipse((h_[0] - 12 * s, h_[1] - 12 * s, h_[0] + 12 * s, h_[1] + 12 * s), fill=SKIN2)
    out = im.resize((Wc // 2, Hc // 2), Image.LANCZOS)
    return out, (hip[0] / 2, hip[1] / 2), (h_[0] / 2, h_[1] / 2)


_HAIR = {}


def _hair_sprite(im, hc, hr, f, tilt):
    """Cheveux = silhouette exacte relevée sur la vidéo de référence de l'utilisateur (hair/goku_base.png),
    recolorée selon la forme ; Super Saiyan = mèches étirées vers le haut."""
    import json
    from pathlib import Path
    if "base" not in _HAIR:
        hd = Path(__file__).resolve().parent / "hair"
        _HAIR["base"] = Image.open(hd / "goku_base.png").convert("L")
        _HAIR["meta"] = json.load(open(hd / "goku_base.json"))
    m, meta = _HAIR["base"], _HAIR["meta"]
    k = hr / meta["head_r"] * 1.05
    ax, ay = meta["anchor"]
    sy = 1.0 if f["spikes"] == "base" else 1.3
    mw, mh = int(m.width * k), int(m.height * k * sy)
    ms = m.resize((max(1, mw), max(1, mh)), Image.LANCZOS)
    a_x, a_y = ax * k, ay * k * sy
    big = Image.new("L", (mw * 2, mh * 2), 0)
    big.paste(ms, (int(mw - a_x), int(mh - a_y)))
    big = big.rotate(-tilt, resample=Image.BICUBIC)
    col = Image.new("RGBA", big.size, f["hair"] + (255,))
    im.paste(col, (int(hc[0] - mw), int(hc[1] - mh)), big)
