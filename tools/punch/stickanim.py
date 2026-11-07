"""Moteur d'animation stickman (07/11, demandé : « améliore nos animations : frapper, sautiller, voler, se TP, se
prendre un coup, se transformer… un prototype qu'on adapte à chaque perso »).

- Un perso = un fichier Stick Nodes (JSON via sticknodes-rs) + une table de RÔLES (cuisse avant, avant-bras arrière…)
  → les poses sont écrites une seule fois par rôle, en angles ABSOLUS (0 = devant/droite, 90 = haut, 270 = bas).
  Pour un nouveau perso il suffit de donner sa table de rôles (voir ROLES_GOKU).
- `Actor` : position du bassin (x, y), rotation du corps entier, miroir (regarde à gauche), couleur des cheveux,
  pose interpolée entre des clés avec easing (anticipation, dépassement « back », snap).
- Effets : traînée d'images fantômes (mouvements rapides), ombre au sol, cheveux qui suivent la vitesse.
"""
import math
from collections import deque

import numpy as np
from PIL import Image, ImageDraw

import sticknodes as sn

# ------------------------------------------------------------------------- rôles
ROLES_GOKU = {  # Goku SSJ1 (library/_sticknodes/Goku SSJ1.json)
    "hip": 50, "spine": 51, "chest": 53, "neck": 54, "head": 55,
    "uarm_f": 240, "farm_f": 253, "uarm_b": 1, "farm_b": 14,
    "thigh_f": 17, "shin_f": 30, "thigh_b": 202, "shin_b": 220,
}
FIST_F, FIST_B = "farm_f", "farm_b"           # bout de l'avant-bras = poing

# ------------------------------------------------------------------------- poses (angles absolus, perso regarde à droite)
P = {}
P["idle"] = dict(hip=93, spine=91, chest=89, neck=88, head=86, uarm_f=295, farm_f=40, uarm_b=258, farm_b=60,
                 thigh_f=282, shin_f=271, thigh_b=258, shin_b=269)
P["stance"] = dict(hip=86, spine=83, chest=80, neck=82, head=86, uarm_f=320, farm_f=62, uarm_b=292, farm_b=78,
                   thigh_f=298, shin_f=274, thigh_b=246, shin_b=258)
P["stance_low"] = dict(P["stance"], hip=84, spine=80, chest=77, thigh_f=310, shin_f=262, thigh_b=234, shin_b=266)
P["run_a"] = dict(hip=74, spine=70, chest=66, neck=68, head=74, uarm_f=235, farm_f=290, uarm_b=330, farm_b=40,
                  thigh_f=330, shin_f=255, thigh_b=230, shin_b=205)
P["run_b"] = dict(hip=74, spine=70, chest=66, neck=68, head=74, uarm_f=330, farm_f=40, uarm_b=235, farm_b=290,
                  thigh_f=230, shin_f=205, thigh_b=330, shin_b=255)
P["jab"] = dict(P["stance"], hip=82, spine=78, chest=74, uarm_f=2, farm_f=0, uarm_b=295, farm_b=80)
P["cross"] = dict(P["stance"], hip=78, spine=72, chest=66, neck=70, uarm_f=300, farm_f=70, uarm_b=0, farm_b=-2,
                  thigh_f=305, shin_f=278, thigh_b=238, shin_b=250)
P["windup"] = dict(hip=104, spine=106, chest=108, neck=98, head=94, uarm_f=205, farm_f=150, uarm_b=330, farm_b=15,
                   thigh_f=295, shin_f=272, thigh_b=245, shin_b=262)
P["punch"] = dict(hip=72, spine=66, chest=60, neck=62, head=60, uarm_f=2, farm_f=0, uarm_b=205, farm_b=240,
                  thigh_f=312, shin_f=280, thigh_b=222, shin_b=214)
P["kick_wind"] = dict(hip=100, spine=103, chest=106, neck=100, head=92, uarm_f=300, farm_f=60, uarm_b=230, farm_b=200,
                      thigh_f=355, shin_f=268, thigh_b=262, shin_b=272)
P["kick"] = dict(hip=112, spine=116, chest=120, neck=112, head=100, uarm_f=300, farm_f=330, uarm_b=200, farm_b=228,
                 thigh_f=12, shin_f=14, thigh_b=258, shin_b=268)
P["hurt"] = dict(hip=112, spine=120, chest=128, neck=138, head=150, uarm_f=30, farm_f=70, uarm_b=60, farm_b=100,
                 thigh_f=300, shin_f=292, thigh_b=252, shin_b=240)
