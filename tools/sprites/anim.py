"""Lecture des animations d'une planche découpée par slice.py (07/11).

anims.json (dans le dossier de la planche) : {"nom": [[numéro, durée_s], ...], ...}
frame(dossier, nom, t, scale, loop) -> (image RGBA agrandie net, (ancre_x, bas)) : l'ancre = centre des jambes au sol,
pour poser le perso au même endroit quelle que soit la largeur de l'image (bras tendu, effet…).
"""
import json
from functools import lru_cache
from pathlib import Path

from PIL import Image


@lru_cache(maxsize=None)
def _meta(d):
    d = Path(d)
    fr = {m["n"]: m for m in json.load(open(d / "frames.json"))["frames"]}
    an = json.load(open(d / "anims.json")) if (d / "anims.json").exists() else {}
    return fr, an


@lru_cache(maxsize=4096)
def image(d, n, scale):
    im = Image.open(Path(d) / "frames" / f"{n:03d}.png").convert("RGBA")
    return im.resize((im.width * scale, im.height * scale), Image.NEAREST)


def length(d, name):
    return sum(x[1] for x in _meta(str(d))[1][name])


def frame(d, name, t, scale=4, loop=True):
    fr, an = _meta(str(d))
    seq = an[name]
    tot = sum(x[1] for x in seq)
    t = t % tot if loop else min(t, tot - 1e-6)
    acc = 0.0
    for n, du in seq:
        if t < acc + du:
            break
        acc += du
    m = fr[n]
    return image(str(d), n, scale), (m["anchor_x"] * scale, m["base"] * scale)
