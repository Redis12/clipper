"""« 1 PUNCH VS 1000 STICKMEN » (07/11, demandé par l'utilisateur) : Goku SSJ1 (stickman Stick Nodes de l'utilisateur)
face à une horde de 1000 stickmen dessinés en code. Ils chargent, Goku se transforme, UN coup → l'onde de choc les
envoie tous voler (compteur), un seul reste debout (999/1000)… petit ki blast du doigt → 1000/1000 FLAWLESS.

python3 tools/punch/one_punch.py "library/_sticknodes/Goku SSJ1.json" <sortie.mp4>
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
from how_far import day_sky  # noqa: E402
from mugen_punch import F, GROUND, H, W, FPS, mountains  # noqa: E402
from stick_punch import GX, SCALE, T_CHARGE, T_HIT, T_SSJ, T_SWING, ease, pose_at  # noqa: E402
from clipper.slides import fusion, render, vfxgen  # noqa: E402

N = 1000
OFF = 3.0                       # Goku attend 3 s pendant que la horde arrive
TP = T_HIT + OFF                # le coup (6,6 s)
WAVE = 1500.0                   # vitesse de l'onde de choc (px/s)
GRAV = 1700.0
T_LOOK = TP + 2.4               # le survivant regarde autour de lui
T_FLICK = TP + 3.7              # petit ki blast du doigt
T_FLY = T_FLICK + 0.45          # il s'envole
FREEZE, SLOW, SL = 0.22, 2.2, 0.3      # arrêt sur image, puis ralenti ×0,3 pendant 2,2 s réelles


def story(t):
    """temps réel → temps de l'histoire (arrêt sur image au coup, puis ralenti)."""
    if t < TP:
        return t
    if t < TP + FREEZE:
        return TP
    if t < TP + FREEZE + SLOW:
        return TP + (t - TP - FREEZE) * SL
    return TP + SLOW * SL + (t - TP - FREEZE - SLOW)


def real(s_):
    if s_ <= TP:
        return s_
    if s_ <= TP + SLOW * SL:
        return TP + FREEZE + (s_ - TP) / SL
    return TP + FREEZE + SLOW + (s_ - TP - SLOW * SL)


DUR = real(T_FLY) + 3.0
HOR_Y0, HOR_Y1 = 1200, 1760     # bande de profondeur de la horde (pieds)
DASH = 120


def stick_pts(x, y, h, phase, rot, mode):
    """Points d'un stickman (pieds en (x, y), hauteur h). mode : run, cheer, stand, fly."""
    s = math.sin(phase)
    hip, neck, head = (0, -0.47 * h), (0, -0.8 * h), (0, -0.92 * h)
    if mode == "run":
        legs = [(0.22 * h * s, 0), (-0.22 * h * s, -0.04 * h * abs(s))]
        arms = [(-0.2 * h * s, -0.6 * h), (0.2 * h * s, -0.6 * h)]
        lean = 0.12 * h
    elif mode == "cheer":
        legs = [(-0.13 * h, 0), (0.13 * h, 0)]
        up = 0.05 * h * s
        arms = [(-0.2 * h, -1.08 * h + up), (0.2 * h, -1.08 * h - up)]
        lean = 0
    elif mode == "fly":
        legs = [(-0.25 * h, -0.1 * h), (0.25 * h, -0.05 * h)]
        arms = [(-0.32 * h, -0.95 * h), (0.32 * h, -0.98 * h)]
        lean = 0
    else:
        legs = [(-0.1 * h, 0), (0.1 * h, 0)]
        arms = [(-0.16 * h, -0.5 * h), (0.16 * h, -0.5 * h)]
        lean = 0
    pts = {"hip": hip, "neck": (neck[0] - lean, neck[1]), "head": (head[0] - lean * 1.15, head[1]),
           "l1": legs[0], "l2": legs[1], "a1": arms[0], "a2": arms[1]}
    c, sn_ = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    cy = -0.47 * h
    out = {}
    for k, (px, py) in pts.items():
        dy = py - cy
        out[k] = (x + px * c - dy * sn_, y + cy + px * sn_ + dy * c)
    return out


