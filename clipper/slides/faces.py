"""Trouve le visage d'un perso dans une image, pour recadrer les icônes rondes (Fusion) sur la tête.

1. Vision de Claude (fiable sur tous les styles, Dragon Ball compris) : une question par image, résultat mémorisé
   dans data/faces.json (clé = chemin + date + taille) → jamais redemandé, coût négligeable.
2. Sans clé / erreur : détecteur OpenCV lbpcascade_animeface (nagadomi, MIT, clipper/assets/) puis visage réaliste.
3. Sinon : heuristique (tête en haut au centre de la silhouette).
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

from PIL import Image

from .. import config
from ..util import log

ASSET = Path(__file__).resolve().parent.parent / "assets" / "lbpcascade_animeface.xml"
_CASCADES: dict = {}


def _cascade(kind: str):
    import cv2
    if kind not in _CASCADES:
        path = str(ASSET) if kind == "anime" else cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        c = cv2.CascadeClassifier(path)
        _CASCADES[kind] = None if c.empty() else c
    return _CASCADES[kind]


FACE_SYSTEM = ("You locate the face of the main character in an anime/manga/comic image. Return the bounding box "
               "of the FACE only (from forehead/hairline to chin, ear to ear, excluding hair spikes and body), "
               "as fractions of the image width/height (0 = left/top, 1 = right/bottom). If several characters, "
               "take the biggest / most central one. found=false if there is no face at all.")
FACE_SCHEMA = {"type": "object", "properties": {
    "found": {"type": "boolean"},
    "x0": {"type": "number"}, "y0": {"type": "number"}, "x1": {"type": "number"}, "y1": {"type": "number"}},
    "required": ["found", "x0", "y0", "x1", "y1"], "additionalProperties": False}
_LOCK = threading.Lock()


def _cache_path() -> Path:
    return config.data_dir() / "faces.json"


def _key(path: Path) -> str:
    st = path.stat()
    return f"{path.resolve()}|{int(st.st_mtime)}|{st.st_size}"


def _load() -> dict:
    try:
        return json.loads(_cache_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def vision_box(path: Path) -> tuple[float, float, float, float] | None:
    """Boîte du visage (fractions 0-1) demandée à Claude, mémorisée. None si pas de visage ou pas de clé."""
    path = Path(path)
    key = _key(path)
    with _LOCK:
        cache = _load()
    if key in cache:
        v = cache[key]
        return tuple(v) if v else None
    tail = "tail:" + "/".join(path.parts[-2:])               # calé à la main, valable sur tout PC / conteneur
    if tail in cache:
        v = cache[tail]
        return tuple(v) if v else None
    try:
        from .. import llm
        from .library import cfg as lcfg
        out = llm.structured(model=lcfg()["model"], system=FACE_SYSTEM,
                             user=[llm.image_block(path, max_side=768), {"type": "text", "text": "Face box?"}],
                             tool_name="face_box", tool_desc="Store the face box.", schema=FACE_SCHEMA, max_tokens=300)
    except Exception as e:                              # pas de clé, pas d'Internet… → détecteur local
        log.info("visage par vision indisponible pour %s (%s) : détection locale", path.name, e)
        return None
    box = None
    if out.get("found"):
        x0, y0, x1, y1 = (min(1.0, max(0.0, float(out[k]))) for k in ("x0", "y0", "x1", "y1"))
        if x1 - x0 > 0.01 and y1 - y0 > 0.01:
            box = (x0, y0, x1, y1)
    with _LOCK:
        cache = _load()
        cache[key] = list(box) if box else None
        _cache_path().write_text(json.dumps(cache, indent=0), encoding="utf-8")
    return box


def detect(img: Image.Image) -> tuple[int, int, int, int] | None:
    """Plus grand visage (x, y, w, h) en pixels de `img`, ou None."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        return None
    rgb = img.convert("RGB")
    k = 800 / max(rgb.size) if max(rgb.size) > 800 else 1.0
    small = rgb.resize((max(1, round(rgb.width * k)), max(1, round(rgb.height * k)))) if k != 1 else rgb
    gray = cv2.equalizeHist(cv2.cvtColor(np.asarray(small), cv2.COLOR_RGB2GRAY))
    side = min(gray.shape)
    for kind, neigh in (("anime", 4), ("anime", 2), ("real", 5)):
        c = _cascade(kind)
        if c is None:
            continue
        found = c.detectMultiScale(gray, scaleFactor=1.08, minNeighbors=neigh, minSize=(max(16, side // 14),) * 2)
        if len(found):
            x, y, w, h = max(found, key=lambda f: f[2] * f[3])
            return int(x / k), int(y / k), int(w / k), int(h / k)
    return None


def _fallback(img: Image.Image) -> tuple[float, float, float]:
    """Sans visage détecté : la tête est en général en haut du perso, au centre de sa silhouette."""
    w, h = img.size
    box = None
    if img.mode in ("RGBA", "LA"):
        box = img.getchannel("A").point(lambda v: 255 if v > 10 else 0).getbbox()
    x0, y0, x1, y1 = box or (0, 0, w, h)
    bw, bh = x1 - x0, y1 - y0
    if bh > bw * 1.25:                                  # perso en pied : la tête est dans le haut
        s = bw * 0.75
        return (x0 + x1) / 2, y0 + s * 0.55, s
    s = min(bw, bh)
    return (x0 + x1) / 2, y0 + min(bh * 0.42, s / 2), s


def head_square(img: Image.Image, path: str | Path | None = None, vision: bool = True) -> Image.Image:
    """Carré centré sur la tête (cheveux compris), quel que soit le format de l'image."""
    w, h = img.size
    box = vision_box(Path(path)) if (vision and path and Path(path).is_file()) else None
    if box:
        x0, y0, x1, y1 = box[0] * w, box[1] * h, box[2] * w, box[3] * h
        fw, fh = x1 - x0, y1 - y0
        cx, cy = (x0 + x1) / 2, y0 + fh * 0.40           # un peu au-dessus du centre : front + cheveux
        side = max(fw, fh) * 1.9
    else:
        f = detect(img)
        if f:
            x, y, fw, fh = f
            cx, cy = x + fw / 2, y + fh * 0.42
            side = fw * 2.3
        else:
            cx, cy, side = _fallback(img)
    side = int(max(16, min(side, w, h)))
    x0 = int(min(max(0, round(cx - side / 2)), w - side))
    y0 = int(min(max(0, round(cy - side / 2)), h - side))
    return img.crop((x0, y0, x0 + side, y0 + side))
