"""« Punch the ball » en stickman lumineux (07/11, demandé : « stickman, respecte juste les cheveux », « un gros coup »).

python3 tools/punch/stick.py <sortie.mp4>
Goku stickman : repos → concentration (aura) → Super Saiyan (flash, cheveux jaunes) → élan → UN coup → la boule part,
la caméra suit, compteur de distance, s'arrête à 999 m (« so close »).
"""
import math
import random
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import rig  # noqa: E402

W, H, FPS = 1080, 1920, 30
F = lambda n, s: ImageFont.truetype(str(ROOT / "tools/money_sim/fonts" / n), s)  # noqa: E731
GROUND = 1340
BALL_R = 300
BALL_X = 720
GOAL_M = 999.0

IDLE = dict(lean=4, sh_f=25, el_f=-70, sh_b=-25, el_b=-60, hip_f=-18, kn_f=22, hip_b=18, kn_b=18, head=0, crouch=0)
CHARGE = dict(lean=-6, sh_f=-35, el_f=-100, sh_b=-40, el_b=-95, hip_f=-38, kn_f=60, hip_b=38, kn_b=40, head=-4, crouch=34)
WINDUP = dict(lean=-18, sh_f=-75, el_f=-95, sh_b=40, el_b=-40, hip_f=-48, kn_f=70, hip_b=45, kn_b=15, head=-6, crouch=28)
PUNCH = dict(lean=28, sh_f=98, el_f=0, sh_b=-55, el_b=-80, hip_f=-55, kn_f=25, hip_b=55, kn_b=0, head=10, crouch=14)

T_CHARGE, T_SSJ, T_WIND, T_DASH, T_HIT = 1.0, 2.4, 3.4, 3.9, 4.15


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def pose_at(t):
    if t < T_CHARGE:
        p = dict(IDLE)
        p["crouch"] = 3 * math.sin(t * 4)
        return p
    if t < T_WIND:
        p = rig.lerp_pose(IDLE, CHARGE, ease((t - T_CHARGE) / 0.4))
        p["crouch"] += 2 * math.sin(t * 30)                  # tremble en chargeant
        return p
    if t < T_DASH:
        return rig.lerp_pose(CHARGE, WINDUP, ease((t - T_WIND) / 0.35))
    if t < T_HIT:
        return rig.lerp_pose(WINDUP, PUNCH, ease((t - T_DASH) / (T_HIT - T_DASH)) ** 0.5)
    return PUNCH


