"""Démo : les mêmes mouvements découpés du Goku, joués par plusieurs persos (skins.py).
python3 skins_demo.py sortie.mp4 goku,naruto,vegeta,luffy,ichigo,saitama"""
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw

import clips
import skins

MOVES = ["arrivee_teleportation", "debout_regarde", "mise_en_garde", "garde_cavalier", "coup_de_poing_fente",
         "retour_du_coup", "appel_saut", "salto", "reception_garde"]
dst, chars = sys.argv[1], sys.argv[2].split(",")
W, H = 1080, 1920
cols, rows = 2, (len(chars) + 1) // 2
CH = 400
cw, rh = W / cols, (H - 120) / rows
seq = {c: [] for c in chars}
for mv in MOVES:
    for c in chars:
        fr, ft = (clips.load(mv, CH) if c == "goku" else skins.load(c, mv, CH))
        seq[c] += [(f, ft[0]) for f in fr]
n = len(seq[chars[0]])
p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", "30",
                      "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", dst], stdin=subprocess.PIPE)
for i in range(n):
    c = Image.new("RGBA", (W, H), (150, 190, 230, 255))
    d = ImageDraw.Draw(c)
    for j, ch in enumerate(chars):
        x0, y0 = (j % cols) * cw, 120 + (j // cols) * rh
        g = y0 + rh - 40
        d.rectangle((x0 + 10, g, x0 + cw - 10, g + 8), fill=(90, 130, 80, 255))
        d.text((x0 + 20, y0 + 10), ch.upper(), fill=(0, 0, 0, 255))
        im, ft = seq[ch][i]
        c.alpha_composite(im, (int(x0 + cw / 2 - im.width / 2), int(g - ft))) if g - ft >= 0 else c.paste(im, (int(x0 + cw / 2 - im.width / 2), int(g - ft)), im)
    p.stdin.write(np.asarray(c.convert("RGB")).tobytes())
p.stdin.close()
p.wait()
