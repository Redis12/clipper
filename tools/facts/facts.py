"""Vidéos « facts » avec voix off (09/11, demandé par l'utilisateur, modèle : une vidéo virale « Saitama peut-il
toucher Goku ? » — on garde le principe, pas la DA : notre fond néon, nos stickmans découpés, nos icônes).
Voix : Kokoro (kokoro-onnx, Apache 2.0) voix am_adam, choisie par l'utilisateur. Modèles dans /tmp/tts
(téléchargés depuis les releases GitHub thewh1teagle/kokoro-onnx, jamais dans le dépôt).
Un script = une liste de BEATS : voix off, petit tag, titre (2 lignes), type de visuel. Sous-titres mot par mot
(temps estimés dans la phrase dite, d'après la longueur des mots et la ponctuation).
python3 facts.py sortie.mp4
"""
import math
import random
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools" / "mocap"))
sys.path.insert(0, str(HERE))
import clips  # noqa: E402

W, H, FPS = 1080, 1920, 30
FONTS = ROOT / "tools" / "money_sim" / "fonts"
LIB = ROOT / "library"
TTS = Path("/tmp/tts")
YEL, CYAN, RED, WHITE = (255, 210, 50), (90, 200, 255), (255, 70, 80), (245, 245, 250)


def font(name, size, _c={}):
    k = (name, size)
    if k not in _c:
        _c[k] = ImageFont.truetype(str(FONTS / name), size)
    return _c[k]


BEATS = [
    dict(say="Everyone says Saitama beats Goku with one punch. But nobody asks the real question: can he even touch him?",
         tag="ONE PUNCH vs ULTRA INSTINCT", title=("CAN SAITAMA", "EVEN TOUCH GOKU?"), col=(WHITE, CYAN), vis="versus"),
    dict(say="A punch only works if it lands. And Goku is not going to stand still.",
         tag="THE PROBLEM", title=("ONE PUNCH", "HAS TO LAND"), col=(WHITE, RED), vis="miss"),
    dict(say="Start with light. In one single second, light travels about three hundred thousand kilometers.",
         tag="SPEED OF LIGHT", title=("IN 1 SECOND", ""), col=(YEL, WHITE), vis="light"),
    dict(say="That's more than seven laps around the entire Earth.",
         tag="IN 1 SECOND", title=("7.5 LAPS", "AROUND EARTH"), col=(WHITE, CYAN), vis="earth"),
    dict(say="And in Dragon Ball Super, fans scale Goku way beyond that speed.",
         tag="SPEED SCALE", title=("FASTER", "THAN LIGHT?"), col=(WHITE, YEL), vis="scale"),
    dict(say="It gets worse. With Instant Transmission, he locks onto an energy and just appears there. Zero travel time.",
         tag="EVEN WORSE", title=("INSTANT", "TRANSMISSION"), col=(WHITE, CYAN), vis="teleport"),
    dict(say="Then comes the real nightmare: Ultra Instinct. His body dodges on its own, before his brain even decides.",
         tag="THE REAL NIGHTMARE", title=("ULTRA", "INSTINCT"), col=((210, 220, 255), WHITE), vis="ui"),
    dict(say="Saitama's strength might be limitless. But a punch that never connects does exactly zero damage.",
         tag="SAITAMA FANS FORGET", title=("INFINITE POWER", "ZERO TARGET"), col=(YEL, RED), vis="strength"),
    dict(say="So, strength or speed? Can Saitama actually land a hit on Goku? Drop your argument below.",
         tag="I'M WAITING", title=("STRENGTH vs SPEED", "WHO WINS?"), col=(YEL, CYAN), vis="final"),
]


# ------------------------------------------------------------------------------------------------- voix
def voice(beats, voice_name="am_adam", speed=1.08):
    from kokoro_onnx import Kokoro
    k = Kokoro(str(TTS / "kokoro-v1.0.onnx"), str(TTS / "voices-v1.0.bin"))
    out, t = [], 0.35
    for b in beats:
        s, sr = k.create(b["say"], voice=voice_name, speed=speed, lang="en-us")
        s = np.asarray(s, np.float32)
        env = np.abs(s)
        thr = env.max() * 0.04
        idx = np.nonzero(env > thr)[0]
        a, z = (idx[0] / sr, idx[-1] / sr) if len(idx) else (0, len(s) / sr)
        b["audio"], b["sr"] = s, sr
        b["t0"] = t
        b["dur"] = len(s) / sr + 0.35
        b["words"] = word_times(b["say"], t + a, t + z)
        t += b["dur"]
    return t + 1.6


