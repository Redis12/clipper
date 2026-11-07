"""« Can Goku punch the ball 1 km? » avec le stickman Stick Nodes de l'utilisateur (Goku SSJ1, 07/11).

python3 tools/punch/stick_punch.py <goku_nodes.json> <sortie.mp4>
Base (cheveux noirs) → concentration → flash Super Saiyan (cheveux jaunes, aura, éclairs, roches) → élan →
UN coup de poing → arrêt sur image, explosion, ondes, débris → la boule part, la caméra suit → 999 m.
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
import sticknodes as sn  # noqa: E402
from mugen_punch import F, GROUND, H, W, FPS, ball_sprite, mountains, sky  # noqa: E402
import rig  # noqa: E402

GOAL_M = 9999.0
FLY = 9.0                                  # secondes de vol


def dist_at(t, t_hit):
    if t < t_hit + 0.2:
        return 0.0
    e = t - t_hit - 0.2
    k = 0.42
    return GOAL_M * (1 - math.exp(-e * k)) / (1 - math.exp(-k * FLY)) if e < FLY else GOAL_M


def height_at(t, t_hit):
    """Hauteur de la boule (px) : grande courbe puis rebonds de plus en plus petits."""
    e = t - t_hit - 0.2
    if e <= 0:
        return 0.0
    arcs = [(1.6, 400), (1.1, 220), (0.8, 110), (0.6, 50), (0.45, 20)]
    for du, hmax in arcs:
        if e < du:
            x = e / du
            return 4 * hmax * x * (1 - x)
        e -= du
    return 0.0
from clipper.slides import render, vfxgen  # noqa: E402

BALL_R = 270
SCALE = 0.9
T_CHARGE, T_SSJ, T_WIND, T_SWING = 0.9, 2.0, 3.1, 3.45
T_HIT = 3.6
GX = 230                                   # x de la hanche au repos


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def pose_at(t):
    if t < T_CHARGE:
        p = dict(gp.IDLE)
        p[53] += 2 * math.sin(t * 5)
        return p
    if t < T_WIND:
        p = sn.lerp_pose(gp.IDLE, gp.CHARGE, ease((t - T_CHARGE) / 0.5))
        p[54] += 1.5 * math.sin(t * 40)
        return p
    if t < T_SWING:
        return sn.lerp_pose(gp.CHARGE, gp.WINDUP, ease((t - T_WIND) / 0.3))
    if t < T_HIT:
        return sn.lerp_pose(gp.WINDUP, gp.PUNCH, ease((t - T_SWING) / (T_HIT - T_SWING)) ** 0.6)
    return gp.PUNCH


def main():
    fig = sn.load(sys.argv[1])
    out = Path(sys.argv[2])
    dur = T_HIT + 0.2 + FLY + 2.4
    # où arrive le poing à l'impact → la boule est posée juste devant
    imP, posP, oP = sn.render(fig, scale=SCALE, absolute=gp.PUNCH)
    bottomP = np.nonzero(np.asarray(imP)[..., 3].max(1) > 0)[0].max()
    DASH = 120
    fist = posP[253]
    fist_x = GX + DASH + (fist[0] - oP[0])
    fist_y = GROUND - (bottomP - fist[1])
    BALL_X = fist_x + BALL_R - 25
    far = mountains(1, (28, 22, 58, 255), 170, 1150, 320, W * 12)
    near = mountains(2, (14, 12, 30, 255), 120, 1290, 230, W * 24)
    ball = ball_sprite(BALL_R)
    explo = list(vfxgen.frames("explosion", 520, (255, 210, 80)))
    ring = list(vfxgen.frames("ring", 700, (255, 240, 180)))
    bolt = list(vfxgen.frames("lightning", 260, (255, 240, 120)))
    fT, fS, fN = F("anton.woff2", 96), F("mont900.woff2", 30), F("anton.woff2", 92)
    rnd = random.Random(7)
    debris = []
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s",
                             f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf",
                             "18", "-pix_fmt", "yuv420p", str(out.with_suffix(".video.mp4"))], stdin=subprocess.PIPE)
    for fi in range(int(dur * FPS)):
        t = fi / FPS
        tt = t if t < T_HIT else max(T_HIT, t - 0.2)             # arrêt sur image à l'impact
        m = dist_at(tt, T_HIT)
        cam = m * 0.62
        img = sky(min(1.0, max(0.0, (tt - T_HIT) / 3.0)))
        img.alpha_composite(far.crop((int(cam * .15) % (W * 10), 0, int(cam * .15) % (W * 10) + W, H)))
        img.alpha_composite(near.crop((int(cam * .45) % (W * 20), 0, int(cam * .45) % (W * 20) + W, H)))
        img = img.convert("RGB")
        d = ImageDraw.Draw(img, "RGBA")
        d.rectangle((0, GROUND, W, H), fill=(8, 8, 18))
        d.line((0, GROUND, W, GROUND), fill=(150, 230, 255), width=4)
        for gx in range(-(int(cam) % 160), W, 160):
            d.line((gx, GROUND + 18, gx + 60, GROUND + 18), fill=(80, 110, 160, 160), width=3)
        # perso
        ssj = tt >= T_SSJ
        cm = None if ssj else (lambda i, c: (22, 22, 28, 255) if c[:3] in gp.HAIR_COLORS else c)
        pim, pos, org = sn.render(fig, scale=SCALE, absolute=pose_at(tt), color_map=cm)
        bottom = np.nonzero(np.asarray(pim)[..., 3].max(1) > 0)[0].max()
        dash = DASH * ease((tt - T_SWING) / (T_HIT - T_SWING)) if tt >= T_SWING else 0
        gx = GX + dash - (cam if tt > T_HIT else 0)
        px, py = int(gx - org[0]), int(GROUND - bottom)
        power = 0.0
        if T_SSJ <= tt < T_HIT + 0.3:
            power = min(1.0, (tt - T_SSJ) / 0.6) * (1 if tt < T_HIT else max(0, 1 - (tt - T_HIT) / 0.3))
            au = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ad = ImageDraw.Draw(au)
            ch_ = (GROUND - py) * 0.62
            acy = GROUND - ch_ * 0.95
            for scl, col, al in ((1.25, (255, 225, 40), 150), (1.0, (255, 245, 150), 190), (0.7, (255, 255, 235), 170)):
                ad.polygon(rig.aura_poly(gx, acy, (150 + 40 * power) * scl, ch_ * scl, t * 1.3 + scl, n=30,
                                         seed=int(scl * 10)), fill=col + (int(al * power),))
            glow = au.filter(ImageFilter.GaussianBlur(18))
            img.paste(glow, (0, 0), glow)
            au = au.filter(ImageFilter.GaussianBlur(1.5))
            img.paste(au, (0, 0), au)
            if rnd.random() < 0.45 * power:
                debris.append([gx + rnd.uniform(-220, 220), GROUND - 6, rnd.uniform(-25, 25), -rnd.uniform(90, 220), t,
                               rnd.uniform(6, 14), 2.0])
            if fi % 3 == 0 and power > 0.3:
                b = bolt[fi // 3 % len(bolt)]
                img.paste(b, (int(gx - b.width / 2 + rnd.uniform(-60, 60)), int(py + rnd.uniform(0, 200))), b)
        if T_CHARGE <= tt < T_SSJ:                                # avant la transformation : poussière, tremblement
            if rnd.random() < 0.3:
                debris.append([gx + rnd.uniform(-160, 160), GROUND - 6, rnd.uniform(-15, 15), -rnd.uniform(40, 120), t,
                               rnd.uniform(4, 9), 1.5])
        img.paste(pim, (px, py), pim)
        rb = ball.rotate(-math.degrees(cam / BALL_R), resample=Image.BICUBIC)
        bx = BALL_X                                                 # la boule reste au centre, le monde défile
        hy = height_at(tt, T_HIT)
        if hy < 5:                                                  # ombre / contact au sol
            pass
        sh_ = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(sh_).ellipse((bx - BALL_R * (1 - hy / 1400), GROUND - 14, bx + BALL_R * (1 - hy / 1400), GROUND + 14),
                                    fill=(0, 0, 0, int(140 * (1 - hy / 700))))
        img.paste(sh_, (0, 0), sh_)
        img.paste(rb, (int(bx - rb.width / 2), int(GROUND - BALL_R - hy - rb.height / 2)), rb)
        d = ImageDraw.Draw(img, "RGBA")
        if 0 <= tt - T_SSJ < 0.35:
            d.rectangle((0, 0, W, H), fill=(255, 245, 180, int(235 * (1 - (tt - T_SSJ) / 0.35))))
        e = t - T_HIT
        cx, cy = fist_x, fist_y
        if 0 <= e < 0.2:                                          # arrêt sur image : 2 tons
            g = img.convert("L").point(lambda v: 255 if v > 80 else 0)
            img = Image.merge("RGB", (g, g.point(lambda v: v * .85), g.point(lambda v: v * .3)))
            d = ImageDraw.Draw(img, "RGBA")
            if e < 1 / FPS:
                for _ in range(22):
                    debris.append([cx + rnd.uniform(-30, 30), cy + rnd.uniform(-50, 50), rnd.uniform(-250, 700),
                                   -rnd.uniform(300, 950), t, rnd.uniform(8, 18), 1.6])
        if 0.2 <= e < 1.2:                                        # explosion + 2 ondes
            k = (e - 0.2) / 1.0
            ex = explo[min(len(explo) - 1, int(k * len(explo)))]
            img.paste(ex, (int(cx - ex.width / 2 - cam * 0), int(cy - ex.height / 2)), ex)
            for dl in (0.0, 0.15):
                k2 = (e - 0.2 - dl) / 0.6
                if 0 <= k2 < 1:
                    rr = ring[min(len(ring) - 1, int(k2 * len(ring)))]
                    img.paste(rr, (int(cx - rr.width / 2), int(cy - rr.height / 2)), rr)
            d = ImageDraw.Draw(img, "RGBA")
            if e < 0.45:
                d.rectangle((0, 0, W, H), fill=(255, 255, 255, int(190 * (1 - (e - 0.2) / 0.25))))
        alive = []
        for db in debris:
            a = t - db[4]
            if a < db[6]:
                x, y = db[0] + db[2] * a, db[1] + db[3] * a + 950 * a * a
                if y < GROUND + 4:
                    s = db[5]
                    d.polygon([(x - s, y), (x - s * .3, y - s), (x + s, y - s * .4), (x + s * .6, y + s * .7)],
                              fill=(70, 60, 80, 255))
                    alive.append(db)
        debris[:] = alive
        if tt > T_HIT and m < GOAL_M - 1:
            sp_ = (dist_at(tt + 0.05, T_HIT) - m) * 30
            for _ in range(int(min(18, sp_ / 25))):
                y, x = rnd.uniform(560, GROUND - 20), rnd.uniform(0, W)
                d.line((x, y, x + min(400, sp_ * 1.5), y), fill=(255, 255, 255, 60), width=3)
        d.text((W / 2, 70), "CAN GOKU PUNCH", font=fT, fill="white", anchor="mt", stroke_width=4, stroke_fill=(20, 10, 40))
        d.text((W / 2, 172), "THE BALL 10 KM?", font=fT, fill=(255, 200, 60), anchor="mt", stroke_width=4, stroke_fill=(20, 10, 40))
        d.text((W * 0.3, 320), "PUNCHES", font=fS, fill=(200, 200, 230), anchor="mt")
        d.text((W * 0.7, 320), "DISTANCE", font=fS, fill=(200, 200, 230), anchor="mt")
        d.text((W * 0.3, 360), "1" if t >= T_HIT else "0", font=fN, fill="white", anchor="mt")
        col = (90, 255, 160) if 1 <= m < GOAL_M - 0.5 else (255, 90, 120)
        d.text((W * 0.7, 360), f"{m:,.0f} m", font=fN, fill=col, anchor="mt")
        d.rounded_rectangle((140, 480, W - 140, 500), 10, fill=(50, 50, 80))
        d.rounded_rectangle((140, 480, 140 + (W - 280) * max(min(1.0, m / 10000), 0.012), 500), 10, fill=(255, 200, 60))
        d.text((W - 140, 512), "10 KM", font=fS, fill=(255, 200, 60), anchor="ra")
        if t > dur - 2.4:
            a = min(1.0, (t - (dur - 2.4)) / 0.25)
            d.text((W / 2, 650), "1 METER SHORT...", font=F("anton.woff2", int(112 * (0.8 + 0.2 * a))),
                   fill=(255, 90, 120), anchor="mm", stroke_width=5, stroke_fill=(20, 10, 40))
            rgba = img.convert("RGBA")
            render.draw_rich(rgba, (W / 2, 740), "Rematch? Comment 👇", F("mont900.woff2", 54), (255, 255, 255),
                             anchor="ma", stroke_width=3, stroke_fill=(0, 0, 0))
            img = rgba.convert("RGB")
        sh = (2 + 6 * power) if T_CHARGE <= tt < T_HIT else 0
        if 0 <= tt - T_SSJ < 0.45:
            sh = 16
        if 0 <= e < 0.8:
            sh = 30 * (1 - e / 0.8)
        if sh:
            dx, dy = rnd.randint(-int(sh), int(sh)), rnd.randint(-int(sh), int(sh))
            bgf = Image.new("RGB", (W, H), (0, 0, 0))
            bgf.paste(img, (dx, dy))
            img = bgf
        proc.stdin.write(img.tobytes())
    proc.stdin.close()
    proc.wait()
    from clipper.slides import domain, fusion
    rate = fusion.RATE
    na = int(dur * rate) + rate
    audio = np.zeros(na, np.float32)

    def put(t_, x, g):
        if x is None:
            return
        i = int(t_ * rate)
        seg = x[: max(0, na - i)]
        audio[i:i + len(seg)] += seg * g
    fr_ = "dragon ball"
    put(T_CHARGE, domain.sfx("bomb", mode="anime", seed=5, franchise=fr_), 0.25)
    put(T_SSJ - 0.05, domain.sfx("transform", mode="anime", franchise=fr_), 0.9)
    put(T_SWING, domain.sfx("teleport", mode="anime", franchise=fr_), 0.5)
    put(T_HIT, domain.sfx("hit", mode="anime", seed=1, franchise=fr_), 1.0)
    put(T_HIT + 0.2, domain.sfx("bomb", mode="anime", seed=2, franchise=fr_), 0.9)
    put(T_HIT + 0.35, domain.sfx("beam", mode="anime", seed=3, franchise=fr_), 0.35)
    put(dur - 2.4, domain.sfx("ko", mode="anime", franchise=fr_), 0.5)
    lvl = float(np.percentile(np.abs(audio), 99.7)) or 1.0
    audio = audio * min(1.0, 0.75 / lvl)
    wav = out.with_suffix(".wav")
    fusion.write_wav(wav, np.tanh(audio * 1.1) / math.tanh(1.1) * 0.3)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out.with_suffix(".video.mp4")), "-i", str(wav),
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", str(out.with_suffix(".raw.mp4"))],
                   check=True)
    render.stamp_video(out.with_suffix(".raw.mp4"), out)
    print("OUT", out, round(dur, 1))


if __name__ == "__main__":
    main()
