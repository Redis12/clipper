"""« If you had Gojo's Infinity », 2e style (18/11) inspiré de la DA « The math behind Gojo's Infinity » (sans la copier) :
fond bleu nuit quadrillé + anneaux lumineux, texte blanc fin en haut (3 mots à la fois), carte compteur jaune en bas à gauche
(DISTANCE LEFT, SPEED…), éléments neutres dessinés (poing, cerveau, horloge), images officielles fournies par l'utilisateur
dans des cadres lumineux, notre mascotte comme « you », fin qui reboucle sur la 1re image. Voix Kokoro am_adam.
python3 tools/explainer/infinity_style.py <script.json> <sortie.mp4>
"""
from __future__ import annotations

import json
import math
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(Path(__file__).parent))
from clipper.slides import fusion, render  # noqa: E402
from explainer import key_image_np, word_times  # noqa: E402
from mascot import mascot  # noqa: E402
import tts  # noqa: E402

W, H, FPS = 1080, 1920, 30
RATE = fusion.RATE
FONTS = ROOT / "tools/money_sim/fonts"
YEL, CYAN, RED, PURP = (255, 205, 70), (120, 210, 255), (255, 80, 80), (170, 90, 255)
HY = ROOT / "library/_sfx/Helton Yan's Old-School Shonen SFX"


def MF(sz):
    return ImageFont.truetype(str(FONTS / "mont800.woff2"), int(sz))


def AF(sz):
    return ImageFont.truetype(str(FONTS / "anton.woff2"), int(sz))


def ease(k):
    k = min(1, max(0, k))
    return k * k * (3 - 2 * k)


def back(k):
    k = min(1, max(0, k))
    return 1 + 2.70158 * (k - 1) ** 3 + 1.70158 * (k - 1) ** 2


def bg():
    y, x = np.mgrid[0:H, 0:W]
    r = np.sqrt((x - W / 2) ** 2 + (y - H * 0.5) ** 2) / (H * 0.7)
    c0, c1 = np.array([18, 40, 92], np.float32), np.array([4, 10, 30], np.float32)
    px = c0 + (c1 - c0) * np.clip(r, 0, 1)[..., None]
    im = Image.fromarray(px.astype(np.uint8))
    d = ImageDraw.Draw(im)
    for gx in range(0, W, 60):
        d.line((gx, 0, gx, H), fill=(30, 56, 110), width=1)
    for gy in range(0, H, 60):
        d.line((0, gy, W, gy), fill=(30, 56, 110), width=1)
    return im


def rings(d, cx, cy, t, col=CYAN, n=5, r0=120, gap=46, a=90):
    for k in range(n):
        r = r0 + k * gap + 8 * math.sin(t * 2 + k)
        d.arc((cx - r, cy - r, cx + r, cy + r), int(t * 40 + k * 30), int(t * 40 + k * 30 + 250), fill=col + (max(10, a - 15 * k),), width=4)


def counter(d, label, value, col=YEL, y=1460):
    f1, f2 = MF(26), AF(88)
    tw = max(d.textlength(value, font=f2), d.textlength(label, font=f1)) + 60
    d.rounded_rectangle((60, y - 80, 60 + tw, y + 70), radius=18, fill=(6, 14, 36, 220), outline=(60, 90, 150, 255), width=3)
    d.text((88, y - 50), label, font=f1, fill=(170, 190, 230), anchor="lm")
    d.text((88, y + 18), value, font=f2, fill=col, anchor="lm")


def fist(d, x, y, s=1.0):
    """Poing de profil (forme neutre, pas un perso)."""
    sk, ink = (247, 205, 160), (60, 40, 30)
    d.rounded_rectangle((x - 230 * s, y - 120 * s, x, y + 120 * s), radius=int(70 * s), fill=sk, outline=ink, width=int(6 * s))
    for k in range(4):
        yy = y - 110 * s + k * 58 * s
        d.rounded_rectangle((x - 40 * s, yy, x + 60 * s, yy + 54 * s), radius=int(26 * s), fill=sk, outline=ink, width=int(5 * s))
    d.rounded_rectangle((x - 300 * s, y - 70 * s, x - 200 * s, y + 70 * s), radius=int(30 * s), fill=(30, 40, 70), outline=ink, width=int(5 * s))