def word_times(text, a, z):
    words = text.split()
    wts = []
    for w in words:
        n = len(w.strip(".,!?:;")) + 1.5
        pause = 4.0 if w[-1] in ".!?" else (2.5 if w[-1] in ",:;" else 0)
        wts.append((n, pause))
    tot = sum(n + p for n, p in wts)
    out, t = [], a
    for w, (n, p) in zip(words, wts):
        d = (z - a) * n / tot
        out.append((w, t, t + d))
        t += d + (z - a) * p / tot
    return out


# ------------------------------------------------------------------------------------------------- décor
def background():
    yy = np.linspace(0, 1, H)[:, None, None]
    c0, c1 = np.array((26, 10, 48), np.float32), np.array((4, 4, 12), np.float32)
    img = Image.fromarray((c0 * (1 - yy) + c1 * yy).repeat(W, 1).clip(0, 255).astype(np.uint8)).convert("RGBA")
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for (gx, gy, gr, gc) in [(0.12, 0.25, 420, (130, 60, 255)), (0.92, 0.55, 460, (40, 120, 255)),
                             (0.5, 1.0, 520, (220, 30, 90))]:
        gd.ellipse((gx * W - gr, gy * H - gr, gx * W + gr, gy * H + gr), fill=gc + (90,))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(140)))
    d = ImageDraw.Draw(img, "RGBA")
    hz = 1300                                                       # sol néon en perspective
    for i in range(-14, 15):
        d.line((W / 2 + i * 26, hz, W / 2 + i * 260, H), fill=(120, 80, 255, 70), width=2)
    for j in range(12):
        y = hz + (H - hz) * (j / 11) ** 1.8
        d.line((0, y, W, y), fill=(120, 80, 255, int(40 + 60 * j / 11)), width=2)
    d.line((0, hz, W, hz), fill=(150, 110, 255, 200), width=4)
    rnd = random.Random(3)
    for _ in range(140):
        x, y = rnd.uniform(0, W), rnd.uniform(0, hz - 40)
        r = rnd.choice((1, 1, 1.5, 2.2))
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, rnd.randint(60, 200)))
    return img


def glow_text(img, xy, txt, f, fill, anchor="mm", stroke=8, glow=None):
    if glow:
        lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(lay).text(xy, txt, font=f, anchor=anchor, fill=glow + (200,), stroke_width=stroke + 6,
                                 stroke_fill=glow + (200,))
        img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(14)))
    ImageDraw.Draw(img).text(xy, txt, font=f, anchor=anchor, fill=fill, stroke_width=stroke, stroke_fill=(10, 6, 20))


def pill(img, cx, cy, txt, col, f=None, a=1.0):
    f = f or font("mont900.woff2", 30)
    d = ImageDraw.Draw(img, "RGBA")
    tw = d.textlength(txt, font=f)
    x0, x1 = cx - tw / 2 - 26, cx + tw / 2 + 26
    d.rounded_rectangle((x0, cy - 28, x1, cy + 28), radius=28, fill=(10, 8, 24, int(220 * a)),
                        outline=col + (int(255 * a),), width=4)
    d.text((cx, cy), txt, font=f, anchor="mm", fill=col + (int(255 * a),))


def ease_out(x):
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


def back_out(x, s=1.7):
    x = min(1.0, max(0.0, x)) - 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


