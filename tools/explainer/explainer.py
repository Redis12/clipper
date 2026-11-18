"""« If you had … » (18/11) : explication animée d'un pouvoir, voix off (Adam, ElevenLabs, fournie par l'utilisateur),
sous-titres mot par mot, notre mascotte originale (mascot.py) et les images de l'anime fournies par l'utilisateur.

python3 tools/explainer/explainer.py <script.json> <sortie.mp4> [voix.mp3]
Sans voix : brouillon (temps estimés, pas de voix) pour vérifier les images.
Avec voix : les phrases sont calées sur les silences de l'audio (une phrase du script = un morceau de voix),
les mots répartis dans la phrase selon leur longueur.
"""
from __future__ import annotations

import json
import math
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))
from clipper.slides import fusion, render  # noqa: E402
from mascot import mascot  # noqa: E402

W, H, FPS = 1080, 1920, 30
CX0, CY0, CX1, CY1 = 70, 270, 1010, 900           # carte (image de la scène)
FONT = str(ROOT / "tools/money_sim/fonts/anton.woff2")
HY = ROOT / "library/_sfx/Helton Yan's Old-School Shonen SFX"
RATE = fusion.RATE
YELLOW = (255, 214, 60)


def F(sz):
    return ImageFont.truetype(FONT, int(sz))


def ease_back(x):
    c1, c3 = 1.70158, 2.70158
    x = min(1.0, max(0.0, x))
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


# --------------------------------------------------------------------------- images

def key_image_np(im: Image.Image, mode: str | None) -> Image.Image:
    """Détoure un fond blanc ou un faux damier gris relié au bord (sans scipy : remplissage par vagues)."""
    im = im.convert("RGBA")
    if not mode:
        return im
    a = np.asarray(im).astype(np.float32)
    rgb = a[..., :3]
    mx, mn = rgb.max(2), rgb.min(2)
    sat = (mx - mn) / (mx + 1e-6)
    cand = (mn > 205) if mode == "white" else ((sat < 0.14) & (mx < 125))
    reach = np.zeros_like(cand)
    reach[0, :], reach[-1, :], reach[:, 0], reach[:, -1] = cand[0, :], cand[-1, :], cand[:, 0], cand[:, -1]
    for _ in range(400):                                # propagation depuis les bords
        n = reach.copy()
        n[1:] |= reach[:-1]; n[:-1] |= reach[1:]; n[:, 1:] |= reach[:, :-1]; n[:, :-1] |= reach[:, 1:]
        n &= cand
        if (n == reach).all():
            break
        reach = n
    alpha = np.where(reach, 0, 255).astype(np.uint8)
    out = Image.fromarray(np.dstack([rgb.astype(np.uint8), alpha]), "RGBA")
    out.putalpha(out.getchannel("A").filter(ImageFilter.GaussianBlur(1.5)))
    return out


def cover(im: Image.Image, w: int, h: int, zoom: float, center=(0.5, 0.5)) -> Image.Image:
    iw, ih = im.size
    s = max(w / iw, h / ih) * zoom
    nw, nh = int(iw * s), int(ih * s)
    big = im.resize((nw, nh), Image.LANCZOS)
    x = int(min(max(0, center[0] * nw - w / 2), nw - w))
    y = int(min(max(0, center[1] * nh - h / 2), nh - h))
    return big.crop((x, y, x + w, y + h))


# --------------------------------------------------------------------------- temps

def words_of(text):
    return text.split()


def estimate_timing(lines):
    t, out = 0.25, []
    for ln in lines:
        n = len(words_of(ln["text"]))
        d = 0.33 * n + 0.15
        out.append((t, t + d))
        t += d + 0.35
    return out


