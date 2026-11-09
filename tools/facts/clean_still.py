"""Image fixe propre d'un perso découpé (09/11 : Saitama debout « mal découpé, dégueulasse ») : chaque pixel est
ramené à la couleur à plat la plus proche de la palette du perso (style vectoriel Stick Nodes), le décor resté
collé (marron de la montagne, ciel) est enlevé, les zones sont lissées (filtre de mode) et le contour est
redessiné net (masque agrandi ×4, flou, seuil, réduit = anticrénelage).
python3 clean_still.py clip index sortie.png"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

PAL_SAITAMA = [(232, 184, 90), (214, 166, 80), (158, 62, 38), (120, 48, 26), (252, 196, 138), (234, 240, 234),
               (34, 28, 26)]
BG = [(86, 68, 44), (70, 52, 34), (120, 90, 58), (60, 170, 240)]


def clean(im, pal=PAL_SAITAMA, bg=BG, up=4):
    a = np.array(im.convert("RGBA")).astype(int)
    rgb, al = a[..., :3], a[..., 3]
    P = np.array(pal)
    dp = np.stack([np.abs(rgb - c).sum(2) for c in P])
    lab = dp.argmin(0)
    dmin = dp.min(0)
    dbg = np.min(np.stack([np.abs(rgb - c).sum(2) for c in bg]), 0)
    keep = (al > 100) & ~((dbg < dmin) & (dbg < 90))
    keep = ndi.binary_opening(keep, iterations=1)
    keep = ndi.binary_fill_holes(keep)
    lb, n = ndi.label(keep)
    if n > 1:
        sz = ndi.sum(keep, lb, range(1, n + 1))
        keep = lb == (int(np.argmax(sz)) + 1)
    # filtre de mode sur les étiquettes (zones à plat, sans grain)
    lab2 = lab.copy()
    for _ in range(2):
        votes = np.stack([ndi.uniform_filter((lab2 == i).astype(float), 5) for i in range(len(P))])
        lab2 = votes.argmax(0)
    # marron fin collé au bord = reste de montagne (les gants / bottes sont des blocs épais)
    brown = keep & np.isin(lab2, [2, 3])
    solid = ndi.binary_opening(brown, iterations=4)
    solid = ndi.binary_propagation(solid, mask=brown) & ndi.binary_dilation(solid, iterations=2)
    keep &= ~(brown & ~solid)
    keep = ndi.binary_opening(keep, iterations=2)
    lb, n = ndi.label(keep)
    if n > 1:
        sz = ndi.sum(keep, lb, range(1, n + 1))
        keep = lb == (int(np.argmax(sz)) + 1)
    for _ in range(2):
        votes = np.stack([ndi.uniform_filter(((lab2 == i) & keep).astype(float), 7) for i in range(len(P))])
        lab2 = votes.argmax(0)
    sk = (lab2 == 4) & keep                                    # la peau = la tête seulement (plus gros bloc)
    lb, n = ndi.label(sk)
    if n:
        sz = ndi.sum(sk, lb, range(1, n + 1))
        head = lb == (int(np.argmax(sz)) + 1)
        stray = sk & ~head
        cape = ndi.binary_dilation((lab2 == 5) & keep, iterations=3)
        lab2[stray & cape] = 5
        lab2[stray & ~cape] = 0
    out = np.zeros((*al.shape, 4), np.uint8)
    out[..., :3] = P[lab2]
    m = Image.fromarray((keep * 255).astype(np.uint8)).resize((al.shape[1] * up, al.shape[0] * up), Image.BICUBIC)
    m = m.filter(__import__("PIL.ImageFilter", fromlist=["x"]).GaussianBlur(up * 0.9))
    m = m.point(lambda v: 255 if v > 128 else 0).resize((al.shape[1], al.shape[0]), Image.LANCZOS)
    out[..., 3] = np.array(m)
    # couleurs du bord : celles de l'intérieur le plus proche
    inner = ndi.binary_erosion(keep, iterations=2)
    _, (iy, ix) = ndi.distance_transform_edt(~inner, return_indices=True)
    edge = (out[..., 3] > 0) & ~inner
    out[..., :3][edge] = P[lab2][iy[edge], ix[edge]]
    return Image.fromarray(out)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mocap"))
    import clips
    d = clips.ROOT / sys.argv[1]
    fs = sorted(d.glob("0*.png"))
    clean(Image.open(fs[int(sys.argv[2])])).save(sys.argv[3])
