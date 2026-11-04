"""« Guess the anime character » (04/11, pour lancer TikTok / Instagram) : on ne voit que les YEUX du perso,
compte à rebours 3-2-1, puis la tête entière + son nom. 5 persos du plus facile au plus dur, ~20 s.
Image 0 = couverture (titre + 1ers yeux déjà visibles). Fin : « How many did you get? Comment 👇 ».

`generate(rounds=[{"name", "image_path", "eye_y"}])` : `eye_y` = hauteur des yeux dans le carré de la tête
(0 = haut, 1 = bas ; faces.head_square), réglée à la main par perso."""
from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from .. import config, db
from ..util import log, require_bin
from . import faces, fusion, render

W, H, FPS = 1080, 1920, 30
GUESS_S, REVEAL_S, END_S = 2.7, 1.1, 1.6
YELLOW = (255, 214, 10)


def _ease(a: float) -> float:
    a = max(0.0, min(1.0, a))
    return 1 - (1 - a) ** 3


def _back(a: float) -> float:
    a = max(0.0, min(1.0, a))
    c = 1.70158
    return 1 + (c + 1) * (a - 1) ** 3 + c * (a - 1) ** 2


def generate(rounds: list[dict], title: str = "GUESS THE ANIME CHARACTER", out: Path | None = None) -> Path:
    k = W / 1080
    heads = []
    for r in rounds:
        im = Image.open(r["image_path"]).convert("RGB")
        heads.append(faces.head_square(im, r["image_path"]).resize((900, 900), Image.LANCZOS))
    bg = Image.new("RGB", (W, H), (14, 12, 24))
    d0 = ImageDraw.Draw(bg)
    for i in range(0, H, 6):                                    # dégradé léger + lignes
        c = int(14 + 18 * (1 - abs(i - H * 0.45) / (H * 0.6)))
        d0.line((0, i, W, i), fill=(c, max(0, c - 4), c + 14), width=6)
    tf = render.font(int(82 * k))
    sf = render.font(int(46 * k))
    nf = render.font(int(96 * k))
    cf = render.font(int(150 * k))
    n = len(rounds)
    pw, ph = int(W * 0.9), int(W * 0.9 * 0.36)                  # bandeau des yeux
    px, py = (W - pw) // 2, int(H * 0.36)
    mask_band = Image.new("L", (pw, ph), 0)
    ImageDraw.Draw(mask_band).rounded_rectangle((0, 0, pw - 1, ph - 1), radius=int(34 * k), fill=255)
    out = out or config.data_dir() / "fusions" / "guess.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".video.mp4")
    ffmpeg = require_bin("ffmpeg")
    proc = subprocess.Popen([ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
                             "-crf", "20", "-pix_fmt", "yuv420p", str(tmp)], stdin=subprocess.PIPE)
    per = GUESS_S + REVEAL_S
    total = n * per + END_S
    ticks, dings = [], []
    try:
        for fi in range(int(total * FPS)):
            t = fi / FPS
            img = bg.copy()
            d = ImageDraw.Draw(img)
            ri = min(n - 1, int(t // per))
            lt = t - ri * per
            ended = t >= n * per
            # titre (toujours visible, image 0 comprise)
            y = int(H * 0.045)
            for line in render.wrap(title, tf, int(W * 0.92), d):
                d.text((W / 2, y), line, font=tf, anchor="ma", fill=(255, 255, 255), stroke_width=int(5 * k),
                       stroke_fill=(0, 0, 0))
                y += int(92 * k)
            render.draw_rich(img, (W / 2, y + 8 * k), "Only 1% get 5/5 😳", sf, YELLOW, "ma", int(4 * k), (0, 0, 0))
            d = ImageDraw.Draw(img)
            if not ended:
                # numéro + points de progression
                d.text((W / 2, py - 90 * k), f"#{ri + 1}/{n}", font=render.font(int(64 * k)), anchor="mm",
                       fill=(200, 200, 220), stroke_width=int(4 * k), stroke_fill=(0, 0, 0))
                for j in range(n):
                    cx = W / 2 + (j - (n - 1) / 2) * 46 * k
                    col = YELLOW if j < ri or (j == ri and lt >= GUESS_S) else ((255, 255, 255) if j == ri else (70, 70, 90))
                    d.ellipse((cx - 11 * k, py - 40 * k, cx + 11 * k, py - 18 * k), fill=col)
                head = heads[ri]
                r = rounds[ri]
                if lt < GUESS_S:                                # les yeux seulement
                    ey = float(r.get("eye_y", 0.42)) * 900
                    zoom = 1.0 + 0.06 * lt / GUESS_S
                    bh = 900 * 0.36 / zoom * (ph / pw) / 0.36
                    bw = 900 / zoom
                    x0 = (900 - bw) / 2
                    band = head.crop((int(x0), int(ey - bh / 2), int(x0 + bw), int(ey + bh / 2))).resize((pw, ph))
                    panel = Image.new("RGB", (pw, ph), (0, 0, 0))
                    panel.paste(band, (0, 0))
                    img.paste(panel, (px, py), mask_band)
                    d = ImageDraw.Draw(img)
                    d.rounded_rectangle((px - 6, py - 6, px + pw + 6, py + ph + 6), radius=int(38 * k),
                                        outline=(255, 255, 255), width=int(6 * k))
                    # compte à rebours 3-2-1
                    sec = 3 - int(lt / (GUESS_S / 3))
                    a = (lt % (GUESS_S / 3)) / (GUESS_S / 3)
                    if a < 1 / FPS * 1.5 and sec >= 1:
                        ticks.append(t)
                    cy_ = py + ph + 260 * k
                    R = 130 * k
                    d.ellipse((W / 2 - R, cy_ - R, W / 2 + R, cy_ + R), fill=(20, 20, 30), outline=(255, 255, 255),
                              width=int(8 * k))
                    d.arc((W / 2 - R, cy_ - R, W / 2 + R, cy_ + R), -90, -90 + 360 * (1 - a), fill=(255, 70, 70),
                          width=int(14 * k))
                    sz = int(150 * k * (1.25 - 0.25 * _ease(a * 3)))
                    d.text((W / 2, cy_), str(max(1, sec)), font=render.font(sz), anchor="mm", fill=(255, 255, 255),
                           stroke_width=int(6 * k), stroke_fill=(0, 0, 0))
                    render.draw_rich(img, (W / 2, cy_ + R + 40 * k), "Who is it? 🤔", sf, (255, 255, 255), "ma",
                                     int(4 * k), (0, 0, 0))
                    d = ImageDraw.Draw(img)
                else:                                           # la réponse : la tête entière + le nom
                    b = lt - GUESS_S
                    if b < 1 / FPS * 1.5:
                        dings.append(t)
                    s = _back(b / 0.35)
                    D = int(W * 0.62 * max(0.05, s))
                    ic = fusion.icon(r["image_path"], max(8, D), YELLOW)
                    cy_ = py + ph / 2 + 120 * k
                    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                    ImageDraw.Draw(glow).ellipse((W / 2 - D * 0.62, cy_ - D * 0.62, W / 2 + D * 0.62, cy_ + D * 0.62),
                                                 fill=YELLOW + (110,))
                    glow = glow.filter(ImageFilter.GaussianBlur(40 * k))
                    img = Image.alpha_composite(img.convert("RGBA"), glow)
                    img.alpha_composite(ic, (int(W / 2 - ic.width / 2), int(cy_ - ic.height / 2)))
                    img = img.convert("RGB")
                    d = ImageDraw.Draw(img)
                    a = min(1.0, b / 0.25)
                    f_ = render.font(int(96 * k * (1.3 - 0.3 * a)))
                    d.text((W / 2, cy_ + W * 0.36), r["name"].upper(), font=f_, anchor="mm", fill=YELLOW,
                           stroke_width=int(6 * k), stroke_fill=(0, 0, 0))
                    if b < 0.12:                                # petit flash blanc
                        img = Image.blend(img, Image.new("RGB", img.size, (255, 255, 255)), 0.6 * (1 - b / 0.12))
            else:                                               # fin : le score en commentaire
                e = t - n * per
                a = _back(e / 0.35)
                f_ = render.font(int(88 * k * max(0.1, a)))
                d.text((W / 2, H * 0.42), "HOW MANY", font=f_, anchor="mm", fill=(255, 255, 255),
                       stroke_width=int(6 * k), stroke_fill=(0, 0, 0))
                d.text((W / 2, H * 0.42 + 105 * k), "DID YOU GET?", font=f_, anchor="mm", fill=YELLOW,
                       stroke_width=int(6 * k), stroke_fill=(0, 0, 0))
                render.draw_rich(img, (W / 2, H * 0.58), "Comment your score 👇", render.font(int(62 * k)),
                                 (255, 255, 255), "ma", int(4 * k), (0, 0, 0))
            proc.stdin.write(img.convert("RGB").tobytes())
        proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError("ffmpeg a échoué")
    finally:
        if proc.poll() is None:
            proc.kill()
    import numpy as np
    from . import domain
    rate = fusion.RATE
    na = int(total * rate) + rate
    audio = np.zeros(na, dtype=np.float32)

    def put(tt, x, g):
        i = int(tt * rate)
        if x is not None and 0 <= i < na:
            seg = x[: na - i]
            audio[i:i + len(seg)] += seg * g
    tick = domain.sfx("tick")
    ding = domain.sfx("win")
    pop = domain.sfx("hit", mode="auto", seed=1)
    for tt in ticks:
        put(tt, tick, 0.6)
    for tt in dings:
        put(tt, pop, 0.5)
        put(tt + 0.02, ding[: int(rate * 1.2)], 0.7)
    put(n * per, ding, 0.6)
    lvl = float(np.percentile(np.abs(audio), 99.7)) or 1.0
    audio = np.tanh(audio * min(1.0, 0.75 / lvl) * 1.1) / math.tanh(1.1) * float(fusion.fcfg().get("volume", 0.13)) * 2.2
    wav = out.with_suffix(".wav")
    fusion.write_wav(wav, audio)
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(tmp), "-i", str(wav), "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "160k", "-shortest", str(out)], check=True)
    tmp.unlink(missing_ok=True)
    wav.unlink(missing_ok=True)
    meta = {"kind": "guess", "title": "Guess the anime character from their eyes", "names": [r["name"] for r in rounds],
            "seconds": round(total, 1), "created_at": db.now()}
    out.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    from .domain import _brand_video
    _brand_video(out)
    log.info("guess : %d persos → %s", len(rounds), out.name)
    return out
