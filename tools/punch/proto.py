"""Prototype « Punch the ball » (07/11) : un perso MUGEN frappe une énorme boule, inspiré de la vidéo « 100 pushes ».

python3 tools/punch/proto.py <sortie.mp4>   (depuis la racine du dépôt)
Luffy : petits coups (la boule ne bouge pas) puis Gear 3 Elephant Gun → la boule part, la caméra suit, compteur.
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
D = ROOT / "library/One Piece/one-piece-mugen/One Piece MUGEN/chars/G6_Luffy"
SC = 3                                   # agrandissement des sprites (net)
GROUND = 1340                            # y du sol sous le perso
BALL_R = 300


def sky(t):
    y = np.linspace(0, 1, H)[:, None, None]
    top, mid, bot = np.array([14, 16, 40.]), np.array([70, 40, 110.]), np.array([255, 120, 90.])
    warm = min(1.0, t)                   # le ciel se réchauffe quand la boule part
    c_mid = mid * (1 - warm) + np.array([255, 110, 80.]) * warm
    a = np.where(y < 0.55, top * (1 - y / 0.55) + c_mid * (y / 0.55), c_mid)
    return Image.fromarray(a.repeat(W, 1).clip(0, 255).astype(np.uint8)).convert("RGBA")


def mountains(seed, col, amp, base, period):
    r = random.Random(seed)
    pts = [(0, H)]
    x = -200
    while x < W * 6:
        pts.append((x, base - r.uniform(0.3, 1) * amp))
        x += r.uniform(period * 0.5, period)
    pts.append((W * 6, H))
    im = Image.new("RGBA", (W * 6, H), (0, 0, 0, 0))
    ImageDraw.Draw(im).polygon(pts, fill=col)
    return im


def ball_sprite(r):
    s = int(r * 2 + 60)
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = s / 2
    for k in range(int(r), 0, -2):
        f = k / r
        col = (int(20 + 30 * (1 - f)), int(28 + 40 * (1 - f)), int(60 + 70 * (1 - f)), 255)
        d.ellipse((c - k - 8 * (1 - f), c - k - 8 * (1 - f), c + k - 8 * (1 - f), c + k - 8 * (1 - f)), fill=col)
    d.ellipse((c - r, c - r, c + r, c + r), outline=(120, 230, 255, 255), width=5)
    d.arc((c - r * 0.8, c - r * 0.8, c + r * 0.8, c + r * 0.8), 200, 320, fill=(255, 255, 255, 50), width=8)
    d.ellipse((c + r * 0.35 - 9, c - r * 0.1 - 9, c + r * 0.35 + 9, c - r * 0.1 + 9), fill=(255, 170, 60, 255))
    glow = im.filter(ImageFilter.GaussianBlur(14))
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    out.alpha_composite(glow)
    out.alpha_composite(im)
    return out


def main():
    out = Path(sys.argv[1])
    spr = mugen.read_sff(D / "Luffy.sff", D / "1.act")
    air = mugen.read_air(D / "Luffy.air")

    def frames(a):
        act = air[a]
        return act.frames if hasattr(act, "frames") else act

    # timeline : (action, répétitions)
    seq = [(0, 1), (200, 1), (300, 1), (250, 1), (200, 1), (300, 1), (230, 1), (0, 3)]
    tl = []                               # (t, sprite, dx, dy, action, index)
    t = 0.0
    for a, rep in seq:
        for _ in range(rep):
            fr = frames(a)
            for i, f in enumerate(fr):
                dur = (f.ticks if f.ticks > 0 else 20) / 60
                tl.append((t, f, a, i, len(fr)))
                t += dur
    T_ANIM = t
    # impacts : dernière image « bras tendu » de chaque coup
    hits = [x[0] for x in tl if x[2] in (200, 300, 250) and x[3] == 2]
    big = next(x[0] for x in tl if x[2] == 230 and x[3] == 4)
    dur = big + 6.5
    bg_far = mountains(1, (30, 24, 60, 255), 160, 1150, 300)
    bg_near = mountains(2, (16, 14, 34, 255), 110, 1290, 220)
    ball = ball_sprite(BALL_R)
    fT, fS, fN = F("anton.woff2", 92), F("mont900.woff2", 30), F("anton.woff2", 88)
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s",
                             f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf",
                             "18", "-pix_fmt", "yuv420p", str(out)], stdin=subprocess.PIPE)
    ball_x0 = 700
    for fi in range(int(dur * FPS)):
        t = fi / FPS
        # distance de la boule : 0 avant le grand coup, puis décélération
        if t < big:
            dist, cam = 0.0, 0.0
        else:
            e = t - big
            dist = 2600 * (1 - math.exp(-e * 0.55))       # en pixels de monde (×0.1 = mètres affichés)
            cam = dist
        shake = 0
        for h in hits:
            if 0 <= t - h < 0.15:
                shake = 6
        if 0 <= t - big < 0.4:
            shake = 22 * (1 - (t - big) / 0.4)
        img = sky(max(0.0, (t - big) / 2.5) if t > big else 0.0)
        img.alpha_composite(bg_far.crop((int(cam * 0.2), 0, int(cam * 0.2) + W, H)))
        img.alpha_composite(bg_near.crop((int(cam * 0.5), 0, int(cam * 0.5) + W, H)))
        d = ImageDraw.Draw(img, "RGBA")
        d.rectangle((0, GROUND, W, H), fill=(10, 10, 20, 255))
        d.line((0, GROUND, W, GROUND), fill=(150, 230, 255, 255), width=4)
        # boule (roule)
        bx = ball_x0 + dist - cam                      # la caméra suit la boule, le décor défile
        rb = ball.rotate(-math.degrees(dist / BALL_R), resample=Image.BICUBIC)
        img.alpha_composite(rb, (int(bx - rb.width / 2), int(GROUND - BALL_R - rb.height / 2 + BALL_R - 30)))
        # perso
        if t < T_ANIM:
            cur = max([x for x in tl if x[0] <= t], key=lambda x: x[0])
            f = cur[1]
            s = spr.get((f.group, f.number))
            if s:
                im = s.image
                im = im.resize((im.width * SC, im.height * SC), Image.NEAREST)
                ax, ay = s.axis
                px = 210 + (f.dx - ax) * SC - cam
                py = GROUND + (f.dy - ay) * SC
                img.alpha_composite(im, (int(px), int(py)))
        # impacts
        for h in hits:
            a = (t - h) / 0.25
            if 0 <= a < 1:
                d.ellipse((ball_x0 - BALL_R - 30 * a - 40, GROUND - 250 - 60 * a, ball_x0 - BALL_R + 40 + 30 * a, GROUND - 150 + 60 * a),
                          outline=(255, 255, 255, int(220 * (1 - a))), width=6)
        if 0 <= t - big < 0.12:
            d.rectangle((0, 0, W, H), fill=(255, 255, 255, int(230 * (1 - (t - big) / 0.12))))
        # HUD
        n_p = sum(1 for h in hits if h <= t) + (1 if t >= big else 0)
        meters = dist * 0.1
        d.text((W / 2, 80), "CAN LUFFY PUNCH", font=fT, fill="white", anchor="mt", stroke_width=4, stroke_fill=(20, 10, 40))
        d.text((W / 2, 180), "THE BALL 1 KM?", font=fT, fill=(255, 200, 60), anchor="mt", stroke_width=4, stroke_fill=(20, 10, 40))
        d.text((W * 0.3, 330), "PUNCHES", font=fS, fill=(200, 200, 230), anchor="mt")
        d.text((W * 0.7, 330), "DISTANCE", font=fS, fill=(200, 200, 230), anchor="mt")
        d.text((W * 0.3, 370), str(n_p), font=fN, fill="white", anchor="mt")
        dtxt = f"{meters:.0f} m" if meters >= 1 else "0 cm"
        d.text((W * 0.7, 370), dtxt, font=fN, fill=(255, 90, 120) if meters < 1 else (90, 255, 160), anchor="mt")
        if shake:
            dx, dy = random.randint(-int(shake), int(shake)), random.randint(-int(shake), int(shake))
            sh = Image.new("RGBA", (W, H), (0, 0, 0, 255))
            sh.alpha_composite(img, (dx, dy))
            img = sh
        proc.stdin.write(img.convert("RGB").tobytes())
    proc.stdin.close()
    proc.wait()
    print("OUT", out, round(dur, 1))


if __name__ == "__main__":
    main()
