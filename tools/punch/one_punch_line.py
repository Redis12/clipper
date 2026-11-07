"""« 1 PUNCH VS 1000 STICKMEN » en FILE INDIENNE (07/11, demandé par l'utilisateur) : les 1000 stickmen font la queue
devant Goku SSJ1 (stickman Stick Nodes), un seul coup → l'onde de choc remonte toute la file (la caméra la suit, le
compteur monte de plus en plus vite), elle meurt juste devant le dernier : 999/1000… il regarde autour de lui,
coupe sur Goku qui fait *flick*, la petite boule de ki arrive → 1000/1000 FLAWLESS.

python3 tools/punch/one_punch_line.py "library/_sticknodes/Goku SSJ1.json" <sortie.mp4>
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
import rig  # noqa: E402
import sticknodes as sn  # noqa: E402
from mugen_punch import F, GROUND, H, W, FPS, mountains  # noqa: E402
from one_punch import draw_stick  # noqa: E402
from stick_punch import GX, SCALE, T_CHARGE, T_HIT, T_SSJ, T_SWING, ease, pose_at  # noqa: E402
from clipper.slides import fusion, render, vfxgen  # noqa: E402

N = 1000
GAP = 52                         # écart entre 2 stickmen de la file
SH = 165                         # taille d'un stickman
TP = 1.4                         # le coup arrive vite (demandé : « ça prend trop de temps »)
K = T_HIT / TP                   # l'animation de stick_punch est accélérée d'autant
FREEZE = 0.22
WA, WB = 500.0, 900.0            # onde : x = WB·a + WA·a² (accélère)
GRAV = 2000.0
DASH = 95
GSC = SCALE * 0.75               # Goku un peu plus petit (demandé)


def desert_sky():
    """Ciel clair au-dessus d'un désert rocheux (autre terrain que « How far »)."""
    y = np.linspace(0, 1, H)[:, None, None]
    top, bot = np.array([70, 150, 230.]), np.array([255, 226, 170.])
    a = top * (1 - y ** 0.8) + bot * y ** 0.8
    im = Image.fromarray(a.repeat(W, 1).clip(0, 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(im)
    for cx_, cy_, w_ in ((160, 620, 300), (720, 760, 380), (420, 900, 260)):
        for j in range(4):
            d.ellipse((cx_ + j * w_ / 5 - w_ / 3, cy_ - 30 - (j % 2) * 26, cx_ + j * w_ / 5 + w_ / 3, cy_ + 30),
                      fill=(255, 255, 255, 230))
    return im


def wave_x(a):
    return WB * a + WA * a * a


def main():
    fig = sn.load(sys.argv[1])
    out = Path(sys.argv[2])
    imP, posP, oP = sn.render(fig, scale=GSC, absolute=gp.PUNCH)
    bottomP = np.nonzero(np.asarray(imP)[..., 3].max(1) > 0)[0].max()
    fist_x = GX + DASH + (posP[253][0] - oP[0])
    fist_y = GROUND - (bottomP - posP[253][1])
    X0 = fist_x + 50
    rnd = random.Random(5)
    pal = [(30, 30, 40)] * 5 + [(70, 70, 85)] * 2 + [(160, 40, 45), (40, 70, 160), (240, 240, 245)]
    men = [dict(x=X0 + i * GAP, col=rnd.choice(pal), ph=rnd.uniform(0, 6.3), hit=None) for i in range(N)]
    men[-1]["col"] = (30, 30, 40)
    X_LAST = men[-1]["x"]
    # fin de l'onde : juste devant le dernier
    span = X_LAST - 30 - fist_x
    A_END = (-WB + math.sqrt(WB * WB + 4 * WA * span)) / (2 * WA)
    T_END = TP + FREEZE + A_END
    T_LOOK = T_END + 0.5
    T_CUT = T_LOOK + 1.9            # coupe sur Goku : *flick*
    T_BACK = T_CUT + 1.5            # retour sur le survivant, la boule arrive
    T_FLY = T_BACK + 0.35
    T_STAR = T_FLY + 0.9             # il devient une étoile qui scintille dans le ciel
    T_WIN = T_STAR + 0.35
    DUR = T_WIN + 3.0
    CAM_MAX = X_LAST - 640
    far = mountains(1, (214, 150, 110, 255), 260, 1080, 420, W * 8)      # terrain « désert rocheux » à la DBZ
    near = mountains(2, (176, 108, 72, 255), 150, 1190, 260, W * 16)
    sky = desert_sky()
    confetti = []
    explo = list(vfxgen.frames("explosion", 620, (255, 210, 80)))
    ring = list(vfxgen.frames("ring", 900, (255, 240, 180)))
    bolt = list(vfxgen.frames("lightning", 260, (255, 240, 120)))
    fT, fS = F("anton.woff2", 112), F("mont900.woff2", 30)
    debris, launches, puffs = [], [], []
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s",
                             f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf",
                             "18", "-pix_fmt", "yuv420p", str(out.with_suffix(".video.mp4"))], stdin=subprocess.PIPE)
    cam = 0.0
    for fi in range(int(DUR * FPS)):
        t = fi / FPS
        a = t - TP - FREEZE                                            # temps depuis la fin de l'arrêt sur image
        wx = fist_x + wave_x(min(a, A_END)) if a >= 0 else -1e9
        if a >= 0 and t < T_END + 0.2:
            cam = max(cam, min(CAM_MAX, wx - 460))
        cut_goku = T_CUT <= t < T_BACK
        cx = 0.0 if cut_goku else cam
        # ------------------------------------------------ décor (parallaxe)
        img = sky.copy()
        img.alpha_composite(far.crop((int(cx * .15) % (W * 6), 0, int(cx * .15) % (W * 6) + W, H)))
        img.alpha_composite(near.crop((int(cx * .4) % (W * 14), 0, int(cx * .4) % (W * 14) + W, H)))
        img = img.convert("RGB")
        d = ImageDraw.Draw(img, "RGBA")
        d.rectangle((0, 1180, W, H), fill=(222, 178, 120))
        for k in range(-1, W // 140 + 2):                              # touffes d'herbe qui défilent
            gx = k * 140 - (cx % 140)
            d.line((gx, GROUND + 60, gx + 34, GROUND + 74), fill=(185, 135, 88), width=4)
            d.ellipse((gx + 70, GROUND + 150, gx + 120, GROUND + 178), fill=(165, 112, 74))
            d.ellipse((gx + 76, GROUND + 148, gx + 112, GROUND + 166), fill=(196, 140, 96))
            d.line((gx + 20, GROUND + 260, gx + 90, GROUND + 250), fill=(185, 135, 88), width=4)
        mk = int(cx // 2000)                                           # bornes de distance
        for j in (mk, mk + 1):
            bx = j * 2000 + 600 - cx
            if j > 0 and -100 < bx < W + 100:
                d.rectangle((bx - 6, GROUND - 120, bx + 6, GROUND), fill=(240, 240, 240))
                d.rounded_rectangle((bx - 60, GROUND - 170, bx + 60, GROUND - 115), 8, fill=(255, 255, 255),
                                    outline=(40, 40, 50), width=4)
                d.text((bx, GROUND - 142), f"#{min(N, j * 50)}", font=F("anton.woff2", 36), fill=(40, 40, 50), anchor="mm")
        # ------------------------------------------------ Goku
        gt = t * K if t < TP else t - TP + T_HIT
        if t < TP:
            pose = pose_at(max(0.0, gt))
            gx_ = GX + (DASH * ease((gt - T_SWING) / (T_HIT - T_SWING)) if gt >= T_SWING else 0)
        else:
            gx_ = GX + DASH
            if cut_goku:                                              # vrai lancer : armé → charge → lancer
                k = t - T_CUT
                if k < 0.6:
                    pose = sn.lerp_pose(gp.IDLE, gp.WINDUP, ease(k / 0.35))
                    pose[54] += 1.5 * math.sin(t * 40)
                elif k < 0.75:
                    pose = sn.lerp_pose(gp.WINDUP, gp.PUNCH, ease((k - 0.6) / 0.15) ** 0.6)
                else:
                    pose = gp.PUNCH
            elif t - TP < 1.4:
                pose = gp.PUNCH
            else:
                pose = sn.lerp_pose(gp.PUNCH, gp.IDLE, ease((t - TP - 1.4) / 0.5))
                pose[53] += 2 * math.sin(t * 5)
        goku_on = gx_ - cx > -400
        if goku_on:
            ssj = gt >= T_SSJ
            cm = None if ssj else (lambda i, c: (22, 22, 28, 255) if c[:3] in gp.HAIR_COLORS else c)
            pim, pos, org = sn.render(fig, scale=GSC, absolute=pose, color_map=cm)
            bottom = np.nonzero(np.asarray(pim)[..., 3].max(1) > 0)[0].max()
            px, py = int(gx_ - org[0] - cx), int(GROUND - bottom)
            power = 0.0
            if T_SSJ <= gt and t < TP + 0.6:
                power = min(1.0, (gt - T_SSJ) / 0.6) * (1 if t < TP else max(0, 1 - (t - TP) / 0.6))
            if t >= TP + 0.6:
                power = 0.35
            if power > 0:
                au = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                ad = ImageDraw.Draw(au)
                ch_ = (GROUND - py) * 0.62
                for scl, col, al in ((1.25, (255, 225, 40), 150), (1.0, (255, 245, 150), 190), (0.7, (255, 255, 235), 170)):
                    ad.polygon(rig.aura_poly(gx_ - cx, GROUND - ch_ * 0.95, (110 + 30 * power) * scl, ch_ * scl,
                                             t * 1.3 + scl, n=30, seed=int(scl * 10)), fill=col + (int(al * power),))
                g_ = au.filter(ImageFilter.GaussianBlur(18))
                img.paste(g_, (0, 0), g_)
                img.paste(au, (0, 0), au)
                if fi % 3 == 0 and power > 0.5:
                    b = bolt[fi // 3 % len(bolt)]
                    img.paste(b, (int(gx_ - cx - b.width / 2 + rnd.uniform(-60, 60)), int(py + rnd.uniform(0, 200))), b)
            img.paste(pim, (px, py), pim)
            d = ImageDraw.Draw(img, "RGBA")
            if cut_goku:
                k = t - T_CUT
                hx, hy = px + pos[253][0], py + pos[253][1]          # la main
                if k < 0.75:                                          # la boule de ki se charge dans la main
                    r = 8 + 30 * ease(k / 0.6)
                    gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                    ImageDraw.Draw(gl).ellipse((hx - r * 2.2, hy - r * 2.2, hx + r * 2.2, hy + r * 2.2), fill=(255, 230, 90, 170))
                    gl = gl.filter(ImageFilter.GaussianBlur(16))
                    img.paste(gl, (0, 0), gl)
                    d = ImageDraw.Draw(img, "RGBA")
                    d.ellipse((hx - r, hy - r, hx + r, hy + r), fill=(255, 250, 210))
                    for j in range(5):                                # énergie qui converge
                        an = j * 1.26 + t * 9
                        rr = 120 * (1 - (k * 3 + j * 0.2) % 1)
                        d.line((hx + math.cos(an) * rr, hy + math.sin(an) * rr, hx + math.cos(an) * (rr + 30),
                                hy + math.sin(an) * (rr + 30)), fill=(255, 240, 150, 220), width=5)
                else:
                    kk = (k - 0.75) / 0.75
                    bx = fist_x + kk * 1100
                    for j in range(8):
                        d.ellipse((bx - j * 40 - 30 + j * 3, fist_y - 30 + j * 3, bx - j * 40 + 30 - j * 3, fist_y + 30 - j * 3),
                                  fill=(255, 235, 110, 160 - j * 18))
                    d.ellipse((bx - 40, fist_y - 40, bx + 40, fist_y + 40), fill=(255, 240, 120, 140))
                    d.ellipse((bx - 22, fist_y - 22, bx + 22, fist_y + 22), fill=(255, 255, 235))
                    if kk < 0.6:
                        s_ = 1 + 0.5 * max(0.0, 1 - kk / 0.12)
                        d.text((fist_x + 40, fist_y - 190), "HA!", font=F("anton.woff2", int(110 * s_)), fill=(255, 230, 60),
                               anchor="mm", stroke_width=6, stroke_fill=(40, 10, 10))
        # ------------------------------------------------ la file
        march = max(0.0, 1.2 - t) * 260                                # elle arrive par la droite au début
        for i, m in enumerate(men):
            if m["hit"] is None and i < N - 1 and wx >= m["x"]:
                m["hit"] = t
                m["vx"] = rnd.uniform(200, 900)
                m["vy"] = -rnd.uniform(1300, 2500)
                m["spin"] = rnd.uniform(600, 1500) * rnd.choice((1, -1))
                launches.append(t)
            if m["hit"] is None:
                x = m["x"] + march - cx
                if not -60 < x < W + 60:
                    continue
                look = 0.0
                if i == N - 1:
                    if T_FLY <= t:
                        continue
                    if T_END <= t < T_END + 0.6:
                        x += 5 * math.sin(t * 60)
                    if t >= T_LOOK:
                        look = math.sin((t - T_LOOK) * 3.4)
                mode = "run" if march > 0 else ("stand" if t > TP else "stand")
                ph = m["ph"] + t * 14
                draw_stick(d, x, GROUND, SH, ph, 0, mode, m["col"], look=look)
            else:
                aa = (t - m["hit"]) * (0.45 if t < TP + FREEZE + 0.9 else 1.0)
                tl = 2 * -m["vy"] / GRAV
                if aa < tl:
                    x = m["x"] + m["vx"] * aa - cx
                    y = GROUND + m["vy"] * aa + 0.5 * GRAV * aa * aa
                    rot = m["spin"] * aa
                else:                                                   # retombé : couché
                    x, y, rot = m["x"] + m["vx"] * tl - cx, GROUND, 90
                if -80 < x < W + 80 and y > -80:
                    draw_stick(d, x, y, SH, 0, rot, "fly", m["col"])
        # le dernier s'envole
        if t >= T_FLY:
            m = men[-1]
            aa = t - T_FLY
            if t < T_STAR:                                            # il file vers le ciel en rapetissant
                k = ease(aa / (T_STAR - T_FLY))
                sx0, sy0 = m["x"] - cx, GROUND
                tx, ty = W * 0.78, 560
                x = sx0 + (tx - sx0) * k
                y = sy0 + (ty - sy0) * k - 260 * math.sin(math.pi * k)
                draw_stick(d, x, y + SH * (1 - k) * 0.5, SH * (1 - 0.92 * k), 0, 1300 * aa, "fly", m["col"])
            elif t < T_STAR + 0.9:                                    # ✦ scintillement « Team Rocket »
                k = (t - T_STAR) / 0.9
                r = 70 * math.sin(math.pi * min(1.0, k * 1.6)) + 8
                cxs, cys = W * 0.78, 560
                for an in (0, 90, 180, 270):
                    ra = math.radians(an + k * 90)
                    d.polygon([(cxs + math.cos(ra) * r, cys + math.sin(ra) * r), (cxs + math.cos(ra + .3) * r * .25,
                               cys + math.sin(ra + .3) * r * .25), (cxs, cys), (cxs + math.cos(ra - .3) * r * .25,
                               cys + math.sin(ra - .3) * r * .25)], fill=(255, 255, 255, 240))
                d.ellipse((cxs - r * .3, cys - r * .3, cxs + r * .3, cys + r * .3), fill=(255, 250, 200))
        if T_BACK <= t < T_FLY:                                        # la boule arrive de la gauche
            k = (t - T_BACK) / (T_FLY - T_BACK)
            bx, by = -40 + (men[-1]["x"] - cx + 40) * k, GROUND - SH * 0.55
            for j in range(6):
                d.line((bx - 60 - j * 30, by, bx - 30 - j * 30, by), fill=(255, 240, 150, 200 - j * 30), width=10)
            d.ellipse((bx - 30, by - 30, bx + 30, by + 30), fill=(255, 240, 120, 130))
            d.ellipse((bx - 16, by - 16, bx + 16, by + 16), fill=(255, 255, 230))
        # ------------------------------------------------ onde + impact
        ee = t - TP
        if 0 <= ee < FREEZE:
            g = img.convert("L").point(lambda v: 255 if v > 90 else 0)
            img = Image.merge("RGB", (g, g.point(lambda v: v * .85), g.point(lambda v: v * .3)))
            d = ImageDraw.Draw(img, "RGBA")
            if ee < 1 / FPS:
                for _ in range(30):
                    debris.append([fist_x + rnd.uniform(-30, 30), GROUND - 10, rnd.uniform(-100, 900),
                                   -rnd.uniform(300, 1100), t, rnd.uniform(8, 18), 1.8])
        if a >= 0 and t < T_END + 0.3:
            sx = wx - cx
            fade = 1.0 if t < T_END else max(0.0, 1 - (t - T_END) / 0.3)
            # nuages de poussière qui roulent derrière l'onde
            if fi % 2 == 0:
                for _ in range(2):
                    puffs.append([wx - rnd.uniform(0, 60), GROUND - rnd.uniform(0, 60), rnd.uniform(40, 80), t])
            # onde d'énergie : mur lumineux en croissant + halo flou + traînée au sol
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ld = ImageDraw.Draw(lay)
            hh = SH * 2.3
            for j, (wd, col, al) in enumerate(((150, (255, 200, 60), 150), (95, (255, 235, 130), 200), (45, (255, 255, 240), 255))):
                ld.ellipse((sx - wd, GROUND - hh, sx + wd * 0.35, GROUND + 40), fill=col + (int(al * fade),))
            ld.ellipse((sx - 260, GROUND - hh * 0.9, sx - 40, GROUND + 50), fill=(0, 0, 0, 0))   # creux du croissant
            for j in range(28):                                        # traînée au sol qui s'éteint
                x0_ = sx - 40 - j * 30
                ld.rectangle((x0_ - 30, GROUND - 14, x0_, GROUND + 10), fill=(255, 220, 110, int(200 * (1 - j / 28) * fade)))
            for _ in range(10):                                        # lignes de vitesse
                yy = GROUND - rnd.uniform(10, hh)
                ln = rnd.uniform(120, 420)
                ld.line((sx - 60 - ln, yy, sx - 60, yy), fill=(255, 250, 220, int(180 * fade)), width=rnd.randint(3, 7))
            glow = lay.filter(ImageFilter.GaussianBlur(22))
            img.paste(glow, (0, 0), glow)
            img.paste(lay, (0, 0), lay)
            d = ImageDraw.Draw(img, "RGBA")
            for _ in range(int(6 * fade)):                             # étincelles
                ang = rnd.uniform(-1.4, 0.4)
                ln = rnd.uniform(30, 90)
                x1, y1 = sx + rnd.uniform(-20, 30), GROUND - rnd.uniform(0, hh * 0.9)
                d.line((x1, y1, x1 + math.cos(ang) * ln, y1 + math.sin(ang) * ln), fill=(255, 255, 210), width=4)
            for _ in range(4):                                         # cailloux soulevés
                debris.append([wx + rnd.uniform(-20, 20), GROUND - 4, rnd.uniform(-200, 300), -rnd.uniform(400, 1000), t,
                               rnd.uniform(6, 13), 0.9])
        if puffs:
            keep_p = []
            for pf in puffs:
                aa = t - pf[3]
                if aa < 1.1:
                    r = pf[2] * (1 + aa * 2.2)
                    x, y = pf[0] - cx - aa * 60, pf[1] - aa * 70
                    if -r < x < W + r:
                        d.ellipse((x - r, y - r * 0.8, x + r, y + r * 0.8), fill=(205, 165, 120, int(150 * (1 - aa / 1.1))))
                    keep_p.append(pf)
            puffs[:] = keep_p
        if 0 <= ee - FREEZE < 1.0:
            k = (ee - FREEZE) / 1.0
            ex = explo[min(len(explo) - 1, int(k * len(explo)))]
            img.paste(ex, (int(fist_x - cx - ex.width / 2), int(fist_y - ex.height / 2)), ex)
            rr_ = ring[min(len(ring) - 1, int(k * len(ring)))]
            img.paste(rr_, (int(fist_x - cx - rr_.width / 2), int(fist_y - rr_.height / 2)), rr_)
            d = ImageDraw.Draw(img, "RGBA")
            if k < 0.25:
                d.rectangle((0, 0, W, H), fill=(255, 255, 255, int(200 * (1 - k / 0.25))))
        keep = []
        for db in debris:
            aa = t - db[4]
            if aa < db[6]:
                x, y = db[0] + db[2] * aa - cx, db[1] + db[3] * aa + 1200 * aa * aa
                if y < GROUND + 4:
                    s = db[5]
                    d.polygon([(x - s, y), (x - s * .3, y - s), (x + s, y - s * .4), (x + s * .6, y + s * .7)], fill=(110, 85, 60))
                    keep.append(db)
        debris[:] = keep
        if T_SSJ <= gt < T_SSJ + 0.35:
            d.rectangle((0, 0, W, H), fill=(255, 245, 180, int(235 * (1 - (gt - T_SSJ) / 0.35))))
        # ------------------------------------------------ textes
        down = len(launches) + (1 if t >= T_FLY else 0)
        d.text((W / 2, 64), "1 PUNCH VS", font=fT, fill="white", anchor="mt", stroke_width=5, stroke_fill=(20, 10, 40))
        d.text((W / 2, 180), "1000 STICKMEN", font=fT, fill=(255, 200, 60), anchor="mt", stroke_width=5,
               stroke_fill=(20, 10, 40))
        pulse = 1.1 if launches and t - launches[-1] < 0.05 and down < 999 else 1.0
        col = (255, 255, 255) if down < 999 else ((255, 90, 90) if down == 999 else (90, 255, 140))
        d.text((W / 2, 330), f"{down} / 1000", font=F("anton.woff2", int(104 * pulse)), fill=col, anchor="mt",
               stroke_width=5, stroke_fill=(10, 10, 30))
        d.text((W / 2, 448), "KNOCKED OUT", font=fS, fill=(30, 40, 80), anchor="mt")
        if T_END + 0.2 <= t < T_FLY and not cut_goku:
            d.text((W / 2, 570), "1 LEFT...", font=F("anton.woff2", 96), fill=(255, 90, 90), anchor="mm",
                   stroke_width=5, stroke_fill=(20, 10, 10))
            m = men[-1]
            d.text((m["x"] - cx, GROUND - SH - 70), "!?" if t < T_LOOK + 0.8 else "?", font=F("anton.woff2", 80),
                   fill=(255, 230, 60), anchor="mm", stroke_width=4, stroke_fill=(20, 10, 10))
        if t >= T_WIN:
            a_ = t - T_WIN
            rays = Image.new("RGBA", (W, H), (0, 0, 0, 0))            # rayons qui tournent derrière le texte
            rd = ImageDraw.Draw(rays)
            for j in range(14):
                an = math.radians(j * 360 / 14 + a_ * 40)
                rd.polygon([(W / 2, 610), (W / 2 + math.cos(an - .09) * 1400, 610 + math.sin(an - .09) * 1400),
                            (W / 2 + math.cos(an + .09) * 1400, 610 + math.sin(an + .09) * 1400)],
                           fill=(255, 235, 120, int(90 * min(1.0, a_ / 0.3))))
            img.paste(rays, (0, 0), rays)
            d = ImageDraw.Draw(img, "RGBA")
            if not confetti:
                for _ in range(160):
                    confetti.append([rnd.uniform(0, W), rnd.uniform(-900, -20), rnd.uniform(-80, 80), rnd.uniform(250, 520),
                                     rnd.choice([(255, 80, 80), (255, 210, 60), (80, 200, 255), (120, 255, 140), (255, 120, 220)]),
                                     rnd.uniform(0, 6.3)])
            for c in confetti:
                x, y = c[0] + c[2] * a_ + 30 * math.sin(a_ * 4 + c[5]), c[1] + c[3] * a_
                w_ = 14 * abs(math.cos(a_ * 6 + c[5])) + 3
                d.rectangle((x - w_, y - 6, x + w_, y + 6), fill=c[4])
            s = 1 + 0.4 * max(0.0, 1 - a_ / 0.15) + 0.04 * math.sin(a_ * 6)
            d.text((W / 2, 610), "FLAWLESS", font=F("anton.woff2", int(150 * s)), fill=(255, 220, 60), anchor="mm",
                   stroke_width=7, stroke_fill=(40, 10, 10))
            if a_ > 0.4:
                rgba = img.convert("RGBA")
                render.draw_rich(rgba, (W / 2, 730), "Who takes 10,000 next? Comment 👇", F("mont900.woff2", 50),
                                 (255, 255, 255), anchor="ma", stroke_width=4, stroke_fill=(0, 0, 0))
                img = rgba.convert("RGB")
        # secousse
        sh = 0
        if T_CHARGE <= gt < T_HIT:
            sh = 4
        if 0 <= gt - T_SSJ < 0.45:
            sh = 16
        if 0 <= ee < 1.2:
            sh = 32 * (1 - ee / 1.2)
        elif a >= 0 and t < T_END:
            sh = 5
        if 0 <= t - T_FLY < 0.25:
            sh = 14
        if sh:
            dx, dy = rnd.randint(-int(sh), int(sh)), rnd.randint(-int(sh), int(sh))
            bgf = Image.new("RGB", (W, H), (0, 0, 0))
            bgf.paste(img, (dx, dy))
            img = bgf
        proc.stdin.write(img.tobytes())
    proc.stdin.close()
    proc.wait()
    # ------------------------------------------------ son
    from clipper.slides import domain
    rate = fusion.RATE
    na = int(DUR * rate) + rate
    audio = np.zeros(na, np.float32)

    def put(t_, x, g):
        if x is None:
            return
        i = int(t_ * rate)
        seg = x[: max(0, na - i)]
        audio[i:i + len(seg)] += seg * g
    S = lambda fam, seed=0: domain.sfx(fam, mode="anime", seed=seed, franchise="dragon ball")  # noqa: E731
    for k in range(6):                                                 # la file qui arrive
        put(k * 0.3, S("hit", 20 + k % 4), 0.08)
    put(T_SSJ / K - 0.05, S("transform"), 0.9)
    put(T_SWING / K, S("teleport"), 0.5)
    put(TP, S("hit", 1), 1.0)
    put(TP + FREEZE, S("bomb", 2), 1.0)
    put(TP + FREEZE + 0.1, S("ko"), 0.6)
    for j in range(0, len(launches), 12):                              # un coup tous les 12 stickmen
        put(launches[j], S("hit", 30 + j % 6), 0.25)
    put(T_CUT + 0.2, S("shots", 3), 0.6)
    put(T_FLY, S("hit", 3), 1.0)
    put(T_STAR, S("teleport", 4), 0.5)
    put(T_WIN, S("ko", 1), 0.7)
    lvl = float(np.percentile(np.abs(audio), 99.7)) or 1.0
    audio = audio * min(1.0, 0.75 / lvl)
    wav = out.with_suffix(".wav")
    fusion.write_wav(wav, np.tanh(audio * 1.1) / math.tanh(1.1) * 0.3)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out.with_suffix(".video.mp4")), "-i", str(wav),
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", str(out.with_suffix(".raw.mp4"))],
                   check=True)
    render.stamp_video(out.with_suffix(".raw.mp4"), out)
    print("OUT", out, round(DUR, 1), "down", len(launches) + 1, "wave", round(A_END, 1))


if __name__ == "__main__":
    main()
