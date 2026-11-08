"""Les persos Stick Nodes (leur VRAI corps) rejouent les mouvements de notre Goku découpé (08/11).
keypoints.py lit le squelette du Goku image par image → angles des 13 os → le modèle Stick Nodes du perso est posé
avec ces angles (stickanim / moveset.MODELS pour les rôles), bassin au même endroit, pieds au même niveau.
    frames, feet = stickify.load("saitama", "coup_de_poing_fente", height=500, flip=False)   # comme clips.load
"""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "punch"))
sys.path.insert(0, str(HERE))
import clips  # noqa: E402
import keypoints as K  # noqa: E402
import moveset  # noqa: E402
import sticknodes as sn  # noqa: E402

BONES = moveset.BONES


def _unwrap(seq):
    out, prev = [], None
    for v in seq:
        if v is None:
            out.append(None)
            continue
        if prev is not None:
            v = prev + ((v - prev + 180) % 360 - 180)
        out.append(v)
        prev = v
    return out


def _smooth(vals, k=1):
    """médiane glissante sur 2k+1 images (angles déroulés), trous comblés par la valeur voisine."""
    v = _unwrap(vals)
    n = len(v)
    filled = list(v)
    last = next((x for x in v if x is not None), 0.0)
    for i in range(n):
        if filled[i] is None:
            filled[i] = last
        last = filled[i]
    out = []
    for i in range(n):
        w = filled[max(0, i - k):i + k + 1]
        out.append(float(np.median(w)))
    return out


def poses(move, height=500.0):
    """→ liste de (pose, kp) par image du mouvement (kp = points du Goku, dans les coordonnées de l'image)."""
    frames, feet = clips.load(move, height, flip=False)
    r = 0.062 * height
    st, kps = {}, []
    for f in frames:
        kps.append(K.extract(np.array(f), r, st))
    raw = [K.to_pose(kp) for kp in kps]
    sm = {b: _smooth([p.get(b) for p in raw]) for b in BONES}
    out = [({b: sm[b][i] for b in BONES}, kps[i]) for i in range(len(kps))]
    return out, frames, feet


def render_model(model, pose, scale, facing):
    m = moveset.MODELS[model]
    fig = moveset._fig(model)
    roles = m["roles"]
    ab = {roles[b]: pose[b] for b in BONES if b in roles}
    flip = facing < 0
    if flip:                                          # le Goku regarde à gauche : même pose vue en miroir
        ab = {k: 180 - v for k, v in ab.items()}
    native_left = roles.get("_native_left", False)
    if native_left:
        ab = {k: 180 - v for k, v in ab.items()}
        flip = not flip
    if m.get("cape"):
        for node, ang in zip(m["cape"], moveset.cape_angles(pose, 0.0)):
            ab[node] = ang if not native_left else 180 - ang
    return sn.render(fig, scale=scale, absolute=ab, flip=flip)


_LEG = {}


def goku_leg(height):
    """longueur bassin → cheville du Goku debout (px), mesurée sur debout_regarde"""
    if "k" not in _LEG:
        ps, frames, _ = poses("debout_regarde", 500.0)
        vals = []
        for pose, kp in ps:
            if kp and kp.get("hip") and kp.get("an_f"):
                vals.append(math.dist(kp["hip"], kp["an_f"]))
        _LEG["k"] = float(np.median(vals)) / 500.0
    return _LEG["k"] * height


def model_leg(model):
    m = moveset.MODELS[model]
    fig = moveset._fig(model)
    lens = {}

    def walk(n):
        for c in n["children"]:
            lens[c["draw_order_index"]] = c["length"]
            walk(c)
    walk(fig["nodes"][0])
    return lens[m["roles"]["thigh_f"]] + lens[m["roles"]["shin_f"]]


def load(model, move, height=500.0, flip=False, pad=None):
    """images agrandies de `pad` px de chaque côté, perso posé sur le bassin du Goku, pieds au même niveau."""
    ps, frames, feet = poses(move, height)
    scale = goku_leg(height) / model_leg(model) * 1.04
    pad = int(0.5 * height) if pad is None else pad
    feet = [ft + pad for ft in feet]
    out = []
    facing0 = None
    for (pose, kp), f in zip(ps, frames):
        canvas = Image.new("RGBA", (f.width + 2 * pad, f.height + 2 * pad), (0, 0, 0, 0))
        if kp is None or kp.get("hip") is None:
            out.append(canvas)
            continue
        facing = kp["facing"] if facing0 is None else facing0
        facing0 = facing0 or kp["facing"]
        im, pos, org = render_model(model, pose, scale, facing)
        a = np.asarray(im)[..., 3]
        ys = np.nonzero(a.max(1) > 20)[0]
        low_m = ys.max() - org[1] if len(ys) else 0
        fa = np.asarray(f)[..., 3]
        fys = np.nonzero(fa.max(1) > 20)[0]
        low_g = fys.max() if len(fys) else f.height
        hx, hy = kp["hip"]
        x = hx + pad - org[0]
        y = low_g + pad - low_m - org[1]
        canvas.alpha_composite(im, (int(round(x)), int(round(y)))) if x >= 0 and y >= 0 else canvas.paste(im, (int(round(x)), int(round(y))), im)
        out.append(canvas)
    if flip:
        out = [o.transpose(Image.FLIP_LEFT_RIGHT) for o in out]
    return out, feet
