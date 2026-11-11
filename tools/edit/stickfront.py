"""Notre stickman noir DE FACE (11/11). Forme demandée par l'utilisateur d'après une capture de la vidéo de référence :
grosse tête ronde, t-shirt à manches courtes, taille fine, pantalon large jambes écartées, bras fins, liseré clair.
Dessin redessiné en code (proportions mesurées), sans les objets du perso (épée, ceinture…) : les objets sont des
images fournies par l'utilisateur, posées sur les points d'accroche (`anchors`).
Unités : 0 = haut de la tête, 1 = bas des pieds, x = 0 au centre. Respiration + léger balancement (jamais figé).
    im, foot = FrontStick("shoulder").render(h=900, t=1.2)    # image RGBA, (x, y) des pieds dans l'image
Poses : shoulder (main gauche à l'épaule, main droite sur la hanche), hip (2 mains sur les hanches), raise (main
levée devant le visage), down (bras le long du corps).
"""
import math

from PIL import Image, ImageDraw, ImageFilter

BLACK = (8, 8, 12, 255)
RIM = (225, 240, 250)
SS = 2                                           # sur-échantillonnage (bords lisses)

# coudes et mains (gauche de l'image, droite de l'image), en unités ; les épaules sont fixes
POSES = {
    "shoulder": {"el_l": (-0.215, 0.395), "ha_l": (-0.215, 0.235), "el_r": (0.215, 0.43), "ha_r": (0.115, 0.49)},
    "hip":      {"el_l": (-0.215, 0.43), "ha_l": (-0.115, 0.49), "el_r": (0.215, 0.43), "ha_r": (0.115, 0.49)},
    "raise":    {"el_l": (-0.185, 0.47), "ha_l": (-0.175, 0.6), "el_r": (0.225, 0.38), "ha_r": (0.15, 0.2)},
    "down":     {"el_l": (-0.185, 0.47), "ha_l": (-0.19, 0.6), "el_r": (0.185, 0.47), "ha_r": (0.19, 0.6)},
}


def _cap(d, p, q, w, fill=BLACK):
    d.line([p, q], fill=fill, width=max(1, int(w)))
    r = w / 2
    for (x, y) in (p, q):
        d.ellipse((x - r, y - r, x + r, y + r), fill=fill)