# ------------------------------------------------------------------------------------------------- acteurs
class Actors:
    def __init__(self):
        HT = 560
        self.sai = {n: clips.load(n, HT) for n in ("saitama_debout", "saitama_poing_armer", "saitama_poing_tendu")}
        st = Image.open(LIB / "_sticknodes/Saitama/saitama_still.png").convert("RGBA")   # 09/11 : modèle Stick Nodes
        k_ = 545 / st.height                                              # de l'utilisateur (image fixe nette)
        st = st.resize((round(st.width * k_), round(st.height * k_)), Image.LANCZOS)
        self.sai["saitama_debout"] = ([st], [st.height])
        self.gok = {n: clips.load(n, HT * 1.02, flip=True) for n in ("debout_regarde", "garde_respire")}
        self.ui = self.icon(LIB / "_fusion/Goku/7 ui.jpg", 330, (200, 210, 255))
        self.goku_ic = self.icon(LIB / "_fusion/Goku/1 Base.png", 150, (90, 200, 255))
        self.earth = [Image.open(LIB / f"_decors/planets/earth/earth_{i}.png").convert("RGBA") for i in range(16)]
        mp = sorted((LIB / "_decors/planets/moon").glob("*.png"))
        self.moon = Image.open(mp[0]).convert("RGBA") if mp else None

    @staticmethod
    def icon(p, size, col):
        from clipper.slides import fusion
        return fusion.icon(str(p), size, col)

    def put(self, img, seq, i, x, ground=1310, alpha=1.0, tint=None):
        fr, ft = seq
        k = i % len(fr)
        im = fr[k]
        if tint:
            t_ = Image.new("RGBA", im.size, tint + (0,))
            t_.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
            im = t_
        elif alpha < 1:
            im = im.copy()
            im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
        img.alpha_composite(im, (int(x - im.width / 2), int(ground - ft[min(k, len(ft) - 1)])))


def rim(img, cx, cy, rx, ry, col, a=1.0):
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=col + (int(150 * a),))
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(60)))


# ------------------------------------------------------------------------------------------------- visuels
def vis_versus(img, A, u, f):
    rim(img, 300, 1100, 200, 330, (255, 180, 40), 0.7)
    rim(img, 790, 1100, 200, 330, (90, 160, 255), 0.8)
    s = ease_out(u / 0.4)
    A.put(img, A.sai["saitama_debout"], f, 300 - 200 * (1 - s))
    A.put(img, A.gok["debout_regarde"], f, 790 + 200 * (1 - s))
    if u > 0.25:
        sc = back_out((u - 0.25) / 0.3)
        glow_text(img, (W / 2, 1000), "VS", font("anton.woff2", int(150 * max(0.01, sc))), WHITE, glow=(255, 60, 120))


def vis_miss(img, A, u, f, dur):
    rim(img, 330, 1100, 200, 330, (255, 180, 40), 0.6)
    armer, tendu = A.sai["saitama_poing_armer"], A.sai["saitama_poing_tendu"]
    t_hit = min(1.4, dur * 0.35)
    if u < t_hit:
        A.put(img, armer, int(u / t_hit * (len(armer[0]) - 1)), 330)
    else:
        A.put(img, tendu, min(len(tendu[0]) - 1, int((u - t_hit) * 24)), 360)
    # Goku : déjà ailleurs (images rémanentes)
    q = ease_out((u - t_hit + 0.1) / 0.25)
    gx = 760 + 140 * q
    for j in range(3):
        if u > t_hit - 0.1:
            A.put(img, A.gok["garde_respire"], f, 760 + 140 * q * j / 3, alpha=0.25, tint=(120, 200, 255))
    A.put(img, A.gok["garde_respire"], f, gx)
    if t_hit <= u < t_hit + 0.5:
        k = (u - t_hit) / 0.5
        d = ImageDraw.Draw(img, "RGBA")
        for i in range(10):
            yy = 860 + i * 34
            d.line((520, yy, 520 + 380 * (1 - k), yy), fill=(255, 255, 255, int(160 * (1 - k))), width=5)


def stopwatch(img, cx, cy, r, frac, col):
    d = ImageDraw.Draw(img, "RGBA")
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=col + (255,), width=10)
    d.rectangle((cx - 24, cy - r - 40, cx + 24, cy - r - 8), fill=col + (255,))
    for i in range(60):
        a = math.radians(i * 6 - 90)
        l = 30 if i % 5 == 0 else 14
        d.line((cx + math.cos(a) * (r - 18), cy + math.sin(a) * (r - 18),
                cx + math.cos(a) * (r - 18 - l), cy + math.sin(a) * (r - 18 - l)), fill=(220, 220, 240, 200), width=4)
    a = math.radians(frac * 360 - 90)
    d.pieslice((cx - r + 30, cy - r + 30, cx + r - 30, cy + r - 30), -90, frac * 360 - 90, fill=col + (60,))
    d.line((cx, cy, cx + math.cos(a) * (r - 40), cy + math.sin(a) * (r - 40)), fill=RED + (255,), width=8)
    d.ellipse((cx - 14, cy - 14, cx + 14, cy + 14), fill=WHITE + (255,))