def stickman(p, hair_col, glow_col, s=1.0):
    """Squelette en traits blancs lumineux + coiffure de Goku."""
    k = 2 * s
    Wc, Hc = int(520 * k), int(640 * k)
    lines = Image.new("L", (Wc, Hc), 0)
    d = ImageDraw.Draw(lines)
    hip = (Wc * 0.45, Hc * 0.66 + p["crouch"] * k)
    th, sl, al = 92 * k, 120 * k, 76 * k
    neck = rig._pt(hip, 180 + p["lean"], sl)
    sh = rig._pt(hip, 180 + p["lean"], sl * 0.9)
    w = int(13 * k)

    def seg(a, b):
        d.line((a, b), fill=255, width=w)
        for q in (a, b):
            d.ellipse((q[0] - w / 2, q[1] - w / 2, q[0] + w / 2, q[1] + w / 2), fill=255)
    for hp, kn in ((p["hip_b"], p["kn_b"]), (p["hip_f"], p["kn_f"])):
        kk = rig._pt(hip, hp, th)
        seg(hip, kk)
        seg(kk, rig._pt(kk, hp - kn, th))
    seg(hip, neck)
    for shp, el in ((p["sh_b"], p["el_b"]), (p["sh_f"], p["el_f"])):
        e = rig._pt(sh, shp, al)
        seg(sh, e)
        hnd = rig._pt(e, shp + el, al * 0.95)
        seg(e, hnd)
        d.ellipse((hnd[0] - 11 * k, hnd[1] - 11 * k, hnd[0] + 11 * k, hnd[1] + 11 * k), fill=255)
    hr = 30 * k
    hc = rig._pt(neck, 180 + p["lean"] + p["head"], hr * 1.15)
    d.ellipse((hc[0] - hr, hc[1] - hr, hc[0] + hr, hc[1] + hr), fill=255)
    fist = rig._pt(rig._pt(sh, p["sh_f"], al), p["sh_f"] + p["el_f"], al * 0.95)
    # cheveux (silhouette de Goku) dans un calque à part
    hair = Image.new("L", (Wc, Hc), 0)
    rig._hair(ImageDraw.Draw(hair), hc, hr * 1.05, "up" if hair_col != (20, 20, 30) else "base", 255,
              p["lean"] * 0.5 + p["head"])
    body_glow = lines.filter(ImageFilter.GaussianBlur(9 * k))
    hair_glow = hair.filter(ImageFilter.MaxFilter(int(5 * k) | 1)).filter(ImageFilter.GaussianBlur(5 * k))
    out = Image.new("RGBA", (Wc, Hc), (0, 0, 0, 0))
    out.paste(Image.new("RGBA", (Wc, Hc), glow_col + (255,)), (0, 0), body_glow.point(lambda v: min(255, v * 2)))
    out.paste(Image.new("RGBA", (Wc, Hc), (255, 255, 255, 255)), (0, 0), hair_glow.point(lambda v: int(v * .9)))
    out.paste(Image.new("RGBA", (Wc, Hc), (255, 255, 255, 255)), (0, 0), lines)
    out.paste(Image.new("RGBA", (Wc, Hc), hair_col + (255,)), (0, 0), hair)
    out = out.resize((Wc // 2, Hc // 2), Image.LANCZOS)
    return out, (hip[0] / 2, hip[1] / 2), (fist[0] / 2, fist[1] / 2)


def sky(warm):
    y = np.linspace(0, 1, H)[:, None, None]
    top = np.array([10, 12, 34.])
    mid = np.array([60, 36, 110.]) * (1 - warm) + np.array([255, 105, 70.]) * warm
    a = np.where(y < 0.62, top * (1 - y / 0.62) + mid * (y / 0.62), mid)
    return Image.fromarray(a.repeat(W, 1).clip(0, 255).astype(np.uint8)).convert("RGBA")


def mountains(seed, col, amp, base, period, width):
    r = random.Random(seed)
    pts, x = [(0, H)], -200
    while x < width:
        pts.append((x, base - r.uniform(0.3, 1) * amp))
        x += r.uniform(period * 0.5, period)
    pts.append((width, H))
    im = Image.new("RGBA", (width, H), (0, 0, 0, 0))
    ImageDraw.Draw(im).polygon(pts, fill=col)
    return im


def ball_sprite(r):
    s = int(r * 2 + 60)
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = s / 2
    for kk in range(int(r), 0, -2):
        f = kk / r
        d.ellipse((c - kk - 10 * (1 - f), c - kk - 10 * (1 - f), c + kk - 10 * (1 - f), c + kk - 10 * (1 - f)),
                  fill=(int(18 + 34 * (1 - f)), int(26 + 44 * (1 - f)), int(58 + 80 * (1 - f)), 255))
    d.ellipse((c - r, c - r, c + r, c + r), outline=(120, 230, 255, 255), width=5)
    for a0 in (0, 120, 240):                                  # coutures : on voit la boule rouler
        d.arc((c - r * .95, c - r * .55, c + r * .95, c + r * .55), a0, a0 + 70, fill=(90, 140, 210, 160), width=4)
    d.ellipse((c + r * .35 - 10, c - r * .1 - 10, c + r * .35 + 10, c - r * .1 + 10), fill=(255, 170, 60, 255))
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    out.alpha_composite(im.filter(ImageFilter.GaussianBlur(16)))
    out.alpha_composite(im)
    return out


def dist_at(t):
    """Distance (m) après le coup : part très vite, ralentit, s'arrête à 999 m."""
    if t < T_HIT + 0.2:
        return 0.0
    e = t - T_HIT - 0.2
    return GOAL_M * (1 - math.exp(-e * 0.42)) / (1 - math.exp(-0.42 * 9.0)) if e < 9.0 else GOAL_M


def main():
    out = Path(sys.argv[1])
    dur = T_HIT + 0.2 + 9.0 + 2.2
    far = mountains(1, (28, 22, 58, 255), 170, 1150, 320, W * 12)
    near = mountains(2, (14, 12, 30, 255), 120, 1290, 230, W * 24)
    ball = ball_sprite(BALL_R)
    fT, fS, fN = F("anton.woff2", 96), F("mont900.woff2", 30), F("anton.woff2", 92)
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s",
                             f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf",
                             "18", "-pix_fmt", "yuv420p", str(out)], stdin=subprocess.PIPE)
    rnd = random.Random(3)
    sparks = []
    for fi in range(int(dur * FPS)):
        t = fi / FPS
        # arrêt sur image à l'impact (4 images figées)
        tt = t if t < T_HIT else max(T_HIT, t - 0.15)
        m = dist_at(tt)
        px_per_m = 6.0
        world = m * px_per_m
        cam = world
        ssj = tt >= T_SSJ
        hair_col = (255, 222, 60) if ssj else (20, 20, 30)
        glow_col = (255, 210, 80) if ssj else (120, 220, 255)
        img = sky(min(1.0, max(0.0, (tt - T_HIT) / 3.0)))
        img.alpha_composite(far.crop((int(cam * 0.15) % (W * 10), 0, int(cam * 0.15) % (W * 10) + W, H)))
        img.alpha_composite(near.crop((int(cam * 0.45) % (W * 20), 0, int(cam * 0.45) % (W * 20) + W, H)))
        d = ImageDraw.Draw(img, "RGBA")
        d.rectangle((0, GROUND, W, H), fill=(8, 8, 18, 255))
        d.line((0, GROUND, W, GROUND), fill=(150, 230, 255, 255), width=4)
        for gx in range(-(int(cam) % 160), W, 160):                # repères au sol qui défilent
            d.line((gx, GROUND + 18, gx + 60, GROUND + 18), fill=(80, 110, 160, 160), width=3)
        # aura qui monte pendant la charge
        p = pose_at(tt)
        dash = ease((tt - T_DASH) / (T_HIT - T_DASH)) * 150 if tt >= T_DASH else 0
        gx0 = 170 + dash - (cam if tt > T_HIT else 0)
        if T_CHARGE <= tt < T_HIT + 0.6 and gx0 > -400:
            power = min(1.0, (tt - T_CHARGE) / 1.4) * (1.0 if tt < T_HIT else max(0, 1 - (tt - T_HIT) / 0.6))
            for _ in range(int(6 * power)):
                sparks.append([gx0 + 230 + rnd.uniform(-90, 90), GROUND - rnd.uniform(0, 40), rnd.uniform(-20, 20),
                               -rnd.uniform(200, 520), t, glow_col])
            au = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(au).ellipse((gx0 + 230 - 150 * power - 40, GROUND - 400 - 120 * power,
                                        gx0 + 230 + 150 * power + 40, GROUND + 20), fill=glow_col + (int(120 * power),))
            img.alpha_composite(au.filter(ImageFilter.GaussianBlur(40)))
        alive = []
        for sp in sparks:
            a = (t - sp[4]) / 0.7
            if a < 1:
                x, y = sp[0] + sp[2] * a, sp[1] + sp[3] * a
                d.line((x, y, x, y + 26 * (1 - a)), fill=sp[5] + (int(255 * (1 - a)),), width=4)
                alive.append(sp)
        sparks[:] = alive
        # boule
        rb = ball.rotate(-math.degrees(world / BALL_R), resample=Image.BICUBIC)
        img.alpha_composite(rb, (int(BALL_X - rb.width / 2), int(GROUND - 30 - rb.height / 2 - BALL_R + BALL_R)))
        # le stickman
        st, hip, fist = stickman(p, hair_col, glow_col)
        img.alpha_composite(st, (int(gx0), int(GROUND - hip[1] - 108)))
        # flash Super Saiyan
        if 0 <= tt - T_SSJ < 0.25:
            d.rectangle((0, 0, W, H), fill=(255, 240, 160, int(220 * (1 - (tt - T_SSJ) / 0.25))))
        # impact : flash, ondes, lignes de vitesse
        e = t - T_HIT
        if 0 <= e < 0.15:                                          # arrêt sur image : image d'impact 2 tons
            g = img.convert("L").point(lambda v: 255 if v > 70 else 0)
            img = Image.merge("RGBA", (g, g.point(lambda v: v * 0.9), g.point(lambda v: v * 0.4), Image.new("L", (W, H), 255)))
            d = ImageDraw.Draw(img, "RGBA")
        if 0.15 <= e < 0.9:
            a = (e - 0.15) / 0.75
            cx, cy = BALL_X - BALL_R + 20, GROUND - BALL_R
            for rr, wd in ((80 + 900 * a, 14), (40 + 600 * a, 8)):
                d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=(255, 255, 255, int(255 * (1 - a))), width=wd)
            if a < 0.3:
                d.rectangle((0, 0, W, H), fill=(255, 255, 255, int(200 * (1 - a / 0.3))))
        if tt > T_HIT and m < GOAL_M - 1:
            sp_ = (dist_at(tt + 0.05) - m) * 30
            for kline in range(int(min(18, sp_ / 25))):
                y = rnd.uniform(500, GROUND - 20)
                x = rnd.uniform(0, W)
                d.line((x, y, x + min(400, sp_ * 1.5), y), fill=(255, 255, 255, 60), width=3)
        # HUD
        d.text((W / 2, 70), "CAN GOKU PUNCH", font=fT, fill="white", anchor="mt", stroke_width=4, stroke_fill=(20, 10, 40))
        d.text((W / 2, 172), "THE BALL 1 KM?", font=fT, fill=(255, 200, 60), anchor="mt", stroke_width=4, stroke_fill=(20, 10, 40))
        d.text((W * 0.3, 320), "PUNCHES", font=fS, fill=(200, 200, 230), anchor="mt")
        d.text((W * 0.7, 320), "DISTANCE", font=fS, fill=(200, 200, 230), anchor="mt")
        d.text((W * 0.3, 360), "1" if t >= T_HIT else "0", font=fN, fill="white", anchor="mt")
        txt = f"{m:,.0f} m" if m >= 1 else "0 m"
        col = (90, 255, 160) if m >= 1 else (255, 90, 120)
        if m >= GOAL_M - 0.5:
            col = (255, 90, 120)
        d.text((W * 0.7, 360), txt, font=fN, fill=col, anchor="mt")
        bar = min(1.0, m / 1000)
        d.rounded_rectangle((140, 480, W - 140, 500), 10, fill=(255, 255, 255, 40))
        d.rounded_rectangle((140, 480, 140 + (W - 280) * bar, 500), 10, fill=(255, 200, 60, 255))
        d.text((W - 140, 510), "1 KM", font=fS, fill=(255, 200, 60), anchor="ra")
        if t > dur - 2.2:
            a = min(1.0, (t - (dur - 2.2)) / 0.25)
            d.text((W / 2, 640), "1 METER SHORT...", font=F("anton.woff2", int(110 * (0.8 + 0.2 * a))), fill=(255, 90, 120),
                   anchor="mm", stroke_width=5, stroke_fill=(20, 10, 40))
        # secousse
        sh = 0
        if 0 <= tt - T_SSJ < 0.4:
            sh = 10
        if 0 <= e < 0.6:
            sh = 26 * (1 - e / 0.6)
        if sh:
            dx, dy = rnd.randint(-int(sh), int(sh)), rnd.randint(-int(sh), int(sh))
            bgf = Image.new("RGBA", (W, H), (0, 0, 0, 255))
            bgf.alpha_composite(img, (dx, dy))
            img = bgf
        proc.stdin.write(img.convert("RGB").tobytes())
    proc.stdin.close()
    proc.wait()
    print("OUT", out, round(dur, 1))


if __name__ == "__main__":
    main()
