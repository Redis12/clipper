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

import stickanim as sa  # noqa: E402
LIB = Path(__file__).resolve().parents[2] / "library/_sticknodes/Dragon Ball"
goku_fig = sn.load(str(LIB / "Goku (Turtle suit Gi).json"))
veg_fig = sn.load(str(LIB / "Vegeta (Armour).json"))
sc = Scene(scale=1.35)
g = sc.actor("Goku", goku_fig, x=180, facing=1, color=(255, 140, 30), roles=sa.ROLES_GOKU_GI)
v = sc.actor("Vegeta", veg_fig, x=560, facing=-1, color=(70, 110, 255), roles=sa.ROLES_VEGETA)
sc.face_off(g, v)
sc.wait(0.35)
sc.dash(g, v)
sc.flurry(g, v, hits=9)
sc.heavy(g, v)
sc.getup(v)
sc.taunt(v, 0.45)
sc.charge(v, g)
sc.dodge(g, v, "jump_over")
sc.launch(g, v)
sc.air_smash(g, v)
sc.wait(0.35)
sc.getup(v)
sc.charge(v, g)
sc.dodge(g, v, "vanish")
sc.finisher_kick(g, v, knock=420)
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
print(sc.render(sys.argv[2], bg, title=("GOKU", "VS VEGETA")), round(sc.real(sc.t), 1))
