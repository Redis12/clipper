"""Pack d'effets pixel-art « Anime Ki Auras & Energy VFX » (WsT, acheté par l'utilisateur le 02/11) : auras en
2 couches (derrière / devant le perso) qui bouclent, projectiles, rayon en 3 morceaux (queue + corps répétable +
tête), explosion en dôme, impact de coup, téléportation, image rémanente, charge, flash…

Le pack est cherché dans library/_domain/fx/** ou library/_vfx/** (fichier `effects.json`). Les planches
`<id>_sheet.png` ont 4 colonnes identiques et une image par ligne : on lit la 1re colonne. Tout est en gris + alpha
→ teinté à la couleur du camp (`couleur × gris`, cœur blanc), agrandi en NEAREST (pixel-art net).

Jamais utilisé dans les cinématiques de transformation (demande de l'utilisateur).
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image

from . import library

SCALE = 4                                                   # agrandissement des pixels (NEAREST)


@lru_cache(maxsize=1)
def _find(root_s: str) -> Path | None:
    root = Path(root_s)
    for base in (root / "_domain" / "fx", root / "_vfx"):
        if base.is_dir():
            for dirpath, _, files in os.walk(base, followlinks=True):
                if "effects.json" in files:
                    p = Path(dirpath) / "effects.json"
                    try:
                        if "effects" in json.loads(p.read_text(encoding="utf-8")):
                            return p.parent
                    except (OSError, ValueError):
                        pass
    return None


def root() -> Path | None:
    return _find(str(library.root()))


def available() -> bool:
    return root() is not None


@lru_cache(maxsize=1)
def catalog(root_s: str) -> dict:
    return json.loads((Path(root_s) / "effects.json").read_text(encoding="utf-8")).get("effects", {})


def info(eid: str) -> dict | None:
    r = root()
    return catalog(str(r)).get(eid) if r else None


def _sheet(eid: str, layer: str | None) -> Path | None:
    r = root()
    if r is None:
        return None
    d = r / "effects" / eid
    cands = [d / f"{eid}_{layer}_sheet.png"] if layer else [d / f"{eid}_sheet.png"]
    cands += [d / "grey" / f"{eid}_grey_{layer}_sheet.png"] if layer else [d / "grey" / f"{eid}_grey_sheet.png"]
    return next((p for p in cands if p.is_file()), None)


@lru_cache(maxsize=128)
def _grey(eid: str, layer: str | None) -> tuple:
    """Images (gris, alpha) de l'effet : (frames, cell_w, cell_h)."""
    p, meta = _sheet(eid, layer), info(eid)
    if p is None or meta is None:
        return ()
    im = Image.open(p).convert("RGBA")
    cw, ch = meta["cell"]
    n = int(meta["frames"])
    if im.height < ch * n:                                  # planche plus courte que prévu : on s'adapte
        n = max(1, im.height // ch)
    return tuple(im.crop((0, i * ch, cw, (i + 1) * ch)) for i in range(n))


def tint(im: Image.Image, col, hot: float = 0.6, scale: int = SCALE) -> Image.Image:
    a = np.asarray(im).astype(np.float32)
    g = a[..., 0:1] / 255
    c = np.asarray(col[:3], dtype=np.float32)[None, None, :]
    rgb = np.clip(c * g + (255 - c) * (g ** 6) * hot, 0, 255)      # couleur × gris, cœur blanc seulement au plus clair
    out = Image.fromarray(np.dstack([rgb, a[..., 3:4]]).astype(np.uint8), "RGBA")
    if scale > 1:
        out = out.resize((out.width * scale, out.height * scale), Image.NEAREST)
    out.info["pixel"] = True                                 # → collé en NEAREST (pixel-art net)
    return out


@lru_cache(maxsize=256)
def frames(eid: str, layer: str | None = None, color=(255, 255, 255), hot: float = 0.6, scale: int = SCALE) -> tuple:
    """Images RGBA teintées et agrandies de l'effet (vide si le pack / l'effet manque)."""
    col = tuple(int(c) for c in color[:3])
    return tuple(tint(f, col, hot, scale) for f in _grey(eid, layer))


def anchor(eid: str) -> tuple[float, float]:
    """Point d'ancrage en fractions de la cellule (0,0 = coin haut gauche)."""
    meta = info(eid)
    if not meta or not meta.get("anchor"):
        return 0.5, 0.5
    ax, ay = meta["anchor"]
    cw, ch = meta["cell"]
    return ax / cw, ay / ch


def fps() -> float:
    r = root()
    if r is None:
        return 20.0
    try:
        return 1000.0 / float(json.loads((r / "effects.json").read_text(encoding="utf-8")).get("frame_ms", 50))
    except (OSError, ValueError):
        return 20.0


@lru_cache(maxsize=512)
def beam_strip(cells: int, frame: int, color=(255, 255, 255), spiral: bool = False, scale: int = SCALE):
    """Rayon assemblé (queue + `cells` corps + tête) pour une image du cycle, tête à droite. None sans pack."""
    body = frames("spiral_beam_body" if spiral else "beam_body", None, color, 0.35, scale)
    head = frames("spiral_beam_head" if spiral else "beam_head", None, color, 0.35, scale)
    tail = () if spiral else frames("beam_tail", None, color, 0.35, scale)
    if not body or not head:
        return None
    b, h = body[frame % len(body)], head[frame % len(head)]
    t = tail[frame % len(tail)] if tail else None
    hi = info("spiral_beam_head" if spiral else "beam_head") or {}
    ax, ay = hi.get("anchor", [0, h.height // 2 // scale])
    ax, ay = ax * scale, ay * scale
    H = max(b.height, h.height, t.height if t else 0)
    W = (t.width if t else 0) + b.width * max(1, cells) + h.width - ax
    out = Image.new("RGBA", (max(2, W), H), (0, 0, 0, 0))
    x = 0
    cy = H // 2
    if t is not None:
        out.alpha_composite(t, (0, cy - t.height // 2))
        x += t.width
    for _ in range(max(1, cells)):
        out.alpha_composite(b, (x, cy - b.height // 2))
        x += b.width
    out.alpha_composite(h, (x - ax, cy - ay))
    out.info["pixel"] = True
    return out