def frame_img(im, src, cx, cy, w, h, t, glow=CYAN, k=1.0):
    from explainer import cover
    c = cover(src.convert("RGB"), int(w), int(h), 1.04 + 0.05 * math.sin(t * 0.8)).convert("RGBA")
    m = Image.new("L", c.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, c.width - 1, c.height - 1), radius=34, fill=255)
    c.putalpha(m)
    s = 0.85 + 0.15 * back(k)
    c = c.resize((int(c.width * s), int(c.height * s)), Image.LANCZOS)
    gl = Image.new("RGBA", (c.width + 120, c.height + 120), (0, 0, 0, 0))
    ImageDraw.Draw(gl).rounded_rectangle((40, 40, c.width + 80, c.height + 80), radius=50, fill=glow + (150,))
    gl = gl.filter(ImageFilter.GaussianBlur(26))
    im.alpha_composite(gl, (int(cx - gl.width / 2), int(cy - gl.height / 2)))
    im.alpha_composite(c, (int(cx - c.width / 2), int(cy - c.height / 2)))


class Show:
    def __init__(self, script):
        self.s = script
        self.base = ROOT / script["dir"]
        self.bg = bg().convert("RGBA")
        self.cache = {}

    def img(self, name, key=None):
        if (name, key) not in self.cache:
            self.cache[(name, key)] = key_image_np(Image.open(self.base / name), key)
        return self.cache[(name, key)]

    def scene(self, im, ln, q, t, tl):
        """tl = temps depuis le début de la phrase."""
        d = ImageDraw.Draw(im, "RGBA")
        kind = ln.get("scene")
        cx, cy = W / 2, 930
        if kind == "punch":                              # le poing s'approche… et n'arrive jamais
            m = mascot("smug" if q < 0.7 else "wink", "down")
            ms = 0.95
            mm = m.resize((int(m.width * ms), int(m.height * ms)), Image.LANCZOS)
            mx = W - mm.width + 120
            rings(d, mx + 170, 700, t, n=4, r0=150)
            im.alpha_composite(mm, (int(mx), 420))
            gap = 26 * math.exp(-2.2 * q) + 6
            fist(d, mx + 40 - gap, 690, 1.15)
            v = 0.0000007 * math.exp(-4 * q)
            counter(d, "DISTANCE LEFT", f"{v:.9f} in")
        elif kind == "series":                           # ½ + ¼ + ⅛ … qui ne finit jamais
            terms = ["1/2", "1/4", "1/8", "1/16", "1/32", "…"]
            n = int(1 + q * 7)
            x = 110
            for i, tm in enumerate(terms[:n]):
                d.text((x, 900), tm, font=AF(96 - i * 10), fill=(255, 255, 255), anchor="lm")
                x += d.textlength(tm, font=AF(96 - i * 10)) + 18
                if i < n - 1 and i < len(terms) - 1:
                    d.text((x, 900), "+", font=AF(70), fill=CYAN, anchor="lm")
                    x += 50
            tot = sum(0.5 ** (i + 1) for i in range(min(n, 30)))
            bw = 860
            d.rounded_rectangle((110, 1060, 110 + bw, 1120), radius=14, outline=(120, 160, 220), width=4)
            d.rounded_rectangle((116, 1066, 116 + (bw - 12) * tot, 1114), radius=10, fill=YEL)
            counter(d, "TOTAL", f"{tot:.4f}…  never 1")
        elif kind == "slow":                             # tout ralentit
            speeds = [182, 91, 45, 22, 11, 5.6, 2.8, 1.4]
            k = min(len(speeds) - 1, int(q * len(speeds)))
            x = 160 + 520 * (1 - 0.5 ** (q * 6))
            rings(d, 860, 930, t, n=4, r0=110)
            d.rounded_rectangle((x - 70, 900, x + 10, 960), radius=24, fill=(240, 200, 90), outline=(40, 30, 20), width=5)
            for j in range(5):
                d.line((x - 110 - 40 * j, 930, x - 80 - 40 * j, 930), fill=(255, 255, 255, 160 - 25 * j), width=5)
            counter(d, "SPEED", f"{speeds[k]:g} mph")
        elif kind == "brain":
            heat = min(1, q * 1.3)
            col = (int(255), int(160 - 120 * heat), int(180 - 160 * heat))
            d.ellipse((cx - 260, cy - 190, cx + 260, cy + 170), fill=col, outline=(40, 20, 30), width=8)
            for k in range(5):
                d.arc((cx - 220 + 88 * k, cy - 120, cx - 100 + 88 * k, cy + 40), 200, 340, fill=(120, 40, 60), width=8)
            for k in range(7):
                tt = (t * 0.8 + k / 7) % 1
                x, y = cx - 260 + 86 * k, cy - 200 - 220 * tt
                r = 30 + 50 * tt
                d.ellipse((x - r, y - r, x + r, y + r), fill=(160, 160, 175, int(200 * (1 - tt))))
            counter(d, "BRAIN LOAD", f"{int(100 + 9900 * heat):,}%", RED)
        elif kind == "image":
            frame_img(im, self.img(ln["img"]), cx, cy, 900, 720, t, tuple(ln.get("glow", CYAN)), tl / 0.35)
            if ln.get("counter"):
                counter(d, *ln["counter"][:2], tuple(ln["counter"][2]) if len(ln["counter"]) > 2 else YEL)
        elif kind in ("blue", "red"):
            sp = self.img(ln["img"], ln.get("key"))
            s = 620 / sp.height * (1 + 0.05 * math.sin(t * 6))
            sp = sp.resize((int(sp.width * s), int(sp.height * s)), Image.LANCZOS).rotate(t * 30, resample=Image.BICUBIC)
            col = CYAN if kind == "blue" else RED
            for k in range(28):
                a = k * 0.8 + t * 2.5
                if kind == "blue":
                    r = (1 - ((q * 1.5 + k / 28) % 1)) * 520
                else:
                    r = ((q * 1.5 + k / 28) % 1) * 560 + 180
                d.ellipse((cx + r * math.cos(a) - 8, cy + r * math.sin(a) - 8, cx + r * math.cos(a) + 8, cy + r * math.sin(a) + 8), fill=col + (220,))
            im.alpha_composite(sp, (int(cx - sp.width / 2), int(cy - sp.height / 2)))
            counter(d, "FORCE", "INWARD" if kind == "blue" else "OUTWARD", col)
        elif kind == "purple":
            k = min(1.0, q / 0.45)
            if k < 1:
                for sx, col in ((-1, CYAN), (1, RED)):
                    x = cx + sx * 330 * (1 - ease(k))
                    for r_, a_ in ((140, 70), (90, 160), (50, 255)):
                        d.ellipse((x - r_, cy - r_, x + r_, cy + r_), fill=col + (a_,))
            else:
                g = min(1.0, (q - 0.45) / 0.35)
                r = 100 + 460 * g
                d.ellipse((cx - r * 1.2, cy - r * 1.2, cx + r * 1.2, cy + r * 1.2), fill=PURP + (80,))
                d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=PURP + (210,))
                d.ellipse((cx - r * 0.45, cy - r * 0.45, cx + r * 0.45, cy + r * 0.45), fill=(8, 0, 18, 255))
            counter(d, "MASS", "IMAGINARY", PURP)
        elif kind == "warning":
            a = int(80 + 60 * math.sin(t * 10))
            d.rectangle((0, 0, W, H), fill=(120, 0, 10, a))
            d.text((cx, cy), "!", font=AF(520), fill=RED, anchor="mm", stroke_width=12, stroke_fill=(20, 0, 0))
        if ln.get("slash") and tl > 0.2:                # entailles par-dessus l'image
            for k in range(3):
                tk = (tl - 0.2) * 3 - k * 0.4
                if 0 < tk < 1.4:
                    p = min(1, tk * 2)
                    a_ = int(255 * min(1, (1.4 - tk) / 0.6))
                    x0, y0, x1, y1 = 140 + 260 * k, 560, 380 + 260 * k, 1300
                    d.line((x0, y0, x0 + (x1 - x0) * p, y0 + (y1 - y0) * p), fill=(255, 60, 60, a_ // 2), width=30)
                    d.line((x0, y0, x0 + (x1 - x0) * p, y0 + (y1 - y0) * p), fill=(255, 255, 255, a_), width=10)

    def caption(self, im, words, t):
        """Texte blanc fin en haut, 3 mots à la fois, le mot en cours un peu plus lumineux."""
        cur = [i for i, (w, a, b) in enumerate(words) if a - 0.05 <= t]
        if not cur:
            return
        i = cur[-1]
        if t > words[-1][2] + 0.4:
            return
        g0 = (i // 3) * 3
        chunk = words[g0:g0 + 3]
        d = ImageDraw.Draw(im, "RGBA")
        f = MF(58)
        txt = " ".join(w for w, a, b in chunk)
        tw = d.textlength(txt, font=f)
        x = W / 2 - tw / 2
        for j, (w, a, b) in enumerate(chunk):
            on = t >= a - 0.05
            col = (255, 255, 255, 255) if on else (255, 255, 255, 90)
            d.text((x, 330), w, font=f, fill=col, anchor="lm", stroke_width=3, stroke_fill=(0, 0, 0, 180))
            x += d.textlength(w + " ", font=f)


def main(script_path, out):
    script = json.loads(Path(script_path).read_text())
    lines = script["lines"]
    vbuf, segs = tts.lines([l["text"] for l in lines], gap=0.3, start=0.15)
    words = [word_times(l["text"], a, b) for l, (a, b) in zip(lines, segs)]
    total = segs[-1][1] + 0.6
    sh = Show(script)
    first = None
    out = Path(out)
    tmp = out.with_suffix(".raw.mp4")
    ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                           "-pix_fmt", "yuv420p", str(tmp)], stdin=subprocess.PIPE)
    nf = int(total * FPS)
    for fi in range(nf):
        t = fi / FPS
        idx = max([i for i, (a, b) in enumerate(segs) if t >= a - 0.1] or [0])
        a, b = segs[idx]
        nxt = segs[idx + 1][0] if idx + 1 < len(segs) else total
        q = min(1.0, max(0.0, (t - a) / max(0.4, nxt - a)))
        im = sh.bg.copy()
        rings(ImageDraw.Draw(im, "RGBA"), W / 2, 930, t * 0.5, col=(80, 140, 230), n=6, r0=420, gap=70, a=40)
        sh.scene(im, lines[idx], q, t, t - a)
        sh.caption(im, words[idx], t)
        if fi == 0:
            first = im.copy()
        if t > total - 0.45 and first is not None:        # boucle : on revient à la 1re image
            im = Image.blend(im, first, (t - (total - 0.45)) / 0.45)
        ff.stdin.write(im.convert("RGB").tobytes())
    ff.stdin.close()
    ff.wait()
    buf = np.zeros(int(total * RATE) + RATE, np.float32)

    def add(s, t, g):
        i = int(t * RATE)
        n = min(len(s), len(buf) - i)
        if n > 0 and i >= 0:
            buf[i:i + n] += s[:n] * g
    whoosh = fusion.load_sound(HY / "FGHTClth_Anime Swing 2.ogg")
    boom = fusion.load_sound(HY / "EXPLDsgn_Anime Explosion 3.ogg")
    tt = np.arange(len(buf)) / RATE                     # nappe grave continue (ambiance « espace »)
    buf += (np.sin(2 * math.pi * 55 * tt) * 0.05 + np.sin(2 * math.pi * 82.5 * tt) * 0.03).astype(np.float32)
    for ln, (a, b) in zip(lines, segs):
        add(whoosh, max(0, a - 0.1), 0.2)
        if ln.get("scene") in ("purple", "red") or ln.get("slash"):
            add(boom, a + 0.3, 0.3)
    n = min(len(buf), len(vbuf))
    buf[:n] += vbuf[:n] * 1.0
    wav = out.with_suffix(".wav")
    fusion.write_wav(wav, np.tanh(buf * 0.9))
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(tmp), "-i", str(wav), "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", str(out)], check=True)
    tmp.unlink(); wav.unlink()
    render.stamp_video(out)
    return out, total


if __name__ == "__main__":
    print(main(sys.argv[1], sys.argv[2]))
