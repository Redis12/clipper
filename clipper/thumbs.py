"""Étape 7 : miniature. 10 images candidates, la plus nette avec un visage, texte posé avec Pillow."""
from __future__ import annotations

import io
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import config, db
from .util import log, require_bin, run, safe_replace

FONT_CANDIDATES = [
    "C:/Windows/Fonts/ariblk.ttf", "C:/Windows/Fonts/arialbd.ttf",
    "/System/Library/Fonts/Supplemental/Arial Black.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


# --- frames -------------------------------------------------------------------

def frame_times(start: float, end: float, n: int) -> list[float]:
    """n instants répartis dans le clip, en évitant les 5 % du début et de la fin (fondus, transitions)."""
    d = end - start
    a, b = start + 0.05 * d, end - 0.05 * d
    return [a + (i + 0.5) * (b - a) / n for i in range(n)]


_CASCADE: list = []


def _cascade():
    """Détecteur de visages Haar (livré avec OpenCV 4). None si indisponible : on retombe sur la netteté seule."""
    import cv2

    if not _CASCADE:
        p = os.path.join(getattr(getattr(cv2, "data", None), "haarcascades", ""), "haarcascade_frontalface_default.xml")
        c = cv2.CascadeClassifier(p) if os.path.exists(p) else None
        if c is None or c.empty():
            log.warning("Détection de visages indisponible (cascade Haar absente) : choix sur la netteté seule")
            c = None
        _CASCADE.append(c)
    return _CASCADE[0]


def score_frame(path: Path) -> tuple[float, float]:
    """(netteté = variance du laplacien, aire du plus grand visage en part de l'image)."""
    import cv2

    img = cv2.imread(str(path))
    gray = cv2.cvtColor(cv2.resize(img, (640, 360)), cv2.COLOR_BGR2GRAY)
    sharp = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    cascade = _cascade()
    if cascade is None:
        return sharp, 0.0
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=6, minSize=(40, 40))
    face = max((w * h for (_, _, w, h) in faces), default=0) / (640 * 360)
    return sharp, float(face)


def best_index(frames: list[dict]) -> int:
    with_face = [i for i, f in enumerate(frames) if f["face"] > 0]
    pool = with_face or range(len(frames))
    return max(pool, key=lambda i: frames[i]["sharp"])


def extract_frames(clip_id: int) -> list[dict]:
    c = db.get_clip(clip_id)
    v = db.get_video(c["video_id"])
    cfg = config.get()["thumbnail"]
    W, H = int(cfg["width"]), int(cfg["height"])
    fdir = config.clip_dir(clip_id) / "frames"
    fdir.mkdir(exist_ok=True)
    frames = []
    for i, t in enumerate(frame_times(float(c["start"]), float(c["end"]), int(cfg["n_frames"]))):
        p = fdir / f"f{i:02d}.jpg"
        run([require_bin("ffmpeg"), "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", v["source_path"],
             "-frames:v", "1", "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}",
             "-q:v", "2", str(p)])
        sharp, face = score_frame(p)
        frames.append({"path": str(p), "t": round(t, 2), "sharp": round(sharp, 1), "face": round(face, 4)})
    return frames


# --- texte --------------------------------------------------------------------

def load_font(size: int) -> ImageFont.FreeTypeFont:
    cfg_path = (config.get()["thumbnail"].get("font_path") or "").strip()
    for p in ([cfg_path] if cfg_path else []) + FONT_CANDIDATES:
        if p and Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default(size)


def _split(words: list[str], max_lines: int, font, draw) -> list[str]:
    """Répartit les mots sur au plus max_lines lignes en minimisant la ligne la plus large."""
    if max_lines <= 1 or len(words) <= 1:
        return [" ".join(words)]
    best, best_w = [" ".join(words)], draw.textlength(" ".join(words), font=font)
    for k in range(1, len(words)):
        lines = [" ".join(words[:k]), " ".join(words[k:])]
        w = max(draw.textlength(l, font=font) for l in lines)
        if w < best_w:
            best, best_w = lines, w
    return best