def voice_timing(voice: Path, lines):
    """Segments de voix (silences ≥ 0,22 s) → une phrase par segment (on fusionne les plus courts si trop)."""
    r = subprocess.run(["ffmpeg", "-i", str(voice), "-af", "silencedetect=n=-38dB:d=0.22", "-f", "null", "-"],
                       capture_output=True, text=True)
    dur = float(re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr).groups()[2]) + \
        60 * float(re.search(r"Duration: (\d+):(\d+):", r.stderr).groups()[1])
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    segs, cur = [], 0.0
    for s, e in zip(starts, ends):
        if s - cur > 0.15:
            segs.append([cur, s])
        cur = e
    if dur - cur > 0.15:
        segs.append([cur, dur])
    # autant de segments que de phrases : on fusionne les deux voisins les plus proches
    while len(segs) > len(lines):
        gaps = [segs[i + 1][0] - segs[i][1] for i in range(len(segs) - 1)]
        i = int(np.argmin(gaps))
        segs[i][1] = segs.pop(i + 1)[1]
    if len(segs) < len(lines):                         # pas assez de silences : partage au prorata des mots
        tot = sum(len(words_of(l["text"])) for l in lines)
        a, b = segs[0][0], segs[-1][1]
        segs, t = [], a
        for l in lines:
            d = (b - a) * len(words_of(l["text"])) / tot
            segs.append([t, t + d])
            t += d
    return [tuple(s) for s in segs], dur


def word_times(text, a, b):
    ws = words_of(text)
    wts = [len(re.sub(r"\W", "", w)) + 2 for w in ws]
    tot = sum(wts)
    out, t = [], a
    for w, k in zip(ws, wts):
        d = (b - a) * k / tot
        out.append((w, t, t + d))
        t += d
    return out


# --------------------------------------------------------------------------- rendu

