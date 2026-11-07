"""Planche vidéo : Goku Pivot qui rejoue les animations Mixamo de library/_mocap/mixamo. python3 demo_mixamo.py doc.json dossier_dae out.mp4"""
import json, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); sys.path.insert(0, str(Path(__file__).parents[1] / "punch"))
import dae, hud, pivot_render as pr
from PIL import Image, ImageDraw
NAMES = [("mx_idle", "Fighting idle"), ("mx_jab", "Jab"), ("mx_cross", "Cross"), ("mx_combo4", "4 punch combo"),
         ("mx_combo8", "8 punch combo"), ("mx_uppercut", "Uppercut"), ("mx_sidekick", "Side kick"),
         ("mx_roundhouse", "Roundhouse kick"), ("mx_flipkick", "Front flip kick"), ("mx_hit", "Hit reaction"),
         ("mx_knockdown", "Knocked down"), ("mx_getup", "Getting up"), ("mx_jump", "Jump"), ("mx_dodgeback", "Dodge back")]
doc = json.load(open(sys.argv[1]))
g = pr.PivotActor(doc, 0, 0, pr.ROLES_PIVOT_GOKU, scale=2.0)
W, H, GY, LEG = 1080, 1080, 980, 330.0           # LEG = longueur de jambe de Goku à cette échelle (px)
font = hud.font("luckiest-guy.woff2", 64)
tmp = Path("/tmp/mixamo/demo"); tmp.mkdir(parents=True, exist_ok=True)
for f in tmp.glob("*.png"):
    f.unlink()
n = 0
for key, label in NAMES:
    F = dae.load(f"{sys.argv[2]}/{key}/{key}.dae")
    if key == "mx_idle":
        F = F[:48]
    xs = [x for _, x, _, _ in F]
    mid = (min(xs) + max(xs)) / 2
    kx = min(1.0, 700 / max(1e-6, (max(xs) - min(xs)) * LEG))      # gros déplacement : on le resserre pour la planche
    for pose, x, lift, fc in F + F[-1:] * 6:
        g.flip = fc < 0
        c = Image.new("RGBA", (W, H), (205, 225, 245, 255))
        d = ImageDraw.Draw(c)
        d.rectangle((0, GY, W, H), fill=(120, 170, 90))
        d.text((40, 40), label.upper(), font=font, fill=(255, 255, 255), stroke_width=5, stroke_fill=(20, 20, 30))
        g.draw(c, pose, W / 2 + (x - mid) * LEG * kx, 0, ground=GY + 14, lift=lift * LEG, shadow_y=GY + 10)
        c.convert("RGB").save(tmp / f"{n:05d}.png"); n += 1
subprocess.run(["ffmpeg", "-v", "error", "-y", "-r", "30", "-i", str(tmp / "%05d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "22", sys.argv[3]], check=True)
print(n)
