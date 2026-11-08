"""Prépare un passage « sale » de la vidéo de référence pour la recopie fine (fit2) : décor qui bouge (nuages,
traits de vitesse, caméra qui glisse), adversaire à l'écran, cheveux d'une autre couleur (UI = argentés).
On ne garde que les pixels de NOTRE Goku : couleurs de sa palette (fit2.PAL), regroupées en morceaux connexes, et
seulement les morceaux reliés à son pantalon orange (l'adversaire SSJ4 a la même peau et le même liseré rouge, mais
un pantalon jaune) ; les cheveux argentés sont repeints dans le noir du Pivot. Le reste = fond vide fixe (le même
pour toutes les images), donc fit2 / check2 / render_fit2 marchent sans changement.
python3 clean.py dossier_brut fond_vide.png dossier_sortie [échelle]
échelle : agrandit/rétrécit l'image autour du bas-centre si Goku n'a pas la même taille que le Goku de référence.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fit2  # noqa: E402

HAIR = np.array([(166, 170, 190), (160, 166, 186), (180, 188, 205), (150, 154, 176)], np.int16)
HAIR_DST = (24, 24, 24)


def clean(rgb, bg, scale=1.0):
    a = rgb.astype(np.int16)
    d = np.abs(a[:, :, None, :] - fit2.PCOL[None, None]).sum(3)
    cls = fit2.PCLS[d.argmin(2)]
    near = d.min(2) < 60
    dh = np.abs(a[:, :, None, :] - HAIR[None, None]).sum(3).min(2)
    hair = dh < 28
    body = near & ~hair & (cls != 1)                       # pas de noir chez le Goku UI (cheveux argentés)
    orange0 = body & np.isin(cls, (2, 3))
    if orange0.any():
        top = np.nonzero(orange0)[0].min()
        hair &= np.arange(a.shape[0])[:, None] < top + 12   # cheveux : au-dessus du haut du gi (pas les murs gris)
    # bleu nuit des bottes : seulement les morceaux bordés du liseré rouge (les fenêtres du temple n'en ont pas)
    navy = body & (cls == 7)
    red = ndi.binary_dilation(body & (cls == 9), iterations=6)
    nl, nn = ndi.label(navy, structure=np.ones((3, 3)))
    ok = set(np.unique(nl[navy & red]).tolist()) - {0}
    body &= ~(navy & ~np.isin(nl, list(ok)))
    lab, n = ndi.label(ndi.binary_dilation(body | hair, iterations=1), structure=np.ones((3, 3)))
    orange = body & np.isin(cls, (2, 3))
    keep_ids = set(np.unique(lab[orange & (lab > 0)]).tolist())
    # morceaux sans orange (tête, bras levé) : gardés s'ils touchent un morceau gardé après une dilatation de 3 px
    keep = np.isin(lab, list(keep_ids)) & (body | hair)
    big = ndi.binary_dilation(keep, iterations=3)
    for i in range(1, n + 1):
        if i in keep_ids:
            continue
        m = lab == i
        if m.sum() < 20000 and (m & big).any():
            # ne pas reprendre l'adversaire : pas de jaune/magenta autour
            keep |= m & (body | hair)
    # on ne garde que le plus gros bloc (Goku) : les miettes de l'adversaire autour partent
    bl, bn = ndi.label(ndi.binary_dilation(keep, iterations=4), structure=np.ones((3, 3)))
    if bn > 1:
        sizes = ndi.sum(keep, bl, range(1, bn + 1))
        main = bl == (1 + int(np.argmax(sizes)))
        near_main = ndi.binary_dilation(main, iterations=14)
        ok_b = [i + 1 for i, sz in enumerate(sizes) if sz >= 120 and (near_main & (bl == i + 1)).any()]
        keep &= np.isin(bl, ok_b)
    # trous laissés par les traits de vitesse blancs qui passent devant lui : bouchés avec la couleur voisine
    filled = ndi.binary_fill_holes(ndi.binary_closing(keep, iterations=2))
    _, (iy, ix) = ndi.distance_transform_edt(~keep, return_indices=True)
    src = rgb.copy()
    src[filled & ~keep] = rgb[iy, ix][filled & ~keep]
    hair = hair | (filled & ~keep & hair[iy, ix])
    keep = filled
    out = bg.copy()
    out[keep] = src[keep]
    out[keep & hair] = HAIR_DST
    if scale != 1.0:
        im = Image.fromarray(out.astype(np.uint8))
        W, H = im.size
        big_im = im.resize((round(W * scale), round(H * scale)), Image.NEAREST)
        canvas = Image.fromarray(bg.astype(np.uint8))
        bx, by = W / 2, H - 31                                     # bas-centre (le sol)
        canvas.paste(big_im, (round(bx - bx * scale), round(by - by * scale)))
        # remettre le fond là où l'image agrandie apporte du fond décalé : on ne garde que les pixels du perso
        cm = np.abs(np.asarray(canvas).astype(np.int16) - bg).sum(2) >= 45
        res = bg.copy()
        res[cm] = np.asarray(canvas)[cm]
        out = res
    return out.astype(np.uint8)


if __name__ == "__main__":
    src, bgp, dst = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
    sc = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
    bg = np.asarray(Image.open(bgp).convert("RGB")).astype(np.int16)
    dst.mkdir(parents=True, exist_ok=True)
    for f in sorted(src.glob("*.png")):
        rgb = np.asarray(Image.open(f).convert("RGB"))
        Image.fromarray(clean(rgb, bg, sc)).save(dst / f.name)
    print("ok")
