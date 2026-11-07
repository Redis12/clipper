"""Premier combat écrit avec le producteur (07/11) : rafale de coups, gros coup, il se relève, fonce, esquive,
uppercut, smash aérien, il se relève encore, fonce, Goku se téléporte dans son dos, coup de pied final.
python3 tools/punch/fight_demo.py "library/_sticknodes/Goku SSJ1.json" <sortie.mp4>
"""
import sys
from pathlib import Path

from PIL import ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sticknodes as sn  # noqa: E402
from director import Scene  # noqa: E402
from demo_moves import gray_gi  # noqa: E402
from mugen_punch import GROUND, H, W, mountains  # noqa: E402
from one_punch_line import desert_sky  # noqa: E402

fig = sn.load(sys.argv[1])
sc = Scene()
g = sc.actor("Goku", fig, x=170, facing=1, hair=(22, 22, 28), color=(245, 110, 30))
v = sc.actor("Rival", fig, x=540, facing=-1, hair=(30, 30, 30), color=(150, 70, 190), recolor=gray_gi)
sc.wait(0.7)
sc.dash(g, v)
sc.flurry(g, v, hits=9)
sc.heavy(g, v, knock=300)
sc.wait(0.3)
sc.getup(v)
sc.taunt(v, 0.4)
sc.charge(v, g)
sc.dodge(g, v, "duck")
sc.launch(g, v)
sc.air_smash(g, v)
sc.wait(0.4)
sc.getup(v)
sc.charge(v, g)
sc.dodge(g, v, "vanish")
sc.finisher_kick(g, v)
sc.wait(0.8)

far = mountains(1, (214, 150, 110, 255), 260, 1080, 420, W * 2)
near = mountains(2, (176, 108, 72, 255), 150, 1190, 260, W * 2)
bg = desert_sky().convert("RGBA")
bg.alpha_composite(far.crop((0, 0, W, H)))
bg.alpha_composite(near.crop((0, 0, W, H)))
bd = ImageDraw.Draw(bg)
bd.rectangle((0, 1180, W, H), fill=(222, 178, 120))
for k in range(9):
    bd.ellipse((k * 130 + 20, GROUND + 140 + (k % 3) * 60, k * 130 + 70, GROUND + 165 + (k % 3) * 60), fill=(196, 140, 96))
print(sc.render(sys.argv[2], bg, title=("GOKU", "VS HIS RIVAL")), round(sc.real(sc.t), 1))
