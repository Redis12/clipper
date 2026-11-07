"""Démo v2 du moteur stickman (07/11) : même chorégraphie que demo_moves.py, avec les effets tirés des vidéos de
référence (ANALYSE_STICKMAN.md) : écho de mouvement, arcs de traînée, traits de vitesse colorés, étoiles d'impact,
lignes manga, flash teinté, impact frames silhouette, anneaux de choc, débris, colonne d'énergie, liseré lumineux,
caméra (zoom, horizon penché).
python3 tools/punch/demo_moves2.py "library/_sticknodes/Goku SSJ1.json" <sortie.mp4>
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
import stickanim as sa  # noqa: E402
import stickfx as fx  # noqa: E402
import sticknodes as sn  # noqa: E402
from demo_moves import (BLACK, END, G_LIFT, G_POSE, G_X, GOLD, SEGS, T_LIFT, T_POSE, T_ROT, T_X, gray_gi, real,  # noqa: E402
                        story)
from stickanim import Track  # noqa: E402
from mugen_punch import GROUND, H, W, FPS, mountains  # noqa: E402
from one_punch_line import desert_sky  # noqa: E402
from clipper.slides import fusion, render, vfxgen  # noqa: E402

ORANGE, PURPLE, SKY = (245, 110, 30), (130, 60, 160), (120, 200, 255)
G_ROT = Track([(0, 0), (12.8, 0), (12.9, 0), (14.1, 0), (18.4, 0)])
# caméra : (t, zoom, cx, cy, tilt)
CAM_Z = Track([(0, 1.0), (3.44, 1.0), (3.47, 1.35, "snap"), (3.85, 1.0, "smooth"), (4.58, 1.0), (4.62, 1.2, "snap"),
               (5.0, 1.0), (7.28, 1.0), (7.32, 1.3, "snap"), (7.8, 1.0), (8.83, 1.0), (8.87, 1.3, "snap"), (9.3, 1.0),
               (9.9, 1.0), (11.5, 1.28, "in"), (11.62, 1.0, "snap"), (16.45, 1.0), (16.5, 1.18, "snap"), (17.2, 1.0)])
CAM_T = Track([(0, 0), (3.44, 0), (3.47, -5, "snap"), (3.85, 0), (7.28, 0), (7.32, 6, "snap"), (7.8, 0), (8.83, 0),
               (8.87, -4, "snap"), (9.3, 0), (12.8, 0), (13.0, -6), (14.1, -6), (14.4, 0), (16.45, 0), (16.5, 3, "snap"),
               (17.2, 0)])
CAM_F = Track([(0, 0.0), (9.9, 0.0), (11.5, 1.0), (11.62, 0.0)])    # 1 = la caméra se centre sur Goku (transfo)


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
    explo = list(vfxgen.frames("explosion", 520, (120, 200, 255)))
    bolt = list(vfxgen.frames("lightning", 240, (255, 240, 120)))
    bolt_b = list(vfxgen.frames("lightning", 200, (140, 210, 255)))
    rnd = random.Random(4)
    rub = fx.Rubble(5)
    fired = set()

    def once(key):
        if key in fired:
            return False
        fired.add(key)
        return True

    def echo(actor, canvas, pose_tr, x_tr, lift_tr, rot_tr, t, n, dt, col, hair, a0=0.55):
        """écho de mouvement : la pose rendue à des instants intermédiaires, teintée, floutée."""
        lay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        infos = []
        for k in range(n, 0, -1):
            tt = t - k * dt
            infos.append(actor.draw(lay, pose_tr.at(tt), x_tr.at(tt), 0, ground=GROUND, lift=lift_tr.at(tt),
                                    rot=rot_tr.at(tt) if rot_tr else 0, hair=hair, tint=col,
                                    alpha=a0 * (1 - k / (n + 1)), record=False))
        canvas.alpha_composite(lay.filter(ImageFilter.GaussianBlur(2.5)))
        return infos
    nf = int(real(END) * FPS)
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s",
                             f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf",
                             "18", "-pix_fmt", "yuv420p", str(out.with_suffix(".video.mp4"))], stdin=subprocess.PIPE)
    for fi in range(nf):
        rt = fi / FPS
        t = story(rt)
        frozen = t != rt - sum(d for at, d in [] if 0)                    # (info) l'arrêt sur image = même t
        img = bg.copy()
        sh = 0
        hair = BLACK if t < 11.6 else GOLD
        gx, glift = G_X.at(t), G_LIFT.at(t)
        fx_x, flift, frot = T_X.at(t), T_LIFT.at(t), T_ROT.at(t)
        tf = (t - 9.9) / 1.6                                              # avancement de la charge de transformation
        # ------------------------------------------------ décor : lignes de vitesse, colonne d'énergie
        if 12.8 <= t < 14.2:
            fx.bg_speed_lines(img, t, angle=-6, alpha=140)
        if 9.9 <= t < 11.6:
            fx.power_column(img, gx, GROUND, min(1.0, tf * 1.4), col=(200, 225, 255), t=t)
        if 11.6 <= t < 12.3:
            fx.power_column(img, gx, GROUND, max(0.0, 1 - (t - 11.6) / 0.7), col=GOLD, t=t, width=320)
        if 15.3 <= t < 16.5:
            fx.power_column(img, gx - 60, GROUND, min(1.0, (t - 15.3) / 1.0) * 0.5, col=SKY, t=t, width=180)
        # aura (rig.aura_poly) derrière Goku
        if 9.9 <= t:
            p_ = min(1.0, tf) if t < 11.6 else (1.0 if t < 12.2 else 0.5)
            col = (190, 210, 255) if t < 11.6 else GOLD
            au = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ad = ImageDraw.Draw(au)
            for scl, al in ((1.25, 120), (1.0, 160), (0.7, 130)):
                c2 = tuple(min(255, v + int(80 * (1 - scl))) for v in col)
                ad.polygon(rig.aura_poly(gx, GROUND - glift - 230, (95 + 50 * p_) * scl, 300 * scl * (0.8 + 0.4 * p_),
                                         t * 1.4 + scl, n=28, seed=int(scl * 10)), fill=c2 + (int(al * p_),))
            img.alpha_composite(au.filter(ImageFilter.GaussianBlur(14)))
            img.alpha_composite(au)
        # traits de vitesse colorés (dash, vol, TP)
        if 2.0 <= t < 2.42:
            fx.color_streaks(img, GROUND - 330, GROUND - 20, ORANGE, n=14, t=t, x0=0, x1=gx - 60, alpha=120)
        if 12.85 <= t < 14.15:
            fx.color_streaks(img, GROUND - glift - 300, GROUND - glift, GOLD, n=16, t=t, x0=0, x1=gx - 80, alpha=150)
        if 7.12 <= t < 7.22:
            fx.color_streaks(img, GROUND - 330, GROUND - 40, SKY, n=16, t=t, x0=430, x1=gx, alpha=180)
        # ------------------------------------------------ échos (avant les persos)
        if 2.0 <= t < 2.45 or 3.3 <= t < 3.55 or 4.45 <= t < 4.7 or 7.1 <= t < 7.4 or 12.7 <= t < 14.5:
            gcol = ORANGE if t < 11.6 else GOLD
            if 7.1 <= t < 7.4:
                gcol = SKY
            g_echo = echo(goku, img, G_POSE, G_X, G_LIFT, None, t, 5, 0.018, gcol, hair)
        else:
            g_echo = []
        if 4.62 <= t < 5.6 or 7.32 <= t < 8.4 or t >= 16.5 or 3.47 <= t < 3.9:
            echo(foe, img, T_POSE, T_X, T_LIFT, T_ROT, t, 4, 0.025, PURPLE, (30, 30, 30), a0=0.45)
        # arcs de traînée du membre qui frappe (sous-positions du poing/pied)
        for t0, t1, key, col in ((2.44, 2.56, "fist", ORANGE), (2.72, 2.86, "fist_b", ORANGE), (3.3, 3.5, "fist", ORANGE),
                                 (4.47, 4.66, "foot", ORANGE), (7.16, 7.34, "fist", SKY)):
            if t0 <= t < t1 + 0.08:
                pts = []
                for k in range(12, -1, -1):
                    tt = min(t, t1) - k * 0.012
                    if tt < t0:
                        continue
                    info = goku.draw(Image.new("RGBA", (8, 8)), G_POSE.at(tt), G_X.at(tt), 0, ground=GROUND,
                                     lift=G_LIFT.at(tt), record=False) if False else None
                    pts.append(tt)
                # positions réelles : rendu léger dans une image vide
                P_ = []
                tmp = Image.new("RGBA", (W, H))
                for tt in pts:
                    info = goku.draw(tmp, G_POSE.at(tt), G_X.at(tt), 0, ground=GROUND, lift=G_LIFT.at(tt), record=False)
                    P_.append(info[key])
                fade = 1.0 if t < t1 else max(0.0, 1 - (t - t1) / 0.08)
                fx.arc_smear(img, P_, col, width=70 if key == "foot" else 52, alpha=int(200 * fade))
        if 8.66 <= t < 8.95:                                              # coup du partenaire
            P_ = []
            tmp = Image.new("RGBA", (W, H))
            for k in range(10, -1, -1):
                tt = min(t, 8.85) - k * 0.015
                if tt >= 8.66:
                    P_.append(foe.draw(tmp, T_POSE.at(tt), T_X.at(tt), 0, ground=GROUND, lift=T_LIFT.at(tt),
                                       record=False)["fist"])
            fx.arc_smear(img, P_, PURPLE, width=52, alpha=int(200 * (1.0 if t < 8.85 else max(0, 1 - (t - 8.85) / 0.1))))
        # ------------------------------------------------ persos
        mask = Image.new("L", (W, H), 0)
        foe_info = foe.draw(img, T_POSE.at(t), fx_x, 0, ground=GROUND, lift=flift, rot=frot, hair=(30, 30, 30),
                            shadow_y=GROUND, mask=mask)
        alpha = 1.0
        if 7.0 <= t < 7.12:
            alpha = max(0.0, 1 - (t - 7.0) / 0.1)
        glow = None
        if 9.9 <= t < 11.6:
            glow = ((255, 255, 255), 12, min(1.0, tf * 1.3))
        elif 11.6 <= t:
            glow = (GOLD, 10, 0.9 if t < 12.3 else 0.5)
        if 15.3 <= t < 16.5:
            glow = (SKY, 12, 1.0)
        info = goku.draw(img, G_POSE.at(t), gx, 0, ground=GROUND, lift=glift, hair=hair, alpha=alpha, shadow_y=GROUND,
                         glow=glow, mask=mask)
        if 7.0 <= t < 7.12:
            d = ImageDraw.Draw(img, "RGBA")
            for j in range(8):
                xx = 420 + rnd.uniform(-60, 60)
                d.line((xx, GROUND - 420, xx, GROUND), fill=(255, 255, 255, 160), width=3)
        # transformation : arcs, éclairs, cailloux qui montent
        if 9.9 <= t < 11.6:
            fx.swirl_arcs(img, gx, GROUND - 260, min(1.0, tf * 1.2), t, col=(200, 225, 255))
            sh = max(sh, 3 + 7 * tf)
            if fi % 2 == 0:
                rub.rocks.append([gx + rnd.uniform(-260, 260), GROUND, rnd.uniform(-20, 20), -rnd.uniform(120, 260), t,
                                  rnd.uniform(5, 12), (60, 55, 50), GROUND + 9999])
            if fi % 3 == 0:
                b = bolt[fi // 3 % len(bolt)]
                img.alpha_composite(b, (int(gx - b.width / 2 + rnd.uniform(-90, 90)), int(GROUND - 380 + rnd.uniform(0, 160))))
        if 15.3 <= t < 16.5:                                              # Kamehameha : charge
            k = min(1.0, (t - 15.3) / 1.1)
            hx, hy = info["fist"]
            r = 10 + 50 * k
            gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(gl).ellipse((hx - r * 2.4, hy - r * 2.4, hx + r * 2.4, hy + r * 2.4), fill=(90, 170, 255, 170))
            img.alpha_composite(gl.filter(ImageFilter.GaussianBlur(r)))
            d = ImageDraw.Draw(img, "RGBA")
            d.ellipse((hx - r, hy - r, hx + r, hy + r), fill=(225, 242, 255))
            for j in range(7):
                an = j * 0.9 + t * 7
                rr = 170 * (1 - ((t * 2.5 + j * 0.15) % 1))
                d.line((hx + math.cos(an) * rr, hy + math.sin(an) * rr, hx + math.cos(an) * (rr + 40),
                        hy + math.sin(an) * (rr + 40)), fill=(170, 220, 255, 230), width=5)
            if fi % 2 == 0:
                b = bolt_b[fi // 2 % len(bolt_b)]
                img.alpha_composite(b, (int(hx - b.width / 2), int(hy - b.height / 2)))
            sh = max(sh, 2 + 4 * k)
        if 16.5 <= t < 17.7:                                              # Kamehameha : rayon
            hx, hy = info["fist"]
            k = min(1.0, (t - 16.5) / 0.08)
            fade = 1.0 if t < 17.4 else max(0.0, 1 - (t - 17.4) / 0.3)
            x2 = hx + (W + 200 - hx) * k
            th = 95 * fade * (1 + 0.08 * math.sin(t * 60))
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ld = ImageDraw.Draw(lay)
            ld.rounded_rectangle((hx, hy - th, x2, hy + th), int(th), fill=(70, 150, 255, 210))
            ld.rounded_rectangle((hx, hy - th * 0.55, x2, hy + th * 0.55), int(th * 0.55), fill=(170, 220, 255, 240))
            ld.rounded_rectangle((hx, hy - th * 0.25, x2, hy + th * 0.25), int(th * 0.25), fill=(255, 255, 255, 255))
            ld.ellipse((hx - th * 1.3, hy - th * 1.3, hx + th * 1.3, hy + th * 1.3), fill=(200, 235, 255, 230))
            img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(20)))
            img.alpha_composite(lay)
            if fi % 2 == 0:
                for j in range(3):
                    b = bolt_b[(fi + j) % len(bolt_b)]
                    img.alpha_composite(b, (int(hx + 150 + j * 260 - b.width / 2), int(hy - b.height / 2)))
            sh = max(sh, 14 * fade)
        # ------------------------------------------------ impacts
        hits = {2.52: ("s", info["fist"]), 2.82: ("s", info["fist_b"]), 3.45: ("B", None), 4.6: ("K", None),
                7.3: ("U", None), 8.85: ("C", None), 11.6: ("T", None), 16.5: ("E", None), 5.55: ("L", None),
                8.4: ("L2", None), 14.5: ("L3", None)}
        for at, (kind, p0) in hits.items():
            a_ = t - at
            if a_ < 0 or a_ > 1.0:
                continue
            if kind == "s" and a_ < 0.15:                                  # jab / cross : petite étoile
                x, y = p0 if a_ < 0.02 else (fx_x - 70, GROUND - 330)
                fx.impact_star(img, fx_x - 70, GROUND - 330, 60 * (1 - a_ / 0.15) + 20, seed=int(at * 10))
            if kind in ("B", "K", "U", "C", "E"):
                if kind == "C":
                    x, y = gx + 40, GROUND - 320
                elif kind == "U":
                    x, y = fx_x - 30, GROUND - 380 - flift
                elif kind == "E":
                    x, y = min(W - 120, fx_x), GROUND - 260 - flift
                else:
                    x, y = fx_x - 60, GROUND - (300 if kind == "B" else 260)
                if a_ < 0.05:                                              # 1 image : flash teinté
                    fx.tint_flash(img, (255, 110, 90) if kind != "E" else (150, 210, 255), 120)
                if a_ < 0.12:
                    fx.manga_lines(img, x, y, col=(20, 20, 30), n=70, inner=200, alpha=int(220 * (1 - a_ / 0.12)),
                                   seed=int(at * 7))
                if a_ < 0.3:
                    fx.impact_star(img, x, y, 150 * (1 - a_ / 0.3) + 40, seed=int(at * 13), rot=a_ * 2)
                if a_ < 0.6:
                    fx.shock_rings(img, x, GROUND, a_ / 0.6)
                sh = max(sh, 26 * max(0.0, 1 - a_ / 0.4))
                if once(("rub", at)):
                    rub.burst(x, GROUND, t, n=12)
                if kind == "E" and a_ < 0.9:
                    fr = explo[min(len(explo) - 1, int(a_ / 0.9 * len(explo)))]
                    img.alpha_composite(fr, (int(x - fr.width / 2), int(y - fr.height / 2)))
                if kind == "C" and a_ < 0.6:                               # COUNTER!
                    s_ = 1 + 0.4 * max(0.0, 1 - a_ / 0.1)
                    img = hud.label(img.convert("RGB"), (W / 2, 640), "COUNTER!", int(110 * s_), fill=(255, 80, 80),
                                    angle=-4).convert("RGBA")
            if kind == "T" and a_ < 0.7:                                   # fin de transformation
                if a_ < 0.08:
                    fx.tint_flash(img, (255, 250, 220), 230 * (1 - a_ / 0.08))
                if a_ < 0.4:
                    fx.manga_lines(img, gx, GROUND - 260, col=GOLD, n=80, inner=260, alpha=int(200 * (1 - a_ / 0.4)))
                fx.shock_rings(img, gx, GROUND, a_ / 0.7, col=(255, 210, 90), rx=650)
                sh = max(sh, 30 * max(0.0, 1 - a_ / 0.5))
                if once("rub_t"):
                    rub.burst(gx, GROUND, t, n=24, power=1100)
            if kind in ("L", "L2", "L3") and a_ < 0.5:                     # atterrissages
                xx = fx_x if kind != "L3" else gx
                fx.shock_rings(img, xx, GROUND, a_ / 0.5, rx=260)
                if once(("land", at)):
                    rub.burst(xx, GROUND, t, n=8, power=600)
                    rub.puff(xx, GROUND - 10, t, n=6)
        # poussière qui roule au sol (glissades)
        for t0, t1, who in ((3.47, 3.95, "f"), (5.55, 5.9, "f"), (8.87, 9.3, "g"), (11.65, 12.0, "f")):
            if t0 <= t < t1 and fi % 2 == 0:
                rub.puff(fx_x if who == "f" else gx, GROUND - 8, t, n=2, size=(26, 48), col=(215, 190, 150))
        rub.draw(img, t)
        # ------------------------------------------------ impact frames silhouette (2 images)
        for at, bgc, fgc in ((4.6, (10, 10, 14), (255, 255, 255)), (7.3, (255, 255, 255), (10, 10, 14)),
                             (11.6, (10, 10, 14), GOLD)):
            if 0 <= t - at < 0.07:
                fx.silhouette_frame(img, mask, bg=bgc, fg=fgc)
                fx.manga_lines(img, gx if at == 11.6 else fx_x, GROUND - 300, col=fgc, n=60, inner=240, alpha=200)
        # ------------------------------------------------ caméra
        foc = CAM_F.at(t)
        z = CAM_Z.at(t)
        if 3.4 <= t < 3.9 or 4.55 <= t < 5.0:
            cx, cy = fx_x - 120, GROUND - 300
        elif 7.25 <= t < 7.8:
            cx, cy = fx_x - 60, GROUND - 400
        elif 8.8 <= t < 9.3:
            cx, cy = gx + 60, GROUND - 300
        elif 16.4 <= t < 17.2:
            cx, cy = gx + 200, GROUND - 330
        else:
            cx, cy = W / 2 * (1 - foc) + gx * foc, (H / 2) * (1 - foc) + (GROUND - 300) * foc
        img = fx.camera(img, zoom=z, cx=cx, cy=cy, tilt=CAM_T.at(t), shake=sh, rnd=rnd)
        # ------------------------------------------------ textes (hors caméra)
        name = [n for s0, n in SEGS if t >= s0][-1]
        s0 = [s0 for s0, n in SEGS if t >= s0][-1]
        sc = 1 + 0.3 * max(0.0, 1 - (t - s0) / 0.12)
        img = hud.label(img.convert("RGB"), (W / 2, 210), name, int(84 * sc), fill=(255, 214, 50), angle=-2).convert("RGBA")
        L = Image.new("RGBA", img.size, (0, 0, 0, 0))
        hud.text3d(L, (W / 2, 90), "STICKMAN ENGINE v2", hud.font("luckiest-guy.woff2", 66), (255, 255, 255),
                   side=(30, 60, 140), depth=8, outline=(20, 20, 50), ow=5)
        img.alpha_composite(L)
        proc.stdin.write(img.convert("RGB").tobytes())
    proc.stdin.close()
    proc.wait()
    # ------------------------------------------------ son (même que v1)
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
    for s_, fam, sd, g in ((2.0, "teleport", 1, .4), (2.52, "hit", 5, .5), (2.82, "hit", 6, .6), (3.45, "hit", 1, 1),
                           (3.46, "bomb", 3, .5), (4.6, "hit", 2, 1), (5.55, "hit", 7, .5), (7.0, "teleport", 2, .8),
                           (7.3, "hit", 3, 1), (8.4, "hit", 8, .4), (8.85, "hit", 4, 1), (9.9, "transform", 0, .9),
                           (11.6, "bomb", 2, .9), (12.7, "teleport", 3, .5), (14.5, "hit", 9, .5), (15.3, "beam", 1, .6),
                           (16.5, "beam", 2, .9), (16.6, "bomb", 4, .8)):
        put(s_, S(fam, sd), g)
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