def vis_light(img, A, u, f, dur):
    frac = ease_out(u / max(1.0, dur * 0.75))
    stopwatch(img, W / 2, 900, 230, frac, CYAN)
    glow_text(img, (W / 2, 900 + 340), f"{frac:.3f} s", font("anton.woff2", 64), WHITE)
    km = int(299792 * frac)
    glow_text(img, (W / 2, 520), f"{km:,} KM".replace(",", " "), font("anton.woff2", 120), YEL, glow=(255, 160, 0))
    x = (u * 1600) % (W + 400) - 200                                   # trait de lumière qui traverse
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).line((x - 260, 640, x, 640), fill=(200, 240, 255, 255), width=10)
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(6)))
    ImageDraw.Draw(img).ellipse((x - 10, 630, x + 10, 650), fill=WHITE)


def vis_earth(img, A, u, f, dur):
    e = A.earth[int(u * 8) % len(A.earth)]
    sz = 520
    e = e.resize((sz, sz), Image.NEAREST)
    cx, cy = W / 2, 930
    rim(img, cx, cy, 300, 300, (60, 140, 255), 0.6)
    img.alpha_composite(e, (int(cx - sz / 2), int(cy - sz / 2)))
    laps = 7.48 * ease_out(u / max(1.0, dur * 0.8))
    ang = laps * 2 * math.pi
    d = ImageDraw.Draw(img, "RGBA")
    rx, ry = 380, 120
    d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), outline=(150, 210, 255, 150), width=4)
    for j in range(14):                                                 # point de lumière + traînée
        a_ = ang - j * 0.09
        px, py = cx + math.cos(a_) * rx, cy + math.sin(a_) * ry
        r = 16 - j
        d.ellipse((px - r, py - r, px + r, py + r), fill=(220, 245, 255, max(0, 255 - j * 18)))
    glow_text(img, (W / 2, 1280), f"{laps:.1f} LAPS", font("anton.woff2", 110), WHITE, glow=(60, 140, 255))


def vis_scale(img, A, u, f, dur):
    rows = [("WALKING", "5 KM/H"), ("CAR", "130 KM/H"), ("JET", "900 KM/H"), ("SOUND", "1 235 KM/H"),
            ("LIGHT", "1 079 252 849 KM/H")]
    d = ImageDraw.Draw(img, "RGBA")
    x0, y_top, y_bot = 230, 600, 1260
    d.line((x0, y_top - 60, x0, y_bot), fill=(200, 200, 255, 160), width=6)
    shown = int(min(len(rows), u / max(0.35, dur * 0.12)) + 1)
    for i, (a, b) in enumerate(rows[:shown]):
        y = y_bot - (i + 0.5) * (y_bot - y_top) / len(rows)
        col = YEL if a == "LIGHT" else WHITE
        d.ellipse((x0 - 14, y - 14, x0 + 14, y + 14), fill=col + (255,))
        d.text((x0 + 40, y - 22), a, font=font("anton.woff2", 58), fill=col, anchor="lm", stroke_width=5,
               stroke_fill=(10, 6, 20))
        d.text((x0 + 40, y + 28), b, font=font("mont800.woff2", 30), fill=(190, 190, 220), anchor="lm")
    if u > dur * 0.6:                                                   # Goku au-dessus de l'échelle
        q = back_out((u - dur * 0.6) / 0.4)
        ic = A.goku_ic.resize((int(170 * q) or 1, int(170 * q) or 1))
        img.alpha_composite(ic, (int(x0 + 420 - ic.width / 2), int(y_top - 120 - ic.height / 2)))
        glow_text(img, (x0 + 420, y_top - 10), "???", font("anton.woff2", 70), CYAN, glow=(40, 140, 255))