P["tumble"] = dict(hip=120, spine=128, chest=136, neck=146, head=160, uarm_f=60, farm_f=110, uarm_b=100, farm_b=150,
                   thigh_f=330, shin_f=300, thigh_b=230, shin_b=200)
P["down"] = dict(hip=170, spine=172, chest=174, neck=176, head=178, uarm_f=200, farm_f=190, uarm_b=160, farm_b=150,
                 thigh_f=350, shin_f=355, thigh_b=5, shin_b=0)
P["crouch"] = dict(hip=70, spine=66, chest=62, neck=64, head=72, uarm_f=230, farm_f=250, uarm_b=225, farm_b=245,
                   thigh_f=345, shin_f=252, thigh_b=318, shin_b=246)
P["air"] = dict(hip=88, spine=86, chest=84, neck=84, head=86, uarm_f=40, farm_f=70, uarm_b=140, farm_b=110,
                thigh_f=330, shin_f=268, thigh_b=238, shin_b=262)
P["fly"] = dict(hip=12, spine=10, chest=8, neck=12, head=18, uarm_f=6, farm_f=4, uarm_b=192, farm_b=186,
                thigh_f=186, shin_f=178, thigh_b=194, shin_b=198)
P["fly_up"] = dict(hip=78, spine=80, chest=82, neck=84, head=86, uarm_f=82, farm_f=86, uarm_b=262, farm_b=268,
                   thigh_f=262, shin_f=270, thigh_b=272, shin_b=278)
P["tp"] = dict(hip=91, spine=90, chest=90, neck=92, head=90, uarm_f=35, farm_f=150, uarm_b=262, farm_b=268,
               thigh_f=276, shin_f=270, thigh_b=264, shin_b=270)
P["elbow"] = dict(P["stance"], hip=80, spine=74, chest=68, uarm_f=10, farm_f=200, uarm_b=250, farm_b=260)
P["scream"] = dict(hip=94, spine=96, chest=98, neck=104, head=112, uarm_f=302, farm_f=312, uarm_b=238, farm_b=228,
                   thigh_f=300, shin_f=280, thigh_b=240, shin_b=260)
P["power"] = dict(P["scream"], uarm_f=318, farm_f=330, uarm_b=222, farm_b=210, head=96, neck=96)
P["kame_charge"] = dict(hip=100, spine=104, chest=108, neck=94, head=84, uarm_f=228, farm_f=196, uarm_b=224,
                        farm_b=190, thigh_f=300, shin_f=278, thigh_b=240, shin_b=256)
P["kame_fire"] = dict(hip=80, spine=74, chest=70, neck=72, head=76, uarm_f=2, farm_f=0, uarm_b=5, farm_b=3,
                      thigh_f=306, shin_f=280, thigh_b=232, shin_b=244)
P["block"] = dict(P["stance"], uarm_f=40, farm_f=110, uarm_b=50, farm_b=118, hip=92, spine=94, chest=96, head=94)


def to_abs(pose, roles):
    return {roles[k]: v for k, v in pose.items() if k in roles}


def lerp(a, b, t):
    out = {}
    for k in set(a) | set(b):
        x, y = a.get(k, b.get(k)), b.get(k, a.get(k))
        out[k] = x + ((y - x + 180) % 360 - 180) * t
    return out


# ------------------------------------------------------------------------- easing
def clamp(t):
    return max(0.0, min(1.0, t))


