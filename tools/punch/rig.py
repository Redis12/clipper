"""Perso plat animable (07/11) : Goku dessiné en code, style « stickman plat » (aplats, petite lueur blanche).

Vue de profil, tourné vers la droite. Une pose = angles en degrés (0 = vers le bas pour les membres) :
    lean (buste), sh_f / el_f (épaule / coude du bras avant), sh_b / el_b (bras arrière),
    hip_f / kn_f (cuisse / genou jambe avant), hip_b / kn_b (jambe arrière), head (tête), crouch (px).
`draw(pose, form, scale)` -> image RGBA. Les formes changent les cheveux, les yeux et l'aura.
"""
import math

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


def _hair(d, c, r, spikes, col, tilt):
    """Mèches = triangles autour du crâne (côté arrière + dessus), plus longues en SSJ3."""
    ln = {"base": 1.0, "up": 1.15, "long": 1.15}[spikes]
    # (angle depuis le haut, sens horaire ; 0 = haut, -90 = arrière), longueur relative
    sp = {"base": [(-150, .9), (-120, 1.1), (-85, 1.2), (-50, 1.1), (-15, .95), (20, .8), (55, .55)],
          "up": [(-140, .8), (-105, 1.0), (-70, 1.25), (-35, 1.35), (0, 1.3), (30, 1.05), (60, .6)],
          "long": [(-160, 1.0), (-120, 1.2), (-80, 1.3), (-40, 1.3), (0, 1.15), (35, .9), (65, .55)]}[spikes]
    for ang, l in sp:
        a = math.radians(ang + tilt)
        base_w = math.radians(24)
        tip = (c[0] + math.sin(a) * r * (1 + l * ln), c[1] - math.cos(a) * r * (1 + l * ln))
        p1 = (c[0] + math.sin(a - base_w) * r * 0.95, c[1] - math.cos(a - base_w) * r * 0.95)
        p2 = (c[0] + math.sin(a + base_w) * r * 0.95, c[1] - math.cos(a + base_w) * r * 0.95)
        d.polygon([p1, tip, p2], fill=col)
    if spikes == "long":                                   # SSJ3 : grande crinière dans le dos
        a0 = math.radians(-100 + tilt)
        pts = [(c[0] + math.sin(a0) * r, c[1] - math.cos(a0) * r)]
        for k in range(5):
            pts.append((c[0] - r * (0.9 + 0.25 * k), c[1] + r * (0.4 + 0.75 * k)))
            pts.append((c[0] - r * (0.45 + 0.2 * k), c[1] + r * (0.7 + 0.75 * k)))
        pts.append((c[0] - r * 0.2, c[1] + r * 0.6))
        d.polygon(pts, fill=col)
    d.chord((c[0] - r, c[1] - r, c[0] + r, c[1] + r), 180 + tilt * 0.3, 360 + tilt * 0.3, fill=col)


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
    hr = 36 * s
    hc = _pt(neck, 180 + pose["lean"] + pose["head"], hr * 0.95)
    d.ellipse((hc[0] - hr, hc[1] - hr, hc[0] + hr, hc[1] + hr), fill=SKIN)
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