def vis_teleport(img, A, u, f, dur):
    e = A.earth[int(u * 8) % len(A.earth)].resize((300, 300), Image.NEAREST)
    ex, ey, mx, my = 270, 1130, 800, 640
    img.alpha_composite(e, (ex - 150, ey - 150))
    if A.moon:
        m = A.moon.resize((170, 170), Image.NEAREST)
        img.alpha_composite(m, (mx - 85, my - 85))
    d = ImageDraw.Draw(img, "RGBA")
    for j in range(22):                                                 # pointillés
        t_ = j / 21
        x, y = ex + (mx - ex) * t_, ey + (my - ey) * t_
        if j % 2 == 0:
            d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(150, 210, 255, 180))
    pill(img, (ex + mx) / 2 + 60, (ey + my) / 2, "0.000 s", CYAN)
    t_tp = dur * 0.45
    ic = A.goku_ic
    if u < t_tp:
        img.alpha_composite(ic, (ex - 75, ey - 150 - 90))
    if t_tp - 0.05 <= u < t_tp + 0.25:
        k = (u - t_tp + 0.05) / 0.3
        for (px, py) in ((ex, ey - 165), (mx, my - 140)):
            d.ellipse((px - 120 * k, py - 120 * k, px + 120 * k, py + 120 * k), outline=(200, 240, 255, int(255 * (1 - k))),
                      width=8)
    if u >= t_tp:
        img.alpha_composite(ic, (mx - 75, my - 140 - 75))


def vis_ui(img, A, u, f, dur):
    rim(img, 790, 920, 260, 300, (200, 210, 255), 0.6 + 0.2 * math.sin(u * 6))
    ic = A.ui
    img.alpha_composite(ic, (790 - ic.width // 2, 920 - ic.height // 2))
    d = ImageDraw.Draw(img, "RGBA")
    fx = 250
    steps_n = [("SEE", WHITE), ("THINK", YEL), ("MOVE", WHITE)]
    f1 = font("anton.woff2", 48)
    d.text((fx, 640), "NORMAL", font=font("mont900.woff2", 30), fill=(190, 190, 220), anchor="mm")
    for i, (s, c) in enumerate(steps_n):
        y = 720 + i * 120
        a = ease_out((u - i * 0.35) / 0.3)
        if a <= 0:
            continue
        d.rounded_rectangle((fx - 120, y - 40, fx + 120, y + 40), radius=20, outline=c + (int(255 * a),), width=5,
                            fill=(10, 8, 24, int(200 * a)))
        d.text((fx, y), s, font=f1, fill=c + (int(255 * a),), anchor="mm")
        if i < 2:
            d.line((fx, y + 42, fx, y + 78), fill=(200, 200, 230, int(200 * a)), width=4)
    if u > dur * 0.45:                                                  # « THINK » barré : le corps agit seul
        a = ease_out((u - dur * 0.45) / 0.3)
        d.line((fx - 130, 840 - 40, fx - 130 + 260 * a, 840 + 40), fill=RED + (255,), width=10)
        glow_text(img, (fx, 1160), "BODY MOVES", font("anton.woff2", 54), CYAN)
        glow_text(img, (fx, 1225), "ON ITS OWN", font("anton.woff2", 54), CYAN)


def vis_strength(img, A, u, f, dur):
    rim(img, 330, 1100, 200, 330, (255, 180, 40), 0.8)
    A.put(img, A.sai["saitama_debout"], f, 300)
    d = ImageDraw.Draw(img, "RGBA")
    bx, y0, y1 = 560, 700, 1260
    fill = ease_out(u / max(0.8, dur * 0.35))
    d.rounded_rectangle((bx, y0, bx + 70, y1), radius=35, outline=YEL + (255,), width=6, fill=(10, 8, 24, 200))
    d.rounded_rectangle((bx + 10, y1 - 10 - (y1 - y0 - 20) * fill, bx + 60, y1 - 10), radius=25, fill=YEL + (255,))
    if fill > 0.98:
        glow_text(img, (bx + 35, y0 - 60), "∞", ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 120),
                  YEL, glow=(255, 160, 0))
    else:
        glow_text(img, (bx + 35, y0 - 60), f"{int(fill * 100)}%", font("anton.woff2", 90), YEL, glow=(255, 160, 0))
    d.text((bx + 35, y1 + 40), "STRENGTH", font=font("mont900.woff2", 30), fill=YEL, anchor="mm")
    if u > dur * 0.5:                                                   # … mais la cible n'est plus là
        a = ease_out((u - dur * 0.5) / 0.3)
        glow_text(img, (850, 950), "0", font("anton.woff2", int(260 * max(0.05, back_out((u - dur * 0.5) / 0.35)))), RED,
                  glow=(255, 30, 60))
        d.text((850, 1110), "DAMAGE", font=font("anton.woff2", 60), fill=RED + (int(255 * a),), anchor="mm",
               stroke_width=5, stroke_fill=(10, 6, 20))


def vis_final(img, A, u, f, dur):
    rim(img, 300, 1100, 200, 330, (255, 180, 40), 0.7)
    rim(img, 790, 1100, 200, 330, (90, 160, 255), 0.8)
    A.put(img, A.sai["saitama_debout"], f, 300)
    A.put(img, A.gok["debout_regarde"], f, 790)
    d = ImageDraw.Draw(img, "RGBA")
    for (bx, col, lab) in ((80, YEL, "STRENGTH"), (W - 150, CYAN, "SPEED")):
        d.rounded_rectangle((bx, 720, bx + 70, 1260), radius=35, outline=col + (255,), width=6, fill=(10, 8, 24, 200))
        h = 520 * (0.92 + 0.06 * math.sin(u * 5 + bx))
        d.rounded_rectangle((bx + 10, 1250 - h, bx + 60, 1250), radius=25, fill=col + (255,))
        d.text((bx + 35, 1300), lab, font=font("mont900.woff2", 26), fill=col, anchor="mm")
    rnd = random.Random(int(u * 20))                                   # éclair entre les deux
    pts = [(400, 980)]
    for i in range(1, 9):
        pts.append((400 + i * 36, 980 + rnd.uniform(-40, 40)))
    pts.append((690, 980))
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).line(pts, fill=(200, 230, 255, 255), width=8)
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(5)))
    ImageDraw.Draw(img).line(pts, fill=WHITE, width=3)
    if u > dur * 0.55:
        pill(img, W / 2, 1390, "DROP YOUR ARGUMENT 👇".replace(" 👇", ""), YEL, font("mont900.woff2", 34),
             ease_out((u - dur * 0.55) / 0.3))


