"""« Can Goku punch the ball 1 km? » avec une planche de sprites découpée par tools/sprites (07/11).

python3 tools/punch/sprite_punch.py <dossier planche découpée> <dossier MUGEN pour les effets> <sortie.mp4>
Base → flash → Super Saiyan (aura, roches, sol qui tremble) → élan → UN coup de poing → arrêt sur image, souffle,
onde, explosion, débris (effets du MUGEN) → la boule part, caméra qui suit, compteur → 999 m, « 1 METER SHORT... ».
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
sys.path.insert(0, str(ROOT / "tools/sprites"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import anim  # noqa: E402
from mugen_punch import F, GROUND, GOAL_M, H, W, FPS, ball_sprite, dist_at, mountains, sky  # noqa: E402
from clipper.slides import mugen, render  # noqa: E402

SC = 4
BALL_R = 280
T_SSJ, T_WIND = 1.1, 2.9


def main():
    SD, MD, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    spr = mugen.read_sff(next(MD.glob("*.sff")), MD / "pal0.act")
    air = mugen.read_air(next(MD.glob("*.air")))

    def fx(a, t, scale):
        x = air[a]
        fr = x.frames if hasattr(x, "frames") else x
        acc = 0.0
        f = fr[-1]
        for ff in fr:
            dd = (ff.ticks if ff.ticks > 0 else 8) / 60
            if t < acc + dd:
                f = ff
                break
            acc += dd
        s = spr.get((f.group, f.number))
        if not s:
            return None
        return s.image.resize((s.image.width * scale, s.image.height * scale), Image.NEAREST)

    seq = anim._meta(str(SD))[1]["punch"]
    t_hit = T_WIND + seq[0][1] + seq[1][1] + seq[2][1]          # poing complètement tendu (dernière image)
    dur = t_hit + 0.2 + 8.5 + 2.4
    # où est le poing à l'impact → la boule commence juste là
    im_p, (ax_p, _) = anim.frame(SD, "punch", t_hit - T_WIND + 0.01, SC, loop=False)
    GX0, DASH = 170, 110
    fist_x = GX0 + DASH + (im_p.width - ax_p)
    BALL_X = fist_x + BALL_R - 10
    far = mountains(1, (28, 22, 58, 255), 170, 1150, 320, W * 12)
    near = mountains(2, (14, 12, 30, 255), 120, 1290, 230, W * 24)
    ball = ball_sprite(BALL_R)
    fT, fS, fN = F("anton.woff2", 96), F("mont900.woff2", 30), F("anton.woff2", 92)
    rnd = random.Random(5)
    rocks = []
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s",
                             f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf",
                             "18", "-pix_fmt", "yuv420p", str(out.with_suffix(".video.mp4"))], stdin=subprocess.PIPE)
    for fi in range(int(dur * FPS)):
        t = fi / FPS
        tt = t if t < t_hit else max(t_hit, t - 0.18)
        m = dist_at(tt, t_hit)
        cam = m * 6.0
        img = sky(min(1.0, max(0.0, (tt - t_hit) / 3.0)))
        img.alpha_composite(far.crop((int(cam * .15) % (W * 10), 0, int(cam * .15) % (W * 10) + W, H)))
        img.alpha_composite(near.crop((int(cam * .45) % (W * 20), 0, int(cam * .45) % (W * 20) + W, H)))
        img = img.convert("RGB")
        d = ImageDraw.Draw(img, "RGBA")
        d.rectangle((0, GROUND, W, H), fill=(8, 8, 18))
        d.line((0, GROUND, W, GROUND), fill=(150, 230, 255), width=4)
        for gx in range(-(int(cam) % 160), W, 160):
            d.line((gx, GROUND + 18, gx + 60, GROUND + 18), fill=(80, 110, 160, 160), width=3)
        # perso
        if tt < T_SSJ:
            name, lt = "base_idle", tt
        elif tt < T_WIND:
            name, lt = "power", tt - T_SSJ
        else:
            name, lt = "punch", tt - T_WIND
        pim, (pax, pbase) = anim.frame(SD, name, lt, SC, loop=name != "punch")
        dash = DASH * min(1.0, max(0.0, (tt - T_WIND) / max(0.01, t_hit - T_WIND))) if tt >= T_WIND else 0
        gx = GX0 + dash - (cam if tt > t_hit else 0)
        power = 0.0
        if T_SSJ <= tt < t_hit + 0.3:
            power = min(1.0, (tt - T_SSJ) / 1.0) * (1 if tt < t_hit else max(0, 1 - (tt - t_hit) / 0.3))
            au = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ad = ImageDraw.Draw(au)
            fl = 0.85 + 0.15 * math.sin(t * 40)
            ad.ellipse((gx - 150 - 60 * power, GROUND - pim.height - 120 * power, gx + 150 + 60 * power, GROUND + 20),
                       fill=(255, 220, 60, int(140 * power * fl)))
            img.paste(au.filter(ImageFilter.GaussianBlur(40)), (0, 0), au.filter(ImageFilter.GaussianBlur(40)))
            if rnd.random() < 0.4 * power:
                rocks.append([gx + rnd.uniform(-200, 200), GROUND - 10, rnd.uniform(-30, 30), -rnd.uniform(80, 200), t,
                              rnd.choice([8760, 8761, 8762, 8764]), 2.0, 0])
            for _ in range(int(3 * power)):                     # éclairs jaunes de l'aura
                x0 = gx + rnd.uniform(-120, 120)
                y0 = GROUND - rnd.uniform(40, pim.height)
                d.line([(x0, y0), (x0 + rnd.uniform(-20, 20), y0 - 30), (x0 + rnd.uniform(-25, 25), y0 - 60)],
                       fill=(255, 250, 180, 220), width=3)
        img.paste(pim, (int(gx - pax), int(GROUND - pim.height - pbase)), pim)
        # boule
        rb = ball.rotate(-math.degrees(cam / BALL_R), resample=Image.BICUBIC)
        img.paste(rb, (int(BALL_X - rb.width / 2), int(GROUND - 30 - rb.height / 2)), rb)
        d = ImageDraw.Draw(img, "RGBA")
        # flash de la transformation
        if 0 <= tt - T_SSJ < 0.3:
            d.rectangle((0, 0, W, H), fill=(255, 245, 180, int(230 * (1 - (tt - T_SSJ) / 0.3))))
        e = t - t_hit
        cx, cy = fist_x, GROUND - im_p.height * 0.62
        if 0 <= e < 0.18:                                       # arrêt sur image en 2 tons
            g = img.convert("L").point(lambda v: 255 if v > 70 else 0)
            img = Image.merge("RGB", (g, g.point(lambda v: v * .85), g.point(lambda v: v * .35)))
            d = ImageDraw.Draw(img, "RGBA")
            if not any(r[7] for r in rocks):
                for _ in range(18):
                    rocks.append([cx + rnd.uniform(-40, 40), cy + rnd.uniform(-60, 60), rnd.uniform(-200, 600),
                                  -rnd.uniform(300, 900), t, rnd.choice([8760, 8761, 8762, 8764, 8765]), 1.4, 1])
        for a_no, t0, scl, ox, oy in ((6005, 0.0, 6, 60, 0), (6010, 0.05, 6, 40, GROUND - cy), (6015, 0.1, 6, 80, -30)):
            ee = e - t0
            if 0 <= ee < 0.9:
                eim = fx(a_no, ee, scl)
                if eim is not None:
                    img.paste(eim, (int(cx + ox - eim.width / 2), int(cy + oy - eim.height / 2)), eim)
        d = ImageDraw.Draw(img, "RGBA")
        if 0.18 <= e < 0.45:
            d.rectangle((0, 0, W, H), fill=(255, 255, 255, int(170 * (1 - (e - 0.18) / 0.27))))
        alive = []
        for rk in rocks:
            a = t - rk[4]
            if a < rk[6]:
                x, y = rk[0] + rk[2] * a, rk[1] + rk[3] * a + 900 * a * a
                if y < GROUND + 10:
                    rim = fx(rk[5], a, 4)
                    if rim is not None:
                        img.paste(rim, (int(x), int(y)), rim)
                    alive.append(rk)
        rocks[:] = alive
        if tt > t_hit and m < GOAL_M - 1:
            sp_ = (dist_at(tt + 0.05, t_hit) - m) * 30
            for _ in range(int(min(18, sp_ / 25))):
                y, x = rnd.uniform(560, GROUND - 20), rnd.uniform(0, W)
                d.line((x, y, x + min(400, sp_ * 1.5), y), fill=(255, 255, 255, 60), width=3)
        # titre + compteurs
        d.text((W / 2, 70), "CAN GOKU PUNCH", font=fT, fill="white", anchor="mt", stroke_width=4, stroke_fill=(20, 10, 40))
        d.text((W / 2, 172), "THE BALL 1 KM?", font=fT, fill=(255, 200, 60), anchor="mt", stroke_width=4, stroke_fill=(20, 10, 40))
        d.text((W * 0.3, 320), "PUNCHES", font=fS, fill=(200, 200, 230), anchor="mt")
        d.text((W * 0.7, 320), "DISTANCE", font=fS, fill=(200, 200, 230), anchor="mt")
        d.text((W * 0.3, 360), "1" if t >= t_hit else "0", font=fN, fill="white", anchor="mt")
        col = (90, 255, 160) if 1 <= m < GOAL_M - 0.5 else (255, 90, 120)
        d.text((W * 0.7, 360), f"{m:,.0f} m", font=fN, fill=col, anchor="mt")
        d.rounded_rectangle((140, 480, W - 140, 500), 10, fill=(50, 50, 80))
        d.rounded_rectangle((140, 480, 140 + (W - 280) * max(min(1.0, m / 1000), 0.012), 500), 10, fill=(255, 200, 60))
        d.text((W - 140, 512), "1 KM", font=fS, fill=(255, 200, 60), anchor="ra")
        if t > dur - 2.4:
            a = min(1.0, (t - (dur - 2.4)) / 0.25)
            d.text((W / 2, 650), "1 METER SHORT...", font=F("anton.woff2", int(112 * (0.8 + 0.2 * a))),
                   fill=(255, 90, 120), anchor="mm", stroke_width=5, stroke_fill=(20, 10, 40))
            rgba = img.convert("RGBA")
            render.draw_rich(rgba, (W / 2, 740), "Rematch? Comment 👇", F("mont900.woff2", 54), (255, 255, 255),
                             anchor="ma", stroke_width=3, stroke_fill=(0, 0, 0))
            img = rgba.convert("RGB")
        sh = 3 + 5 * power if T_SSJ <= tt < t_hit else 0
        if 0 <= tt - T_SSJ < 0.4:
            sh = 14
        if 0 <= e < 0.7:
            sh = 28 * (1 - e / 0.7)
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
    put(T_SSJ - 0.05, domain.sfx("transform", mode="anime", franchise=fr_), 0.8)
    put(T_WIND, domain.sfx("teleport", mode="anime", franchise=fr_), 0.5)
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