def compose(frame: Path, text: str, out: Path) -> Path:
    cfg = config.get()["thumbnail"]
    W, H, pad = int(cfg["width"]), int(cfg["height"]), int(cfg["padding"])
    with Image.open(frame) as src:   # fermé tout de suite : Windows refuse de remplacer un fichier ouvert
        img = src.convert("RGB")
    if img.size != (W, H):
        scale = max(W / img.width, H / img.height)
        img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
        l, t = (img.width - W) // 2, (img.height - H) // 2
        img = img.crop((l, t, l + W, t + H))

    text = " ".join(text.split())
    if cfg.get("uppercase", True):
        text = text.upper()
    pos = cfg.get("position", "bottom-left")
    stroke = int(cfg["stroke_width"])
    max_w = (W - 2 * pad) if pos == "center" else int(W * 0.66)

    # Ombrage du côté du texte pour la lisibilité.
    op = float(cfg.get("shade_opacity", 0))
    if op > 0 and text:
        import numpy as np

        ys = np.linspace(0, 1, H)[:, None]
        xs = np.linspace(0, 1, W)[None, :]
        fy = ys if "bottom" in pos else 1 - ys if "top" in pos else np.full_like(ys, 0.5)
        fx = 1 - xs if "left" in pos else xs if "right" in pos else np.full_like(xs, 0.6)
        alpha = np.clip(fx * 0.6 + fy * 0.8 - 0.25, 0, 1) * op * 255
        shade = Image.fromarray(alpha.astype("uint8"), "L")
        img = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), img, shade)

    draw = ImageDraw.Draw(img)
    words = text.split()
    size = int(cfg["font_size_max"])
    while True:
        font = load_font(size)
        lines = _split(words, int(cfg["max_lines"]), font, draw)
        widest = max(draw.textlength(l, font=font) for l in lines) + 2 * stroke if words else 0
        if widest <= max_w or size <= int(cfg["font_size_min"]):
            break
        size -= 4

    if words:
        asc, desc = font.getmetrics()
        lh = int((asc + desc) * 1.02)
        block_h = lh * len(lines)
        y0 = {"top": pad, "bottom": H - pad - block_h}.get(pos.split("-")[0], (H - block_h) // 2)
        accent = (cfg.get("accent_word_color") or "").strip()
        for li, line in enumerate(lines):
            lw = draw.textlength(line, font=font)
            x = pad if "left" in pos else W - pad - lw if "right" in pos else (W - lw) / 2
            y = y0 + li * lh
            if accent and li == len(lines) - 1 and " " in line:
                head, last = line.rsplit(" ", 1)
                draw.text((x, y), head + " ", font=font, fill=cfg["text_color"],
                          stroke_width=stroke, stroke_fill=cfg["stroke_color"])
                x += draw.textlength(head + " ", font=font)
                draw.text((x, y), last, font=font, fill=accent, stroke_width=stroke, stroke_fill=cfg["stroke_color"])
            else:
                fill = accent if accent and li == len(lines) - 1 and len(lines) > 1 else cfg["text_color"]
                draw.text((x, y), line, font=font, fill=fill, stroke_width=stroke, stroke_fill=cfg["stroke_color"])

    return save_under(img, out, int(cfg["max_bytes"]))


def save_under(img: Image.Image, out: Path, max_bytes: int) -> Path:
    for q in (92, 88, 84, 78, 72, 65, 58, 50):
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=q, optimize=True, progressive=True)
        if buf.tell() <= max_bytes:
            break
    tmp = out.with_suffix(".tmp.jpg")
    tmp.write_bytes(buf.getvalue())
    safe_replace(tmp, out)
    return out


# --- étape --------------------------------------------------------------------

def make(clip_id: int, refresh_frames: bool = False) -> Path:
    c = db.get_clip(clip_id)
    frames = c["frames"]
    if refresh_frames or not frames or not all(Path(f["path"]).exists() for f in frames):
        frames = extract_frames(clip_id)
        db.update_clip(clip_id, frames=frames, frame_idx=best_index(frames))
        c = db.get_clip(clip_id)
    idx = c["frame_idx"] if c["frame_idx"] is not None else best_index(frames)
    out = config.clip_dir(clip_id) / "thumb.jpg"
    compose(Path(frames[idx]["path"]), c["thumb_text"] or "", out)
    db.update_clip(clip_id, thumb_path=str(out))
    log.info("clip %s : miniature (image %d, %.0f Ko)", clip_id, idx, out.stat().st_size / 1024)
    return out