VIS = dict(versus=vis_versus, miss=vis_miss, light=vis_light, earth=vis_earth, scale=vis_scale, teleport=vis_teleport,
           ui=vis_ui, strength=vis_strength, final=vis_final)


# ------------------------------------------------------------------------------------------------- textes
def draw_title(img, b, u):
    pill(img, W / 2, 175, b["tag"], b["col"][0] if b["col"][0] != WHITE else YEL, a=ease_out(u / 0.25))
    t1, t2 = b["title"]
    s = back_out(u / 0.3)
    f1 = font("anton.woff2", int(118 * max(0.05, s)))
    while f1.size > 40 and ImageDraw.Draw(img).textlength(t1, font=f1) > W * 0.92:
        f1 = font("anton.woff2", f1.size - 4)
    glow_text(img, (W / 2, 290), t1, f1, b["col"][0], glow=(60, 20, 120))
    if t2:
        s2 = back_out((u - 0.12) / 0.3)
        f2 = font("anton.woff2", int(104 * max(0.05, s2)))
        while f2.size > 40 and ImageDraw.Draw(img).textlength(t2, font=f2) > W * 0.92:
            f2 = font("anton.woff2", f2.size - 4)
        glow_text(img, (W / 2, 405), t2, f2, b["col"][1], glow=tuple(int(c * 0.5) for c in b["col"][1]))


def chunks(words, maxw=4):
    out, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= maxw or w[0][-1] in ".,!?:;":
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def draw_caption(img, b, t):
    for ch in chunks(b["words"]):
        if ch[0][1] - 0.05 <= t < ch[-1][2] + 0.25 or (ch is chunks(b["words"])[-1] and ch[0][1] <= t < b["t0"] + b["dur"]):
            f_ = font("mont900.woff2", 58)
            d = ImageDraw.Draw(img, "RGBA")
            ws = [w for w, _, _ in ch]
            gaps = 18
            widths = [d.textlength(w, font=f_) for w in ws]
            total = sum(widths) + gaps * (len(ws) - 1)
            x = W / 2 - total / 2
            y = 1480
            d.rounded_rectangle((x - 30, y - 50, x + total + 30, y + 50), radius=24, fill=(8, 6, 18, 190))
            for (w, a, z), wd in zip(ch, widths):
                on = a <= t < z
                if on:
                    d.rounded_rectangle((x - 8, y - 38, x + wd + 8, y + 38), radius=12, fill=YEL + (255,))
                d.text((x, y), w, font=f_, anchor="lm", fill=(15, 10, 25) if on else WHITE)
                x += wd + gaps
            return


