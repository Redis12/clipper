"""Découpeur de planches de sprites (07/11, demandé : « crée un outil pixel art animation »).

python3 tools/sprites/slice.py <planche.png> [dossier_sortie]
- Devine la couleur de fond (coins de l'image) et la retire (transparent), ou garde la transparence du PNG.
- Trouve chaque sprite (zones reliées, les petits morceaux proches fusionnés : cheveux, effets).
- Range les sprites en lignes (de haut en bas, de gauche à droite) → frames/001.png, 002.png…
- Ligne de base commune : chaque frame garde sa position « pieds au sol » (bas de la boîte) → pas de tremblement.
- Écrit index.png (planche numérotée pour choisir) et frames.json (boîte, ligne, numéro).
Les traits verticaux de séparation de la planche sont ignorés (trop fins).

Ensuite une animation = une liste de numéros + durées, ex. dans anims.json :
  {"punch": [[12, 0.06], [13, 0.06], [14, 0.12]], "idle": [[3, 0.12], [4, 0.12]]}
et `sprites.anim(dossier, "punch", t)` rend l'image à l'instant t (voir anim.py).
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage


def background_mask(a):
    """True = fond. Alpha si le PNG en a, sinon couleur des coins (± tolérance)."""
    if a.shape[2] == 4 and (a[..., 3] < 10).mean() > 0.2:
        return a[..., 3] < 10
    rgb = a[..., :3].astype(int)
    corners = np.array([rgb[0, 0], rgb[0, -1], rgb[-1, 0], rgb[-1, -1]])
    bgc = np.median(corners, axis=0)
    dist = np.abs(rgb - bgc).sum(2)
    return dist < 24


def slice_sheet(path, out=None, merge_px=1, min_area=60):
    path = Path(path)
    out = Path(out) if out else path.with_suffix("")
    (out / "frames").mkdir(parents=True, exist_ok=True)
    im = Image.open(path).convert("RGBA")
    a = np.asarray(im).copy()
    bg = background_mask(a)
    a[bg, 3] = 0
    fg = ~bg
    # traits de séparation verticaux (1-3 px de large, très hauts) → retirés
    lab0, n0 = ndimage.label(fg)
    for i, sl in enumerate(ndimage.find_objects(lab0), 1):
        h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if w <= 3 and h > 30:
            fg[lab0 == i] = False
            a[lab0 == i, 3] = 0
    grown = ndimage.binary_dilation(fg, iterations=merge_px)
    lab, n = ndimage.label(grown)
    boxes = []
    for i, sl in enumerate(ndimage.find_objects(lab), 1):
        m = (lab[sl] == i) & fg[sl]
        if m.sum() < min_area:
            continue
        ys, xs = np.nonzero(m)
        y0, y1 = sl[0].start + ys.min(), sl[0].start + ys.max() + 1
        x0, x1 = sl[1].start + xs.min(), sl[1].start + xs.max() + 1
        boxes.append((x0, y0, x1, y1))
    # lignes : on regroupe par recouvrement vertical
    boxes.sort(key=lambda b: (b[1] + b[3]) / 2)
    rows = []
    for b in boxes:
        cy = (b[1] + b[3]) / 2
        for r in rows:
            if r["y0"] - 4 <= cy <= r["y1"] + 4:
                r["b"].append(b)
                r["y0"], r["y1"] = min(r["y0"], b[1]), max(r["y1"], b[3])
                break
        else:
            rows.append({"y0": b[1], "y1": b[3], "b": [b]})
    rows.sort(key=lambda r: r["y0"])
    meta = []
    k = 0
    clean = Image.fromarray(a)
    for ri, r in enumerate(rows):
        for b in sorted(r["b"], key=lambda b: b[0]):
            k += 1
            fr = clean.crop(b)
            fr.save(out / "frames" / f"{k:03d}.png")
            al = np.asarray(fr)[..., 3] > 0                       # ancre x = centre des jambes (bas 35 %)
            low = al[int(al.shape[0] * 0.65):]
            cols = np.nonzero(low.any(0))[0]
            ax = float((np.nonzero(low)[1].mean())) if low.any() else fr.width / 2
            meta.append({"n": k, "row": ri + 1, "box": [int(v) for v in b], "w": int(b[2] - b[0]), "h": int(b[3] - b[1]),
                         "base": int(r["y1"]) - int(b[3]), "anchor_x": round(ax, 1)})     # distance au bas de la ligne (pieds)
    json.dump({"sheet": path.name, "frames": meta}, open(out / "frames.json", "w"), indent=1)
    # planche numérotée
    sc = 2
    idx = clean.resize((clean.width * sc, clean.height * sc), Image.NEAREST)
    bgim = Image.new("RGBA", idx.size, (40, 44, 60, 255))
    bgim.alpha_composite(idx)
    d = ImageDraw.Draw(bgim)
    try:
        font = ImageFont.truetype(str(Path(__file__).resolve().parents[1] / "money_sim/fonts/mont900.woff2"), 18)
    except OSError:
        font = None
    for m in meta:
        x0, y0, x1, y1 = (v * sc for v in m["box"])
        d.rectangle((x0, y0, x1, y1), outline=(255, 210, 60, 200), width=1)
        d.text((x0 + 2, y0 + 1), str(m["n"]), fill=(255, 255, 255), font=font, stroke_width=2, stroke_fill=(0, 0, 0))
    bgim.save(out / "index.png")
    return out, meta


if __name__ == "__main__":
    o, m = slice_sheet(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    print(o, len(m), "images")