def draw_stick(d, x, y, h, phase, rot, mode, col, look=0.0):
    p = stick_pts(x, y, h, phase, rot, mode)
    w = max(2, int(h * 0.075))
    for a, b in (("hip", "l1"), ("hip", "l2"), ("hip", "neck"), ("neck", "a1"), ("neck", "a2")):
        d.line((p[a], p[b]), fill=col, width=w)
    hx, hy = p["head"]
    r = h * 0.11
    d.ellipse((hx - r, hy - r, hx + r, hy + r), fill=col)
    if look:                                                         # yeux (survivant)
        for ex in (-0.35, 0.35):
            d.ellipse((hx + (ex + look * 0.4) * r - 3, hy - 0.15 * r - 3, hx + (ex + look * 0.4) * r + 3, hy - 0.15 * r + 3),
                      fill=(255, 255, 255))


def main():
    fig = sn.load(sys.argv[1])
    out = Path(sys.argv[2])
    imP, posP, oP = sn.render(fig, scale=SCALE, absolute=gp.PUNCH)
    bottomP = np.nonzero(np.asarray(imP)[..., 3].max(1) > 0)[0].max()
    fist_x = GX + DASH + (posP[253][0] - oP[0])
    fist_y = GROUND - (bottomP - posP[253][1])
    rnd = random.Random(11)
    # --- la horde : x de départ, x d'arrivée (tassés devant Goku), profondeur, hauteur
    men = []
    for i in range(N):
        x0 = rnd.uniform(560, 4600)
        y = rnd.uniform(HOR_Y0, HOR_Y1)
        k = (y - HOR_Y0) / (HOR_Y1 - HOR_Y0)
        xf = fist_x + 40 + (x0 - 560) * 0.3 + rnd.uniform(0, 30)
        col = rnd.choice([(30, 30, 40)] * 5 + [(70, 70, 85)] * 2 + [(150, 40, 45), (40, 70, 150), (235, 235, 240)])
        men.append(dict(x0=x0, xf=xf, y=y, h=50 + 80 * k, ph=rnd.uniform(0, 6.3), sp=rnd.uniform(520, 640), col=col,
                        hit=None, vx=0, vy=0, spin=0))
    surv = min(range(N), key=lambda i: abs(men[i]["xf"] - 800) + abs(men[i]["y"] - 1560) * 2)
    men[surv]["col"] = (30, 30, 40)
    order = sorted(range(N), key=lambda i: men[i]["y"])
    far = mountains(1, (120, 160, 220, 255), 170, 1100, 320, W * 2)
    near = mountains(2, (90, 160, 100, 255), 110, 1200, 230, W * 2)
    bg = day_sky(0.0)
    bg.alpha_composite(far.crop((0, 0, W, H)))
    bg.alpha_composite(near.crop((0, 0, W, H)))
    bgd = ImageDraw.Draw(bg)
    bgd.rectangle((0, 1180, W, H), fill=(90, 170, 80))
    for k in range(40):
        yy = 1190 + k * 18
        bgd.line((0, yy, W, yy), fill=(80, 160, 72), width=2)
    bg = bg.convert("RGB")
    explo = list(vfxgen.frames("explosion", 620, (255, 210, 80)))
    ring = list(vfxgen.frames("ring", 900, (255, 240, 180)))
    bolt = list(vfxgen.frames("lightning", 260, (255, 240, 120)))
    fT, fS, fN = F("anton.woff2", 112), F("mont900.woff2", 30), F("anton.woff2", 120)
    debris = []
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s",
                             f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf",
                             "18", "-pix_fmt", "yuv420p", str(out.with_suffix(".video.mp4"))], stdin=subprocess.PIPE)
    launch_times = []
    count_shown = 0
    for fi in range(int(DUR * FPS)):
        t = fi / FPS
        ts = story(t)
        img = bg.copy()
        d = ImageDraw.Draw(img, "RGBA")
        # ------------------------------------------------ Goku
        gt = ts - OFF
        if ts < TP:
            pose = pose_at(max(0.0, gt))
            gx_ = GX + (DASH * ease((gt - T_SWING) / (T_HIT - T_SWING)) if gt >= T_SWING else 0)
        else:
            gx_ = GX + DASH
            a_ = ts - TP
            if T_FLICK - 0.4 <= ts < T_FLY + 0.6:                    # le doigt
                pose = sn.lerp_pose(gp.IDLE, gp.PUNCH, ease((ts - (T_FLICK - 0.4)) / 0.3))
            elif a_ < 1.3:
                pose = gp.PUNCH
            else:
                pose = sn.lerp_pose(gp.PUNCH, gp.IDLE, ease((a_ - 1.3) / 0.5))
                pose[53] += 2 * math.sin(t * 5)
        ssj = gt >= T_SSJ
        cm = None if ssj else (lambda i, c: (22, 22, 28, 255) if c[:3] in gp.HAIR_COLORS else c)
        pim, pos, org = sn.render(fig, scale=SCALE, absolute=pose, color_map=cm)
        bottom = np.nonzero(np.asarray(pim)[..., 3].max(1) > 0)[0].max()
        px, py = int(gx_ - org[0]), int(GROUND - bottom)
        power = 0.0
        if T_SSJ <= gt and ts < TP + 0.6:
            power = min(1.0, (gt - T_SSJ) / 0.6) * (1 if ts < TP else max(0, 1 - (ts - TP) / 0.6))
        if ts >= TP + 0.6:
            power = 0.35                                              # aura calme après le coup
        if power > 0:
            au = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ad = ImageDraw.Draw(au)
            ch_ = (GROUND - py) * 0.62
            for scl, col, al in ((1.25, (255, 225, 40), 150), (1.0, (255, 245, 150), 190), (0.7, (255, 255, 235), 170)):
                ad.polygon(rig.aura_poly(gx_, GROUND - ch_ * 0.95, (150 + 40 * power) * scl, ch_ * scl, t * 1.3 + scl,
                                         n=30, seed=int(scl * 10)), fill=col + (int(al * power),))
            g_ = au.filter(ImageFilter.GaussianBlur(18))
            img.paste(g_, (0, 0), g_)
            img.paste(au, (0, 0), au)
            if fi % 3 == 0 and power > 0.5:
                b = bolt[fi // 3 % len(bolt)]
                img.paste(b, (int(gx_ - b.width / 2 + rnd.uniform(-60, 60)), int(py + rnd.uniform(0, 200))), b)
        # ------------------------------------------------ horde (derrière Goku si plus loin, devant sinon)
        wave_x = fist_x + WAVE * (ts - TP) if ts >= TP else -1e9
        alive = 0
        layers = ([], [])
        for i in order:
            m = men[i]
            if m["hit"] is None and i != surv and wave_x >= m["xf"] - (m["xf"] - m["x0"] + m["sp"] * ts if False else 0):
                x_now = max(m["x0"] - m["sp"] * ts, m["xf"])
                if wave_x >= x_now:
                    m["hit"] = ts
                    m["hx"] = x_now
                    dist = max(0.0, (x_now - fist_x) / 1400)
                    m["vx"] = rnd.uniform(250, 1300) * (1.15 - 0.4 * dist)
                    m["vy"] = -rnd.uniform(1000, 2600) * (1.1 - 0.4 * dist)
                    m["spin"] = rnd.uniform(500, 1400) * rnd.choice((1, 1, -1))
                    launch_times.append(ts)
            layers[0 if m["y"] < GROUND - 10 else 1].append(i)
        for li, lst in enumerate(layers):
            if li == 1:                                               # Goku entre les deux couches
                img.paste(pim, (px, py), pim)
                d = ImageDraw.Draw(img, "RGBA")
            for i in lst:
                m = men[i]
                if m["hit"] is None:
                    alive += 1
                    x_now = max(m["x0"] - m["sp"] * ts, m["xf"])
                    if x_now > W + 80:
                        continue
                    arrived = x_now <= m["xf"] + 1
                    mode = "run" if not arrived else ("cheer" if ts < TP else "stand")
                    ph = m["ph"] + ts * (14 if mode == "run" else 6)
                    look = 0.0
                    rot = 0
                    xx = x_now
                    if i == surv and ts >= TP:
                        mode = "stand"
                        if ts < TP + 1.0:
                            xx += 6 * math.sin(ts * 60) * (1 - (ts - TP))     # il tremble
                        look = math.sin((ts - T_LOOK) * 3.2) if ts >= T_LOOK else 0.0
                        if T_FLY <= ts:
                            continue
                    draw_stick(d, xx, m["y"], m["h"], ph, rot, mode, m["col"], look=look if i == surv else 0)
                else:
                    a = ts - m["hit"]
                    x = m["hx"] + m["vx"] * a
                    y = m["y"] + m["vy"] * a + 0.5 * GRAV * a * a
                    if y >= m["y"] and a > 0.2:                       # retombé : couché au sol
                        y, rot = m["y"], 90
                        x = m["hx"] + m["vx"] * (2 * -m["vy"] / GRAV)
                    else:
                        rot = m["spin"] * a
                    if -100 < x < W + 100 and y > -100:
                        draw_stick(d, x, y, m["h"], 0, rot, "fly", m["col"])
        # le survivant s'envole (ki blast)
        if ts >= T_FLY:
            m = men[surv]
            a = ts - T_FLY
            x, y = m["xf"] + 1500 * a, m["y"] - 1900 * a + 0.5 * GRAV * a * a
            draw_stick(d, x, y, m["h"], 0, 1100 * a, "fly", m["col"])
        if T_FLICK <= ts < T_FLY:                                    # petite boule de ki
            k = (ts - T_FLICK) / (T_FLY - T_FLICK)
            m = men[surv]
            bx = fist_x + (m["xf"] - fist_x) * k
            by = fist_y + (m["y"] - m["h"] * 0.5 - fist_y) * k
            d.ellipse((bx - 26, by - 26, bx + 26, by + 26), fill=(255, 240, 120, 120))
            d.ellipse((bx - 14, by - 14, bx + 14, by + 14), fill=(255, 255, 230))
        # ------------------------------------------------ onde de choc + impact
        ee = t - TP
        if 0 <= ee < 0.22:                                           # image figée 2 tons
            g = img.convert("L").point(lambda v: 255 if v > 90 else 0)
            img = Image.merge("RGB", (g, g.point(lambda v: v * .85), g.point(lambda v: v * .3)))
            d = ImageDraw.Draw(img, "RGBA")
            if ee < 1 / FPS:
                for _ in range(30):
                    debris.append([fist_x + rnd.uniform(-30, 30), GROUND - 10, rnd.uniform(-100, 900), -rnd.uniform(300, 1100),
                                   t, rnd.uniform(8, 18), 1.8])
        if 0.22 <= ee < 2.6:
            a_ = ts - TP
            wx = fist_x + WAVE * a_
            for j in range(4):                                        # croissant de l'onde
                rr = 300 + j * 40
                d.arc((wx - rr * 0.45, GROUND - rr * 1.6, wx + rr * 0.45, GROUND + rr * 0.3), 280, 80,
                      fill=(255, 255, 255, int(200 * (1 - a_ / 1.4)) if a_ < 1.4 else 0), width=10 - j * 2)
            d.rectangle((fist_x, GROUND - 4, min(W, wx), GROUND + 8), fill=(255, 250, 200, int(160 * max(0, 1 - a_))))
            k = (ee - 0.22) / 1.6
            if k < 1:
                ex = explo[min(len(explo) - 1, int(k * len(explo)))]
                img.paste(ex, (int(fist_x - ex.width / 2), int(fist_y - ex.height / 2)), ex)
                rr_ = ring[min(len(ring) - 1, int(k * len(ring)))]
                img.paste(rr_, (int(fist_x - rr_.width / 2), int(fist_y - rr_.height / 2)), rr_)
            d = ImageDraw.Draw(img, "RGBA")
            if ee < 0.45:
                d.rectangle((0, 0, W, H), fill=(255, 255, 255, int(200 * (1 - (ee - 0.22) / 0.23))))
        keep = []
        for db in debris:
            a = t - db[4]
            if a < db[6]:
                x, y = db[0] + db[2] * a, db[1] + db[3] * a + 950 * a * a
                if y < GROUND + 4:
                    s = db[5]
                    d.polygon([(x - s, y), (x - s * .3, y - s), (x + s, y - s * .4), (x + s * .6, y + s * .7)], fill=(90, 70, 50))
                    keep.append(db)
        debris[:] = keep
        if T_SSJ <= gt < T_SSJ + 0.35:
            d.rectangle((0, 0, W, H), fill=(255, 245, 180, int(235 * (1 - (gt - T_SSJ) / 0.35))))
        # ------------------------------------------------ textes
        down = len(launch_times) + (1 if ts >= T_FLY else 0)
        count_shown = down
        d.text((W / 2, 64), "1 PUNCH VS", font=fT, fill="white", anchor="mt", stroke_width=5, stroke_fill=(20, 10, 40))
        d.text((W / 2, 180), "1000 STICKMEN", font=fT, fill=(255, 200, 60), anchor="mt", stroke_width=5, stroke_fill=(20, 10, 40))
        pulse = 1 + 0.12 * max(0.0, 1 - (ts - launch_times[-1]) / 0.1) if launch_times and ts - launch_times[-1] < 0.1 else 1
        col = (255, 255, 255) if down < 999 else ((255, 90, 90) if down == 999 else (90, 255, 140))
        d.text((W / 2, 330), f"{down} / 1000", font=F("anton.woff2", int(104 * pulse)), fill=col, anchor="mt",
               stroke_width=5, stroke_fill=(10, 10, 30))
        d.text((W / 2, 448), "KNOCKED OUT", font=fS, fill=(30, 40, 80), anchor="mt")
        m = men[surv]
        if T_LOOK - 1.4 <= ts < T_FLICK:                              # « ... ? » au-dessus du survivant
            hx, hy = m["xf"], m["y"] - m["h"] - 70
            txt = "!?" if ts < T_LOOK else "?"
            d.text((hx, hy), txt, font=F("anton.woff2", 70), fill=(255, 230, 60), anchor="mm", stroke_width=4,
                   stroke_fill=(20, 10, 10))
        if T_LOOK - 1.4 <= ts < T_FLY:
            d.text((W / 2, 560), "1 LEFT...", font=F("anton.woff2", 84), fill=(255, 90, 90), anchor="mm",
                   stroke_width=5, stroke_fill=(20, 10, 10))
        if T_FLICK - 0.2 <= ts < T_FLY + 0.3:
            d.text((fist_x + 40, fist_y - 150), "*flick*", font=F("anton.woff2", 60), fill=(255, 255, 255), anchor="mm",
                   stroke_width=4, stroke_fill=(20, 10, 40))
        if ts >= T_FLY + 0.5:
            a_ = ts - (T_FLY + 0.5)
            s = 1 + 0.4 * max(0.0, 1 - a_ / 0.15)
            d.text((W / 2, 600), "FLAWLESS", font=F("anton.woff2", int(150 * s)), fill=(255, 220, 60), anchor="mm",
                   stroke_width=7, stroke_fill=(40, 10, 10))
            if a_ > 0.5:
                rgba = img.convert("RGBA")
                render.draw_rich(rgba, (W / 2, 720), "Who takes 10,000 next? Comment 👇", F("mont900.woff2", 50),
                                 (255, 255, 255), anchor="ma", stroke_width=4, stroke_fill=(0, 0, 0))
                img = rgba.convert("RGB")
        # secousse
        sh = 0
        if T_CHARGE <= gt < T_HIT:
            sh = 4
        if 0 <= gt - T_SSJ < 0.45:
            sh = 16
        if 0 <= ee < 1.6:
            sh = 34 * (1 - ee / 1.6)
        if 0 <= ts - T_FLY < 0.25:
            sh = 12
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
    rt = real
    for k in range(0, int(OFF * 3)):                                 # piétinement de la horde
        put(k / 3, S("hit", 20 + k % 4), 0.08)
    put(OFF + T_CHARGE, S("bomb", 5), 0.25)
    put(OFF + T_SSJ - 0.05, S("transform"), 0.9)
    put(OFF + T_SWING, S("teleport"), 0.5)
    put(TP, S("hit", 1), 1.0)
    put(TP + 0.22, S("bomb", 2), 1.0)
    put(TP + 0.3, S("ko"), 0.6)
    lt = sorted(launch_times)
    for j in range(0, len(lt), max(1, len(lt) // 45)):              # crépitement des 999 coups
        put(rt(lt[j]), S("hit", 30 + j % 6), 0.22)
    put(rt(T_FLICK), S("shots", 3), 0.5)
    put(rt(T_FLY), S("hit", 3), 0.9)
    put(rt(T_FLY) + 0.5, S("ko", 1), 0.7)
    lvl = float(np.percentile(np.abs(audio), 99.7)) or 1.0
    audio = audio * min(1.0, 0.75 / lvl)
    wav = out.with_suffix(".wav")
    fusion.write_wav(wav, np.tanh(audio * 1.1) / math.tanh(1.1) * 0.3)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out.with_suffix(".video.mp4")), "-i", str(wav),
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", str(out.with_suffix(".raw.mp4"))],
                   check=True)
    render.stamp_video(out.with_suffix(".raw.mp4"), out)
    print("OUT", out, round(DUR, 1), "down", count_shown)


if __name__ == "__main__":
    main()