# ------------------------------------------------------------------------------------------------- rendu
def render(out, BEATS=BEATS, VIS=VIS, actors=None, music_start=8):
    total = voice(BEATS)
    A = (actors or Actors)()
    bg = background()
    n = int(total * FPS)
    tmp = Path(out).with_suffix(".video.mp4")
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r",
                          str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt",
                          "yuv420p", str(tmp)], stdin=subprocess.PIPE)
    for fi in range(n):
        t = fi / FPS
        bi = max(i for i, b in enumerate(BEATS) if t >= b["t0"] or i == 0)
        b = BEATS[bi]
        u = max(0.0, t - b["t0"]) if bi else t + 1.0                     # 1re partie : déjà en place à l'image 0
        img = bg.copy()
        VIS[b["vis"]](img, A, u, fi, b["dur"]) if b["vis"] != "versus" else VIS["versus"](img, A, u, fi)
        draw_title(img, b, u)
        draw_caption(img, b, t)
        if 0 < bi and 0 <= u < 0.12:                                     # flash de changement de partie (pas sur l'image 0)
            img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(150 * (1 - u / 0.12)))))
        p.stdin.write(img.convert("RGB").tobytes())
    p.stdin.close()
    p.wait()
    # ---------- son
    sr = BEATS[0]["sr"]
    na = int(total * sr) + sr
    audio = np.zeros(na, np.float32)

    def put(tt, x, g):
        i = int(tt * sr)
        if x is not None and 0 <= i < na:
            seg = np.asarray(x, np.float32)[: na - i]
            audio[i:i + len(seg)] += seg * g
    for b in BEATS:
        put(b["t0"], b["audio"], 1.0)
    from clipper.slides import domain

    def sfx(fam, seed=0):
        try:
            x = domain.sfx(fam, mode="anime", seed=seed, franchise="dragon ball")
            if x is None:
                return None
            from clipper.slides import fusion
            if fusion.RATE != sr:                                       # ré-échantillonnage simple
                idx = np.arange(0, len(x), fusion.RATE / sr)
                x = np.interp(idx, np.arange(len(x)), x)
            return x / (np.abs(x).max() or 1)
        except Exception:
            return None
    for i, b in enumerate(BEATS):
        put(b["t0"], sfx("vanish", i), 0.18)
        if b["vis"] == "miss":
            put(b["t0"] + min(1.4, b["dur"] * 0.35), sfx("hit", 1), 0.35)
        if b["vis"] == "teleport":
            put(b["t0"] + b["dur"] * 0.45, sfx("vanish", 9), 0.35)
        if b["vis"] == "ui":
            put(b["t0"], sfx("transform"), 0.22)
        for (at, fam, g, sd) in b.get("sfx", []):                     # bruitages propres au script : (s après début, famille, gain, graine)
            put(b["t0"] + at, sfx(fam, sd), g)
    music = LIB / "_music" / "Delirious.mp3"
    if music.exists():
        r_ = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(music_start), "-i", str(music), "-t", str(total), "-f", "f32le",
                             "-ac", "1", "-ar", str(sr), "-"], capture_output=True)
        mu = np.frombuffer(r_.stdout, np.float32)
        if len(mu):
            mu = mu / (np.percentile(np.abs(mu), 99.7) or 1)
            env = np.ones(len(mu), np.float32)
            fo = int(1.5 * sr)
            env[-fo:] = np.linspace(1, 0, fo)
            put(0, mu * env, 0.07)
    lvl = np.percentile(np.abs(audio), 99.8) or 1
    audio = np.tanh(audio / lvl * 0.9) * 0.6
    wav = Path(out).with_suffix(".wav")
    import soundfile as sf
    sf.write(str(wav), audio, sr)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(tmp), "-i", str(wav), "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "160k", "-shortest", str(out)], check=True)
    tmp.unlink()
    wav.unlink()
    from clipper.slides import render as rr
    rr.stamp_video(Path(out))
    print(out, round(total, 1))


if __name__ == "__main__":
    render(sys.argv[1])
