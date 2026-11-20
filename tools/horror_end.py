"""Fin « uncanny » (20/11, Joseph vs every anime) : image qui zoome de plus en plus, grain, scintillement, vignette,
lignes de glitch ; au coup du son (hit_at) : flash négatif + saut de zoom + secousse.
python3 tools/horror_end.py <image> <sortie.mp4> [durée=7.0] [hit_at=5.2]"""
import math
import random
import subprocess
import sys

import numpy as np
from PIL import Image, ImageOps

W, H, FPS = 1080, 1920, 30
src, out = sys.argv[1], sys.argv[2]
dur = float(sys.argv[3]) if len(sys.argv) > 3 else 7.0
hit = float(sys.argv[4]) if len(sys.argv) > 4 else 5.2
im = Image.open(src).convert("L")
sq = min(im.size)
im = im.crop(((im.width - sq) // 2, (im.height - sq) // 2, (im.width + sq) // 2, (im.height + sq) // 2))
big = im.resize((2400, 2400), Image.LANCZOS)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
vig = 1 - 0.75 * np.clip(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.42)) ** 2, 0, 1)
rnd = random.Random(3)
p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{W}x{H}",
                      "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt",
                      "yuv420p", out], stdin=subprocess.PIPE)
n = int(dur * FPS)
for f in range(n):
    t = f / FPS
    if t < hit:                                           # zoom lent qui accélère un peu
        z = 1.0 + 0.32 * (t / hit) ** 1.4
        sh = 2.0
    else:                                                 # le coup : saut de zoom, secousse qui décroît
        e = t - hit
        z = 1.32 + 0.38 * (1 - math.exp(-e * 9)) + 0.06 * e
        sh = 2 + 26 * math.exp(-e * 3.5)
    side = int(H * 0.82 * z)                              # l image couvre l écran (bords hors champ)
    s_ = big.resize((side, side), Image.BILINEAR)
    cx = side / 2 + rnd.uniform(-sh, sh)
    cy = side / 2 + rnd.uniform(-sh, sh) - side * 0.04 * (z - 1)
    frame = Image.new("L", (W, H), 0)
    frame.paste(s_, (int(W / 2 - cx), int(H / 2 - cy)))
    a = np.asarray(frame, np.float32)
    flick = 1 + rnd.uniform(-0.07, 0.07)
    if t >= hit:
        a = np.clip((a - 128) * 1.25 + 128, 0, 255)       # plus de contraste après le coup
    a = a * vig * flick + np.random.normal(0, 14, (H, W)).astype(np.float32)   # grain
    if rnd.random() < 0.18:                               # lignes de glitch horizontales
        for _ in range(rnd.randint(1, 3)):
            y0 = rnd.randint(0, H - 40)
            hh = rnd.randint(4, 30)
            a[y0:y0 + hh] = np.roll(a[y0:y0 + hh], rnd.randint(-60, 60), axis=1) + 25
    if hit <= t < hit + 2 / FPS:                          # 2 images en négatif
        a = 255 - a
    if t < 0.1:                                           # coupe sèche depuis l'écran de fin
        a = a * (t / 0.1)
    p.stdin.write(np.clip(a, 0, 255).astype(np.uint8).tobytes())
p.stdin.close()
p.wait()
print(out)
