"""PRODUCTEUR de combats stickman (07/11, demandé : « un outil qui génère des scénarios d'animation, les zooms de
caméra… un producteur pour faire de vrais combats »).

On écrit le combat comme une liste d'actions :
    sc = Scene()
    g = sc.actor("Goku", fig, x=240, facing=1, hair=BLACK, color=ORANGE)
    v = sc.actor("Foe", fig, x=760, facing=-1, recolor=gray_gi, color=PURPLE)
    sc.wait(0.8); sc.dash(g, v); sc.flurry(g, v, hits=8); sc.heavy(g, v); sc.getup(v); sc.charge(v, g)
    sc.dodge(g, v, "duck"); sc.launch(g, v); sc.air_smash(g, v); sc.render(sortie)
Le producteur calcule les poses (bibliothèque `stickanim.P`), les distances de frappe (allonge mesurée sur le
squelette), les réactions, les arrêts sur impact, la caméra (zooms, horizon penché, suivi), les effets (`stickfx`)
et le son. Chaque action avance le curseur de temps `sc.t`.
"""
import math
import random
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hud  # noqa: E402
import stickanim as sa  # noqa: E402
import stickfx as fx  # noqa: E402
from stickanim import P, Track  # noqa: E402
from mugen_punch import GROUND, H, W, FPS  # noqa: E402

XMIN, XMAX = 140, 960


def mix(a, b, k):
    return sa.lerp(a, b, k)


class Who:
    """Un combattant : ses pistes d'animation + son état au curseur."""

    def __init__(self, name, fig, x, facing, scale, hair, color, recolor, hair_nodes, roles):
        self.name, self.fig, self.facing, self.hair, self.color = name, fig, facing, hair, color
        self.actors = {f: sa.Actor(fig, roles=roles, scale=scale, hair_nodes_colors=hair_nodes, flip=(f < 0),
                                   recolor=recolor) for f in (1, -1)}
        self.x, self.pose, self.lift, self.rot = float(x), P["stance"], 0.0, 0.0
        self.k_pose, self.k_x, self.k_lift, self.k_rot = [(0, P["stance"])], [(0, float(x))], [(0, 0.0)], [(0, 0.0)]
        self.k_face, self.k_alpha, self.k_hair = [(0, facing)], [(0, 1.0)], [(0, hair)]
        self.busy, self.down = 0.0, False
        self.reach = {}
        a = sa.Actor(fig, roles=roles, scale=scale)                 # allonge de chaque coup, mesurée sur CE squelette
        for mv, limb in (("jab", "fist"), ("cross", "fist_b"), ("punch", "fist"), ("kick", "foot"),
                         ("uppercut", "fist"), ("hammer", "fist"), ("elbow", "fist")):
            c = Image.new("RGBA", (1600, 1600))
            self.reach[mv] = a.draw(c, P[mv], 800, 0, ground=1500, record=False)[limb][0] - 800

    def hold(self, t):
        """Fige l'état courant à t : la prochaine clé part de là (sinon le perso glisse AVANT l'action)."""
        for ks, v in ((self.k_pose, self.pose), (self.k_x, self.x), (self.k_lift, self.lift), (self.k_rot, self.rot)):
            if ks[-1][0] < t:
                ks.append((t, v))

    def key(self, t, pose=None, x=None, lift=None, rot=None, ease="smooth"):
        if pose is not None:
            self.k_pose.append((t, pose, ease))
            self.pose = pose
        if x is not None:
            x = min(XMAX, max(XMIN, x))
            self.k_x.append((t, float(x), ease))
            self.x = x
        if lift is not None:
            self.k_lift.append((t, float(lift), ease))
            self.lift = lift
        if rot is not None:
            self.k_rot.append((t, float(rot), ease))
            self.rot = rot

    def face(self, t, f):
        self.k_face.append((t, f))
        self.facing = f

    def build(self):
        for ks in (self.k_pose, self.k_x, self.k_lift, self.k_rot):
            ks.sort(key=lambda k: k[0])
        self.T_pose, self.T_x = Track(self.k_pose), Track(self.k_x)
        self.T_lift, self.T_rot, self.T_alpha = Track(self.k_lift), Track(self.k_rot), Track(self.k_alpha)

    def facing_at(self, t):
        f = self.k_face[0][1]
        for t0, v in self.k_face:
            if t >= t0:
                f = v
        return f

    def hair_at(self, t):
        h = self.k_hair[0][1]
        for t0, v in self.k_hair:
            if t >= t0:
                h = v
        return h


