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
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", str(t0), "-t", str(round(t1 - t0, 3)), "-i", video, "-vf", f"fps={fps}",
                    str(d / "%04d.png")], check=True)
    return sorted(d.glob("*.png"))


def cut(rgb, base, empty=None, thr=60):
    """Découpe d'une image. empty = décor vide de la même prise (« clean plate » : décor fixe d'une animation 2D,
    pixels identiques d'une image à l'autre) → masque = ce qui diffère du décor, PUIS bords « dé-mélangés »
    (matting à fond connu) : un pixel de bord C = α·F + (1−α)·B, B = décor connu, F = couleur du perso la plus
    proche → α exact, plus de liseré clair ni de trace du décor. Sans décor : clean.py (moins propre)."""
    if empty is None:
        bg = np.zeros(rgb.shape, np.int16)
        bg[:] = KEY
        out = clean.clean(rgb, bg, 1.0, base).astype(np.int16)
        a = (np.abs(out - np.array(KEY)).sum(2) > 0)
        return np.dstack([rgb, (a * 255).astype(np.uint8)]), a
    k = rgb.shape[1] / 640.0                                          # constantes réglées en 640×360
    C = rgb.astype(np.float32)
    B = empty.astype(np.float32)
    d = np.abs(C - B).sum(2)
    core = d >= thr
    core = ndi.binary_opening(core, iterations=1) | (core & ndi.binary_erosion(core))   # poussières de compression
    lab, n = ndi.label(ndi.binary_dilation(core, iterations=max(3, round(3 * k))), structure=np.ones((3, 3)))
    if n > 1:                                                         # le perso = gros morceaux (pas de miettes)
        sz = ndi.sum(core, lab, range(1, n + 1))
        core &= np.isin(lab, [i + 1 for i in range(n) if sz[i] >= max(80 * k * k, 0.02 * sz.max())])
    holes = ndi.binary_fill_holes(core) & ~core                         # petits trous (logo blanc ≈ ciel) bouchés
    hl, hn = ndi.label(holes)
    if hn:
        hs = ndi.sum(holes, hl, range(1, hn + 1))
        core |= np.isin(hl, [i + 1 for i in range(hn) if hs[i] <= 250 * k * k])
    sure = ndi.binary_erosion(core, iterations=1)
    band = ndi.binary_dilation(core, iterations=max(2, round(1.5 * k))) & ~sure
    _, (iy, ix) = ndi.distance_transform_edt(~sure, return_indices=True)
    F = C[iy, ix]                                                      # couleur du perso la plus proche
    FB = F - B
    alpha = np.where(sure, 1.0, 0.0)
    den = (FB * FB).sum(2)
    ab = np.clip(((C - B) * FB).sum(2) / np.maximum(den, 1.0), 0.0, 1.0)
    ab[den < 400] = core[den < 400]                                     # perso ≈ décor : on garde le masque dur
    alpha = np.where(band, ab, alpha)
    alpha[core & (d < thr)] = 1.0                                     # trous bouchés : opaques
    alpha[alpha < 0.12] = 0
    px = np.where((band & ~(core & (d < thr)))[..., None], F, C)
    rgba = np.dstack([np.clip(px, 0, 255).astype(np.uint8), (alpha * 255).astype(np.uint8)])
    return rgba, alpha > 0.5


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
    W0 = 640
    for f in frames(video, t0, t1):
        rgb_ = np.asarray(Image.open(f).convert("RGB"))
        W0 = rgb_.shape[1]
        rgba, a = cut(rgb_, base, empty)
        if a.sum() < 300 * (W0 / 640.0) ** 2:
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
    json.dump({"goku_h": round(250.0 * W0 / 640.0, 1), "source": Path(video).name, "t": [t0, t1], "fps": 30, "n": len(ims), "size": list(gif[0].size),
               "feet_y": feet, "x_in_video": box[0]}, open(root / "info.json", "w"))
    print(name, len(ims), gif[0].size)