def smooth(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def out_cubic(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def in_cubic(t):
    t = clamp(t)
    return t ** 3


def out_back(t, s=1.9):
    t = clamp(t) - 1
    return t * t * ((s + 1) * t + s) + 1


def snap(t):                      # frappe : très rapide au début, se pose
    t = clamp(t)
    return 1 - (1 - t) ** 5


EASE = {"smooth": smooth, "out": out_cubic, "in": in_cubic, "back": out_back, "snap": snap, "lin": clamp}


class Track:
    """Clés (t, valeur, easing) : pose (dict de rôles) ou nombre. Easing de la clé = arrivée sur cette clé."""

    def __init__(self, keys):
        self.keys = sorted(keys, key=lambda k: k[0])

    def at(self, t):
        ks = self.keys
        if t <= ks[0][0]:
            return ks[0][1]
        for (t0, v0, *_), (t1, v1, *e) in zip(ks, ks[1:]):
            if t <= t1:
                f = EASE[e[0] if e else "smooth"]((t - t0) / max(1e-6, t1 - t0))
                if isinstance(v0, dict):
                    return lerp(v0, v1, f)
                return v0 + (v1 - v0) * f
        return ks[-1][1]


class Actor:
    def __init__(self, fig, roles=ROLES_GOKU, scale=0.75, hair_nodes_colors=None, flip=False, recolor=None):
        self.fig, self.roles, self.scale, self.flip = fig, roles, scale, flip
        self.recolor = recolor
        self.hair_cols = hair_nodes_colors or set()
        self.trail = deque(maxlen=6)
        self.last = None

    def render(self, pose, hair=None, gi=None):
        hc, gc = hair, gi

        def cm(i, c):
            if hc is not None and c[:3] in self.hair_cols:
                return tuple(hc) + (255,)
            if self.recolor:
                return self.recolor(c)
            return c
        im, pos, org = sn.render(self.fig, scale=self.scale, absolute=to_abs(pose, self.roles), flip=self.flip,
                                 color_map=cm)
        return im, pos, org

    def draw(self, canvas, pose, x, y, rot=0.0, hair=None, alpha=1.0, ground=None, trail=0, ghost_col=None,
             shadow_y=None, lift=0.0, record=True, glow=None, tint=None, mask=None):
        """x, y = bassin. ground = y du sol → les pieds y sont posés (y ignoré). trail = nb d'images fantômes.
        glow = (couleur, taille) liseré lumineux ; tint = couleur unie (écho coloré) ; mask = image L où l'on ajoute
        la silhouette (pour les impact frames)."""
        im, pos, org = self.render(pose, hair)
        if ground is not None:
            a = np.asarray(im)[..., 3]
            bottom = np.nonzero(a.max(1) > 0)[0].max()
            y = ground - (bottom - org[1]) - lift
        if rot:
            im = im.rotate(rot, resample=Image.BICUBIC, center=org, expand=False)
            ca, sa_ = math.cos(math.radians(-rot)), math.sin(math.radians(-rot))
            pos = {k: (org[0] + (v[0] - org[0]) * ca - (v[1] - org[1]) * sa_,
                       org[1] + (v[0] - org[0]) * sa_ + (v[1] - org[1]) * ca) for k, v in pos.items()}
        px, py = int(x - org[0]), int(y - org[1])
        if shadow_y is not None:
            d = ImageDraw.Draw(canvas, "RGBA")
            h = max(0.15, 1 - (shadow_y - y) / 900)
            d.ellipse((x - 70 * h, shadow_y - 10 * h, x + 70 * h, shadow_y + 10 * h), fill=(0, 0, 0, int(70 * h)))
        if trail and self.trail:
            for j, (gim, gx, gy) in enumerate(list(self.trail)[-trail:]):
                k = (j + 1) / (trail + 1)
                g = gim.copy()
                if ghost_col:
                    col = Image.new("RGBA", g.size, ghost_col + (0,))
                    col.putalpha(g.getchannel("A"))
                    g = col
                g.putalpha(g.getchannel("A").point(lambda v, k=k: int(v * 0.45 * k)))
                canvas.paste(g, (gx, gy), g)
        if tint is not None:
            col = Image.new("RGBA", im.size, tuple(tint) + (0,))
            col.putalpha(im.getchannel("A"))
            im = col
        if alpha < 1:
            im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
        if glow:
            from stickfx import rim_glow
            g = rim_glow(im, glow[0], glow[1], glow[2] if len(glow) > 2 else 1.0)
            canvas.alpha_composite(g, (max(0, px), max(0, py))) if px >= 0 and py >= 0 else canvas.paste(g, (px, py), g)
        canvas.paste(im, (px, py), im)
        if mask is not None:
            mask.paste(255, (px, py), im.getchannel("A"))
        if record:
            self.trail.append((im, px, py))
        P_ = lambda k: (px + pos[self.roles[k]][0], py + pos[self.roles[k]][1])  # noqa: E731
        info = dict(x=x, y=y, fist=P_(FIST_F), fist_b=P_(FIST_B), foot=P_("shin_f"), head=P_("head"),
                    box=(px, py, px + im.width, py + im.height))
        if record:
            self.last = info
        return info


def contact_sheet(fig, path, roles=ROLES_GOKU, names=None, scale=0.45, hair=None):
    names = names or list(P)
    cells = []
    a = Actor(fig, roles, scale)
    for n in names:
        c = Image.new("RGBA", (300, 380), (150, 190, 220, 255))
        a.draw(c, P[n], 150, 0, ground=330, hair=hair)
        ImageDraw.Draw(c).text((8, 350), n, fill=(0, 0, 0))
        cells.append(c)
    cols = 8
    rows = (len(cells) + cols - 1) // cols
    sh = Image.new("RGB", (cols * 300, rows * 380), (255, 255, 255))
    for i, c in enumerate(cells):
        sh.paste(c, ((i % cols) * 300, (i // cols) * 380))
    sh.save(path)
