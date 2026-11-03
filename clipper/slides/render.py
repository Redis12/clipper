"""Rendu des slides (Pillow) en 9:16 et 4:5, et du Short vidéo (ffmpeg)."""
from __future__ import annotations

import random
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .. import config, db
from ..util import log, require_bin, run, safe_replace
from . import library

FONTS = [
    "C:/Windows/Fonts/impact.ttf", "C:/Windows/Fonts/ariblk.ttf", "C:/Windows/Fonts/arialbd.ttf",
    "/System/Library/Fonts/Supplemental/Impact.ttf", "/System/Library/Fonts/Supplemental/Arial Black.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


THIN_FONTS = [
    "C:/Windows/Fonts/segoeuil.ttf", "C:/Windows/Fonts/segoeuisl.ttf", "C:/Windows/Fonts/segoeui.ttf",
    "/System/Library/Fonts/SFNS.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-ExtraLight.ttf",
]
PLAIN_FONTS = [
    "C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def font_from(paths: list[str], size: int) -> ImageFont.FreeTypeFont:
    for f in paths:
        if Path(f).exists():
            return ImageFont.truetype(f, size)
    return font(size)


def free_height(img: Image.Image, y_from: int, y_max: int) -> int:
    """Hauteur de « vide » (peu de contours) sous y_from, dans la bande centrale, avant de toucher le sujet."""
    import numpy as np

    W, H = img.size
    g = np.asarray(img.convert("L").resize((W // 4, H // 4)).filter(ImageFilter.FIND_EDGES), dtype=float)
    band = g[:, g.shape[1] // 8: g.shape[1] * 7 // 8]
    rows = band.mean(axis=1)
    rows = np.convolve(rows, np.ones(5) / 5, mode="same")
    limit = max(6.0, float(np.percentile(rows, 40)) * 1.6)
    y0, y1 = max(0, y_from // 4), min(len(rows), y_max // 4)
    for y in range(y0, y1):
        if rows[y] > limit:
            return (y - y0) * 4
    return (y1 - y0) * 4


CLOCK_FONTS = [   # chiffres épais et arrondis, façon iOS 26
    "C:/Windows/Fonts/ARLRDBD.TTF", "C:/Windows/Fonts/seguibl.ttf", "C:/Windows/Fonts/segoeuib.ttf",
    "/System/Library/Fonts/SFNSRounded.ttf", "/usr/share/fonts/opentype/inter/Inter-Black.otf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def draw_lockscreen(img: Image.Image, slide: dict) -> Image.Image:
    """Écran de verrouillage style iOS 26 : petite date en gras, puis une heure énorme en « verre liquide »
    (chiffres translucides qui floutent et éclaircissent l'image derrière, avec un liseré clair)."""
    from PIL import ImageChops, ImageEnhance

    W, H = img.size
    k = W / 1080
    lk = slide.get("lock") or {}
    date, clock = lk.get("date") or "Sunday, November 1", lk.get("time") or "9:41"
    base = img.convert("RGB")
    top = int(H * (0.075 if H / W > 1.5 else 0.05))

    # Heure : la plus grande possible sur ~86 % de la largeur.
    size = int(W * 0.5)
    tf = font_from(CLOCK_FONTS, size)
    while tf.getlength(clock) > W * 0.86 and size > 40:
        size -= 6
        tf = font_from(CLOCK_FONTS, size)
    df = font_from(PLAIN_FONTS, int(46 * k))
    ty = top + int(70 * k)
    # Comme iOS 26 : s'il y a du vide sous l'heure (ciel, fond uni), les chiffres s'étirent en hauteur jusqu'au sujet.
    glyph = Image.new("L", (W, int(size * 1.4)), 0)
    ImageDraw.Draw(glyph).text((W / 2, 0), clock, font=tf, anchor="mt", fill=255)
    box = glyph.getbbox() or (0, 0, W, size)
    glyph = glyph.crop((0, box[1], W, box[3]))
    gh = glyph.height
    free = free_height(base, ty + gh, int(H * 0.62)) + gh
    target = int(min(max(gh, (free - 30 * k) * 0.8), gh * 1.8, H * 0.30))   # étirement modéré, jamais caricatural
    if target > gh * 1.12:
        glyph = glyph.resize((W, target), Image.LANCZOS)
    mask = Image.new("L", (W, H), 0)
    mask.paste(glyph, (0, ty))

    # Ombre douce sous les chiffres.
    sh = mask.filter(ImageFilter.GaussianBlur(int(18 * k))).point(lambda v: int(v * 0.35))
    out = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), base, ImageChops.offset(sh, 0, int(8 * k)))
    # Verre : l'image derrière, floutée, éclaircie et blanchie.
    glass = ImageEnhance.Brightness(base.filter(ImageFilter.GaussianBlur(int(22 * k)))).enhance(1.35)
    glass = Image.blend(glass, Image.new("RGB", (W, H), (255, 255, 255)), 0.32)
    out = Image.composite(glass, out, mask.point(lambda v: int(v * 0.88)))
    # Liseré clair sur les bords (reflet), un peu plus marqué en haut.
    edge = ImageChops.subtract(mask, mask.filter(ImageFilter.MinFilter(max(3, int(5 * k)) | 1)))
    hi = ImageChops.subtract(mask, ImageChops.offset(mask, 0, int(4 * k)))
    rim = ImageChops.lighter(edge.point(lambda v: int(v * 0.55)), hi.point(lambda v: int(v * 0.8)))
    out = Image.composite(Image.new("RGB", (W, H), (255, 255, 255)), out, rim.filter(ImageFilter.GaussianBlur(1)))

    d = ImageDraw.Draw(out)
    d.text((W / 2, top), date, font=df, anchor="mt", fill=(255, 255, 255),
           stroke_width=0)
    return out


def _card(path: str | None, cw: int, ch: int, lock: dict | None) -> Image.Image:
    """Un « téléphone » : le wallpaper aux coins arrondis (avec l'écran de verrouillage si `lock`)."""
    if path and Path(path).exists():
        with Image.open(path) as src:
            card = smart_crop(src.convert("RGB"), cw, ch)
    else:
        card = Image.new("RGB", (cw, ch), (30, 30, 34))
    if lock is not None:
        card = draw_lockscreen(card, {"lock": lock})
    r = int(cw * 0.10)
    mask = Image.new("L", (cw, ch), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, cw - 1, ch - 1), radius=r, fill=255)
    out = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    out.paste(card, (0, 0), mask)
    ImageDraw.Draw(out).rounded_rectangle((1, 1, cw - 2, ch - 2), radius=r, outline=(90, 90, 96, 255),
                                          width=max(2, cw // 220))
    return out


def draw_lock_carousel(slide: dict, W: int, H: int) -> Image.Image:
    """Comme le sélecteur d'écran de verrouillage : le wallpaper au centre, les voisins qui dépassent sur les côtés
    (ça donne envie de swiper)."""
    k = W / 1080
    ratio = 19.5 / 9
    cw = int(min(W * 0.66, H * 0.84 / ratio))           # un peu dézoomé : les voisins se voient bien
    ch = int(cw * ratio)
    gap = int(34 * k)
    img = Image.new("RGBA", (W, H), (8, 8, 10, 255))
    x0, y0 = (W - cw) // 2, (H - ch) // 2
    for path, x in ((slide.get("_prev"), x0 - gap - cw), (slide.get("_next"), x0 + cw + gap)):
        if path:
            side = _card(path, cw, ch, None)
            side.putalpha(side.getchannel("A").point(lambda v: int(v * 0.75)))
            img.alpha_composite(side, (x, y0))
    img.alpha_composite(_card(slide.get("image_path"), cw, ch, slide.get("lock") or {}), (x0, y0))
    # Points de pagination sous le téléphone (le point courant en blanc, les autres plus petits vers les bords).
    total, pos = int(slide.get("_total") or 0), int(slide.get("_pos") or 0)
    if total > 1:
        d = ImageDraw.Draw(img)
        step, cy = int(34 * k), y0 + ch + int((H - y0 - ch) * 0.45)
        sx = W / 2 - step * (total - 1) / 2
        for i in range(total):
            r = (9 if i == pos else 7 - min(3, abs(i - pos) // 2)) * k
            col = (245, 245, 245, 255) if i == pos else (120, 120, 126, 255)
            cx = sx + i * step
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col)
    return img.convert("RGB")


def draw_phone_fit(slide: dict, W: int, H: int) -> Image.Image:
    """Instagram 4:5 : le wallpaper (9:16) entier dans un téléphone, sur un fond flouté de la même image."""
    k = W / 1080
    ratio = 19.5 / 9
    ch = int(H * 0.92)
    cw = int(ch / ratio)
    path = slide.get("image_path")
    if path and Path(path).exists():
        with Image.open(path) as src:
            bg = smart_crop(src.convert("RGB"), W, H).filter(ImageFilter.GaussianBlur(int(40 * k)))
        bg = Image.blend(bg, Image.new("RGB", (W, H), (0, 0, 0)), 0.45)
    else:
        bg = Image.new("RGB", (W, H), (8, 8, 10))
    out = bg.convert("RGBA")
    out.alpha_composite(_card(path, cw, ch, None), ((W - cw) // 2, (H - ch) // 2))
    return out.convert("RGB")


def draw_plain_title(img: Image.Image, text: str, c: dict) -> Image.Image:
    """Couverture « Wallpapers >>> » : texte simple, casse normale, ombre douce, au centre."""
    W, H = img.size
    k = W / 1080
    f = font_from(PLAIN_FONTS, int(78 * k))
    draw = ImageDraw.Draw(img)
    lines = wrap(text, f, int(W * 0.8), draw)
    lh = int(sum(f.getmetrics()) * 1.1)
    y = (H - lh * len(lines)) // 2
    for line in lines:
        draw_rich(img, (W / 2, y), line, f, (255, 255, 255), "ma", max(2, int(4 * k)), (0, 0, 0))
        y += lh
    return img


def rcfg() -> dict:
    return config.get()["slides"]["render"]


def out_dir(slideshow_id: int) -> Path:
    d = config.data_dir() / "slides" / str(slideshow_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def font(size: int) -> ImageFont.FreeTypeFont:
    p = (rcfg().get("font_path") or "").strip()
    for f in ([p] if p else []) + FONTS:
        if f and Path(f).exists():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default(size)


# --- emojis ---------------------------------------------------------------------------
# Les polices de texte (Impact…) n'ont pas d'emojis : on découpe le texte en morceaux et on dessine
# les emojis avec une police emoji couleur (Segoe UI Emoji sous Windows, Apple / Noto ailleurs).

import re as _re

EMOJI_FONTS = [
    "C:/Windows/Fonts/seguiemj.ttf",
    "/System/Library/Fonts/Apple Color Emoji.ttc",
    "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
    "/usr/share/fonts/noto/NotoColorEmoji.ttf",
]
_EMOJI_RE = _re.compile(
    "(?:[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\u2300-\u23FF\u2190-\u21FF\u3030\u303D"
    "\u3297\u3299\u00A9\u00AE\u203C\u2049\u2122\u2139\u24C2\u25AA-\u25FE\u2934\u2935]"
    "[\uFE0F\u200D\U0001F3FB-\U0001F3FF\u20E3]*"
    "(?:\u200D[\U0001F000-\U0001FAFF\u2600-\u27BF][\uFE0F]*)*)")
_emoji_cache: dict = {}


def split_emoji(text: str) -> list[tuple[str, bool]]:
    """« Hi ⚠️ there » → [("Hi ", False), ("⚠️", True), (" there", False)]."""
    out, pos = [], 0
    for m in _EMOJI_RE.finditer(text):
        if m.start() > pos:
            out.append((text[pos:m.start()], False))
        out.append((m.group(), True))
        pos = m.end()
    if pos < len(text):
        out.append((text[pos:], False))
    return out


def _emoji_font():
    if "font" not in _emoji_cache:
        _emoji_cache["font"] = None
        for p in EMOJI_FONTS:
            if not Path(p).exists():
                continue
            for size in (109, 160, 64, 96, 128):      # Noto = 109, Apple = 160, Segoe = libre
                try:
                    _emoji_cache["font"] = ImageFont.truetype(p, size)
                    break
                except OSError:
                    continue
            if _emoji_cache["font"]:
                break
    return _emoji_cache["font"]


def emoji_image(e: str, height: int) -> Image.Image | None:
    """L'emoji en couleur, rendu à la taille native de la police puis mis à la hauteur voulue."""
    ef = _emoji_font()
    if ef is None:
        return None
    key = (e, height)
    if key not in _emoji_cache:
        box = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox((0, 0), e, font=ef, embedded_color=True)
        w, h = max(1, box[2] - box[0]), max(1, box[3] - box[1])
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((-box[0], -box[1]), e, font=ef, embedded_color=True)
        if im.getbbox() is None:                       # glyphe absent : on n'affiche rien plutôt qu'un carré
            _emoji_cache[key] = None
        else:
            _emoji_cache[key] = im.resize((max(1, round(w * height / h)), height), Image.LANCZOS)
    return _emoji_cache[key]


def text_width(draw: ImageDraw.ImageDraw, text: str, f: ImageFont.FreeTypeFont) -> float:
    total = 0.0
    for part, is_emoji in split_emoji(text):
        if is_emoji:
            im = emoji_image(part, emoji_height(f))
            total += (im.width + emoji_height(f) * 0.08) if im else 0
        else:
            total += draw.textlength(part, font=f)
    return total


def emoji_height(f: ImageFont.FreeTypeFont) -> int:
    asc, _ = f.getmetrics()
    return max(8, int(asc * 0.95))


def draw_rich(img: Image.Image, xy: tuple[float, float], text: str, f: ImageFont.FreeTypeFont, fill, anchor: str = "ma",
              stroke_width: int = 0, stroke_fill=None) -> None:
    """Comme draw.text (ancres « ma » ou « md »), mais avec des emojis en couleur."""
    draw = ImageDraw.Draw(img)
    parts = split_emoji(text)
    if not any(e for _, e in parts):
        draw.text(xy, text, font=f, fill=fill, anchor=anchor, stroke_width=stroke_width, stroke_fill=stroke_fill)
        return
    asc, desc = f.getmetrics()
    x = xy[0] - text_width(draw, text, f) / 2
    top = xy[1] if anchor[1] == "a" else xy[1] - (asc + desc)
    eh = emoji_height(f)
    for part, is_emoji in parts:
        if is_emoji:
            im = emoji_image(part, eh)
            if im is not None:
                img.paste(im, (int(x + eh * 0.04), int(top + (asc - eh) * 0.75)), im)
                x += im.width + eh * 0.08
        else:
            draw.text((x, top), part, font=f, fill=fill, anchor="la", stroke_width=stroke_width, stroke_fill=stroke_fill)
            x += draw.textlength(part, font=f)


# --- recadrage ----------------------------------------------------------------------

def smart_crop(img: Image.Image, W: int, H: int) -> Image.Image:
    """Remplit W×H. Sur l'axe recadré, garde la zone la plus « chargée » (contours = visages, persos)."""
    import numpy as np

    scale = max(W / img.width, H / img.height)
    img = img.resize((max(W, round(img.width * scale)), max(H, round(img.height * scale))), Image.LANCZOS)
    if img.size == (W, H):
        return img
    g = np.asarray(img.convert("L").resize((max(1, img.width // 4), max(1, img.height // 4))), dtype=np.float32)
    gx = np.abs(np.diff(g, axis=1, prepend=g[:, :1]))
    gy = np.abs(np.diff(g, axis=0, prepend=g[:1, :]))
    energy = gx + gy
    if img.width > W:                                   # recadrage horizontal
        prof, win, n = energy.sum(axis=0), W // 4, img.width // 4
    else:                                               # recadrage vertical
        prof, win, n = energy.sum(axis=1), H // 4, img.height // 4
    win = max(1, min(win, n))
    cs = np.concatenate([[0], np.cumsum(prof)])
    sums = cs[win:] - cs[:-win]
    centre = (len(sums) - 1) / 2
    bias = 1 - 0.25 * np.abs(np.arange(len(sums)) - centre) / max(1, centre)   # léger biais vers le centre
    best = int(np.argmax(sums * bias)) * 4
    if img.width > W:
        x = min(max(0, best), img.width - W)
        return img.crop((x, 0, x + W, H))
    y = min(max(0, best), img.height - H)
    return img.crop((0, y, W, y + H))


# --- texte ---------------------------------------------------------------------------

def wrap(text: str, f: ImageFont.FreeTypeFont, max_w: int, draw: ImageDraw.ImageDraw) -> list[str]:
    lines, cur = [], ""
    for w in text.split():
        trial = f"{cur} {w}".strip()
        if text_width(draw, trial, f) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def layout(text: str, max_w: int, max_h: int, size_max: int, size_min: int, stroke: int,
           draw: ImageDraw.ImageDraw) -> tuple[ImageFont.FreeTypeFont, list[str], int]:
    size = size_max
    while True:
        f = font(size)
        lines = wrap(text, f, max_w - 2 * stroke, draw)
        asc, desc = f.getmetrics()
        lh = int((asc + desc) * 1.08)
        widest = max((text_width(draw, l, f) for l in lines), default=0)
        if (lh * len(lines) <= max_h and widest <= max_w - 2 * stroke) or size <= size_min:
            return f, lines, lh
        size -= 4


def brand_dir() -> Path:
    from . import library
    d = library.root() / "_brand"
    d.mkdir(parents=True, exist_ok=True)
    return d


def logo_path(anime: str) -> Path:
    """Logo d'un anime (PNG transparent) : library/_brand/logos/<anime>.png (jamais pris comme image de slide).
    À défaut, un PNG déposé à la main dans library/logos/ dont le nom contient les mots de l'anime."""
    import re
    from . import library
    d = brand_dir() / "logos"
    d.mkdir(exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", (anime or "").lower()).strip("-")
    p = d / (slug + ".png")
    if p.exists() or not slug:
        return p
    words = [w for w in slug.split("-") if len(w) > 2]
    for folder in (d, library.root() / "logos"):
        if folder.is_dir():
            for f in sorted(folder.glob("*.png")):
                name = re.sub(r"[^a-z0-9]+", " ", f.stem.lower())
                if words and all(w in name for w in words):
                    return f
    return p


def save_logo(anime: str, data: bytes) -> Path:
    import io
    with Image.open(io.BytesIO(data)) as im:
        im = im.convert("RGBA")
        im.thumbnail((1600, 800))
        p = logo_path(anime)
        im.save(p)
    return p


def make_badge(text: str, highlight: str, height: int = 64) -> Image.Image:
    """Filigrane « badge » à notre DA : pilule sombre translucide, lettres espacées, une partie en jaune.
    Ex. @ANIME|LORE|HQ avec LORE en jaune."""
    c = rcfg()
    t = text.upper()
    hl = highlight.upper().strip()
    i = t.find(hl) if hl else -1
    parts = [(t[:i], False), (hl, True), (t[i + len(hl):], False)] if i >= 0 else [(t, False)]
    f = font(int(height * 0.42))
    track = height * 0.09                                  # espacement des lettres
    chars = [(ch, on) for seg, on in parts for ch in seg]
    widths = [f.getlength(ch) for ch, _ in chars]
    tw = sum(widths) + track * (len(chars) - 1)
    pad_x = height * 0.55
    W, H = int(tw + 2 * pad_x), height
    scale = 3                                              # dessiné en grand puis réduit : bords nets
    big = Image.new("RGBA", (W * scale, H * scale), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    d.rounded_rectangle((0, 0, W * scale - 1, H * scale - 1), radius=H * scale // 2, fill=(12, 12, 14, 170),
                        outline=(255, 255, 255, 60), width=max(2, scale))
    fb = font(int(height * 0.42 * scale))
    x = pad_x * scale
    accent = c.get("accent_color", "#FFD400")
    for (ch, on), w in zip(chars, widths):
        d.text((x, H * scale / 2), ch, font=fb, anchor="lm", fill=accent if on else (255, 255, 255, 235))
        x += (w + track) * scale
    return big.resize((W, H), Image.LANCZOS)


def badge_image() -> Image.Image | None:
    """Le badge est généré UNE fois (library/_brand/watermark.png) puis réutilisé.
    Pour en changer : supprime le fichier (il sera regénéré) ou remplace-le par ton propre PNG transparent."""
    c = rcfg()
    text = (c.get("watermark") or "").strip()
    if not text:
        return None
    p = brand_dir() / "watermark.png"
    if not p.exists():
        make_badge(text, c.get("watermark_highlight", "")).save(p)
    with Image.open(p) as im:
        return im.convert("RGBA")


def watermark(img: Image.Image, vertical: bool, y_frac: float | None = None) -> Image.Image:
    """Filigrane placé hors des zones cachées par l'interface TikTok/Instagram.
    9:16 : au-dessus de la légende TikTok (bas ≈ 20 % masqué) ; 4:5 : en bas, centré."""
    c = rcfg()
    text = (c.get("watermark") or "").strip()
    if not text:
        return img
    W, H = img.size
    k = W / 1080
    y = int(H * (y_frac if y_frac is not None else (0.74 if vertical else 0.955)))
    alpha = float(c.get("watermark_opacity", 0.6))
    if c.get("watermark_style", "badge") == "badge":
        b = badge_image()
        h = max(20, int(float(c.get("watermark_size", 34)) * 1.6 * k))
        b = b.resize((max(1, int(b.width * h / b.height)), h), Image.LANCZOS)
        if alpha < 1:
            b.putalpha(b.getchannel("A").point(lambda v: int(v * min(1.0, alpha + 0.3))))
        out = img.convert("RGBA")
        out.alpha_composite(b, (int((W - b.width) / 2), y - b.height))
        return out.convert("RGB")
    f = font(max(16, int(float(c.get("watermark_size", 34)) * k)))
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a = int(255 * alpha)
    d.text((W / 2, y), text, font=f, anchor="md", fill=(255, 255, 255, a),
           stroke_width=max(1, int(2 * k)), stroke_fill=(0, 0, 0, int(a * 0.8)))
    return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")


def chart_geometry(W: int, H: int) -> tuple[int, int]:
    """(haut, bas) de la zone du graphique. 9:16 : on reste au-dessus de la légende TikTok (≈ 20 % du bas)."""
    vertical = H / W > 1.5
    return (int(H * 0.50), int(H * 0.78)) if vertical else (int(H * 0.56), int(H * 0.92))


def draw_chart(img: Image.Image, slide: dict, c: dict) -> Image.Image:
    """Note globale + barres par épisode (posts « notes IMDb »)."""
    W, H = img.size
    k = W / 1080
    vertical = H / W > 1.5
    ch = slide["chart"]
    vals = [float(v) for v in ch["values"]]
    labels = list(ch.get("labels") or [f"EP {i}" for i in range(1, len(vals) + 1)])
    top, bottom = chart_geometry(W, H)
    pad = int(c["padding"] * k)
    right_safe = int(110 * k) if vertical else 0

    # Fond : dégradé noir qui monte depuis le bas, pour que tout reste lisible.
    grad = Image.new("L", (1, H), 0)
    start = top - int(H * 0.22)
    for y in range(H):
        grad.putpixel((0, y), int(235 * min(1, max(0, (y - start) / (H * 0.20)))))
    img = Image.composite(Image.new("RGB", (W, H), (8, 8, 10)), img, grad.resize((W, H)))
    draw = ImageDraw.Draw(img)

    # Barres (une par épisode) ; un seul épisode : une jauge sur 10.
    n = len(vals)
    if n == 1:
        x0, x1 = pad + right_safe, W - pad - right_safe     # marges symétriques : tout est centré
        bh = int(70 * k)
        yb = bottom - bh
        draw.rounded_rectangle((x0, yb, x1, bottom), radius=bh // 2, fill=(45, 45, 50))
        fill_w = max(bh, int((x1 - x0) * vals[0] / 10))
        draw.rounded_rectangle((x0, yb, x0 + fill_w, bottom), radius=bh // 2, fill=c["accent_color"])
        tf_ = font(int(40 * k))
        for t in range(0, 11, 2):                       # graduations 0 2 4 6 8 10
            tx = x0 + (x1 - x0) * t / 10
            draw.text((tx, yb - 12 * k), str(t), font=tf_, anchor="md" if 0 < t < 10 else ("ld" if t == 0 else "rd"),
                      fill=(170, 170, 170))
    else:
        x0, x1 = pad + right_safe, W - pad - right_safe
        slot = (x1 - x0) / n
        bw = slot * 0.84
        base = max(0.0, min(vals) - 1.5)
        vf = font(int(min(54 * k, slot * 0.42)))
        lf = font(int(min(30 * k, slot * 0.26)))
        head = int(sum(vf.getmetrics()) + sum(lf.getmetrics()) + 10 * k)
        maxh = (bottom - top) - head
        best = max(vals)
        for i, (lab, v) in enumerate(zip(labels, vals)):
            h = max(int(maxh * 0.08), int(maxh * (v - base) / (10 - base)))
            bx = x0 + i * slot + (slot - bw) / 2
            y_top = bottom - h
            color = c["accent_color"]
            draw.rectangle((bx, y_top, bx + bw, bottom), fill=color)
            cx = bx + bw / 2
            draw.text((cx, y_top - 6 * k), f"{v:.1f}", font=vf, anchor="md",
                      fill=(255, 255, 255) if v != best else color)
            draw.text((cx, y_top - 6 * k - sum(vf.getmetrics())), str(lab), font=lf, anchor="md", fill=(170, 170, 170))

    # Titre + note globale, centrés au-dessus du graphique.
    stroke = int(c["stroke_width"] * k)
    max_w = W - 2 * (pad + right_safe)
    title = (slide.get("text") or "").upper()
    region_top = int(H * (0.12 if vertical else 0.06))
    sf = font(int((260 if len(vals) == 1 else 190) * k))
    s_h = sum(sf.getmetrics())
    tf, lines, lh = layout(title, max_w, int((top - region_top) * 0.45), int(c["cover_font_size_max"] * k * 0.75),
                           int(c["font_size_min"] * k), stroke, draw) if title else (None, [], 0)
    logo = None
    lp = ch.get("logo")
    if lp and Path(lp).exists():
        with Image.open(lp) as li:
            logo = li.convert("RGBA")
        lw = int(max_w * 0.85)
        lh_max = int((top - region_top) * 0.45)
        r = min(lw / logo.width, lh_max / logo.height)
        logo = logo.resize((max(1, int(logo.width * r)), max(1, int(logo.height * r))), Image.LANCZOS)
        if slide.get("kind") == "cover":
            lines, lh = [], 0                               # couverture : le logo remplace le titre
    score = str(ch.get("score") or f"{sum(vals) / n:.1f}")
    src = (ch.get("source") or "").strip()
    if n == 1:                                           # un épisode : sa note, et son numéro en accroche
        score = f"{vals[0]:.1f}"
        if labels[0]:
            src = f"{str(labels[0]).replace('EP', 'EPISODE')}" + (f" · {src.replace(' rating', '')}" if src else "")
    elif src and not ch.get("score_given", True):
        src = "Avg. " + src.replace(" rating", " episode rating")      # moyenne calculée, pas la note officielle
    srcf = font(int(40 * k))
    src_h = int(sum(srcf.getmetrics()) * 1.2) if src else 0
    logo_h = logo.height + int(24 * k) if logo else 0
    block = logo_h + lh * len(lines) + src_h + s_h
    anchor_y = top if n > 1 else bottom - int(H * 0.09)        # un épisode : la note juste au-dessus de la jauge
    y = max(region_top, anchor_y - int(40 * k) - block)
    cx = W / 2
    if logo:
        out = img.convert("RGBA")
        out.alpha_composite(logo, (int(cx - logo.width / 2), int(y)))
        img = out.convert("RGB")
        draw = ImageDraw.Draw(img)
        y += logo_h
    for line in lines:
        draw_rich(img, (cx, y), line, tf, c["text_color"], "ma", stroke, c["stroke_color"])
        y += lh
    draw = ImageDraw.Draw(img)
    if src:
        draw.text((cx, y), src, font=srcf, anchor="ma", fill=c["accent_color"],
                  stroke_width=max(1, stroke // 2), stroke_fill=c["stroke_color"])
        y += src_h
    draw.text((cx, y), score, font=sf, anchor="ma", fill=(255, 255, 255), stroke_width=stroke, stroke_fill=c["stroke_color"])
    return watermark(img, vertical, (bottom / H) + (0.035 if vertical else 0.035))


def balanced_wrap(text: str, f: ImageFont.FreeTypeFont, max_w: int, draw: ImageDraw.ImageDraw) -> list[str]:
    """Même nombre de lignes que wrap(), mais des lignes de longueur égale (pas de mot tout seul en bas)."""
    lines = wrap(text, f, max_w, draw)
    if len(lines) < 2:
        return lines
    lo, hi = 1, max_w
    while lo < hi:                                   # plus petite largeur qui garde le même nombre de lignes
        mid = (lo + hi) // 2
        if len(wrap(text, f, mid, draw)) <= len(lines):
            hi = mid
        else:
            lo = mid + 1
    return wrap(text, f, lo, draw)


def draw_marked(img: Image.Image, cx: float, y: float, line: str, f: ImageFont.FreeTypeFont, fill, accent,
                stroke: int, stroke_fill, on: bool = False, align: str = "center") -> bool:
    """Ligne où *ces mots* sont en couleur d'accent (centrée, ou alignée à gauche / à droite sur cx).
    Rend l'état (dans un *…* ou non) pour la ligne suivante."""
    draw = ImageDraw.Draw(img)
    segs, cur = [], on
    for i, piece in enumerate(line.split("*")):
        if i:
            cur = not cur
        if piece:
            segs.append((piece, cur))
    total = sum(text_width(draw, t, f) for t, _ in segs)
    x = {"left": cx, "right": cx - total}.get(align, cx - total / 2)
    for t, hl in segs:
        draw_rich(img, (x + text_width(draw, t, f) / 2, y), t, f, accent if hl else fill, "ma", stroke, stroke_fill)
        x += text_width(draw, t, f)
    return cur


def draw_news(img: Image.Image, slide: dict, c: dict) -> Image.Image:
    """Carte « NEWS » : badge en haut à droite, en bas « — NEWS — », gros titre, « MORE DETAILS… ▼ »."""
    W, H = img.size
    k = W / 1080
    vertical = H / W > 1.5
    pad = int(c["padding"] * k)
    right_safe = int(110 * k) if vertical else 0
    side = pad + right_safe
    max_w = W - 2 * side
    stroke = int(c["stroke_width"] * k)
    news = slide.get("news") or {}
    tag = (news.get("tag") or c.get("news_tag") or "NEWS").upper()
    sub = news["sub"] if "sub" in news else (c.get("news_sub") or "").upper()
    arrow = news.get("arrow", "sub" not in news)          # ▼ seulement pour « more details in the description »
    bottom = int(H * (0.78 if vertical else 0.93))          # 9:16 : au-dessus de la légende TikTok

    draw = ImageDraw.Draw(img)
    import re as _re2
    parts = [p.strip().upper() for p in _re2.split(r"\||//", slide.get("text") or "") if p.strip()]
    tf, _, _ = layout(" ".join(parts), max_w, int(H * (0.26 if len(parts) > 2 else 0.20)), int(c["cover_font_size_max"] * k * 1.05),
                      int(c["font_size_min"] * k), stroke, draw)
    lines = [l for p in parts for l in balanced_wrap(p, tf, max_w - 2 * stroke, draw)]
    while len(lines) > 1 and max(text_width(draw, l, tf) for l in lines) > max_w and tf.size > 30:
        tf = font(tf.size - 4)
        lines = [l for p in parts for l in balanced_wrap(p, tf, max_w - 2 * stroke, draw)]
    lh = int(sum(tf.getmetrics()) * 1.02)
    # Liste « titre — date » (≥ 2 lignes qui ont toutes un tiret) : titre à gauche, date à droite, une ligne chacun.
    rows = [re.split(r"\s+[—–-]\s+", p, maxsplit=1) for p in parts]
    table = len(rows) >= 2 and all(len(r) == 2 for r in rows)
    if table:
        rf = font(int(c["cover_font_size_max"] * k * 0.62))
        while rf.size > 24:
            widest = max(text_width(draw, a.replace("*", ""), rf) + text_width(draw, b.replace("*", ""), rf) for a, b in rows)
            if widest + 40 * k <= max_w:
                break
            rf = font(rf.size - 2)
        tf, lh = rf, int(sum(rf.getmetrics()) * 1.55)
        lines = rows
    gf, sf = font(int(52 * k)), font(int(34 * k))
    g_h, s_h = int(sum(gf.getmetrics()) * 1.5), int(sum(sf.getmetrics()) * 1.6) if sub else 0
    block = g_h + lh * len(lines) + s_h
    y = bottom - block

    # Dégradé sombre sous le texte.
    grad = Image.new("L", (1, H), 0)
    start = y - int(H * 0.18)
    for yy in range(H):
        grad.putpixel((0, yy), int(225 * min(1, max(0, (yy - start) / (H * 0.16)))))
    img = Image.composite(Image.new("RGB", (W, H), (6, 6, 8)), img, grad.resize((W, H)))
    draw = ImageDraw.Draw(img)

    cx = W / 2
    tw = draw.textlength(tag, font=gf)
    ly = y + g_h * 0.33
    line_w = int(max_w * 0.30)
    for x0, x1 in ((cx - tw / 2 - 24 * k - line_w, cx - tw / 2 - 24 * k), (cx + tw / 2 + 24 * k, cx + tw / 2 + 24 * k + line_w)):
        draw.line((x0, ly, x1, ly), fill=(235, 235, 235), width=max(2, int(3 * k)))
    draw.text((cx, ly), tag, font=gf, anchor="mm", fill=(255, 255, 255))
    y += g_h
    state = False
    if table:
        x0, x1 = side, W - side
        for i, (a, b) in enumerate(lines):
            ty = y + (lh - sum(tf.getmetrics())) / 2
            draw_marked(img, x0, ty, a, tf, c["text_color"], c["accent_color"], stroke, c["stroke_color"], align="left")
            draw_marked(img, x1, ty, b, tf, c["text_color"], c["accent_color"], stroke, c["stroke_color"], align="right")
            if i < len(lines) - 1:
                ImageDraw.Draw(img).line((x0, y + lh, x1, y + lh), fill=(110, 110, 115), width=max(1, int(2 * k)))
            y += lh
    else:
        for line in lines:
            state = draw_marked(img, cx, y, line, tf, c["text_color"], c["accent_color"], stroke, c["stroke_color"], state)
            y += lh
    draw = ImageDraw.Draw(img)
    if sub:
        sy = y + s_h * 0.30
        right = sub.rstrip().endswith(("→", "->"))           # « SWIPE FOR MORE → » : flèche dessinée (pas un glyphe)
        if right:
            sub = sub.rstrip().rstrip("→").rstrip("->").rstrip()
        draw_marked(img, cx, sy, sub, sf, (235, 235, 235), c["accent_color"], max(1, stroke // 3), c["stroke_color"])
        draw = ImageDraw.Draw(img)
        if right:
            t = 13 * k
            ax = cx + text_width(draw, sub.replace("*", ""), sf) / 2 + 14 * k
            ay = sy + sum(sf.getmetrics()) * 0.45
            draw.polygon([(ax, ay - t), (ax, ay + t), (ax + t * 1.2, ay)], fill=(235, 235, 235))
        elif arrow:
            ty = sy + sum(sf.getmetrics()) + 8 * k
            t = 14 * k
            draw.polygon([(cx - t, ty), (cx + t, ty), (cx, ty + t * 1.1)], fill=(235, 235, 235))

    # Badge du compte en haut à droite (zone libre de l'interface).
    if (c.get("watermark") or "").strip() and c.get("watermark_style", "badge") == "badge":
        b = badge_image()
        h = int(float(c.get("watermark_size", 34)) * 1.9 * k)
        b = b.resize((max(1, int(b.width * h / b.height)), h), Image.LANCZOS)
        out = img.convert("RGBA")
        out.alpha_composite(b, (W - pad - b.width, int(H * (0.11 if vertical else 0.04))))
        return out.convert("RGB")
    return watermark(img, vertical, 0.10)


def draw_slide(slide: dict, W: int, H: int, out: Path, slideshow_id: int = 0, fallback: str | None = None) -> Path:
    c = rcfg()
    pad, stroke = int(c["padding"] * W / 1080), int(c["stroke_width"] * W / 1080)
    path = slide.get("image_path")
    if path and Path(path).exists():
        with Image.open(path) as src:
            img = smart_crop(src.convert("RGB"), W, H)
    elif fallback and Path(fallback).exists():
        # Couverture / fin sans image : une image du slideshow, floutée et assombrie.
        with Image.open(fallback) as src:
            img = smart_crop(src.convert("RGB"), W, H).filter(ImageFilter.GaussianBlur(int(28 * W / 1080)))
        img = Image.blend(img, Image.new("RGB", (W, H), (0, 0, 0)), 0.45)
    else:  # aucune image du tout : fond sombre neutre
        img = Image.new("RGB", (W, H), (22, 22, 28))

    if slide.get("twin") and H / W <= 1.5:                # Instagram : on montre le wallpaper entier
        img = draw_phone_fit(slide, W, H)
        tmp = out.with_suffix(".tmp.jpg")
        img.save(tmp, "JPEG", quality=int(c.get("jpeg_quality", 90)), optimize=True)
        safe_replace(tmp, out)
        return out

    if slide.get("lock") is not None or slide.get("plain"):
        img = draw_lock_carousel(slide, W, H) if slide.get("lock") is not None else draw_plain_title(img, slide["text"], c)
        if slide.get("plain"):                            # wallpapers : le logo seulement sur la couverture
            img = watermark(img, H / W > 1.5)
        tmp = out.with_suffix(".tmp.jpg")
        img.save(tmp, "JPEG", quality=int(c.get("jpeg_quality", 90)), optimize=True)
        safe_replace(tmp, out)
        return out

    if (slide.get("chart") or {}).get("values") or slide.get("news") is not None:
        img = draw_chart(img, slide, c) if slide.get("chart") else draw_news(img, slide, c)
        tmp = out.with_suffix(".tmp.jpg")
        img.save(tmp, "JPEG", quality=int(c.get("jpeg_quality", 90)), optimize=True)
        safe_replace(tmp, out)
        return out

    is_cover = slide["kind"] == "cover"
    text = slide["text"].upper() if is_cover else slide["text"]
    label = slide.get("label") or ""
    vertical = H / W > 1.5
    right_safe = int(110 * W / 1080) if vertical else 0      # icônes TikTok/Shorts à droite
    max_w = W - 2 * (pad + right_safe)                        # même marge des deux côtés : texte centré
    draw = ImageDraw.Draw(img)
    k = W / 1080
    f, lines, lh = layout(text, max_w, int(H * (0.42 if is_cover else 0.38)),
                          int((c["cover_font_size_max"] if is_cover else c["font_size_max"]) * k),
                          int(c["font_size_min"] * k), stroke, draw)
    lf = font(int(f.size * 0.95)) if label else None
    l_h = int(sum(lf.getmetrics()) * 1.15) if lf else 0
    cta = (c.get("end_cta") or "").strip() if slide["kind"] == "end" else ""
    cf = font(max(int(c["font_size_min"] * k), int(f.size * 0.7))) if cta else None
    cta_lines = wrap(cta, cf, max_w - 2 * stroke, draw) if cta else []
    c_lh = int(sum(cf.getmetrics()) * 1.08) if cf else 0
    gap = int(lh * 0.6) if cta and lines else 0
    block_h = l_h + lh * len(lines) + gap + c_lh * len(cta_lines)
    pos = c.get("text_position", "middle")
    if vertical and pos == "bottom":
        pos = "middle"                                   # le bas est masqué par l'interface TikTok
    y0 = {"top": int(H * 0.12), "bottom": H - pad - block_h - int(H * 0.06)}.get(pos, (H - block_h) // 2)
    cx = W / 2

    # Lisibilité : assombrit doucement une bande derrière le texte (rien à assombrir sans texte).
    op = float(c.get("shade_opacity", 0)) if (lines or label) else 0
    if c.get("text_style") == "box" and (lines or label):
        box_w = max([text_width(draw, l, f) for l in lines] + [text_width(draw, label, lf) if lf else 0])
        x0b, x1b = int(cx - box_w / 2 - pad / 2), int(cx + box_w / 2 + pad / 2)
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(overlay).rounded_rectangle((x0b, y0 - pad // 2, x1b, y0 + block_h + pad // 2),
                                                  radius=int(24 * k), fill=(0, 0, 0, int(255 * max(op, 0.55))))
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(img)
        stroke_eff = 0
    else:
        if op > 0:
            band = Image.new("L", (W, H), 0)
            ImageDraw.Draw(band).rectangle((0, y0 - pad, W, y0 + block_h + pad), fill=int(255 * op))
            band = band.filter(ImageFilter.GaussianBlur(int(60 * k)))
            img = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), img, band)
            draw = ImageDraw.Draw(img)
        stroke_eff = stroke

    y = y0
    if lf:
        draw_rich(img, (cx, y), label, lf, c["accent_color"], "ma", stroke_eff, c["stroke_color"])
        y += l_h
    for line in lines:
        draw_rich(img, (cx, y), line, f, c["text_color"], "ma", stroke_eff, c["stroke_color"])
        y += lh
    y += gap
    for line in cta_lines:                                # « Follow @… for more » sur la dernière slide
        draw_rich(img, (cx, y), line, cf, c["accent_color"], "ma", stroke_eff, c["stroke_color"])
        y += c_lh

    if not slide.get("twin") and not slide.get("wallpaper"):   # wallpapers : logo seulement sur la couverture
        img = watermark(img, vertical)
    tmp = out.with_suffix(".tmp.jpg")
    img.save(tmp, "JPEG", quality=int(c.get("jpeg_quality", 90)), optimize=True)
    safe_replace(tmp, out)
    return out


def slide_paths(slideshow_id: int, fmt: str) -> list[Path]:
    d = out_dir(slideshow_id) / fmt
    return sorted(d.glob("[0-9][0-9].jpg"))


def render_slide(slideshow_id: int, index: int) -> None:
    s = db.get("slideshows", slideshow_id)
    slide = s["slides"][index]
    fallback = None
    if slide["kind"] in ("cover", "end") and not slide.get("image_path"):
        pool = [sl.get("image_path") for sl in s["slides"] if sl.get("image_path")]
        fallback = (pool[-1] if slide["kind"] == "end" else pool[0]) if pool else None
    if slide.get("lock") is not None:                     # aperçu : les wallpapers d'avant et d'après dépassent
        locks = [i for i, x in enumerate(s["slides"]) if x.get("lock") is not None]
        k = locks.index(index)
        slide = {**slide, "_prev": s["slides"][locks[k - 1]].get("image_path") if k > 0 else None,
                 "_next": s["slides"][locks[k + 1]].get("image_path") if k + 1 < len(locks) else None,
                 "_pos": k, "_total": len(locks)}
    for fmt, (W, H) in rcfg()["sizes"].items():
        d = out_dir(slideshow_id) / fmt
        d.mkdir(exist_ok=True)
        draw_slide(slide, int(W), int(H), d / f"{index + 1:02d}.jpg", slideshow_id, fallback)
    db.update("slideshows", slideshow_id, render_needed=1)    # la vidéo devra être refaite
    if slide["kind"] == "body" and s["format"] in GRID_FORMATS:
        render_grid(slideshow_id)


def render_all(slideshow_id: int) -> None:
    s = db.get("slideshows", slideshow_id)
    for fmt in rcfg()["sizes"]:
        d = out_dir(slideshow_id) / fmt
        d.mkdir(exist_ok=True)
        for old in d.glob("*.jpg"):                         # le nombre de slides peut avoir changé
            if not old.stem.isdigit() or int(old.stem) > len(s["slides"]):
                old.unlink(missing_ok=True)
    for i in range(len(s["slides"])):
        render_slide(slideshow_id, i)
    render_grid(slideshow_id)


# --- grille (une seule image : « ton mois = ton perso ») ------------------------------------

GRID_FORMATS = {"assign", "zodiac"}


def render_grid(slideshow_id: int) -> list[Path]:
    """3 colonnes × 4 lignes avec l'étiquette (mois, signe) de chaque case ; titre en haut si la place le permet."""
    s = db.get("slideshows", slideshow_id)
    body = [sl for sl in s["slides"] if sl["kind"] == "body"]
    if s["format"] not in GRID_FORMATS or not body:
        return []
    c = rcfg()
    cols = 3
    rows = -(-len(body) // cols)
    outs = []
    for fmt, (W, H) in c["sizes"].items():
        W, H = int(W), int(H)
        title_h = int(H * 0.16) if H / W > 1.5 else 0          # 9:16 : bandeau titre ; 4:5 : grille pleine
        cw, ch = W // cols, (H - title_h) // rows
        img = Image.new("RGB", (W, H), (12, 12, 16))
        draw = ImageDraw.Draw(img)
        k = W / 1080
        stroke = max(3, int(c["stroke_width"] * k * 0.8))
        labels = [(sl.get("label") or "").strip() for sl in body]
        lf = font(int(min(cw * 0.22, ch * 0.16)))            # même taille pour toutes les cases
        while any(text_width(draw, l, lf) > cw - 16 for l in labels) and lf.size > 18:
            lf = font(lf.size - 2)
        for i, sl in enumerate(body):
            x, y = (i % cols) * cw, title_h + (i // cols) * ch
            p = sl.get("image_path")
            if p and Path(p).exists():
                with Image.open(p) as src:
                    img.paste(smart_crop(src.convert("RGB"), cw - 2, ch - 2), (x + 1, y + 1))
            if labels[i]:
                draw_rich(img, (x + cw / 2, y + ch - 14 * k), labels[i], lf, c["text_color"], "md", stroke,
                          c["stroke_color"])
        if title_h:
            cover = next((sl for sl in s["slides"] if sl["kind"] == "cover"), None)
            text = (cover["text"] if cover else s["topic"]).upper()
            f, lines, lh = layout(text, W - 2 * int(40 * k), title_h - int(20 * k), int(78 * k), int(36 * k),
                                  stroke, draw)
            y = (title_h - lh * len(lines)) // 2
            for line in lines:
                draw_rich(img, (W / 2, y), line, f, c["text_color"], "ma", stroke, c["stroke_color"])
                y += lh
        img = watermark(img, False)
        out = out_dir(slideshow_id) / f"grid_{fmt}.jpg"
        tmp = out.with_suffix(".tmp.jpg")
        img.save(tmp, "JPEG", quality=int(c.get("jpeg_quality", 90)), optimize=True)
        safe_replace(tmp, out)
        outs.append(out)
    return outs


# --- Short vidéo -----------------------------------------------------------------------

def durations(slides: list[dict]) -> list[float]:
    v = config.get()["slides"]["video"]
    out = []
    for s in slides:
        base = {"cover": v["cover_seconds"], "end": v["end_seconds"]}.get(s["kind"], v["seconds_per_slide"])
        extra = max(0, len(s["text"].split()) - 12) * 0.12         # texte long : un peu plus de temps
        out.append(round(float(base) + extra, 2))
    return out


def video_auto() -> bool:
    """La vidéo est-elle fabriquée automatiquement avec chaque slideshow ? (sinon : sur demande)"""
    v = config.get()["slides"]["video"]
    return bool(v.get("auto", v.get("enabled", False)))


def has_video(slideshow_id: int) -> bool:
    return (out_dir(slideshow_id) / "short.mp4").exists()


def render_video(slideshow_id: int, force: bool = False) -> Path:
    s = db.get("slideshows", slideshow_id)
    out = out_dir(slideshow_id) / "short.mp4"
    if out.exists() and not s["render_needed"] and not force:
        return out
    v = config.get()["slides"]["video"]
    imgs = slide_paths(slideshow_id, "vertical")
    if len(imgs) != len(s["slides"]):
        render_all(slideshow_id)
        imgs = slide_paths(slideshow_id, "vertical")
    W, H = (int(x) for x in rcfg()["sizes"]["vertical"])
    fps, fade, z = int(v["fps"]), float(v["crossfade"]), float(v.get("zoom", 1.0))
    durs = durations(s["slides"])
    cmd = [require_bin("ffmpeg"), "-y", "-v", "error"]
    for p in imgs:
        cmd += ["-i", str(p)]
    parts = []
    for i, d in enumerate(durs):
        n = max(1, round((d + fade) * fps))
        zexpr = f"1+{z - 1:.4f}*on/{n}" if z > 1 else "1"
        parts.append(f"[{i}:v]scale={W * 2}:{H * 2},zoompan=z='{zexpr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                     f":d={n}:s={W}x{H}:fps={fps},trim=duration={d + fade:.3f},setsar=1,format=yuv420p[v{i}]")
    # Chaque plan dure d+fondu ; le fondu i démarre à la fin cumulée des plans précédents moins le fondu.
    lens = [d + fade for d in durs]
    last, acc = "v0", lens[0]
    for i in range(1, len(durs)):
        parts.append(f"[{last}][v{i}]xfade=transition=fade:duration={fade}:offset={acc - fade:.3f}[x{i}]")
        acc += lens[i] - fade
        last = f"x{i}"
    total = acc
    music = library.music_files()
    if music:
        track = random.Random(slideshow_id).choice(music)
        cmd += ["-stream_loop", "-1", "-i", str(track)]
        a = len(imgs)
        parts.append(f"[{a}:a]atrim=0:{total:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=0.4,"
                     f"afade=t=out:st={max(0, total - 1.2):.3f}:d=1.2,loudnorm=I={v['music_lufs']}:TP=-1.5,"
                     f"aresample=48000[aout]")
    else:
        cmd += ["-f", "lavfi", "-t", f"{total:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
        parts.append(f"[{len(imgs)}:a]anull[aout]")
    tmp = out.with_name("short.tmp.mp4")
    cmd += ["-filter_complex", ";".join(parts), "-map", f"[{last}]", "-map", "[aout]",
            "-t", f"{total:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-r", str(fps), "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(tmp)]
    log.info("slideshow %s : Short %.1f s (%d slides)", slideshow_id, total, len(imgs))
    run(cmd)
    safe_replace(tmp, out)
    db.update("slideshows", slideshow_id, video_path=str(out), render_needed=0)
    return out


# Positions (fractions de l'image) du filigrane anti-vol des vidéos : il change de place toutes les quelques secondes
# (comme celui de TikTok) → impossible de le recadrer ou de le flouter d'un seul coup. Toujours hors des zones
# cachées par TikTok / Instagram (icônes à droite ≈ 15 %, légende en bas ≈ 20 %).
VIDEO_WM_SPOTS = [(0.50, 0.805), (0.17, 0.46), (0.50, 0.805), (0.17, 0.66)]   # surtout en bas, au centre


def stamp_video(src: Path, dst: Path | None = None, every: float = 6.0, crf: int = 20) -> Path:
    """Filigrane anti-vol sur une vidéo finie (demandé le 02/11 : « mets notre overlay, comme ça personne ne les
    vole ») : le badge @animelorehq, semi-transparent, qui saute d'une position à l'autre toutes les `every` s.
    Son copié tel quel. `dst` = None → remplace le fichier."""
    import subprocess
    import tempfile

    from ..util import require_bin
    src = Path(src)
    c = rcfg()
    b = badge_image()
    if b is None:
        return src
    with subprocess.Popen([require_bin("ffprobe"), "-v", "error", "-select_streams", "v:0", "-show_entries",
                           "stream=width", "-of", "csv=p=0", str(src)], stdout=subprocess.PIPE, text=True) as pr:
        W = int((pr.stdout.read() or "1080").strip() or 1080)
    k = W / 1080
    h = max(16, int(float(c.get("watermark_size", 34)) * 1.25 * k))      # petit : ne gêne pas la vue
    b = b.resize((max(1, int(b.width * h / b.height)), h), Image.LANCZOS)
    alpha = float(c.get("video_watermark_opacity", 0.5))
    b.putalpha(b.getchannel("A").point(lambda v: int(v * alpha)))
    n = len(VIDEO_WM_SPOTS)
    cycle = every * n
    xs = ys = ""
    for i, (fx, fy) in enumerate(VIDEO_WM_SPOTS):          # if(lt(mod(t,C),6),X0,if(lt(mod(t,C),12),X1,…))
        last = i == n - 1
        cond = f"lt(mod(t,{cycle}),{every * (i + 1)})"
        xi, yi = f"main_w*{fx}-overlay_w/2", f"main_h*{fy}-overlay_h"
        xs += xi if last else f"if({cond},{xi},"
        ys += yi if last else f"if({cond},{yi},"
    xs += ")" * (n - 1)
    ys += ")" * (n - 1)
    out = Path(dst) if dst else src.with_suffix(".wm.mp4")
    with tempfile.TemporaryDirectory() as td:
        bp = Path(td) / "wm.png"
        b.save(bp)
        subprocess.run([require_bin("ffmpeg"), "-y", "-loglevel", "error", "-i", str(src), "-i", str(bp),
                        "-filter_complex", f"[0:v][1:v]overlay=x='{xs}':y='{ys}':format=auto",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf), "-pix_fmt", "yuv420p",
                        "-c:a", "copy", "-movflags", "+faststart", str(out)], check=True)
    if dst is None:
        out.replace(src)
        return src
    return out


def like_follow(img: Image.Image, cx: float, y: float, a: float = 1.0) -> None:
    """Pilule « Like ❤️ & Follow » de l'accroche (demandé le 02/11 : « à chaque début on demande de like et follow,
    sur l'écran où on voit les 2 persos »). `a` = 0→1 : petit « pop » d'apparition. Texte : `slides.render.like_cta`."""
    c = rcfg()
    txt = c.get("like_cta", "Like ❤️ & Follow for more")
    if not txt or a <= 0:
        return
    W = img.width
    k = W / 1080
    pop = 1 + 0.35 * max(0.0, 1 - a / 0.35)
    f = font(int(50 * k * pop))
    d = ImageDraw.Draw(img)
    tw = d.textlength(txt.replace("❤️", "  "), font=f) + 70 * k
    h = 84 * k * pop
    d.rounded_rectangle((cx - tw / 2, y, cx + tw / 2, y + h), radius=h / 2, fill=(14, 14, 20),
                        outline=(255, 50, 80), width=max(3, int(5 * k)))
    draw_rich(img, (cx, y + h * 0.18), txt, f, (255, 255, 255), "ma", int(3 * k), (0, 0, 0))
