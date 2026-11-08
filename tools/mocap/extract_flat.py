"""Découpe d'un perso dans une animation 2D à décor en APLATS (ex. « All Saitama Skills in Stick Nodes », 08/11).
Pas de décor vide fourni : pour chaque image, le décor est reconstruit (« clean plate » par image) = couleurs
dominantes de l'image (ciel, montagnes, sol), le perso et sa marge sont bouchés par le pixel de décor le plus proche,
puis extract.cut fait le matting à fond connu (bords nets). Zone = rectangle où le perso est seul (pas l'adversaire,
pas les textes).
python3 extract_flat.py video.mp4 debut fin nom x0 y0 x1 y1 [hauteur_debout_px]
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import extract  # noqa: E402


def plate(rgb, frac=0.02, tol=34):
    q = (rgb // 8).reshape(-1, 3)
    u, cnt = np.unique(q, axis=0, return_counts=True)
    bg = u[cnt > frac * len(q)] * 8 + 4
    d = np.min(np.stack([np.abs(rgb.astype(int) - c).sum(2) for c in bg]), axis=0) if len(bg) else np.full(rgb.shape[:2], 999)
    rough = d > tol
    rough = ndi.binary_opening(rough, iterations=3)
    lab, n = ndi.label(rough)
    if n:
        sz = ndi.sum(rough, lab, range(1, n + 1))
        rough &= np.isin(lab, [i + 1 for i in range(n) if sz[i] >= 150])
    M = ndi.binary_dilation(rough, iterations=6)
    _, (iy, ix) = ndi.distance_transform_edt(M, return_indices=True)
    return rgb[iy, ix], rough


def run(video, t0, t1, name, box, stand_h=None):
    x0, y0, x1, y1 = box
    root = HERE.parents[1] / "library" / "_mocap" / "clips" / name
    root.mkdir(parents=True, exist_ok=True)
    for f in root.glob("*.png"):
        f.unlink()
    ims, boxes = [], []
    W0 = None
    for f in extract.frames(video, t0, t1):
        rgb = np.asarray(Image.open(f).convert("RGB"))
        W0 = rgb.shape[1]
        plf, roughf = plate(rgb)                                      # palette du décor sur l'image entière
        sub = rgb[y0:y1, x0:x1]
        pl, rough = plf[y0:y1, x0:x1], roughf[y0:y1, x0:x1]
        rgba, a = extract.cut(sub, False, pl.astype(np.int16))
        keep = ndi.binary_dilation(rough, iterations=3)
        al = rgba[..., 3].astype(float) * keep
        lab, n = ndi.label(al > 128)
        if n > 1:                                                     # le perso = le plus gros morceau (+ cape reliée)
            sz = ndi.sum(al > 128, lab, range(1, n + 1))
            big = ndi.binary_dilation(np.isin(lab, [i + 1 for i in range(n) if sz[i] >= 0.03 * sz.max()]), iterations=3)
            al *= big
        rgba[..., 3] = al.astype(np.uint8)
        a = al > 128
        if a.sum() < 400:
            continue
        full = np.zeros((rgb.shape[0], rgb.shape[1], 4), np.uint8)
        full[y0:y1, x0:x1] = rgba
        ys, xs = np.nonzero(full[..., 3] > 128)
        boxes.append((xs.min(), ys.min(), xs.max(), ys.max()))
        ims.append(full)
    b = np.array(boxes)
    bx = (int(b[:, 0].min()) - 2, int(b[:, 1].min()) - 2, int(b[:, 2].max()) + 3, int(b[:, 3].max()) + 3)
    feet = [int(bb[3]) - bx[1] for bb in boxes]
    gif = []
    for i, rgba in enumerate(ims):
        im = Image.fromarray(rgba).crop(bx)
        im.save(root / f"{i + 1:04d}.png")
        g = Image.new("RGB", im.size, (200, 225, 240))
        g.paste(im, (0, 0), im)
        gif.append(g)
    gif[0].save(root / "apercu.gif", save_all=True, append_images=gif[1:], duration=33, loop=0)
    json.dump({"goku_h": stand_h or 0, "source": Path(video).name, "t": [t0, t1], "fps": 30, "n": len(ims),
               "size": list(gif[0].size), "feet_y": feet, "x_in_video": bx[0]}, open(root / "info.json", "w"))
    return name, len(ims), gif[0].size


if __name__ == "__main__":
    a = sys.argv
    print(run(a[1], float(a[2]), float(a[3]), a[4], tuple(int(v) for v in a[5:9]), float(a[9]) if len(a) > 9 else None))