class Scene:
    def __init__(self, script, base: Path):
        self.s = script
        self.base = base
        self.cache = {}
        self.bg = self._bg()
        self.acc = tuple(script.get("accent", YELLOW))
        self.kw = {k.lower() for k in script.get("keywords", [])}

    def _bg(self):
        yy, xx = np.mgrid[0:H, 0:W]
        px = np.zeros((H, W, 3), np.float32) + np.array([16, 12, 30], np.float32)
        for cx, cy, r, c in ((0.2, 0.15, 600, (60, 40, 140)), (0.85, 0.6, 620, (30, 70, 140)), (0.4, 1.0, 600, (90, 30, 90))):
            g = np.exp(-(((xx - cx * W) ** 2 + (yy - cy * H) ** 2) / (2 * r * r)))[..., None]
            px += g * np.array(c, np.float32) * 0.8
        im = Image.fromarray(np.clip(px, 0, 255).astype(np.uint8))
        d = ImageDraw.Draw(im)
        rng = np.random.default_rng(3)
        for _ in range(140):
            x, y, r = rng.uniform(0, W), rng.uniform(0, H), rng.uniform(1, 3)
            d.ellipse((x - r, y - r, x + r, y + r), fill=(200, 200, 255))
        return im

    def img(self, name, key=None):
        k = (name, key)
        if k not in self.cache:
            self.cache[k] = key_image_np(Image.open(self.base / name), key)
        return self.cache[k]

    def card(self, ln, q, t):
        w, h = CX1 - CX0, CY1 - CY0
        z0 = ln.get("zoom")
        if ln.get("img") and not ln.get("key"):
            zoom = 1.0 + 0.10 * q + (0.35 if z0 else 0)
            c = cover(self.img(ln["img"]).convert("RGB"), w, h, zoom, tuple(z0) if z0 else (0.5, 0.45))
            c = c.convert("RGBA")
        else:
            c = Image.new("RGBA", (w, h), (10, 10, 24, 255))
            g = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            ImageDraw.Draw(g).ellipse((w * 0.2, h * 0.1, w * 0.8, h * 0.9), fill=self.acc + (70,))
            c = Image.alpha_composite(c, g.filter(ImageFilter.GaussianBlur(60)))
            if ln.get("img"):
                sp = self.img(ln["img"], ln["key"])
                s = (h * 0.78 / sp.height) * (1 + 0.06 * math.sin(t * 5))
                sp = sp.resize((int(sp.width * s), int(sp.height * s)), Image.LANCZOS).rotate(t * 25, resample=Image.BICUBIC)
                c.alpha_composite(sp, (int(w / 2 - sp.width / 2), int(h / 2 - sp.height / 2)))
        c = self.fx_card(c, ln.get("fx"), q, t)
        m = Image.new("L", (w, h), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), radius=38, fill=255)
        c.putalpha(m)
        return c

    def fx_card(self, c, fx, q, t):
        d = ImageDraw.Draw(c, "RGBA")
        w, h = c.size
        cx, cy = w / 2, h / 2
        if fx == "rings":                                   # le symbole de l'infini qui se dessine
            pts = []
            for k in range(int(200 * min(1, q * 2.5)) + 1):
                u = k / 200 * 2 * math.pi
                den = 1 + math.sin(u) ** 2
                pts.append((cx + 300 * math.cos(u) / den, cy + 300 * math.sin(u) * math.cos(u) / den))
            if len(pts) > 1:
                d.line(pts, fill=(140, 210, 255, 90), width=40, joint="curve")
                d.line(pts, fill=(230, 245, 255, 255), width=14, joint="curve")
        elif fx == "smoke":                                 # cerveau qui surchauffe
            r = 150
            d.ellipse((cx - r * 1.3, cy - r, cx + r * 1.3, cy + r * 0.9), fill=(255, 150, 170, 255), outline=(0, 0, 0), width=6)
            for k in range(5):
                d.arc((cx - 160 + 60 * k, cy - 80, cx - 60 + 60 * k, cy + 40), 200, 340, fill=(180, 70, 100), width=6)
            for k in range(6):
                tt = (q * 2 + k / 6) % 1
                px_, py_ = cx - 200 + 80 * k, cy - r - 160 * tt
                rr = 28 + 40 * tt
                d.ellipse((px_ - rr, py_ - rr, px_ + rr, py_ + rr), fill=(170, 170, 180, int(220 * (1 - tt))))
        elif fx == "bullets":                                 # tout ralentit sans jamais toucher
            d.ellipse((cx - 150, cy - 150, cx + 150, cy + 150), outline=(140, 210, 255, 200), width=6)
            for k, (yy, col) in enumerate(((cy - 110, (200, 200, 210)), (cy, (255, 200, 80)), (cy + 110, (200, 120, 90)))):
                x = cx - 160 - 420 * math.exp(-3.2 * (q + 0.05 * k))
                if k == 1:                                  # balle
                    d.rounded_rectangle((x - 46, yy - 14, x + 6, yy + 14), radius=12, fill=col, outline=(0, 0, 0), width=3)
                    for j in range(4):
                        d.line((x - 70 - 30 * j, yy, x - 52 - 30 * j, yy), fill=(255, 255, 255, 120), width=3)
                elif k == 0:                                # poing
                    d.ellipse((x - 44, yy - 34, x + 14, yy + 34), fill=(250, 210, 170), outline=(0, 0, 0), width=4)
                else:                                       # camion
                    d.rectangle((x - 170, yy - 46, x - 40, yy + 30), fill=(200, 60, 60), outline=(0, 0, 0), width=4)
                    d.rectangle((x - 40, yy - 20, x + 10, yy + 30), fill=(230, 230, 240), outline=(0, 0, 0), width=4)
                    for wx in (x - 140, x - 20):
                        d.ellipse((wx - 18, yy + 18, wx + 18, yy + 54), fill=(30, 30, 30))
        elif fx == "pull":
            for k in range(26):
                a = k * 0.9 + t * 3
                r = (1 - ((q * 1.6 + k / 26) % 1)) * 420
                x, y = cx + r * math.cos(a), cy + r * math.sin(a)
                d.ellipse((x - 9, y - 9, x + 9, y + 9), fill=(170, 220, 255, 220))
        elif fx == "blast":
            for k in range(3):
                r = ((q * 1.5 + k / 3) % 1) * 600
                d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(255, 90, 90, int(230 * (1 - r / 600))), width=12)
        elif fx == "purple":                                # Blue + Red → Hollow Purple
            k = min(1.0, q / 0.45)
            if k < 1:
                for sx, col in ((-1, (90, 160, 255)), (1, (255, 70, 70))):
                    x = cx + sx * 330 * (1 - k)
                    for r_, a_ in ((110, 70), (70, 160), (40, 255)):
                        d.ellipse((x - r_, cy - r_, x + r_, cy + r_), fill=col + (a_,))
            else:
                g = min(1.0, (q - 0.45) / 0.3)
                r = 80 + 420 * g
                d.ellipse((cx - r * 1.2, cy - r * 1.2, cx + r * 1.2, cy + r * 1.2), fill=(150, 60, 255, 90))
                d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(160, 70, 255, 200))
                d.ellipse((cx - r * 0.45, cy - r * 0.45, cx + r * 0.45, cy + r * 0.45), fill=(10, 0, 20, 255))
                if q > 0.85:
                    d.rectangle((0, 0, w, h), fill=(255, 255, 255, int(255 * min(1, (q - 0.85) / 0.15))))
        elif fx == "slash":
            for k in range(4):
                tk = q * 4 - k * 0.5
                if 0 < tk < 1.2:
                    x0, y0 = w * (0.1 + 0.2 * k), 0
                    x1, y1 = w * (0.3 + 0.2 * k), h
                    a_ = int(255 * min(1, (1.2 - tk) / 0.6))
                    d.line((x0, y0, x0 + (x1 - x0) * min(1, tk * 3), y0 + (y1 - y0) * min(1, tk * 3)), fill=(255, 255, 255, a_), width=10)
                    d.line((x0, y0, x0 + (x1 - x0) * min(1, tk * 3), y0 + (y1 - y0) * min(1, tk * 3)), fill=(255, 40, 40, a_ // 2), width=26)
        elif fx == "freeze":
            ov = Image.new("RGBA", c.size, (120, 180, 255, int(110 * min(1, q * 3))))
            c = Image.alpha_composite(c, ov)
        elif fx == "crown":
            pass
        return c

    def mascot_layer(self, im, ln, q, t, shake):
        e, a = ln.get("expr", "neutral"), ln.get("arm", "down")
        m = mascot(e, a)
        s = 0.72
        m = m.resize((int(m.width * s), int(m.height * s)), Image.LANCZOS)
        bob = math.sin(t * 4) * 8
        x, y = 70 + shake[0], int(1150 + bob) + shake[1]
        fx = ln.get("fx")
        if fx == "freeze" and q > 0.6:
            m = ImageOps.colorize(m.convert("L"), (40, 80, 160), (200, 230, 255)).convert("RGBA")
            m.putalpha(mascot(e, a).resize(m.size).getchannel("A"))
        d = ImageDraw.Draw(im, "RGBA")
        mx, my = x + m.width / 2, y + m.height * 0.42
        if fx in ("rings", "bullets", "shatter"):           # bulle de l'Infini autour de lui
            for k in range(3):
                r = 250 + k * 40 + 10 * math.sin(t * 3 + k)
                d.ellipse((mx - r, my - r, mx + r, my + r), outline=(140, 210, 255, 130 - 30 * k), width=6)
            if fx == "shatter" and q > 0.3:
                rnd = np.random.default_rng(7)
                for _ in range(9):
                    a0 = rnd.uniform(0, 2 * math.pi)
                    d.line((mx + 250 * math.cos(a0), my + 250 * math.sin(a0), mx + 150 * math.cos(a0 + 0.3), my + 150 * math.sin(a0 + 0.3)),
                           fill=(255, 255, 255, 230), width=5)
        im.paste(m, (int(x), int(y)), m)
        if fx == "smoke":
            for k in range(5):
                tt = (q * 2 + k / 5) % 1
                px_, py_ = mx + 40 * math.sin(k * 2 + t), y - 40 - 160 * tt
                r = 30 + 40 * tt
                d.ellipse((px_ - r, py_ - r, px_ + r, py_ + r), fill=(150, 150, 160, int(200 * (1 - tt))))
        if fx == "crown":
            cy = y - 30 + bob * 0.2
            pts = [(mx - 80, cy), (mx - 80, cy - 70), (mx - 40, cy - 30), (mx, cy - 90), (mx + 40, cy - 30), (mx + 80, cy - 70), (mx + 80, cy)]
            d.polygon(pts, fill=(255, 200, 40), outline=(0, 0, 0))
            d.line(pts + [pts[0]], fill=(0, 0, 0), width=5)

    def frame(self, t, lines, segs, words):
        idx = 0
        for i, (a, b) in enumerate(segs):
            if t >= a - 0.12:
                idx = i
        ln = lines[idx]
        a, b = segs[idx]
        nxt = segs[idx + 1][0] if idx + 1 < len(segs) else b + 1.0
        q = max(0.0, min(1.0, (t - a) / max(0.3, nxt - a)))
        shake = (0, 0)
        if ln.get("fx") in ("shake", "slash", "blast") or (ln.get("fx") == "purple" and q > 0.45):
            k = 14 * max(0.0, 1 - (t - a) / 0.6) if ln.get("fx") == "shake" else 6
            shake = (int(np.random.uniform(-k, k)), int(np.random.uniform(-k, k)))
        im = self.bg.copy()
        d = ImageDraw.Draw(im, "RGBA")
        # titre fixe en haut
        title = self.s["title"].split("|")
        d.text((W / 2, 70), title[0], font=F(64), fill=(255, 255, 255), anchor="mm", stroke_width=6, stroke_fill=(0, 0, 0))
        d.text((W / 2, 150), title[1], font=F(88), fill=self.acc, anchor="mm", stroke_width=7, stroke_fill=(0, 0, 0))
        # carte (entrée en « pop » à chaque phrase)
        c = self.card(ln, q, t)
        pop = ease_back((t - a + 0.12) / 0.3)
        sc = 0.86 + 0.14 * pop
        c2 = c.resize((int(c.width * sc), int(c.height * sc)), Image.LANCZOS)
        cx, cy = (CX0 + CX1) / 2 + shake[0], (CY0 + CY1) / 2 + 40 + shake[1]
        d.rounded_rectangle((cx - c2.width / 2 - 8, cy - c2.height / 2 - 8, cx + c2.width / 2 + 8, cy + c2.height / 2 + 8),
                            radius=44, fill=(255, 255, 255))
        im.paste(c2, (int(cx - c2.width / 2), int(cy - c2.height / 2)), c2)
        if ln.get("label"):                                 # ruban au-dessus de la carte
            f = F(46)
            tw = d.textlength(ln["label"], font=f)
            y0 = cy - c2.height / 2 - 34
            d.rounded_rectangle((W / 2 - tw / 2 - 30, y0 - 32, W / 2 + tw / 2 + 30, y0 + 32), radius=14,
                                fill=(220, 40, 60), outline=(0, 0, 0), width=5)
            d.text((W / 2, y0), ln["label"], font=f, fill=(255, 255, 255), anchor="mm")
        self.mascot_layer(im, ln, q, t, shake)
        # sous-titre : le mot en cours, en gros
        cur = None
        for (w, wa, wb) in words[idx]:
            if wa - 0.02 <= t < wb + 0.25:
                cur = (w, wa)
        if cur and t < b + 0.35:
            w, wa = cur
            clean = re.sub(r"[^\w']", "", w).lower()
            col = self.acc if clean in self.kw else (255, 255, 255)
            k = ease_back((t - wa) / 0.12)
            f = F(118 * (0.8 + 0.2 * k))
            txt = w.strip(",.?!…").upper()
            d.text((W / 2 + 120, 1290), txt, font=f, fill=col, anchor="mm", stroke_width=9, stroke_fill=(0, 0, 0))
        return im


def soundtrack(lines, segs, words, total, voice, kw):
    buf = np.zeros(int(total * RATE) + RATE, np.float32)

    def add(snd, t, g):
        i = int(t * RATE)
        if 0 <= i < len(buf):
            n = min(len(snd), len(buf) - i)
            buf[i:i + n] += snd[:n] * g

    whoosh = fusion.load_sound(HY / "FGHTClth_Anime Swing 2.ogg")
    boom = fusion.load_sound(HY / "EXPLDsgn_Anime Explosion 3.ogg")
    slash = fusion.load_sound(HY / "FGHTClth_Anime Swing 4.ogg")
    tt = np.arange(int(0.06 * RATE)) / RATE
    tick = (np.sin(2 * np.pi * 1400 * tt) * np.exp(-tt * 60)).astype(np.float32)
    for ln, (a, b) in zip(lines, segs):
        add(whoosh, max(0, a - 0.12), 0.25)
        fx = ln.get("fx")
        if fx in ("blast", "purple"):
            add(boom, a + (b - a) * (0.45 if fx == "purple" else 0.1), 0.35)
        if fx == "slash":
            for k in range(3):
                add(slash, a + 0.15 * k, 0.3)
    for ws in words:
        for (w, wa, wb) in ws:
            if re.sub(r"[^\w']", "", w).lower() in kw:
                add(tick, wa, 0.12)
    if voice:
        r = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(voice), "-ac", "1", "-ar", str(RATE), "-f", "f32le", "-"],
                           capture_output=True)
        v = np.frombuffer(r.stdout, np.float32)
        add(v / (np.abs(v).max() + 1e-6), 0, 0.9)
    return np.tanh(buf * 1.1) / math.tanh(1.1) * 0.8


