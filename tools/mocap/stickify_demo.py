"""Démo côte à côte : Goku découpé | modèles Stick Nodes qui rejouent ses mouvements (stickify.py).
python3 stickify_demo.py sortie.mp4 saitama,goku mouvement1 mouvement2 …"""
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw

import clips
import stickify

dst, models, moves = sys.argv[1], sys.argv[2].split(","), sys.argv[3:]
cols = ["clip"] + models
W, H = 1080, 1080
HT = 300
G = 860
cw = W / len(cols)
seqs = {c: [] for c in cols}
for mv in moves:
    fr, ft = clips.load(mv, HT)
    seqs["clip"] += [(f, ft[0]) for f in fr]
    for m in models:
        f2, ft2 = stickify.load(m, mv, HT)
        seqs[m] += [(f, ft2[0]) for f in f2]
n = len(seqs["clip"])
p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", "30",
                      "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", dst], stdin=subprocess.PIPE)
for i in range(n):
    c = Image.new("RGBA", (W, H), (150, 190, 230, 255))
    d = ImageDraw.Draw(c)
    d.rectangle((0, G, W, H), fill=(110, 150, 90, 255))
    for j, col in enumerate(cols):
        im, ft = seqs[col][i]
        x = int(cw * (j + 0.5) - im.width / 2)
        y = int(G - ft)
        c.paste(im, (x, y), im)
        d.text((cw * j + 10, 10), col.upper(), fill=(0, 0, 0, 255))
    p.stdin.write(np.asarray(c.convert("RGB")).tobytes())
p.stdin.close()
p.wait()
