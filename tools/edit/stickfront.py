"""Notre stickman noir DE FACE (11/11, demandé : « comme dans la vidéo », silhouettes de face) — dessin original.
Proportions en unités de hauteur (0 = haut de la tête, 1 = sol). Respiration + léger balancement (jamais figé).
Points d'accroche (`anchors`) pour poser des objets plus tard : head, eyes, neck, sh_l/sh_r, hand_l/hand_r, hip, back.
    im, foot = FrontStick("hip").render(h=900, t=1.2)        # image RGBA, (x, y) des pieds dans l'image
Poses : hip (main droite sur la hanche), raise (main levée, deux doigts), cross (bras croisés), down (bras le long).
"""
import math

from PIL import Image, ImageDraw

BLACK = (10, 9, 16, 255)
SS = 2                                           # sur-échantillonnage (bords lisses)


def _cap(d, p, q, w, fill=BLACK):
    d.line([p, q], fill=fill, width=int(w))
    r = w / 2
    for (x, y) in (p, q):
        d.ellipse((x - r, y - r, x + r, y + r), fill=fill)


def _arm(sh, a1, a2, L1, L2):
    """épaule → coude → main ; angles en degrés depuis la verticale vers le bas (positif = vers l'extérieur droit)"""
    el = (sh[0] + L1 * math.sin(math.radians(a1)), sh[1] + L1 * math.cos(math.radians(a1)))
    ha = (el[0] + L2 * math.sin(math.radians(a2)), el[1] + L2 * math.cos(math.radians(a2)))
    return el, ha


# angles (bras gauche de l'image, bras droit de l'image) : (épaule→coude, coude→main) ; le gauche est en miroir
POSES = {
    "hip":   {"l": (12, 6), "r": (48, -55)},      # main droite sur la hanche, coude bien sorti
    "raise": {"l": (14, 4), "r": (40, 172)},      # avant-bras droit levé vers le visage
    "cross": {"l": (20, -100), "r": (20, -100)},    # avant-bras croisés devant le torse
    "down":  {"l": (10, 4), "r": (10, 4)},
}


class FrontStick:
    def __init__(self, pose="hip", seed=0, width=1.0):
        self.pose = pose
        self.seed = seed
        self.wk = width                           # carrure (1 = normal)
        self.anchors = {}

    def render(self, h, t=0.0, extra=None):
        """`extra(draw, P, s)` : objets à dessiner par-dessus (P = points d'accroche en px de l'image, s = échelle)"""
        s = h * SS
        W_, H_ = int(s * 0.9), int(s * 1.04)
        im = Image.new("RGBA", (W_, H_), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        cx = W_ / 2
        br = math.sin(t * 2.4 + self.seed) * 0.006   # respiration
        sway = math.sin(t * 1.3 + self.seed * 2) * 0.004
        wk = self.wk

        def P(x, y):
            return (cx + (x + sway * (1 - y)) * s, (y + 0.02) * s)

        head_c = P(0, 0.085 - br * 0.5)
        hr = 0.08 * s
        neck = P(0, 0.17)
        sh_l, sh_r = P(-0.135 * wk, 0.245), P(0.135 * wk, 0.245)
        waist_l, waist_r = P(-0.085 * wk, 0.52), P(0.085 * wk, 0.52)
        hip_l, hip_r = P(-0.068 * wk, 0.56), P(0.068 * wk, 0.56)
        foot_l, foot_r = P(-0.125, 0.975), P(0.125, 0.975)
        knee_l, knee_r = P(-0.098, 0.77), P(0.098, 0.77)
        # jambes : tubes lisses, même largeur partout, petites chaussures tournées vers l'extérieur
        lw = 0.072 * s
        for hp, kn, ft, sd in ((hip_l, knee_l, foot_l, -1), (hip_r, knee_r, foot_r, 1)):
            _cap(d, hp, kn, lw)
            _cap(d, kn, ft, lw * 0.95)
            d.ellipse((ft[0] - lw * 0.55 + sd * lw * 0.25, ft[1] - lw * 0.45, ft[0] + lw * 0.55 + sd * lw * 0.25,
                       ft[1] + lw * 0.25), fill=BLACK)
        # torse d'un seul bloc : épaules arrondies (un tube d'une épaule à l'autre) + buste qui s'affine à la taille
        tw = 1 + br * 2
        sw = 0.075 * s
        _cap(d, (sh_l[0] + sw * 0.25, sh_l[1]), (sh_r[0] - sw * 0.25, sh_r[1]), sw * tw)
        d.polygon([(sh_l[0] - sw * 0.1, sh_l[1]), (sh_r[0] + sw * 0.1, sh_r[1]),
                   (waist_r[0], waist_r[1]), (hip_r[0] + 0.012 * s, hip_r[1] + 0.035 * s),
                   (hip_l[0] - 0.012 * s, hip_l[1] + 0.035 * s), (waist_l[0], waist_l[1])], fill=BLACK)
        _cap(d, neck, P(0, 0.24), 0.085 * s)
        # bras : tubes lisses, mains à peine plus larges
        aw = 0.06 * s
        L1, L2 = 0.165 * s, 0.155 * s
        pose = POSES[self.pose]
        swing = math.sin(t * 1.7 + self.seed) * 2.5
        a = pose["l"]
        el_l, ha_l = _arm(sh_l, -(a[0] + swing * 0.5), -(a[1] + swing), L1, L2)
        a = pose["r"]
        el_r, ha_r = _arm(sh_r, a[0] + swing * 0.3, a[1] + swing * 0.6, L1, L2)
        for sh, el, ha in ((sh_l, el_l, ha_l), (sh_r, el_r, ha_r)):
            _cap(d, sh, el, aw)
            _cap(d, el, ha, aw * 0.95)
            d.ellipse((ha[0] - aw * 0.58, ha[1] - aw * 0.58, ha[0] + aw * 0.58, ha[1] + aw * 0.58), fill=BLACK)
        # tête
        d.ellipse((head_c[0] - hr, head_c[1] - hr * 1.04, head_c[0] + hr, head_c[1] + hr), fill=BLACK)
        self.anchors = {"head": head_c, "head_r": hr, "eyes": (head_c[0], head_c[1] + hr * 0.05), "neck": neck,
                        "sh_l": sh_l, "sh_r": sh_r, "hand_l": ha_l, "hand_r": ha_r, "el_l": el_l, "el_r": el_r,
                        "hip": P(0, 0.55), "back": P(0, 0.33), "foot_l": foot_l, "foot_r": foot_r}
        if extra:
            extra(d, self.anchors, s)
        out = im.resize((W_ // SS, H_ // SS), Image.LANCZOS)
        return out, (W_ / SS / 2, (0.985 + 0.02) * s / SS + 0.02 * h)


if __name__ == "__main__":
    import sys
    tiles = []
    for p in POSES:
        im, _ = FrontStick(p).render(600, 0.3)
        bg = Image.new("RGBA", (im.width + 40, im.height + 40), (200, 90, 110, 255))
        bg.alpha_composite(im, (20, 20))
        tiles.append(bg)
    sheet = Image.new("RGB", (sum(t.width for t in tiles), tiles[0].height))
    x = 0
    for t in tiles:
        sheet.paste(t, (x, 0))
        x += t.width
    sheet.save(sys.argv[1])
