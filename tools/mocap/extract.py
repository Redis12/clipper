"""Découpe les mouvements directement dans la vidéo de référence (08/11, idée de l'utilisateur : « green screen »
sur la vidéo originale au lieu de recopier les coups) : chaque image → PNG transparent de Goku seul (clean.py :
couleurs de sa palette, morceaux reliés au gi), recadré sur une boîte commune à tout le mouvement (ne tremble pas),
pieds en bas. Sortie : library/_mocap/clips/<nom>/0001.png… + aperçu.gif + info.json (sol, ancre).
python3 extract.py video.mp4 debut_s fin_s nom [base] [decor_vide.png]
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import clean  # noqa: E402
import fit2  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

KEY = (255, 0, 255)


def frames(video, t0, t1, fps=30):
    d = Path(tempfile.mkdtemp())
    subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t0), "-to", str(t1), "-i", video, "-vf", f"fps={fps}",
                    str(d / "%04d.png")], check=True)
    return sorted(d.glob("*.png"))


def cut(rgb, base, empty=None):
    """empty = image du décor vide (caméra fixe, 0:19–0:30) : masque = différence avec le décor, bien plus propre quand
    Goku passe devant le palais ; sinon (caméra qui bouge) : clean.py."""
    bg = np.zeros(rgb.shape, np.int16)
    bg[:] = KEY
    if empty is None:
        out = clean.clean(rgb, bg, 1.0, base).astype(np.int16)
        a = (np.abs(out - np.array(KEY)).sum(2) > 0)
    else:
        out = rgb.astype(np.int16)
        a = np.abs(rgb.astype(np.int16) - empty).sum(2) >= 45
        a = ndi.binary_opening(a, iterations=1) | (a & ndi.binary_erosion(a))
    # dorés (classe 8 = liseré du gi) : les traits fins restent, les gros morceaux = dôme du palais derrière
    d = np.abs(rgb.astype(np.int16)[:, :, None, :] - fit2.PCOL[None, None]).sum(3)
    gold = a & (fit2.PCLS[d.argmin(2)] == 8)
    thick = ndi.binary_dilation(ndi.binary_erosion(gold, iterations=2), iterations=4) & gold
    gl, gn = ndi.label(gold, structure=np.ones((3, 3)))
    if empty is None:
        a &= ~np.isin(gl, [i for i in np.unique(gl[thick]) if i])
    lab, n = ndi.label(a, structure=np.ones((3, 3)))
    if n > 1:
        sz = ndi.sum(a, lab, range(1, n + 1))
        a &= ndi.binary_dilation(lab == 1 + int(np.argmax(sz)), iterations=3) | np.isin(lab, [i + 1 for i in range(n) if sz[i] >= 60])
    px = rgb.copy()                                               # couleurs d'origine de la vidéo
    # aplats nets (la compression de la vidéo fait des taches) : chaque pixel proche d'une couleur du perso y est ramené
    pal = np.array([c for c, _ in clean.REMAP_BASE] if base else [], np.int16).reshape(-1, 3)
    pal = np.concatenate([fit2.PCOL, pal]) if len(pal) else fit2.PCOL
    # gi plus rouge (1:46) ou orange du Pivot (0:19) : on garde celui qui domine dans l'image
    red = [c for c, _ in clean.REMAP_BASE]
    piv = [c for c, k in zip(fit2.PCOL.tolist(), fit2.PCLS.tolist()) if k in (2, 3)][:1] + \
          [c for c, k in zip(fit2.PCOL.tolist(), fit2.PCLS.tolist()) if k == 3][:1]
    n_red = sum(int((np.abs(rgb.astype(np.int16) - np.array(c)).sum(2) < 20).sum()) for c in red)
    n_piv = sum(int((np.abs(rgb.astype(np.int16) - np.array(c)).sum(2) < 20).sum()) for c in piv)
    oranges = red if n_red > n_piv else piv
    pal = np.array([c for c, k in zip(fit2.PCOL.tolist(), fit2.PCLS.tolist()) if k not in (2, 3)] + oranges, np.int16)
    dp = np.abs(rgb.astype(np.int16)[:, :, None, :] - pal[None, None]).sum(3)
    snap = a & (dp.min(2) < 40)
    idx = dp.argmin(2)
    if True:                                                       # 2 tons du gi : vote sur 13×13 (taches de compression)
        lo, hi = len(pal) - 2, len(pal) - 1
        org = snap & np.isin(idx, (lo, hi))
        light = ndi.uniform_filter((org & (idx == lo)).astype(float), 13)
        tot = ndi.uniform_filter(org.astype(float), 13) + 1e-6
        idx = np.where(org, np.where(light / tot >= 0.5, lo, hi), idx)
    px[snap] = pal[idx][snap].astype(np.uint8)
    fill = a & (dp.min(2) >= 60)                                  # trous bouchés par clean (traits de vitesse blancs)
    fl, fn = ndi.label(fill, structure=np.ones((3, 3)))            # petits détails (logo du gi) gardés tels quels
    if fn:
        fsz = ndi.sum(fill, fl, range(1, fn + 1))
        fill &= np.isin(fl, [i + 1 for i in range(fn) if fsz[i] > 60])
    if fill.any():                                                # couleur du voisin net le plus proche
        _, (iy, ix) = ndi.distance_transform_edt(~(snap & ~fill), return_indices=True)
        px[fill] = px[iy, ix][fill]
    hair = a & (np.abs(out - np.array(clean.HAIR_DST)).sum(2) == 0)
    if not base:
        px[hair] = out[hair].astype(np.uint8)                     # UI : cheveux argentés → noirs comme clean
    rgba = np.dstack([px, (a * 255).astype(np.uint8)])
    return rgba, a


if __name__ == "__main__":
    video, t0, t1, name = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
    base = len(sys.argv) > 5 and sys.argv[5] == "base"
    empty = None
    if len(sys.argv) > 6:                                          # décor vide (caméra fixe)
        empty = np.asarray(Image.open(sys.argv[6]).convert("RGB")).astype(np.int16)
    root = HERE.parents[1] / "library" / "_mocap" / "clips" / name
    root.mkdir(parents=True, exist_ok=True)
    for f in root.glob("*.png"):
        f.unlink()
    ims, boxes = [], []
    for f in frames(video, t0, t1):
        rgba, a = cut(np.asarray(Image.open(f).convert("RGB")), base, empty)
        if a.sum() < 300:
            continue
        ys, xs = np.nonzero(a)
        boxes.append((xs.min(), ys.min(), xs.max(), ys.max()))
        ims.append(rgba)
    b = np.array(boxes)
    box = (int(b[:, 0].min()) - 2, int(b[:, 1].min()) - 2, int(b[:, 2].max()) + 3, int(b[:, 3].max()) + 3)
    feet = [int(bb[3]) - box[1] for bb in boxes]
    gif = []
    for i, rgba in enumerate(ims):
        im = Image.fromarray(rgba).crop(box)
        im.save(root / f"{i + 1:04d}.png")
        g = Image.new("RGB", im.size, (200, 225, 240))
        g.paste(im, (0, 0), im)
        gif.append(g)
    gif[0].save(root / "apercu.gif", save_all=True, append_images=gif[1:], duration=33, loop=0)
    json.dump({"source": Path(video).name, "t": [t0, t1], "fps": 30, "n": len(ims), "size": list(gif[0].size),
               "feet_y": feet, "x_in_video": box[0]}, open(root / "info.json", "w"))
    print(name, len(ims), gif[0].size)
