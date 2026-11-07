"""Démo du moteur stickman (07/11) : Goku vs un sparring partner, toutes les situations à la suite.
python3 tools/punch/demo_moves.py "library/_sticknodes/Goku SSJ1.json" <sortie.mp4>
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
import goku_poses as gp  # noqa: E402
import hud  # noqa: E402
import rig  # noqa: E402
import sticknodes as sn  # noqa: E402
import stickanim as sa  # noqa: E402
from stickanim import P, Track  # noqa: E402
from mugen_punch import GROUND, H, W, FPS, mountains  # noqa: E402
from one_punch_line import desert_sky  # noqa: E402
from clipper.slides import fusion, render, vfxgen  # noqa: E402

BLACK, GOLD = (22, 22, 28), (255, 225, 40)
STOPS = [(3.45, .08), (4.6, .08), (7.3, .1), (8.85, .08), (11.6, .12), (16.5, .1)]   # arrêts sur impact


def story(t):
    """temps réel → temps de la chorégraphie (arrêts sur image aux impacts)."""
    s = t
    for at, d in STOPS:
        if s > at:
            s = max(at, s - d)
    return s


def real(s):
    r = s
    for at, d in STOPS:
        if s > at:
            r += d
    return r


def mix(a, b, k):
    return sa.lerp(a, b, k)


SEGS = [(0, "IDLE"), (2.0, "COMBO"), (4.4, "KICK"), (6.3, "INSTANT TRANSMISSION"), (8.4, "GETTING HIT"),
        (9.6, "TRANSFORM"), (12.4, "FLY"), (15.0, "KAMEHAMEHA")]
END = 18.4

# ------------------------------------------------------------------ Goku
G_POSE = Track([
    (0, P["stance"]), (0.5, P["stance_low"]), (1.0, P["stance"]), (1.5, P["stance_low"]), (2.0, P["stance"]),
    (2.08, P["run_a"], "out"), (2.2, P["run_b"]), (2.32, P["run_a"]), (2.42, P["stance"], "out"),
    (2.52, P["jab"], "snap"), (2.68, P["stance"], "out"), (2.8, P["cross"], "snap"), (2.98, P["stance"], "out"),
    (3.25, P["windup"], "out"), (3.45, P["punch"], "snap"), (3.9, P["punch"]), (4.25, P["stance"]),
    (4.45, P["kick_wind"], "out"), (4.6, P["kick"], "snap"), (5.0, P["kick"]), (5.35, P["stance"]),
    (6.4, P["stance"]), (6.7, P["tp"], "back"), (7.0, P["tp"]), (7.12, P["crouch"]), (7.3, P["fly_up"], "snap"),
    (7.7, P["fly_up"]), (8.1, P["stance"]),
    (8.82, P["stance"]), (8.9, P["hurt"], "snap"), (9.3, P["hurt"]), (9.6, P["stance"], "back"),
    (9.9, P["power"], "out"), (10.2, P["scream"], "out"), (11.55, P["scream"]), (11.62, P["power"], "snap"),
    (12.2, P["stance"]),
    (12.5, P["crouch"], "out"), (12.7, P["air"], "snap"), (12.9, P["fly"], "out"), (13.6, P["fly"]),
    (14.1, P["fly"]), (14.25, P["air"]), (14.5, P["crouch"], "in"), (14.8, P["stance"], "back"),
    (15.0, P["stance"]), (15.3, P["kame_charge"], "out"), (16.45, P["kame_charge"]), (16.5, P["kame_fire"], "snap"),
    (17.6, P["kame_fire"]), (18.0, P["stance"]),
])
G_X = Track([(0, 180), (2.0, 180), (2.42, 384, "out"), (3.25, 384), (3.45, 410, "snap"), (3.9, 400), (4.45, 400),
             (4.6, 420, "snap"), (6.95, 420), (7.0, 420), (7.12, 745), (7.3, 745), (8.1, 745), (8.82, 745),
             (9.3, 540, "out"), (12.5, 540), (12.9, 620), (13.25, 1400, "in"), (13.3, -300), (14.1, 460, "out"),
             (14.5, 500), (16.4, 500), (16.6, 450, "out"), (18.4, 450)])
G_LIFT = Track([(0, 0), (0.5, 0), (7.12, 0), (7.3, 60, "snap"), (7.7, 0, "in"), (8.85, 0), (8.95, 20, "snap"),
                (9.3, 0, "in"), (12.6, 0), (12.75, 160, "snap"), (12.9, 420), (13.6, 480), (14.1, 480),
                (14.5, 0, "in"), (18.4, 0)])

# ------------------------------------------------------------------ partenaire (regarde à gauche)
hurt_s = mix(P["stance"], P["hurt"], 0.45)
T_POSE = Track([
    (0, P["stance"]), (0.5, P["stance_low"]), (1.0, P["stance"]), (1.5, P["stance_low"]), (2.0, P["stance"]),
    (2.5, P["stance"]), (2.55, hurt_s, "snap"), (2.7, P["stance"]), (2.82, P["stance"]), (2.87, hurt_s, "snap"),
    (3.05, P["stance"]), (3.45, P["stance"]), (3.5, P["hurt"], "snap"), (3.95, P["hurt"]), (4.3, P["stance"]),
    (4.6, P["stance"]), (4.65, P["tumble"], "snap"), (5.45, P["tumble"]), (5.55, P["down"], "snap"), (6.4, P["down"]),
    (6.7, P["crouch"], "out"), (7.0, P["stance"], "back"), (7.3, P["stance"]), (7.35, P["tumble"], "snap"),
    (7.9, P["tumble"]), (8.25, P["air"]), (8.4, P["crouch"], "in"), (8.6, P["stance"]),
    (8.62, P["windup"], "out"), (8.85, P["punch"], "snap"), (9.2, P["punch"]), (9.5, P["stance"]),
    (11.6, P["stance"]), (11.65, P["block"], "snap"), (12.3, P["block"]), (12.6, P["stance"]),
    (16.5, P["stance"]), (16.55, P["tumble"], "snap"), (18.4, P["tumble"]),
])
T_X = Track([(0, 640), (3.45, 640), (3.95, 720, "out"), (4.6, 720), (5.55, 870, "lin"), (5.9, 895, "out"),
             (6.7, 895), (7.0, 895), (7.3, 895), (7.9, 925, "out"), (8.4, 935), (8.6, 935), (8.85, 900, "snap"),
             (11.6, 900), (12.0, 950, "out"), (16.5, 950), (17.6, 1500, "in")])
T_LIFT = Track([(0, 0), (4.6, 0), (5.0, 230, "out"), (5.55, 0, "in"), (7.3, 0), (7.8, 430, "out"), (8.4, 0, "in"),
                (16.5, 0), (17.0, 160, "out"), (17.6, 260)])
T_ROT = Track([(0, 0), (4.6, 0), (5.55, 330), (5.56, 0), (7.3, 0), (8.25, -360), (8.26, 0), (16.5, 0), (17.6, 500)])


def gray_gi(c):
    r, g, b, a = c
    if r > 200 and g < 120:                                       # orange du gi → gris sombre
        return (70, 70, 85, a)
    if b > 200 and r < 60:                                        # bleu → violet
        return (120, 40, 140, a)
    return c


def main():
    fig = sn.load(sys.argv[1])
    out = Path(sys.argv[2])
    goku = sa.Actor(fig, scale=0.9, hair_nodes_colors=gp.HAIR_COLORS)
    foe = sa.Actor(fig, scale=0.9, hair_nodes_colors=gp.HAIR_COLORS, flip=True, recolor=gray_gi)
    far = mountains(1, (214, 150, 110, 255), 260, 1080, 420, W * 2)
    near = mountains(2, (176, 108, 72, 255), 150, 1190, 260, W * 2)
    bg = desert_sky().convert("RGBA")
    bg.alpha_composite(far.crop((0, 0, W, H)))
    bg.alpha_composite(near.crop((0, 0, W, H)))
    bd = ImageDraw.Draw(bg)
    bd.rectangle((0, 1180, W, H), fill=(222, 178, 120))
    for k in range(9):
        bd.ellipse((k * 130 + 20, GROUND + 140 + (k % 3) * 60, k * 130 + 70, GROUND + 165 + (k % 3) * 60), fill=(196, 140, 96))
    bg = bg.convert("RGB")
    hitfx = list(vfxgen.frames("hit", 300, (255, 230, 140)))
    ring = list(vfxgen.frames("ring", 600, (255, 240, 180)))
    explo = list(vfxgen.frames("explosion", 520, (120, 200, 255)))
    bolt = list(vfxgen.frames("lightning", 240, (255, 240, 120)))
    rnd = random.Random(4)
    puffs, sparks, debris = [], [], []
    impacts = []                                                   # (t, x, y, kind)
    fired = set()

    def once(key):
        if key in fired:
            return False
        fired.add(key)
        return True
    nf = int(real(END) * FPS)
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s",
                             f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf",
                             "18", "-pix_fmt", "yuv420p", str(out.with_suffix(".video.mp4"))], stdin=subprocess.PIPE)
    for fi in range(nf):
        rt = fi / FPS
        t = story(rt)
        img = bg.copy().convert("RGBA")
        d = ImageDraw.Draw(img, "RGBA")
        sh = 0
        hair = BLACK if t < 11.6 else GOLD
        # ---------------------------------------------------- aura de transformation (derrière Goku)
        gx, glift = G_X.at(t), G_LIFT.at(t)
        if 9.9 <= t < 12.6 or t >= 11.6:
            p_ = min(1.0, (t - 9.9) / 1.2) if t < 11.6 else (1.0 if t < 12.2 else 0.45)
            col = (255, 255, 255) if t < 11.6 else GOLD
            if t < 11.6:
                col = (180, 200, 255)
            au = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ad = ImageDraw.Draw(au)
            ch = 300
            for scl, al in ((1.25, 120), (1.0, 160), (0.7, 130)):
                c2 = tuple(min(255, v + int(80 * (1 - scl))) for v in col)
                ad.polygon(rig.aura_poly(gx, GROUND - glift - ch * 0.75, (95 + 50 * p_) * scl, ch * scl * (0.8 + 0.4 * p_),
                                         t * 1.4 + scl, n=28, seed=int(scl * 10)), fill=c2 + (int(al * p_),))
            g_ = au.filter(ImageFilter.GaussianBlur(14))
            img.alpha_composite(g_)
            img.alpha_composite(au)
            if 10.2 <= t < 11.6:
                sh = 3 + 6 * (t - 10.2) / 1.4
                if rnd.random() < 0.35:                               # cailloux qui montent
                    debris.append([gx + rnd.uniform(-260, 260), GROUND, rnd.uniform(-20, 20), -rnd.uniform(60, 180), t,
                                   rnd.uniform(5, 12), 2.0, -1])
                if fi % 3 == 0:
                    b = bolt[fi // 3 % len(bolt)]
                    img.paste(b, (int(gx - b.width / 2 + rnd.uniform(-90, 90)), int(GROUND - 380 + rnd.uniform(0, 160))), b)
        # ---------------------------------------------------- lignes de vitesse (dash / vol)
        if 2.0 <= t < 2.42 or 12.8 <= t < 14.2:
            for _ in range(10):
                y = rnd.uniform(GROUND - 520, GROUND - 40)
                x = rnd.uniform(0, W)
                d.line((x, y, x + rnd.uniform(160, 420), y), fill=(255, 255, 255, 110), width=3)
        # ---------------------------------------------------- partenaire
        fx, flift, frot = T_X.at(t), T_LIFT.at(t), T_ROT.at(t)
        foe.draw(img, T_POSE.at(t), fx, 0, ground=GROUND, lift=flift, rot=frot, hair=(30, 30, 30),
                 trail=3 if (4.6 < t < 5.5 or 7.3 < t < 8.3 or t > 16.5) else 0, shadow_y=GROUND)
        # ---------------------------------------------------- Goku
        alpha = 1.0
        if 7.0 <= t < 7.12:                                            # Instant Transmission : il se dissout
            alpha = max(0.0, 1 - (t - 7.0) / 0.1)
            for j in range(8):
                xx = 530 + rnd.uniform(-60, 60)
                d.line((xx, GROUND - 420, xx, GROUND), fill=(255, 255, 255, 140), width=3)
        fast = (2.0 < t < 2.45) or (3.3 < t < 3.6) or (4.45 < t < 4.7) or (12.7 < t < 14.4) or (7.1 < t < 7.4)
        info = goku.draw(img, G_POSE.at(t), gx, 0, ground=GROUND, lift=glift, hair=hair, alpha=alpha,
                         trail=4 if fast else 0, ghost_col=(255, 240, 160) if t > 11.6 else (200, 220, 255),
                         shadow_y=GROUND)
        if 7.12 <= t < 7.25:                                           # réapparition : anneau + traits
            k = (t - 7.12) / 0.13
            d.ellipse((gx - 90 - 120 * k, GROUND - 260 - 120 * k, gx + 90 + 120 * k, GROUND - 40 + 120 * k),
                      outline=(255, 255, 255, int(220 * (1 - k))), width=6)
        # ---------------------------------------------------- Kamehameha
        if 15.3 <= t < 16.5:
            k = min(1.0, (t - 15.3) / 1.1)
            hx, hy = info["fist"]
            r = 10 + 46 * k
            gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(gl).ellipse((hx - r * 2.4, hy - r * 2.4, hx + r * 2.4, hy + r * 2.4), fill=(90, 170, 255, 170))
            img.alpha_composite(gl.filter(ImageFilter.GaussianBlur(r)))
            d = ImageDraw.Draw(img, "RGBA")
            d.ellipse((hx - r, hy - r, hx + r, hy + r), fill=(220, 240, 255))
            for j in range(6):
                an = j * 1.05 + t * 7
                rr = 160 * (1 - ((t * 2.5 + j * 0.17) % 1))
                d.line((hx + math.cos(an) * rr, hy + math.sin(an) * rr, hx + math.cos(an) * (rr + 34),
                        hy + math.sin(an) * (rr + 34)), fill=(170, 220, 255, 230), width=5)
            sh = max(sh, 3 * k)
        if 16.5 <= t < 17.7:
            hx, hy = info["fist"]
            k = min(1.0, (t - 16.5) / 0.08)
            fade = 1.0 if t < 17.4 else max(0.0, 1 - (t - 17.4) / 0.3)
            x2 = hx + (W + 200 - hx) * k
            th = 90 * fade * (1 + 0.08 * math.sin(t * 60))
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ld = ImageDraw.Draw(lay)
            ld.rounded_rectangle((hx, hy - th, x2, hy + th), int(th), fill=(70, 150, 255, 210))
            ld.rounded_rectangle((hx, hy - th * 0.55, x2, hy + th * 0.55), int(th * 0.55), fill=(170, 220, 255, 240))
            ld.rounded_rectangle((hx, hy - th * 0.25, x2, hy + th * 0.25), int(th * 0.25), fill=(255, 255, 255, 255))
            ld.ellipse((hx - th * 1.3, hy - th * 1.3, hx + th * 1.3, hy + th * 1.3), fill=(200, 235, 255, 230))
            img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(20)))
            img.alpha_composite(lay)
            d = ImageDraw.Draw(img, "RGBA")
            sh = max(sh, 14 * fade)
            if once("kame_hit"):
                impacts.append((t, T_X.at(t), GROUND - 200, "explo"))
        # ---------------------------------------------------- impacts programmés
        for at, who, kind in ((2.52, "f", "small"), (2.82, "f", "small"), (3.45, "f", "big"), (4.6, "f", "big"),
                              (7.3, "f", "big"), (8.85, "g", "big"), (11.6, "g", "wave")):
            if t >= at and once(("imp", at)):
                if who == "f":
                    x, y = info["fist"] if at not in (4.6, 7.3) else ((fx - 60, GROUND - 260) if at == 4.6 else (fx - 40, GROUND - 330))
                else:
                    x, y = gx + 40, GROUND - 230
                impacts.append((t, x, y, kind))
        for (t0, x, y, kind) in impacts:
            a_ = t - t0
            if kind in ("small", "big") and a_ < 0.3:
                fr = hitfx[min(len(hitfx) - 1, int(a_ / 0.3 * len(hitfx)))]
                s_ = 0.6 if kind == "small" else 1.2
                fr = fr.resize((int(fr.width * s_), int(fr.height * s_)))
                img.alpha_composite(fr, (int(x - fr.width / 2), int(y - fr.height / 2)))
                if kind == "big":
                    rr = ring[min(len(ring) - 1, int(a_ / 0.3 * len(ring)))]
                    img.alpha_composite(rr, (int(x - rr.width / 2), int(y - rr.height / 2)))
                    sh = max(sh, 22 * (1 - a_ / 0.3))
                    if a_ < 1 / FPS:
                        for _ in range(14):
                            ang = rnd.uniform(-1.2, 1.2)
                            sparks.append([x, y, math.cos(ang) * rnd.uniform(500, 1100), math.sin(ang) * rnd.uniform(500, 1100), t])
            if kind == "wave" and a_ < 0.6:
                rr = ring[min(len(ring) - 1, int(a_ / 0.6 * len(ring)))]
                rr = rr.resize((int(rr.width * 2), int(rr.height * 2)))
                img.alpha_composite(rr, (int(x - rr.width / 2), int(y - rr.height / 2)))
                if a_ < 0.12:
                    ImageDraw.Draw(img, "RGBA").rectangle((0, 0, W, H), fill=(255, 245, 190, int(240 * (1 - a_ / 0.12))))
                sh = max(sh, 26 * (1 - a_ / 0.6))
            if kind == "explo" and a_ < 0.9:
                fr = explo[min(len(explo) - 1, int(a_ / 0.9 * len(explo)))]
                img.alpha_composite(fr, (int(x - fr.width / 2), int(y - fr.height / 2)))
        d = ImageDraw.Draw(img, "RGBA")
        # poussière : atterrissages, glissades
        for at, x_of in ((5.55, lambda: T_X.at(t)), (8.4, lambda: T_X.at(t)), (14.5, lambda: G_X.at(t)),
                         (9.0, lambda: G_X.at(t)), (3.6, lambda: T_X.at(t))):
            if at <= t < at + 0.35 and fi % 2 == 0:
                for _ in range(3):
                    puffs.append([x_of() + rnd.uniform(-60, 60), GROUND - 10, rnd.uniform(30, 55), t])
        keep = []
        for pf in puffs:
            a_ = t - pf[3]
            if a_ < 0.8:
                r = pf[2] * (1 + a_ * 1.8)
                d.ellipse((pf[0] - r, pf[1] - r * 0.6 - a_ * 50, pf[0] + r, pf[1] + r * 0.6 - a_ * 50),
                          fill=(225, 195, 150, int(170 * (1 - a_ / 0.8))))
                keep.append(pf)
        puffs[:] = keep
        keep = []
        for sp in sparks:
            a_ = t - sp[4]
            if a_ < 0.25:
                x, y = sp[0] + sp[2] * a_, sp[1] + sp[3] * a_
                d.line((x, y, x - sp[2] * 0.03, y - sp[3] * 0.03), fill=(255, 250, 200, int(255 * (1 - a_ / 0.25))), width=4)
                keep.append(sp)
        sparks[:] = keep
        keep = []
        for db in debris:
            a_ = t - db[4]
            if a_ < db[6]:
                x, y = db[0] + db[2] * a_, db[1] + db[3] * a_
                s = db[5]
                d.polygon([(x - s, y), (x - s * .3, y - s), (x + s, y - s * .4), (x + s * .6, y + s * .7)], fill=(150, 110, 75))
                keep.append(db)
        debris[:] = keep
        # ---------------------------------------------------- textes
        name = [n for s0, n in SEGS if t >= s0][-1]
        s0 = [s0 for s0, n in SEGS if t >= s0][-1]
        a_ = t - s0
        sc = 1 + 0.3 * max(0.0, 1 - a_ / 0.12)
        img = hud.label(img.convert("RGB"), (W / 2, 210), name, int(84 * sc), fill=(255, 214, 50), angle=-2).convert("RGBA")
        base = img
        L = Image.new("RGBA", base.size, (0, 0, 0, 0))
        hud.text3d(L, (W / 2, 90), "STICKMAN ENGINE", hud.font("luckiest-guy.woff2", 70), (255, 255, 255),
                   side=(30, 60, 140), depth=8, outline=(20, 20, 50), ow=5)
        base.alpha_composite(L)
        img = base.convert("RGB")
        if sh:
            dx, dy = rnd.randint(-int(sh), int(sh)), rnd.randint(-int(sh), int(sh))
            bgf = Image.new("RGB", (W, H), (0, 0, 0))
            bgf.paste(img, (dx, dy))
            img = bgf
        proc.stdin.write(img.tobytes())
    proc.stdin.close()
    proc.wait()
    # ---------------------------------------------------- son
    from clipper.slides import domain
    rate = fusion.RATE
    na = int(real(END) * rate) + rate
    audio = np.zeros(na, np.float32)

    def put(s_, x, g):
        if x is None:
            return
        i = int(real(s_) * rate)
        seg = x[: max(0, na - i)]
        audio[i:i + len(seg)] += seg * g
    S = lambda fam, seed=0: domain.sfx(fam, mode="anime", seed=seed, franchise="dragon ball")  # noqa: E731
    put(2.0, S("teleport", 1), 0.4)
    put(2.52, S("hit", 5), 0.5)
    put(2.82, S("hit", 6), 0.6)
    put(3.45, S("hit", 1), 1.0)
    put(4.6, S("hit", 2), 1.0)
    put(5.55, S("hit", 7), 0.5)
    put(7.0, S("teleport", 2), 0.8)
    put(7.3, S("hit", 3), 1.0)
    put(8.4, S("hit", 8), 0.4)
    put(8.85, S("hit", 4), 1.0)
    put(9.9, S("transform"), 0.9)
    put(11.6, S("bomb", 2), 0.9)
    put(12.7, S("teleport", 3), 0.5)
    put(14.5, S("hit", 9), 0.5)
    put(15.3, S("beam", 1), 0.6)
    put(16.5, S("beam", 2), 0.9)
    put(16.6, S("bomb", 4), 0.8)
    lvl = float(np.percentile(np.abs(audio), 99.7)) or 1.0
    audio = audio * min(1.0, 0.75 / lvl)
    wav = out.with_suffix(".wav")
    fusion.write_wav(wav, np.tanh(audio * 1.1) / math.tanh(1.1) * 0.3)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out.with_suffix(".video.mp4")), "-i", str(wav),
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", str(out.with_suffix(".raw.mp4"))],
                   check=True)
    render.stamp_video(out.with_suffix(".raw.mp4"), out)
    print("OUT", out, round(real(END), 1))


if __name__ == "__main__":
    main()
