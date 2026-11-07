"""« Can Goku punch the ball 1 km? » avec un perso MUGEN (07/11, JUS Goku fourni par l'utilisateur).

python3 tools/punch/mugen_punch.py <dossier du perso> <sortie.mp4>
Repos → charge (sphère d'énergie au poing, roches qui montent, sol qui tremble) → UNE ruée + coup de poing (230)
→ arrêt sur image, souffle 6005, onde 6010, explosion 6015, débris → la boule part, la caméra suit,
compteur → 999 m, « 1 METER SHORT... ». Effets = ceux du perso MUGEN ; décor et textes = notre DA.
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
from clipper.slides import mugen, render  # noqa: E402

W, H, FPS = 1080, 1920, 30
F = lambda n, s: ImageFont.truetype(str(ROOT / "tools/money_sim/fonts" / n), s)  # noqa: E731
SC = 4                                    # agrandissement net des sprites (pixel-art)
GROUND = 1340
BALL_R = 280
BALL_X = 700
GOAL_M = 999.0
T_CHARGE, T_DASH = 1.2, 3.2


def sky(warm):
    y = np.linspace(0, 1, H)[:, None, None]
    top = np.array([10, 12, 34.])
    mid = np.array([60, 36, 110.]) * (1 - warm) + np.array([255, 110, 70.]) * warm
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
    for k in range(int(r), 0, -2):
        f = k / r
        d.ellipse((c - k - 10 * (1 - f), c - k - 10 * (1 - f), c + k - 10 * (1 - f), c + k - 10 * (1 - f)),
                  fill=(int(18 + 34 * (1 - f)), int(26 + 44 * (1 - f)), int(58 + 80 * (1 - f)), 255))
    d.ellipse((c - r, c - r, c + r, c + r), outline=(120, 230, 255, 255), width=5)
    for a0 in (0, 120, 240):
        d.arc((c - r * .95, c - r * .55, c + r * .95, c + r * .55), a0, a0 + 70, fill=(90, 140, 210, 160), width=4)
    d.ellipse((c + r * .35 - 10, c - r * .1 - 10, c + r * .35 + 10, c - r * .1 + 10), fill=(255, 170, 60, 255))
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    out.alpha_composite(im.filter(ImageFilter.GaussianBlur(16)))
    out.alpha_composite(im)
    return out


def dist_at(t, t_hit):
    if t < t_hit + 0.2:
        return 0.0
    e = t - t_hit - 0.2
    k = 0.45
    return GOAL_M * (1 - math.exp(-e * k)) / (1 - math.exp(-k * 8.5)) if e < 8.5 else GOAL_M


def main():
    D, out = Path(sys.argv[1]), Path(sys.argv[2])
    sff = next(D.glob("*.sff"))
    air_f = next(D.glob("*.air"))
    act = D / "pal0.act" if (D / "pal0.act").exists() else None
    spr = mugen.read_sff(sff, act)
    air = mugen.read_air(air_f)

    def frames(a):
        x = air[a]
        return x.frames if hasattr(x, "frames") else x

    def sprite(f, scale=SC, flip=False):
        s = spr.get((f.group, f.number))
        if not s:
            return None, (0, 0)
        im = s.image.resize((s.image.width * scale, s.image.height * scale), Image.NEAREST)
        return im, s.axis

    def anim(a, t, loop=True):
        fr = frames(a)
        total = sum((f.ticks if f.ticks > 0 else 8) for f in fr) / 60
        if loop:
            t = t % total
        acc = 0.0
        for f in fr:
            dd = (f.ticks if f.ticks > 0 else 8) / 60
            if t < acc + dd:
                return f
            acc += dd
        return fr[-1]

    # coup de poing : ruée 230, l'impact = 3e image (poing tendu)
    dash = frames(230)
    t_hit = T_DASH + sum((f.ticks if f.ticks > 0 else 8) for f in dash[:2]) / 60
    dur = t_hit + 0.2 + 8.5 + 2.4
    far = mountains(1, (28, 22, 58, 255), 170, 1150, 320, W * 12)
    near = mountains(2, (14, 12, 30, 255), 120, 1290, 230, W * 24)
    ball = ball_sprite(BALL_R)
    fT, fS, fN = F("anton.woff2", 96), F("mont900.woff2", 30), F("anton.woff2", 92)
    rnd = random.Random(5)
    rocks = []
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s",
                             f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf",
                             "18", "-pix_fmt", "yuv420p", str(out.with_suffix(".video.mp4"))], stdin=subprocess.PIPE)
    events = []
    for fi in range(int(dur * FPS)):
        t = fi / FPS
        tt = t if t < t_hit else max(t_hit, t - 0.18)          # arrêt sur image à l'impact
        m = dist_at(tt, t_hit)
        world = m * 6.0
        cam = world
        img = sky(min(1.0, max(0.0, (tt - t_hit) / 3.0)))
        img.alpha_composite(far.crop((int(cam * .15) % (W * 10), 0, int(cam * .15) % (W * 10) + W, H)))
        img.alpha_composite(near.crop((int(cam * .45) % (W * 20), 0, int(cam * .45) % (W * 20) + W, H)))
        d = ImageDraw.Draw(img, "RGBA")
        d.rectangle((0, GROUND, W, H), fill=(8, 8, 18, 255))
        d.line((0, GROUND, W, GROUND), fill=(150, 230, 255, 255), width=4)
        for gx in range(-(int(cam) % 160), W, 160):
            d.line((gx, GROUND + 18, gx + 60, GROUND + 18), fill=(80, 110, 160, 160), width=3)
        # perso
        gx = 150 - (cam if tt > t_hit else 0)
        if tt < T_CHARGE:
            f = anim(0, tt)
        elif tt < T_DASH:
            f = anim(2000, tt - T_CHARGE) if 2000 in air else anim(0, tt)
        else:
            e = tt - T_DASH
            acc, f = 0.0, dash[-1]
            for ff in dash:
                dd = (ff.ticks if ff.ticks > 0 else 8) / 60
                if e < acc + dd:
                    f = ff
                    break
                acc += dd
            gx += min(1.0, e / max(0.01, t_hit - T_DASH)) * 170
        # charge : sphère d'énergie + roches qui montent + tremblement
        power = 0.0
        if T_CHARGE <= tt < t_hit:
            power = min(1.0, (tt - T_CHARGE) / 1.6)
            if rnd.random() < 0.35 * power:
                rocks.append([gx + rnd.uniform(-60, 260), GROUND, rnd.uniform(-30, 30), -rnd.uniform(60, 160), t,
                              rnd.choice([8760, 8761, 8762, 8764]), 2.2])
            au = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(au).ellipse((gx + 40 - 130 * power, GROUND - 330 - 80 * power, gx + 240 + 130 * power, GROUND + 10),
                                       fill=(90, 170, 255, int(110 * power)))
            img.alpha_composite(au.filter(ImageFilter.GaussianBlur(45)))
        im, ax = sprite(f)
        if im is not None:
            img.alpha_composite(im, (int(gx + (f.dx - ax[0]) * SC), int(GROUND + (f.dy - ax[1]) * SC)))
        if T_CHARGE <= tt < T_DASH and 8000 in air:            # boule d'énergie dans la main
            ef = anim(8000, tt - T_CHARGE)
            eim, eax = sprite(ef, scale=int(2 + 3 * power))
            if eim is not None:
                img.alpha_composite(eim, (int(gx + 150 - eim.width / 2), int(GROUND - 190 - eim.height / 2)))
        # boule
        rb = ball.rotate(-math.degrees(world / BALL_R), resample=Image.BICUBIC)
        img.alpha_composite(rb, (int(BALL_X - rb.width / 2), int(GROUND - 30 - rb.height / 2)))
        # impact : effets du perso (souffle, onde, explosion) + débris
        e = t - t_hit
        cx, cy = BALL_X - BALL_R + 10, GROUND - 200
        if 0 <= e < 0.18:
            g = img.convert("L").point(lambda v: 255 if v > 70 else 0)
            img = Image.merge("RGBA", (g, g.point(lambda v: v * .85), g.point(lambda v: v * .35), Image.new("L", (W, H), 255)))
            d = ImageDraw.Draw(img, "RGBA")
            if not events or events[-1][1] != "hit":
                events.append((t, "hit"))
                for _ in range(16):
                    rocks.append([cx + rnd.uniform(-40, 40), cy + rnd.uniform(-60, 60), rnd.uniform(-500, 300),
                                  -rnd.uniform(300, 900), t, rnd.choice([8760, 8761, 8762, 8764, 8765]), 1.4])
        for a_no, t0, scl, ox, oy in ((6005, 0.0, 6, 40, 0), (6010, 0.05, 6, 0, 170), (6015, 0.1, 6, 60, -40)):
            ee = e - t0
            if a_no in air and 0 <= ee < 0.9:
                fr = anim(a_no, ee, loop=False)
                eim, eax = sprite(fr, scale=scl)
                if eim is not None:
                    img.alpha_composite(eim, (int(cx + ox - eim.width / 2), int(cy + oy - eim.height / 2)))
        if 0.18 <= e < 0.45:
            d.rectangle((0, 0, W, H), fill=(255, 255, 255, int(170 * (1 - (e - 0.18) / 0.27))))
        alive = []
        for rk in rocks:
            a = t - rk[4]
            if a < rk[6]:
                x = rk[0] + rk[2] * a - (cam if rk[4] > t_hit - 0.01 else 0) * 0
                y = rk[1] + rk[3] * a + 900 * a * a
                if y < GROUND + 10:
                    fr = anim(rk[5], a)
                    rim, _ = sprite(fr, scale=4)
                    if rim is not None:
                        img.alpha_composite(rim, (int(x), int(y)))
                    alive.append(rk)
        rocks[:] = alive
        if tt > t_hit and m < GOAL_M - 1:                         # lignes de vitesse
            sp_ = (dist_at(tt + 0.05, t_hit) - m) * 30
            for _ in range(int(min(18, sp_ / 25))):
                y = rnd.uniform(560, GROUND - 20)
                x = rnd.uniform(0, W)
                d.line((x, y, x + min(400, sp_ * 1.5), y), fill=(255, 255, 255, 60), width=3)
        # titre + compteurs
        d.text((W / 2, 70), "CAN GOKU PUNCH", font=fT, fill="white", anchor="mt", stroke_width=4, stroke_fill=(20, 10, 40))
        d.text((W / 2, 172), "THE BALL 1 KM?", font=fT, fill=(255, 200, 60), anchor="mt", stroke_width=4, stroke_fill=(20, 10, 40))
        d.text((W * 0.3, 320), "PUNCHES", font=fS, fill=(200, 200, 230), anchor="mt")
        d.text((W * 0.7, 320), "DISTANCE", font=fS, fill=(200, 200, 230), anchor="mt")
        d.text((W * 0.3, 360), "1" if t >= t_hit else "0", font=fN, fill="white", anchor="mt")
        col = (90, 255, 160) if 1 <= m < GOAL_M - 0.5 else (255, 90, 120)
        d.text((W * 0.7, 360), f"{m:,.0f} m", font=fN, fill=col, anchor="mt")
        bar = min(1.0, m / 1000)
        d.rounded_rectangle((140, 480, W - 140, 500), 10, fill=(255, 255, 255, 40))
        d.rounded_rectangle((140, 480, 140 + (W - 280) * max(bar, 0.012), 500), 10, fill=(255, 200, 60, 255))
        d.text((W - 140, 512), "1 KM", font=fS, fill=(255, 200, 60), anchor="ra")
        if t > dur - 2.4:
            a = min(1.0, (t - (dur - 2.4)) / 0.25)
            d.text((W / 2, 650), "1 METER SHORT...", font=F("anton.woff2", int(112 * (0.8 + 0.2 * a))),
                   fill=(255, 90, 120), anchor="mm", stroke_width=5, stroke_fill=(20, 10, 40))
            render.draw_rich(img, (W / 2, 740), "Rematch? Comment 👇", F("mont900.woff2", 54), (255, 255, 255),
                             anchor="ma", stroke_width=3, stroke_fill=(0, 0, 0))
        sh = 0
        if T_CHARGE <= tt < t_hit:
            sh = 3 + 5 * power
        if 0 <= e < 0.7:
            sh = 28 * (1 - e / 0.7)
        if sh:
            dx, dy = rnd.randint(-int(sh), int(sh)), rnd.randint(-int(sh), int(sh))
            bgf = Image.new("RGBA", (W, H), (0, 0, 0, 255))
            bgf.alpha_composite(img, (dx, dy))
            img = bgf
        proc.stdin.write(img.convert("RGB").tobytes())
    proc.stdin.close()
    proc.wait()
    # son : banque Dragon Ball (charge, coup, explosion) + roulement
    from clipper.slides import domain, fusion
    rate = fusion.RATE
    na = int(dur * rate) + rate
    audio = np.zeros(na, np.float32)

    def put(tt_, x, g):
        if x is None:
            return
        i = int(tt_ * rate)
        seg = x[: max(0, na - i)]
        audio[i:i + len(seg)] += seg * g
    fr_ = "dragon ball"
    put(T_CHARGE, domain.sfx("transform", mode="anime", franchise=fr_), 0.7)
    put(T_DASH, domain.sfx("teleport", mode="anime", franchise=fr_), 0.6)
    put(t_hit, domain.sfx("hit", mode="anime", seed=1, franchise=fr_), 1.0)
    put(t_hit + 0.03, domain.sfx("bomb", mode="anime", seed=2, franchise=fr_), 0.9)
    put(t_hit + 0.2, domain.sfx("beam", mode="anime", seed=3, franchise=fr_), 0.4)
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
