"""Mouvements « n'importe quel perso » (08/11, demandé : « une animation où on met n'importe quel modèle facilement,
avec les mêmes sets de moves »).

- Les MOUVEMENTS : library/_mocap/sequences/<nom>.json = poses recopiées image par image du Goku de la vidéo de
  référence (13 os en angles absolus : hip, spine, chest, neck, head, uarm/farm avant/arrière, thigh/shin
  avant/arrière ; voir sequences.py).
- Les MODÈLES : un fichier Stick Nodes (library/_sticknodes/…) + sa table de RÔLES (quel nœud est la cuisse avant…).
  Ajouter un perso = ajouter une entrée dans MODELS (+ la liste des nœuds de cape / cheveux longs si besoin).
- frames(modèle, mouvement, hauteur, flip) → images RGBA + bas des pieds, même interface que clips.load : on peut
  remplacer le Goku découpé par n'importe quel modèle dans les vidéos (How Far, 1 Punch…).
"""
import json
import math
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE.parent / "punch"))
import stickanim as sa  # noqa: E402
import sticknodes as sn  # noqa: E402

SEQ = ROOT / "library" / "_mocap" / "sequences"
SN = ROOT / "library" / "_sticknodes"
BONES = ["hip", "spine", "chest", "neck", "head", "uarm_f", "farm_f", "uarm_b", "farm_b",
         "thigh_f", "shin_f", "thigh_b", "shin_b"]

MODELS = {
    "saitama": {"file": SN / "Saitama" / "Saitama-OPM.json",
                "roles": {"hip": 16, "spine": 18, "chest": 26, "neck": 24, "head": 25, "uarm_f": 28, "farm_f": 29,
                          "uarm_b": 5, "farm_b": 6, "thigh_f": 11, "shin_f": 12, "thigh_b": 10, "shin_b": 1,
                          "_native_left": False},
                "cape": [45, 27, 44, 43, 42, 37, 38, 39]},
    "goku_ssj": {"file": SN / "Goku SSJ1.json", "roles": sa.ROLES_GOKU},
    "goku": {"file": SN / "Dragon Ball" / "Goku (Turtle suit Gi).json", "roles": sa.ROLES_GOKU_GI},
    "vegeta": {"file": SN / "Dragon Ball" / "Vegeta (Armour Calssic).json", "roles": sa.ROLES_VEGETA},
}
_FIG = {}


def names():
    return sorted(p.stem for p in SEQ.glob("*.json"))


def _fig(model):
    m = MODELS[model]
    if model not in _FIG:
        _FIG[model] = sn.load(m["file"])
    return _FIG[model]


def standing_height(model, scale=1.0):
    a = sa.Actor(_fig(model), MODELS[model]["roles"], scale)
    im, *_ = a.render(sa.P["idle"])
    al = im.getchannel("A").point(lambda v: 255 if v > 20 else 0)
    box = al.getbbox()
    return box[3] - box[1]


def pose_frames(move):
    """poses du mouvement à 30 i/s (une entrée par image de la référence) + déplacement dx/dy en px de la référence"""
    seq = json.load(open(SEQ / f"{move}.json"))
    return seq["frames"], seq.get("fps", 30)


def cape_angles(pose, t, speed=0.0, n=8):
    """cape qui pend derrière (le perso regarde à droite dans les angles des rôles) : vers le bas, un peu en arrière,
    ondule, plus soulevée quand il bouge vite."""
    lift = min(55.0, speed * 0.35)
    out = []
    for j in range(n):
        wave = 6 * math.sin(t * 7.5 - j * 0.9) * (0.4 + j / n)
        out.append(262 - 10 - lift * (0.5 + j / n) + wave)
    return out


def frames(model, move, height=500.0, flip=False, t0=0.0):
    """→ (images RGBA, pieds) : chaque image = le modèle dans la pose, à l'échelle où il fait `height` px debout."""
    m = MODELS[model]
    scale = height / standing_height(model, 1.0)
    fr, fps = pose_frames(move)
    out, feet = [], []
    prev = None
    for i, f in enumerate(fr):
        pose = {k: f[k] for k in BONES}
        fl = bool(f.get("flip")) ^ flip
        act = sa.Actor(_fig(model), m["roles"], scale, flip=fl)
        extra = {}
        if m.get("cape"):
            sp = 0.0
            if prev is not None:
                sp = math.hypot(f["dx"] - prev["dx"], f["dy"] - prev["dy"]) * fps
            for node, ang in zip(m["cape"], cape_angles(pose, t0 + i / fps, sp)):
                extra[node] = ang
        prev = f
        ab = sa.to_abs(pose, m["roles"])
        ab.update(extra)
        if act.native_left:
            ab = {k: 180 - v for k, v in ab.items()}
            fl = not fl
        im, pos, org = sn.render(act.fig, scale=scale, absolute=ab, flip=fl)
        a = im.getchannel("A")
        bottom = max(y for y in range(im.height) if a.crop((0, y, im.width, y + 1)).getbbox()) if a.getbbox() else 0
        out.append((im, org, f["dx"], f["dy"]))
        feet.append(bottom)
    return out, feet


if __name__ == "__main__":
    # démo : python3 moveset.py saitama sortie.mp4 mouvement1 mouvement2 …
    import subprocess
    import numpy as np
    models, dst, moves = sys.argv[1].split(","), sys.argv[2], sys.argv[3:]
    W, H, G, HT = 1080, 1080, 900, 430
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", "30",
           "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", dst]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    from PIL import ImageDraw
    for mv in moves:
        per = [frames(m, mv, HT) for m in models]
        n = len(per[0][0])
        for i in range(n):
            c = Image.new("RGBA", (W, H), (150, 190, 230, 255))
            d = ImageDraw.Draw(c)
            d.rectangle((0, G, W, H), fill=(110, 160, 90, 255))
            d.text((20, 20), mv, fill=(0, 0, 0, 255))
            for j, (fs, feet) in enumerate(per):
                im, org, dx, dy = fs[i]
                x = W * (j + 0.5) / len(models) + dx * HT / 250.0 * 0.25 - org[0]
                c.alpha_composite(im, (int(x), int(G - feet[i])))
            p.stdin.write(np.asarray(c.convert("RGB")).tobytes())
    p.stdin.close()
    p.wait()
