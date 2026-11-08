"""Répare les images où un pied sort du cadre de la vidéo d'origine (salto : la botte passe au-dessus de l'image) :
on reprend la botte entière d'une image du même mouvement (modèle), on la tourne / décale pour qu'elle recouvre au
mieux le morceau de botte encore visible au bord, et on la colle (seulement là où il n'y a rien). L'image est
agrandie vers le haut si besoin (info.json : feet_y mis à jour).
python3 patch_cut.py <dossier_clip> <image_modèle> <x0,y0,x1,y1 de la botte du modèle> <images à réparer>
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

BOOT = np.array([(3, 33, 58), (1, 27, 58), (6, 43, 58), (197, 40, 35), (219, 40, 40), (226, 222, 120), (240, 230, 130)],
                np.int16)


def bootmask(rgba):
    c = rgba[..., :3].astype(np.int16)
    d = np.abs(c[:, :, None, :] - BOOT[None, None]).sum(3).min(2)
    navy = (c[..., 2] > c[..., 0] + 15) & (c.sum(2) < 200)
    return ((d < 70) | navy) & (rgba[..., 3] > 128)


def main():
    d = Path(sys.argv[1])
    model = np.asarray(Image.open(d / f"{int(sys.argv[2]):04d}.png").convert("RGBA"))
    x0, y0, x1, y1 = map(int, sys.argv[3].split(","))
    sub = model[y0:y1, x0:x1].copy()
    m = bootmask(sub)
    lab, n = ndi.label(ndi.binary_dilation(m, iterations=2))
    big = 1 + int(np.argmax(ndi.sum(m, lab, range(1, n + 1))))
    keep = (lab == big) & (sub[..., 3] > 0)
    sub[~keep] = 0
    T = Image.fromarray(sub)
    info = json.load(open(d / "info.json"))
    PAD = 220
    todo = [int(x) for x in sys.argv[4].split(",")]
    files = sorted(d.glob("0*.png"))
    for f in files:                                           # tout le mouvement agrandi vers le haut (même cadre)
        im = Image.open(f).convert("RGBA")
        can = Image.new("RGBA", (im.width, im.height + PAD), (0, 0, 0, 0))
        can.alpha_composite(im, (0, PAD))
        can.save(f)
    info["feet_y"] = [y + PAD for y in info["feet_y"]]
    info["size"] = [info["size"][0], info["size"][1] + PAD]
    for k in todo:
        f = d / f"{k:04d}.png"
        a = np.asarray(Image.open(f).convert("RGBA"))
        bm = bootmask(a)
        top = PAD + 2
        E = bm.copy()
        E[top + 160:] = False                                  # morceau visible près du bord coupé
        el, en = ndi.label(E)
        edge_ids = set(np.unique(el[top:top + 3][E[top:top + 3]]).tolist()) - {0}
        E = np.isin(el, list(edge_ids))
        body = (a[..., 3] > 128) & ~bm
        ys, xs = np.nonzero(E)
        best = None
        for ang in range(0, 360, 6):
            R = T.rotate(ang, expand=True, resample=Image.BICUBIC)
            ra = np.asarray(R)[..., 3] > 128
            h, w = ra.shape
            for ty in range(int(ys.min()) - h + 10, int(ys.max()) - 5, 4):
                for tx in range(int(xs.min()) - w + 10, int(xs.max()) - 5, 4):
                    if ty < 0 or tx < 0 or ty + h > a.shape[0] or tx + w > a.shape[1]:
                        continue
                    win_e = E[ty:ty + h, tx:tx + w]
                    win_b = body[ty:ty + h, tx:tx + w]
                    ov = (ra & win_e).sum()
                    sc = ov / max(1, E.sum()) - 0.8 * (ra & win_b).sum() / max(1, ra.sum()) \
                        - 0.3 * (ra & ~win_e & (np.arange(ty, ty + h)[:, None] >= top)).sum() / max(1, ra.sum())
                    if best is None or sc > best[0]:
                        best = (sc, ang, tx, ty)
        sc, ang, tx, ty = best
        R = T.rotate(ang, expand=True, resample=Image.BICUBIC)
        im = Image.open(f).convert("RGBA")
        under = Image.new("RGBA", im.size, (0, 0, 0, 0))
        under.alpha_composite(R, (tx, ty))
        under.alpha_composite(im)                               # le perso d'origine reste devant
        under.save(f)
        print(k, round(sc, 3), ang, tx, ty, flush=True)
    json.dump(info, open(d / "info.json", "w"))


if __name__ == "__main__":
    main()