class Scene:
    def __init__(self, scale=0.9, seed=3):
        self.who, self.t, self.scale = [], 0.0, scale
        self.ev = []                      # événements (effets, sons)
        self.stops = []                   # arrêts sur impact (t, durée)
        self.cam_z, self.cam_t = [(0, 1.0)], [(0, 0.0)]
        self.cam_f = []                   # (t0, t1, cible) : cible = (x, y) ou ("head", who)
        self.rnd = random.Random(seed)

    # ------------------------------------------------------------------ préparation
    def actor(self, name, fig, x, facing=1, hair=None, color=(245, 110, 30), recolor=None, hair_nodes=None,
              roles=None, scale=None):
        w = Who(name, fig, x, facing, scale or self.scale, hair, color, recolor, hair_nodes or set(),
                roles or sa.ROLES_GOKU)
        self.who.append(w)
        return w

    def at_range(self, att, tgt, move, overlap=18):
        """Position du bassin de l'attaquant pour que le coup touche le devant du corps de la cible."""
        return tgt.x - att.facing * (att.reach[move] + 42 - overlap)

    def hold(self, *ws):
        for w in ws:
            w.hold(self.t)

    # ------------------------------------------------------------------ caméra
    def punch_cam(self, t, x, y, z=1.3, tilt=-5, hold=0.35):
        self.cam_z += [(t - 0.02, 1.0), (t + 0.02, z, "snap"), (t + hold, 1.0, "smooth")]
        self.cam_t += [(t - 0.02, 0.0), (t + 0.02, tilt, "snap"), (t + hold, 0.0, "smooth")]
        self.cam_f.append((t - 0.02, t + hold, (x, y)))

    def closeup(self, w, d=0.5, z=2.4, tilt=0.0, wait=True):
        """Gros plan coupé net sur le visage (SvS 0:50, 2:14 ; gaara 1:51)."""
        t = self.t
        self.cam_z += [(t, 1.0), (t + 0.001, z, "lin"), (t + d, z), (t + d + 0.001, 1.0, "lin")]
        self.cam_t += [(t, 0.0), (t + 0.001, tilt, "lin"), (t + d, tilt), (t + d + 0.001, 0.0, "lin")]
        self.cam_f.append((t, t + d, ("head", w)))
        if wait:
            self.wait(d)

    def stop(self, t, d):
        self.stops.append((t, d))

    def label(self, t, txt, col):
        self.ev.append(dict(k="label", t=t, txt=txt, col=col))

    # ------------------------------------------------------------------ actions
    def wait(self, d, bob=True):
        """Tout le monde respire / sautille en garde (sauf ceux qui sont au sol)."""
        for w in self.who:
            w.hold(self.t)
            if w.busy > self.t or not bob or w.down:
                continue
            n = max(1, int(d / 0.5))
            for i in range(n):
                t0 = self.t + i * d / n
                w.key(t0 + d / n * 0.5, pose=P["stance_low"])
                w.key(t0 + d / n, pose=P["stance"])
        self.t += d
        for w in self.who:
            w.hold(self.t)

    def face_off(self, a, b, d=0.55):
        """Ouverture : gros plan sur chacun (face à face), puis plan large."""
        self.closeup(a, d, z=1.8, tilt=-4)
        self.closeup(b, d, z=1.8, tilt=4)

    def dash(self, a, tgt, move="jab", d=0.3):
        self.hold(a, tgt)
        t = self.t
        x1 = self.at_range(a, tgt, move)
        a.key(t + 0.06, pose=P["run_a"], ease="out")
        a.key(t + d * 0.55, pose=P["run_b"])
        a.key(t + d, pose=P["stance"], x=x1, ease="out")
        self.ev += [dict(k="echo", w=a, t0=t, t1=t + d, n=5), dict(k="streak", w=a, t0=t, t1=t + d),
                    dict(k="dust", w=a, t0=t, t1=t + d), dict(k="snd", t=t, fam="teleport", g=0.35)]
        self.t += d

    def flurry(self, a, tgt, hits=8, every=0.11, push=10):
        """Rafale de coups rapides (jab/cross alternés), l'adversaire encaisse et recule pas à pas."""
        self.hold(a, tgt)
        t = self.t
        flinch = mix(P["stance"], P["hurt"], 0.45)
        for i in range(hits):
            h = t + 0.06 + i * every
            mv = "jab" if i % 2 == 0 else "cross"
            limb = "fist" if mv == "jab" else "fist_b"
            tgt.hold(h - 0.01)
            tgt.key(h, pose=flinch, x=tgt.x + a.facing * push, ease="snap")
            tgt.key(h + every * 0.6, pose=mix(P["stance"], P["hurt"], 0.2))
            a.hold(h - every * 0.5)
            a.key(h - every * 0.45, pose=mix(P["stance"], P[mv], 0.25))
            a.key(h, pose=P[mv], x=self.at_range(a, tgt, mv), ease="snap")
            self.ev += [dict(k="arc", w=a, limb=limb, t0=h - every * 0.45, t1=h),
                        dict(k="hit", t=h, att=a, tgt=tgt, p="light", limb=limb),
                        dict(k="snd", t=h, fam="hit", seed=10 + i, g=0.45)]
            self.stop(h, 0.025)
        self.ev.append(dict(k="echo", w=a, t0=t, t1=t + 0.06 + hits * every, n=3, a0=0.35))
        self.t = t + 0.06 + hits * every
        a.key(self.t + 0.1, pose=P["stance"])
        tgt.key(self.t + 0.1, pose=P["stance"])
        self.t += 0.1

    def heavy(self, a, tgt, move="punch", knock=380, wind=0.3, face_cam=True):
        """Gros coup : gros plan sur l'attaquant pendant l'armé, frappe au contact, arrêt, zoom, la cible glisse loin."""
        self.hold(a, tgt)
        t = self.t
        windup = "windup" if move == "punch" else "kick_wind"
        a.key(t + wind, pose=P[windup], ease="out")
        if face_cam:
            self.cam_z += [(t + 0.02, 1.0), (t + 0.021, 1.55, "lin"), (t + wind - 0.02, 1.7), (t + wind - 0.019, 1.0, "lin")]
            self.cam_f.append((t + 0.02, t + wind - 0.02, ("head", a)))
        h = t + wind + 0.12
        a.key(h, pose=P[move], x=self.at_range(a, tgt, move, overlap=26), ease="snap")
        a.key(h + 0.45, pose=P[move])
        a.key(h + 0.75, pose=P["stance"])
        tgt.hold(h)
        tgt.key(h + 0.04, pose=P["hurt"], ease="snap")
        tgt.key(h + 0.55, pose=P["hurt"], x=tgt.x + a.facing * knock, ease="out")
        tgt.key(h + 0.9, pose=P["stance"])
        limb = "foot" if move == "kick" else "fist"
        hy = GROUND - (260 if move == "kick" else 320)
        self.ev += [dict(k="arc", w=a, limb=limb, t0=t + wind, t1=h), dict(k="echo", w=a, t0=t + wind, t1=h + 0.02, n=5),
                    dict(k="hit", t=h, att=a, tgt=tgt, p="heavy", limb=limb, y=hy),
                    dict(k="dust", w=tgt, t0=h + 0.04, t1=h + 0.55), dict(k="echo", w=tgt, t0=h, t1=h + 0.4, n=4),
                    dict(k="streak", w=tgt, t0=h + 0.04, t1=h + 0.4, back=True),
                    dict(k="snd", t=h, fam="hit", seed=1, g=1.0), dict(k="snd", t=h + 0.01, fam="bomb", seed=3, g=0.5)]
        self.stop(h, 0.1)
        self.punch_cam(h, tgt.x - a.facing * knock * 0.2, hy, z=1.3, tilt=-5 * a.facing)
        self.t = h + 0.9

    def getup(self, w, d=0.7):
        self.hold(w)
        w.down = False
        t = self.t
        w.key(t + d * 0.45, pose=P["crouch"], rot=0.0, ease="out")
        w.key(t + d, pose=P["stance"], ease="back")
        self.t += d

    def taunt(self, w, d=0.6):
        self.hold(w)
        t = self.t
        w.key(t + 0.15, pose=P["taunt"], ease="back")
        w.key(t + d, pose=P["stance"])
        self.t += d

    def charge(self, a, tgt, d=0.5, stop_short=170):
        """Fonce vers l'adversaire (course penchée vers l'avant, traits, poussière) et s'arrête à portée."""
        self.hold(a, tgt)
        t = self.t
        x1 = tgt.x - a.facing * stop_short
        steps = 4
        for i in range(steps):
            a.key(t + d * (i + 1) / (steps + 1), pose=P["run_a" if i % 2 == 0 else "run_b"])
        a.key(t + d, pose=P["windup"], x=x1, ease="in")
        self.ev += [dict(k="echo", w=a, t0=t, t1=t + d, n=5), dict(k="streak", w=a, t0=t + 0.1, t1=t + d),
                    dict(k="dust", w=a, t0=t, t1=t + d), dict(k="snd", t=t, fam="teleport", seed=4, g=0.4)]
        self.t += d

    def dodge(self, d_, a, kind="behind"):
        """`a` (qui vient de charger) frappe dans le vide. `d_` esquive :
        behind = file derrière lui ; jump_over = saute par-dessus en vrille ; slide_under = glisse entre ses jambes ;
        vanish = disparaît (image rémanente) et réapparaît dans son dos. Les deux se retournent ensuite."""
        self.hold(a, d_)
        t = self.t
        h = t + 0.12
        a.key(h, pose=P["punch"], x=a.x + a.facing * 70, ease="snap")
        a.key(h + 0.3, pose=P["punch"])
        self.ev += [dict(k="arc", w=a, limb="fist", t0=t, t1=h), dict(k="snd", t=h, fam="teleport", seed=7, g=0.5),
                    dict(k="whiff", t=h, w=a)]
        x0 = d_.x
        behind = a.x - a.facing * 230
        f0 = d_.facing
        if kind == "behind":
            d_.key(h - 0.04, pose=P["run_a"], ease="out")
            d_.key(h + 0.14, pose=P["crouch"], x=behind, ease="out")
            d_.face(h + 0.06, -f0)
            d_.key(h + 0.35, pose=P["stance"], ease="back")
            self.ev += [dict(k="echo", w=d_, t0=h - 0.06, t1=h + 0.16, n=6), dict(k="vanish", w=d_, t=h, x0=x0, x1=behind),
                        dict(k="snd", t=h - 0.04, fam="teleport", seed=2, g=0.7)]
            self.label(h, "TOO SLOW!", (255, 225, 60))
            end = h + 0.4
        elif kind == "jump_over":
            d_.key(h - 0.1, pose=P["crouch"], ease="out")
            d_.key(h + 0.05, pose=P["air"], lift=300, x=(x0 + behind) / 2, rot=f0 * 180, ease="out")
            d_.face(h + 0.05, -f0)
            d_.key(h + 0.22, pose=P["crouch"], lift=0, x=behind, rot=f0 * 360, ease="in")
            d_.key(h + 0.23, rot=0.0)
            d_.key(h + 0.45, pose=P["stance"], ease="back")
            self.ev += [dict(k="echo", w=d_, t0=h - 0.1, t1=h + 0.22, n=5), dict(k="land", t=h + 0.22, w=d_),
                        dict(k="snd", t=h - 0.1, fam="teleport", seed=5, g=0.6)]
            self.label(h, "DODGE!", (120, 220, 255))
            end = h + 0.5
        elif kind == "slide_under":
            d_.key(h - 0.06, pose=P["slide"], ease="snap")
            d_.key(h + 0.18, x=behind, ease="out")
            d_.face(h + 0.12, -f0)
            d_.key(h + 0.3, pose=P["crouch"], ease="out")
            d_.key(h + 0.5, pose=P["stance"], ease="back")
            self.ev += [dict(k="echo", w=d_, t0=h - 0.06, t1=h + 0.18, n=5), dict(k="dust", w=d_, t0=h - 0.06, t1=h + 0.2),
                        dict(k="snd", t=h - 0.06, fam="teleport", seed=6, g=0.6)]
            self.label(h, "DODGE!", (120, 220, 255))
            end = h + 0.5
        else:                                                         # vanish
            d_.k_alpha += [(h - 0.06, 1.0), (h - 0.02, 0.0, "lin"), (h + 0.16, 0.0), (h + 0.2, 1.0, "lin")]
            d_.hold(h + 0.16)
            d_.key(h + 0.17, x=behind, pose=P["stance"], ease="lin")
            d_.face(h + 0.17, -f0)
            self.ev += [dict(k="ghost", w=d_, t0=h - 0.02, t1=h + 0.35, x=x0),
                        dict(k="vanish", w=d_, t=h + 0.17, x0=x0, x1=behind),
                        dict(k="snd", t=h - 0.02, fam="teleport", seed=2, g=0.8)]
            self.label(h, "TOO SLOW!", (255, 225, 60))
            end = h + 0.35
        a.face(end + 0.1, -a.facing)                                  # l'attaquant se retourne
        a.key(end + 0.1, pose=P["hurt"] if False else mix(P["stance"], P["hurt"], 0.15), ease="snap")
        a.key(end + 0.3, pose=P["stance"])
        self.t = end + 0.12

    def launch(self, a, tgt, height=330):
        """Uppercut qui envoie l'adversaire en l'air."""
        self.hold(a, tgt)
        t = self.t
        a.key(t + 0.08, pose=P["crouch"], ease="out")
        h = t + 0.2
        a.key(h, pose=P["uppercut"], x=self.at_range(a, tgt, "uppercut", overlap=40), lift=40, ease="snap")
        tgt.hold(h)
        tgt.key(h + 0.05, pose=P["tumble"], ease="snap")
        tgt.key(h + 0.5, lift=height, x=tgt.x + a.facing * 60, rot=-a.facing * 200, ease="out")
        self.ev += [dict(k="arc", w=a, limb="fist", t0=t + 0.08, t1=h), dict(k="echo", w=a, t0=t + 0.08, t1=h, n=4),
                    dict(k="hit", t=h, att=a, tgt=tgt, p="heavy", limb="fist", y=GROUND - 360),
                    dict(k="echo", w=tgt, t0=h, t1=h + 0.5, n=4), dict(k="silhouette", t=h, inv=True),
                    dict(k="snd", t=h, fam="hit", seed=3, g=1.0)]
        self.stop(h, 0.1)
        self.punch_cam(h, tgt.x, GROUND - 380, z=1.3, tilt=6 * a.facing)
        a.key(h + 0.25, lift=0.0, ease="in")
        self.t = h + 0.5

    def air_smash(self, a, tgt):
        """Saute au-dessus de l'adversaire en l'air et le renvoie au sol à deux mains → cratère."""
        self.hold(a, tgt)
        t = self.t
        a.key(t + 0.08, pose=P["crouch"], ease="out")
        top = tgt.lift + 120
        a.key(t + 0.3, pose=P["hammer_up"], lift=top, x=tgt.x - a.facing * 70, ease="out")
        h = t + 0.42
        a.key(h, pose=P["hammer"], ease="snap")
        tgt.hold(h)
        land = h + 0.22
        tgt.key(land, lift=0.0, pose=P["down"], rot=0.0, ease="in")
        tgt.down = True
        a.key(land + 0.35, lift=0.0, pose=P["crouch"], ease="in")
        a.key(land + 0.6, pose=P["stance"], ease="back")
        self.ev += [dict(k="arc", w=a, limb="fist", t0=t + 0.32, t1=h), dict(k="echo", w=a, t0=t + 0.08, t1=t + 0.3, n=4),
                    dict(k="hit", t=h, att=a, tgt=tgt, p="heavy", limb="fist"), dict(k="echo", w=tgt, t0=h, t1=land, n=5),
                    dict(k="crater", t=land, w=tgt), dict(k="land", t=land + 0.35, w=a),
                    dict(k="snd", t=h, fam="hit", seed=6, g=1.0), dict(k="snd", t=land, fam="bomb", seed=2, g=1.0),
                    dict(k="silhouette", t=land, inv=False)]
        self.stop(h, 0.08)
        self.stop(land, 0.12)
        self.punch_cam(land, tgt.x, GROUND - 120, z=1.25, tilt=4, hold=0.5)
        self.t = land + 0.6

    def finisher_kick(self, a, tgt, knock=520):
        """Coup de pied qui envoie l'adversaire voler au loin (tumble + chute + glissade)."""
        self.hold(a, tgt)
        t = self.t
        a.key(t + 0.18, pose=P["kick_wind"], ease="out")
        h = t + 0.3
        a.key(h, pose=P["kick"], x=self.at_range(a, tgt, "kick", overlap=30), ease="snap")
        a.key(h + 0.6, pose=P["kick"])
        a.key(h + 0.9, pose=P["stance"])
        land = h + 0.6
        tgt.hold(h)
        tgt.key(h + 0.04, pose=P["tumble"], ease="snap")
        tgt.key(h + 0.3, lift=200, ease="out")
        tgt.key(land, lift=0.0, x=tgt.x + a.facing * knock, rot=a.facing * 330, ease="in")
        tgt.key(land + 0.01, pose=P["down"], rot=0.0)
        tgt.down = True
        self.ev += [dict(k="arc", w=a, limb="foot", t0=t + 0.18, t1=h), dict(k="echo", w=a, t0=t + 0.18, t1=h, n=4),
                    dict(k="hit", t=h, att=a, tgt=tgt, p="heavy", limb="foot", y=GROUND - 270),
                    dict(k="echo", w=tgt, t0=h, t1=land, n=5), dict(k="land", t=land, w=tgt),
                    dict(k="dust", w=tgt, t0=land, t1=land + 0.3), dict(k="silhouette", t=h, inv=True),
                    dict(k="snd", t=h, fam="hit", seed=2, g=1.0), dict(k="snd", t=land, fam="hit", seed=8, g=0.5)]
        self.stop(h, 0.1)
        self.punch_cam(h, tgt.x - a.facing * 60, GROUND - 270, z=1.35, tilt=-6 * a.facing)
        self.t = land + 0.5

    # ------------------------------------------------------------------ rendu
    def story(self, rt):
        s = rt
        for at, d in sorted(self.stops):
            if s > at:
                s = max(at, s - d)
        return s

    def real(self, s):
        return s + sum(d for at, d in self.stops if s > at)

    def render(self, out, bg, end_pad=0.6, title=None):
        out = Path(out)
        for w in self.who:
            w.build()
        END = self.t + end_pad
        CZ, CT = Track(self.cam_z), Track(self.cam_t)
        rnd = self.rnd
        rub = fx.Rubble(5)
        done = set()
        nf = int(self.real(END) * FPS)
        proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s",
                                 f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
                                 "-crf", "18", "-pix_fmt", "yuv420p", str(out.with_suffix(".video.mp4"))],
                                stdin=subprocess.PIPE)

        def draw_w(canvas, w, t, **kw):
            f = w.facing_at(t)
            return w.actors[f].draw(canvas, w.T_pose.at(t), w.T_x.at(t), 0, ground=GROUND, lift=w.T_lift.at(t),
                                    rot=w.T_rot.at(t), hair=w.hair_at(t), **kw)

        tmp = Image.new("RGBA", (W, H))
        for fi in range(nf):
            t = self.story(fi / FPS)
            img = bg.copy().convert("RGBA")
            sh = 0
            live = [e for e in self.ev if e.get("t0", e.get("t", 0)) - 0.02 <= t <= e.get("t1", e.get("t", 0)) + 1.0]
            # --- traits colorés, échos, arcs (sous les persos)
            for e in live:
                k = e["k"]
                if k == "streak" and e["t0"] <= t < e["t1"]:
                    w = e["w"]
                    x = w.T_x.at(t)
                    f = w.facing_at(t)
                    vx = w.T_x.at(t) - w.T_x.at(t - 0.03)
                    if abs(vx) > 1:
                        f = 1 if vx > 0 else -1
                    fx.color_streaks(img, GROUND - w.T_lift.at(t) - 330, GROUND - w.T_lift.at(t) - 20, w.color, n=14,
                                     t=t, x0=(0 if f > 0 else x + 60), x1=(x - 60 if f > 0 else W), alpha=130, dirx=f)
                if k == "echo" and e["t0"] <= t < e["t1"] + 0.04:
                    w = e["w"]
                    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                    n = e.get("n", 4)
                    for j in range(n, 0, -1):
                        tt = t - j * 0.02
                        draw_w(lay, w, tt, tint=w.color, alpha=e.get("a0", 0.55) * (1 - j / (n + 1)), record=False)
                    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(2.5)))
                if k == "arc" and e["t0"] <= t < e["t1"] + 0.08:
                    pts = []
                    for j in range(12, -1, -1):
                        tt = min(t, e["t1"]) - j * 0.01
                        if tt >= e["t0"]:
                            pts.append(draw_w(tmp, e["w"], tt, record=False)[e["limb"]])
                    fade = 1.0 if t < e["t1"] else max(0.0, 1 - (t - e["t1"]) / 0.08)
                    fx.arc_smear(img, pts, e["w"].color, width=70 if e["limb"] == "foot" else 50, alpha=int(200 * fade))
                if k == "ghost" and e["t0"] <= t < e["t1"]:                 # image rémanente de l'esquive
                    w = e["w"]
                    a_ = (t - e["t0"]) / (e["t1"] - e["t0"])
                    w.actors[w.facing_at(e["t0"])].draw(img, w.T_pose.at(e["t0"]), e["x"], 0, ground=GROUND,
                                                         tint=(200, 230, 255), alpha=0.6 * (1 - a_), record=False)
                if k == "vanish" and 0 <= t - e["t"] < 0.12:
                    fx.color_streaks(img, GROUND - 330, GROUND - 30, (200, 230, 255), n=16, t=t,
                                     x0=min(e["x0"], e["x1"]), x1=max(e["x0"], e["x1"]), alpha=170)
                if k == "dust" and e["t0"] <= t < e["t1"] and fi % 2 == 0:
                    rub.puff(e["w"].T_x.at(t), GROUND - 8, t, n=2, size=(26, 46), col=(215, 190, 150))
            # --- persos
            mask = Image.new("L", (W, H), 0)
            infos = {}
            for w in sorted(self.who, key=lambda w: -w.T_lift.at(t)):
                al = w.T_alpha.at(t)
                if al <= 0.01:
                    continue
                infos[w.name] = draw_w(img, w, t, shadow_y=GROUND, alpha=al, mask=mask)
            # --- impacts
            for e in live:
                k = e["k"]
                if k == "hit":
                    a_ = t - e["t"]
                    if a_ < 0:
                        continue
                    tgt = e["tgt"]
                    x = tgt.T_x.at(e["t"]) - e["att"].facing_at(e["t"]) * 60
                    y = e.get("y", GROUND - 320 - tgt.T_lift.at(t))
                    if e["p"] == "light" and a_ < 0.12:
                        fx.impact_star(img, x, y + rnd.uniform(-30, 30), 55 * (1 - a_ / 0.12) + 18, seed=int(e["t"] * 97))
                    if e["p"] == "heavy":
                        if a_ < 0.05:
                            fx.tint_flash(img, (255, 110, 90), 120)
                        if a_ < 0.12:
                            fx.manga_lines(img, x, y, col=(20, 20, 30), n=70, inner=200, alpha=int(220 * (1 - a_ / 0.12)),
                                           seed=int(e["t"] * 7))
                        if a_ < 0.3:
                            fx.impact_star(img, x, y, 150 * (1 - a_ / 0.3) + 40, seed=int(e["t"] * 13), rot=a_ * 2)
                        if a_ < 0.6:
                            fx.shock_rings(img, x, GROUND, a_ / 0.6)
                        sh = max(sh, 24 * max(0.0, 1 - a_ / 0.4))
                        if ("rub", e["t"]) not in done:
                            done.add(("rub", e["t"]))
                            rub.burst(x, GROUND, t, n=10)
                if k in ("land", "crater"):
                    a_ = t - e["t"]
                    if 0 <= a_ < 0.6:
                        xx = e["w"].T_x.at(e["t"])
                        big = k == "crater"
                        fx.shock_rings(img, xx, GROUND, a_ / 0.6, rx=480 if big else 260, col=(80, 70, 60) if big else (90, 90, 100))
                        if big and a_ < 0.3:
                            fx.impact_star(img, xx, GROUND - 40, 180 * (1 - a_ / 0.3) + 50, c_out=(240, 150, 60), seed=5)
                        sh = max(sh, (30 if big else 10) * max(0.0, 1 - a_ / 0.5))
                        if ("land", e["t"]) not in done:
                            done.add(("land", e["t"]))
                            rub.burst(xx, GROUND, t, n=22 if big else 8, power=1100 if big else 600)
                            rub.puff(xx, GROUND - 10, t, n=8 if big else 5)
                if k == "whiff" and 0 <= t - e["t"] < 0.12:
                    w = e["w"]
                    fx.color_streaks(img, GROUND - 360, GROUND - 260, (255, 255, 255), n=6, t=t,
                                     x0=w.T_x.at(t), x1=w.T_x.at(t) + w.facing_at(t) * 400, alpha=150)
            rub.draw(img, t)
            for e in live:
                if e["k"] == "silhouette" and 0 <= t - e["t"] < 0.07:
                    bgc, fgc = ((255, 255, 255), (10, 10, 14)) if e.get("inv") else ((10, 10, 14), (255, 255, 255))
                    fx.silhouette_frame(img, mask, bg=bgc, fg=fgc)
            # --- caméra : suit le milieu, ou vise un impact
            xs = [w.T_x.at(t) for w in self.who]
            cx, cy = (min(xs) + max(xs)) / 2, GROUND - 300
            cy -= max(w.T_lift.at(t) for w in self.who) * 0.5          # suit les persos en l'air
            for t0, t1, spec in self.cam_f:
                if t0 <= t < t1:
                    if spec[0] == "head":
                        inf = infos.get(spec[1].name)
                        if not inf:
                            continue
                        cx, cy = inf["head"][0], inf["head"][1] + 40
                        continue
                    x, y = spec
                    k = 1 - max(0.0, (t - t0) / (t1 - t0) - 0.5) * 2
                    cx, cy = cx + (x - cx) * k, cy + (y - cy) * k
            img = fx.camera(img, zoom=CZ.at(t), cx=cx, cy=cy, tilt=CT.at(t), shake=sh, rnd=rnd)
            # --- textes (hors caméra)
            for e in live:
                if e["k"] == "label" and 0 <= t - e["t"] < 0.7:
                    a_ = t - e["t"]
                    s_ = 1 + 0.4 * max(0.0, 1 - a_ / 0.1)
                    img = hud.label(img.convert("RGB"), (W / 2, 640), e["txt"], int(104 * s_), fill=e["col"],
                                    angle=-4).convert("RGBA")
            if title:
                L = Image.new("RGBA", img.size, (0, 0, 0, 0))
                hud.text3d(L, (W / 2, 120), title[0], hud.font("luckiest-guy.woff2", 96), (255, 255, 255),
                           side=(30, 60, 140), depth=10, outline=(20, 20, 50), ow=6)
                if len(title) > 1:
                    hud.text3d(L, (W / 2, 225), title[1], hud.font("luckiest-guy.woff2", 70), (255, 214, 50),
                               side=(150, 70, 10), depth=8, outline=(40, 15, 5), ow=5)
                img.alpha_composite(L.rotate(2, resample=Image.BICUBIC, center=(W / 2, 170)))
            proc.stdin.write(img.convert("RGB").tobytes())
        proc.stdin.close()
        proc.wait()
        self._sound(out, END)
        return out

    def _sound(self, out, END):
        from clipper.slides import domain, fusion, render
        rate = fusion.RATE
        na = int(self.real(END) * rate) + rate
        audio = np.zeros(na, np.float32)
        for e in self.ev:
            if e["k"] != "snd":
                continue
            x = domain.sfx(e["fam"], mode="anime", seed=e.get("seed", 0), franchise="dragon ball")
            if x is None:
                continue
            i = int(self.real(e["t"]) * rate)
            seg = x[: max(0, na - i)]
            audio[i:i + len(seg)] += seg * e.get("g", 1.0)
        lvl = float(np.percentile(np.abs(audio), 99.7)) or 1.0
        audio = audio * min(1.0, 0.75 / lvl)
        wav = out.with_suffix(".wav")
        fusion.write_wav(wav, np.tanh(audio * 1.1) / math.tanh(1.1) * 0.3)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out.with_suffix(".video.mp4")), "-i", str(wav),
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", str(out.with_suffix(".raw.mp4"))],
                       check=True)
        render.stamp_video(out.with_suffix(".raw.mp4"), out)
