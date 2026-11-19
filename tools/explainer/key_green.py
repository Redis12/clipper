"""Détourage fond vert qui GARDE les éléments verts du perso (cœurs/bandeau de DIO) :
alpha = distance à la couleur du fond ; débordement retiré seulement sur les pixels proches du fond."""
import sys
from PIL import Image
import numpy as np
from scipy import ndimage


def key(src, crop=True, scale=None):
    im = Image.open(src).convert('RGB'); a = np.asarray(im).astype(np.float32)
    c = np.concatenate([a[:8, :8].reshape(-1, 3), a[:8, -8:].reshape(-1, 3), a[-8:, :8].reshape(-1, 3), a[-8:, -8:].reshape(-1, 3)])
    g = np.asarray([x for x in c if x[1] - max(x[0], x[2]) > 120])
    bg = np.median(g if len(g) else c, axis=0)
    d = np.sqrt(((a - bg) ** 2).sum(-1))
    alpha = np.clip((d - 28) / 30, 0, 1)
    alpha = ndimage.grey_erosion(alpha, size=(3, 3))
    r, gg, b = a[..., 0], a[..., 1], a[..., 2]
    edge = ndimage.binary_dilation(alpha < 0.5, iterations=3) & (alpha > 0)
    spill = ((d < 70) & (alpha < 1)) | (edge & (gg - np.maximum(r, b) > 20))   # bords seulement (cœurs intacts)
    greenish = (gg - np.maximum(r, b) > 40) & (gg > 110) & (alpha > 0)
    lab, n = ndimage.label(greenish)
    if n:
        sz = ndimage.sum(greenish, lab, range(1, n + 1))
        spill |= np.isin(lab, 1 + np.nonzero(sz < 400)[0])   # miettes vertes (pas les cœurs, qui sont grands)
        alpha = np.where(np.isin(lab, 1 + np.nonzero(sz < 400)[0]) & (d < 90), alpha * 0.3, alpha)
    g2 = np.where(spill, np.minimum(gg, np.maximum(r, b) + 10), gg)
    out = Image.fromarray(np.dstack([np.stack([r, g2, b], -1).clip(0, 255).astype(np.uint8), (alpha * 255).astype(np.uint8)]), 'RGBA')
    if crop:
        out = out.crop(out.getbbox())
    s = scale or (2 if out.width < 800 else 1)
    return out.resize((out.width * s, out.height * s), Image.LANCZOS)


if __name__ == "__main__":
    key(sys.argv[1], crop=sys.argv[3] != "nocrop" if len(sys.argv) > 3 else True).save(sys.argv[2])