def main(script_path, out, voice=None):
    script = json.loads(Path(script_path).read_text())
    lines = script["lines"]
    base = ROOT / script["dir"]
    vbuf = None
    if voice == "tts":                                  # voix Kokoro am_adam générée ici (timings exacts)
        sys.path.insert(0, str(ROOT / "tools"))
        import tts
        vbuf, segs = tts.lines([l["text"] for l in lines], gap=0.32)
        voice = None
    elif voice:
        segs, vdur = voice_timing(Path(voice), lines)
    else:
        segs = estimate_timing(lines)
    words = [word_times(l["text"], a, b) for l, (a, b) in zip(lines, segs)]
    total = segs[-1][1] + 0.9
    sc = Scene(script, base)
    out = Path(out)
    tmp = out.with_suffix(".raw.mp4")
    ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                           "-pix_fmt", "yuv420p", str(tmp)], stdin=subprocess.PIPE)
    for fi in range(int(total * FPS)):
        ff.stdin.write(sc.frame(fi / FPS, lines, segs, words).convert("RGB").tobytes())
    ff.stdin.close()
    ff.wait()
    audio = soundtrack(lines, segs, words, total, voice, sc.kw)
    if vbuf is not None:
        n = min(len(audio), len(vbuf))
        audio[:n] = np.tanh(audio[:n] * 0.55 + vbuf[:n] * 0.95)
    wav = out.with_suffix(".wav")
    fusion.write_wav(wav, audio)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(tmp), "-i", str(wav), "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", str(out)], check=True)
    tmp.unlink(); wav.unlink()
    render.stamp_video(out)
    return out, total


if __name__ == "__main__":
    print(main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None))
