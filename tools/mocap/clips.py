"""Lecture des mouvements découpés dans la vidéo de référence (library/_mocap/clips/<nom>/, voir extract.py).
    frames, feet = clips.load("coup_de_poing_fente", height=700)   # images RGBA mises à l'échelle + bas des pieds
    clips.paste(canvas, frames[i], x_centre, y_sol, feet[i])       # pose l'image, pieds sur le sol
Agrandissement LANCZOS puis contours nets (la source fait 640×360 : Goku ≈ 250 px de haut).
"""
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2] / "library" / "_mocap" / "clips"
GOKU_H = 250.0                                   # hauteur de Goku debout dans la vidéo source (px)


def names():
    return sorted(p.name for p in ROOT.iterdir() if p.is_dir() and (p / "info.json").exists())


def load(name, height=700.0, flip=False):
    """height = taille voulue de Goku debout (pas de l'image) : tous les mouvements gardent la même échelle."""
    d = ROOT / name
    info = json.load(open(d / "info.json"))
    k = height / GOKU_H
    out = []
    for f in sorted(d.glob("0*.png")):
        im = Image.open(f).convert("RGBA")
        im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
        a = im.getchannel("A").point(lambda v: 255 if v > 110 else 0)      # bord net (pas de halo)
        im.putalpha(a)
        if flip:
            im = im.transpose(Image.FLIP_LEFT_RIGHT)
        out.append(im)
    feet = [y * k for y in info["feet_y"]]
    return out, feet


def paste(canvas, im, x, ground, feet_y):
    """centre horizontal de l'image en x, bas des pieds sur la ligne ground."""
    canvas.alpha_composite(im, (round(x - im.width / 2), round(ground - feet_y)))
