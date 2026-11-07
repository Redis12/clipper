"""Planche vidéo : Goku Pivot qui rejoue des mouvements de la base CMU (libre). python3 demo_cmu.py doc.json out.mp4"""
import json, subprocess, sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); sys.path.insert(0, str(Path(__file__).parents[1] / "punch"))
import bvh, pivot_render as pr
from PIL import Image, ImageDraw, ImageFont
D = "/tmp/cmu/data/"
CLIPS = [("Boxing", "014/14_01.bvh", 2, 8), ("Front kick", "135/135_04.bvh", 0, 5), ("Roundhouse kick", "135/135_07.bvh", 0, 4),
         ("Punch", "135/135_09.bvh", 0, 4), ("Side kick", "135/135_11.bvh", 0, 4), ("Jump kick", "090/90_05.bvh", 0, 4),
         ("Jump spin kick", "088/88_06.bvh", 0, 4), ("Spin kick", "087/87_01.bvh", 0, 5), ("Backflip", "087/87_03.bvh", 0, 4),
         ("Fall", "090/90_16.bvh", 0, 5)]
doc = json.load(open(sys.argv[1]))
g = pr.PivotActor(doc, 0, 0, pr.ROLES_PIVOT_GOKU, scale=2.2)
import hud
font = hud.font("luckiest-guy.woff2", 64)
W, H, GY, K = 1080, 1080, 960, 15.0
tmp = Path("/tmp/mocap/demo"); tmp.mkdir(parents=True, exist_ok=True)
n = 0
for name, f, a, b in CLIPS:
    F = bvh.load(D + f, a, b)
    x0 = F[0][1]
    xs = [x for _, x, _, _ in F]
    mid = (min(xs) + max(xs)) / 2
    for pose, x, lift, fc in F:
        g.flip = fc < 0
        c = Image.new("RGBA", (W, H), (205, 225, 245, 255))
        d = ImageDraw.Draw(c)
        d.rectangle((0, GY, W, H), fill=(120, 170, 90))
        d.text((40, 40), name.upper(), font=font, fill=(255, 255, 255), stroke_width=5, stroke_fill=(20, 20, 30))
        g.draw(c, pose, W / 2 + (x - mid) * K, 0, ground=GY, lift=lift * K, shadow_y=GY)
        c.convert("RGB").save(tmp / f"{n:05d}.png"); n += 1
subprocess.run(["ffmpeg", "-v", "error", "-y", "-r", "24", "-i", str(tmp / "%05d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "22", sys.argv[2]], check=True)
print(n)