class FrontStick:
    def __init__(self, pose="shoulder", seed=0, rim=True):
        self.pose = pose
        self.seed = seed
        self.rim = rim
        self.anchors = {}

    def render(self, h, t=0.0, extra=None):
        """`extra(draw, P, s)` : objets dessinés par-dessus (P = points d'accroche en px, s = échelle)"""
        s = float(h) * SS
        pad = 0.06
        W_, H_ = int(s * (0.62 + 2 * pad)), int(s * (1 + 2 * pad))
        im = Image.new("RGBA", (W_, H_), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        br = math.sin(t * 2.4 + self.seed) * 0.005           # respiration
        sw = math.sin(t * 1.3 + self.seed * 2) * 0.004       # balancement (plus fort en haut)

        def P(x, y):
            return (W_ / 2 + (x + sw * (1 - y)) * s, (y + pad) * s)

        # --- pantalon : 2 jambes larges et droites, écartées, bas arrondi
        crotch = 0.66
        for side in (-1, 1):
            top_o, top_i = P(side * 0.112, 0.50), P(side * 0.01, crotch)
            bot_o, bot_i = P(side * 0.205, 0.965), P(side * 0.11, 0.975)
            d.polygon([P(0, 0.50), top_o, bot_o, bot_i, top_i], fill=BLACK)
            cx_, cy_ = (bot_o[0] + bot_i[0]) / 2, (bot_o[1] + bot_i[1]) / 2
            r_ = abs(bot_o[0] - bot_i[0]) / 2 + 0.004 * s
            d.ellipse((cx_ - r_, cy_ - r_ * 0.75, cx_ + r_, cy_ + r_ * 0.6), fill=BLACK)
        # --- t-shirt : buste qui s'affine à la taille + manches courtes
        k = 1 + br * 2
        sh_l, sh_r = P(-0.135 * k, 0.255), P(0.135 * k, 0.255)
        d.polygon([P(-0.115 * k, 0.235), P(0.115 * k, 0.235), sh_r, P(0.105, 0.50), P(-0.105, 0.50), sh_l], fill=BLACK)
        for side in (-1, 1):
            d.polygon([P(side * 0.105 * k, 0.235), P(side * 0.15 * k, 0.25), P(side * 0.185, 0.345),
                       P(side * 0.128, 0.365), P(side * 0.112, 0.30)], fill=BLACK)
        _cap(d, P(0, 0.205), P(0, 0.245), 0.075 * s)            # cou
        # --- bras fins : de la manche au coude, puis à la main
        po = POSES[self.pose]
        sway = math.sin(t * 1.7 + self.seed) * 0.006
        aw = 0.042 * s
        shl, shr = P(-0.152, 0.33), P(0.152, 0.33)
        el_l = P(po["el_l"][0] - sway, po["el_l"][1])
        ha_l = P(po["ha_l"][0] - sway * 1.5, po["ha_l"][1] + sway)
        el_r = P(po["el_r"][0] + sway, po["el_r"][1])
        ha_r = P(po["ha_r"][0] + sway * 0.5, po["ha_r"][1])
        for a_, b_, c_ in ((shl, el_l, ha_l), (shr, el_r, ha_r)):
            _cap(d, a_, b_, aw)
            _cap(d, b_, c_, aw * 0.95)
            d.ellipse((c_[0] - aw * 0.75, c_[1] - aw * 0.75, c_[0] + aw * 0.75, c_[1] + aw * 0.75), fill=BLACK)
        # --- grosse tête ronde
        hc = P(0.008, 0.113 - br * 0.4)
        hr = 0.113 * s
        d.ellipse((hc[0] - hr, hc[1] - hr, hc[0] + hr, hc[1] + hr), fill=BLACK)
        self.anchors = {"head": hc, "head_r": hr, "eyes": (hc[0], hc[1] + hr * 0.1), "neck": P(0, 0.22),
                        "sh_l": sh_l, "sh_r": sh_r, "el_l": el_l, "el_r": el_r, "hand_l": ha_l, "hand_r": ha_r,
                        "belt": P(0, 0.505), "back": P(0, 0.33), "foot_l": P(-0.16, 0.97), "foot_r": P(0.16, 0.97)}
        if extra:
            extra(d, self.anchors, s)
        if self.rim:                                               # liseré clair + halo autour de la silhouette
            al = im.getchannel("A")
            grow = al.filter(ImageFilter.MaxFilter(max(3, int(0.006 * s) | 1)))
            ring = Image.new("RGBA", im.size, RIM + (0,))
            ring.putalpha(grow.point(lambda v: int(v * 0.85)))
            halo = ring.filter(ImageFilter.GaussianBlur(0.012 * s))
            base = Image.new("RGBA", im.size, (0, 0, 0, 0))
            base.alpha_composite(halo)
            base.alpha_composite(ring)
            base.alpha_composite(im)
            im = base
        out = im.resize((W_ // SS, H_ // SS), Image.LANCZOS)
        return out, (W_ / SS / 2, (0.975 + pad) * s / SS)


if __name__ == "__main__":
    import sys
    tiles = []
    for p in POSES:
        im, _ = FrontStick(p).render(600, 0.3)
        bg = Image.new("RGBA", (im.width + 40, im.height + 40), (60, 140, 120, 255))
        bg.alpha_composite(im, (20, 20))
        tiles.append(bg)
    sheet = Image.new("RGB", (sum(t.width for t in tiles), tiles[0].height))
    x = 0
    for t in tiles:
        sheet.paste(t, (x, 0))
        x += t.width
    sheet.save(sys.argv[1])
