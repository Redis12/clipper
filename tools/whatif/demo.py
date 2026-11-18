"""Démo 30 s du format long « What If » (18/11), d'après l'analyse ANALYSE_WHAT_IF.md (cold open → chiffre → titre → règle).
Sujet de la démo : « What if you could stop time for 5 seconds? ». Tout est dessiné en code (stickmans ORIGINAUX,
décors crépuscule), 16:9 1920×1080, 24 i/s. Pas encore de voix (sous-titres à l'écran) : la voix Adam se cale ensuite.
python3 tools/whatif/demo.py sortie.mp4
"""
from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from clipper.slides import fusion, render  # noqa: E402

W, H, FPS = 1920, 1080, 24
FONT = str(ROOT / "tools/money_sim/fonts/anton.woff2")
MONT = ROOT / "tools/money_sim/fonts"
RED, YEL, INK = (214, 52, 48), (250, 196, 40), (14, 12, 18)
RATE = fusion.RATE
HY = ROOT / "library/_sfx/Helton Yan's Old-School Shonen SFX"


def F(sz):
    return ImageFont.truetype(FONT, int(sz))


def lerp(a, b, k):
    return a + (b - a) * k


def ease(k):
    k = min(1, max(0, k))
    return k * k * (3 - 2 * k)


# --------------------------------------------------------------------------- décor (crépuscule)

def sky(top=(52, 34, 84), mid=(150, 80, 110), low=(250, 160, 90)):
    y = np.linspace(0, 1, H)[:, None]
    c = np.where(y < 0.55, np.array(top) + (np.array(mid) - np.array(top)) * (y / 0.55),
                 np.array(mid) + (np.array(low) - np.array(mid)) * ((y - 0.55) / 0.45))
    img = np.repeat(c[:, None, :], W, 1).reshape(H, W, 3)
    return Image.fromarray(img.astype(np.uint8))


def street(seed=1, sun=(0.72, 0.58)):
    im = sky().convert("RGBA")
    d = ImageDraw.Draw(im, "RGBA")
    sx, sy = W * sun[0], H * sun[1]
    for r, a in ((420, 40), (260, 70), (120, 255)):                       # soleil + halo
        d.ellipse((sx - r, sy - r, sx + r, sy + r), fill=(255, 220, 150, a))
    for k in range(10):                                                   # rayons
        ang = -math.pi / 2 + (k - 4.5) * 0.18
        d.polygon([(sx, sy), (sx + 1600 * math.cos(ang - 0.03), sy + 1600 * math.sin(ang - 0.03)),
                   (sx + 1600 * math.cos(ang + 0.03), sy + 1600 * math.sin(ang + 0.03))], fill=(255, 230, 190, 14))
    rnd = np.random.default_rng(seed)
    x = -40
    while x < W + 40:                                                     # immeubles + fenêtres chaudes
        bw, bh = rnd.integers(180, 320), rnd.integers(300, 620)
        col = tuple(int(v) for v in rnd.integers(46, 70, 3)) + (255,)
        d.rectangle((x, 820 - bh, x + bw, 860), fill=col)
        for wy in range(820 - bh + 40, 800, 80):
            for wx in range(x + 24, x + bw - 40, 62):
                if rnd.random() < 0.55:
                    d.rectangle((wx, wy, wx + 32, wy + 44), fill=(255, 196, 96, 255))
                else:
                    d.rectangle((wx, wy, wx + 32, wy + 44), fill=(40, 30, 60, 255))
        x += bw + rnd.integers(10, 40)
    d.rectangle((0, 860, W, H), fill=(58, 40, 62, 255))                    # trottoir
    d.rectangle((0, 860, W, 872), fill=(96, 70, 90, 255))
    for k in range(6):                                                     # silhouettes au 1er plan (profondeur)
        tx = 120 + k * 360
        d.ellipse((tx - 90, 600, tx + 90, 780), fill=(30, 20, 40, 255))
        d.rectangle((tx - 8, 760, tx + 8, 870), fill=(30, 20, 40, 255))
    return im.filter(ImageFilter.GaussianBlur(0.6))


# --------------------------------------------------------------------------- stickman original

def stickman(d, x, y, s=1.0, jacket=None, cap=None, pose=0.0, look=1, eyes="dot", arm=None, lean=0.0):
    """Stickman noir à tête ronde (pieds en (x, y)). pose = phase de marche, arm = angle du bras avant (radians)."""
    k = s
    hip = (x + lean * 20 * k, y - 150 * k)
    neck = (x + lean * 40 * k, y - 290 * k)
    lw = int(16 * k)
    sw = math.sin(pose) * 0.5
    for sgn in (1, -1):                                                     # jambes
        a = sgn * sw
        knee = (hip[0] + math.sin(a) * 75 * k, hip[1] + math.cos(a) * 75 * k)
        foot = (knee[0] + math.sin(a * 0.6) * 75 * k, knee[1] + 75 * k)
        d.line([hip, knee, foot], fill=INK, width=lw, joint="curve")
    if jacket:                                                              # veste (repère du héros)
        d.polygon([(neck[0] - 42 * k, neck[1] + 10 * k), (neck[0] + 42 * k, neck[1] + 10 * k),
                   (hip[0] + 46 * k, hip[1] + 10 * k), (hip[0] - 46 * k, hip[1] + 10 * k)], fill=jacket)
    d.line([neck, hip], fill=INK, width=lw)
    a1 = arm if arm is not None else 0.25 + sw * 0.6                        # bras
    for sgn, aa in ((1, a1), (-1, 0.25 - sw * 0.6)):
        el = (neck[0] + math.sin(aa) * 70 * k * look, neck[1] + 20 * k + math.cos(aa) * 70 * k)
        hand = (el[0] + math.sin(aa) * 65 * k * look, el[1] + math.cos(aa) * 65 * k)
        d.line([(neck[0], neck[1] + 16 * k), el, hand], fill=(jacket[:3] if jacket else INK), width=lw + 2, joint="curve")
        d.ellipse((hand[0] - 10 * k, hand[1] - 10 * k, hand[0] + 10 * k, hand[1] + 10 * k), fill=INK)
    hr = 62 * k                                                              # tête
    hc = (neck[0] + 6 * k * look, neck[1] - hr + 6 * k)
    d.ellipse((hc[0] - hr, hc[1] - hr, hc[0] + hr, hc[1] + hr), fill=INK)
    ex = hc[0] + 18 * k * look
    if eyes == "wide":
        for dx in (-17, 17):
            d.ellipse((ex + dx * k - 13 * k, hc[1] - 14 * k, ex + dx * k + 13 * k, hc[1] + 12 * k), fill=(255, 255, 255))
            d.ellipse((ex + dx * k - 5 * k, hc[1] - 6 * k, ex + dx * k + 5 * k, hc[1] + 4 * k), fill=INK)
    elif eyes == "glow":
        for dx in (-17, 17):
            d.ellipse((ex + dx * k - 15 * k, hc[1] - 12 * k, ex + dx * k + 15 * k, hc[1] + 12 * k), fill=(120, 220, 255))
    else:
        for dx in (-16, 16):
            d.ellipse((ex + dx * k - 7 * k, hc[1] - 9 * k, ex + dx * k + 7 * k, hc[1] + 9 * k), fill=(255, 255, 255))
    if cap:
        d.chord((hc[0] - hr, hc[1] - hr - 4 * k, hc[0] + hr, hc[1] + hr * 0.4), 180, 360, fill=cap)
        d.rectangle((hc[0] + hr * 0.2 * look, hc[1] - 18 * k, hc[0] + hr * 1.5 * look, hc[1] - 4 * k) if look > 0 else
                    (hc[0] - hr * 1.5, hc[1] - 18 * k, hc[0] - hr * 0.2, hc[1] - 4 * k), fill=cap)
    return hc


# --------------------------------------------------------------------------- effets

def freeze_fx(im, k):
    """Le temps s'arrête : désaturé, bleuté, vignette."""
    if k <= 0:
        return im
    g = im.convert("L").convert("RGB")
    blue = Image.blend(g, Image.new("RGB", im.size, (70, 110, 190)), 0.35)
    return Image.blend(im.convert("RGB"), blue, min(1, k))


def subtitle(im, txt, a=1.0):
    if not txt:
        return
    d = ImageDraw.Draw(im, "RGBA")
    f = ImageFont.truetype(str(MONT / "mont800.woff2"), 54)
    tw = d.textlength(txt, font=f)
    d.rounded_rectangle((W / 2 - tw / 2 - 26, 940 - 44, W / 2 + tw / 2 + 26, 940 + 44), radius=18, fill=(0, 0, 0, int(150 * a)))
    d.text((W / 2, 940), txt, font=f, fill=(255, 255, 255, int(255 * a)), anchor="mm")


# --------------------------------------------------------------------------- scènes

BG1 = None


def scene_rain(t, T):                                   # 0–5 s : la pluie se fige autour de lui
    im = BG1.copy()
    d = ImageDraw.Draw(im, "RGBA")
    fz = ease((t - 2.6) / 0.35)
    rnd = np.random.default_rng(4)
    for i in range(260):
        x0, y0, sp = rnd.uniform(0, W), rnd.uniform(-H, H), rnd.uniform(1400, 1900)
        tt = min(t, 2.6 + (t - 2.6) * 0.02) if t > 2.6 else t
        y = (y0 + sp * tt) % (H + 100) - 50
        ln = 34 * (1 - fz) + 6
        d.line((x0, y, x0 - 6, y + ln), fill=(200, 210, 255, 150), width=3)
        if fz > 0.5 and i % 9 == 0:
            d.ellipse((x0 - 4, y - 4, x0 + 4, y + 4), fill=(230, 240, 255, 200))
    walk = t * 7 if t < 2.6 else 2.6 * 7
    hx = lerp(700, 860, min(t, 2.6) / 2.6)
    stickman(d, hx, 880, 1.25, jacket=RED, pose=walk, look=1, eyes="glow" if t > 2.4 else "dot")
    if 2.4 < t < 3.2:                                                       # onde au moment où tout s'arrête
        r = (t - 2.4) / 0.8 * 1500
        d.ellipse((hx - r, 560 - r, hx + r, 560 + r), outline=(150, 220, 255, int(220 * (1 - (t - 2.4) / 0.8))), width=10)
    im = freeze_fx(im, fz * 0.9)
    sub = "It starts raining." if t < 2.4 else "Then… it doesn't."
    return im, sub


def scene_icecream(t, T):                               # 5–11 s : la glace du pote, remise sur le cornet
    im = BG2.copy()
    d = ImageDraw.Draw(im, "RGBA")
    fz = 1.0 if 1.2 < t < 4.0 else 0.0
    # pote (casquette jaune) + héros
    stickman(d, 1180, 880, 1.25, cap=YEL, look=-1, arm=0.9, eyes="wide" if t > 4.0 else "dot")
    hero_x = 700 if t < 1.2 else (lerp(700, 1030, ease((t - 1.6) / 1.2)) if t < 4.0 else 1030)
    stickman(d, hero_x, 880, 1.25, jacket=RED, look=1, pose=t * 6 if 1.6 < t < 2.8 else 0,
             arm=1.6 if 2.8 < t < 4.0 else None, eyes="glow" if fz else "dot")
    # boule de glace : tombe, se fige, remise en place
    cone = (1095, 640)
    if t < 1.2:
        bx, by = cone[0], cone[1] - 40 + 300 * (t / 1.2) ** 2 * 0.5
    elif t < 3.0:
        bx, by = cone[0] + 10, cone[1] + 110
    elif t < 3.6:
        k = ease((t - 3.0) / 0.6)
        bx, by = cone[0] + 10 - 10 * k, lerp(cone[1] + 110, cone[1] - 40, k)
    else:
        bx, by = cone[0], cone[1] - 40
    d.polygon([(cone[0] - 26, cone[1]), (cone[0] + 26, cone[1]), (cone[0], cone[1] + 90)], fill=(210, 160, 90))
    d.ellipse((bx - 40, by - 40, bx + 40, by + 40), fill=(255, 170, 200), outline=INK, width=4)
    im = freeze_fx(im, fz * 0.9)
    if t > 4.2:
        d2 = ImageDraw.Draw(im, "RGBA")
        d2.rounded_rectangle((1240, 470, 1640, 560), radius=26, fill=(255, 255, 255, 240), outline=INK, width=4)
        d2.text((1440, 515), "Wait… what?", font=F(54), fill=INK, anchor="mm")
    sub = ["Your friend drops his ice cream.", "You don't even think.", "Back on the cone.", ""][min(3, int(t / 1.6))]
    return im, sub


def scene_fact(t, T):                                   # 11–15 s : le chiffre
    im = sky((24, 20, 46), (40, 30, 70), (70, 40, 80)).convert("RGBA")
    d = ImageDraw.Draw(im, "RGBA")
    cx, cy = W / 2, 470
    d.ellipse((cx - 260, cy - 260, cx + 260, cy + 260), fill=(250, 245, 235), outline=INK, width=14)
    for k in range(12):
        a = k * math.pi / 6
        d.line((cx + 220 * math.sin(a), cy - 220 * math.cos(a), cx + 240 * math.sin(a), cy - 240 * math.cos(a)), fill=INK, width=8)
    ang = 0 if t > 1.2 else t * 6                          # l'aiguille tourne, puis se fige
    d.line((cx, cy, cx + 200 * math.sin(ang), cy - 200 * math.cos(ang)), fill=RED, width=10)
    d.ellipse((cx - 16, cy - 16, cx + 16, cy + 16), fill=INK)
    if t > 1.2:
        k = ease((t - 1.2) / 0.3)
        d.text((cx, 790), "5.00 s", font=F(140 * (0.8 + 0.2 * k)), fill=(140, 220, 255), anchor="mm", stroke_width=8, stroke_fill=INK)
    sub = "A blink lasts a tenth of a second." if t < 1.6 else "You get five full seconds… of frozen time."
    return im, sub


def scene_title(t, T):                                  # 15–19 s : le titre (APRÈS l'accroche)
    im = BG1.copy()
    im = freeze_fx(im, 0.5)
    d = ImageDraw.Draw(im, "RGBA")
    stickman(d, W / 2, 900, 1.0, jacket=RED, eyes="glow")
    k = ease(t / 0.5)
    d.text((W / 2, 250), "WHAT IF YOU COULD", font=F(96), fill=(255, 255, 255, int(255 * k)), anchor="mm", stroke_width=6, stroke_fill=INK)
    d.text((W / 2, 380), "STOP TIME FOR 5 SECONDS?", font=F(132), fill=(140, 220, 255, int(255 * k)), anchor="mm", stroke_width=8, stroke_fill=INK)
    d.text((W / 2, 480), "AN ANIMELORE WHAT IF", font=F(40), fill=(255, 220, 150, int(220 * k)), anchor="mm")
    return im, ""


def scene_rule(t, T):                                   # 19–30 s : la règle du jeu
    im = sky((30, 26, 60), (60, 44, 90), (110, 70, 100)).convert("RGBA")
    d = ImageDraw.Draw(im, "RGBA")
    # 3 cases : MONDE figé / TOI tu bouges / RECHARGE 1 h
    boxes = [("THE WORLD", "FROZEN", (140, 220, 255)), ("YOU", "MOVE", RED), ("RECHARGE", "1 HOUR", YEL)]
    for i, (a, b, col) in enumerate(boxes):
        k = ease((t - i * 1.6) / 0.4)
        if k <= 0:
            continue
        x = 360 + i * 600
        d.rounded_rectangle((x - 230, 300, x + 230, 760), radius=36, fill=(20, 16, 36, int(230 * k)), outline=col + (255,), width=8)
        d.text((x, 380), a, font=F(66), fill=(255, 255, 255), anchor="mm")
        d.text((x, 680), b, font=F(86), fill=col, anchor="mm", stroke_width=5, stroke_fill=INK)
        if i == 0:
            ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
            ImageDraw.Draw(ov).rounded_rectangle((x - 222, 308, x + 222, 752), radius=30, fill=(70, 110, 190, 70))
            im.alpha_composite(ov)
            d = ImageDraw.Draw(im, "RGBA")
            stickman(d, x, 640, 0.55, cap=YEL, eyes="dot")
        elif i == 1:
            stickman(d, x, 640, 0.55, jacket=RED, pose=t * 8, eyes="glow")
        else:
            bw = 300
            d.rounded_rectangle((x - bw / 2, 470, x + bw / 2, 560), radius=14, outline=(255, 255, 255), width=6)
            fill = (t - 3.2) / 6 if t > 3.2 else 0
            d.rounded_rectangle((x - bw / 2 + 10, 480, x - bw / 2 + 10 + (bw - 20) * min(1, max(0.05, fill)), 550), radius=8, fill=YEL)
    subs = ["The world freezes.", "You don't.", "But it only recharges once an hour.", "So… what would you use it for?"]
    sub = subs[min(3, int(t / 2.7))]
    return im, sub


SCENES = [(scene_rain, 5.0), (scene_icecream, 6.0), (scene_fact, 4.0), (scene_title, 4.0), (scene_rule, 11.0)]


def soundtrack(total, cuts):
    buf = np.zeros(int(total * RATE) + RATE, np.float32)

    def add(s, t, g):
        i = int(t * RATE)
        if i < 0:
            s, i = s[-i:], 0
        n = min(len(s), len(buf) - i)
        if n > 0:
            buf[i:i + n] += s[:n] * g
    t = np.arange(len(buf)) / RATE                     # nappe douce (accords lents) : musique de fond continue
    pad = np.zeros_like(buf)
    chords = [(220.0, 261.6, 329.6), (196.0, 246.9, 293.7), (174.6, 220.0, 261.6), (196.0, 246.9, 329.6)]
    for i, ch in enumerate(chords * 3):
        a, b = i * 2.6, i * 2.6 + 3.2
        m = (t >= a) & (t < b)
        env = np.sin(np.clip((t[m] - a) / (b - a), 0, 1) * math.pi)
        for f in ch:
            pad[m] += np.sin(2 * math.pi * f * t[m]) * env * 0.05
    buf += pad
    rain = np.random.default_rng(1).normal(0, 1, int(2.6 * RATE)).astype(np.float32) * 0.05
    add(rain, 0, 1.0)
    whoosh = fusion.load_sound(HY / "FGHTClth_Anime Swing 2.ogg")
    boom = fusion.load_sound(HY / "EXPLDsgn_Anime Explosion 1.ogg")
    for c in cuts:
        add(whoosh, max(0, c - 0.15), 0.25)
    for tz in (2.5, 6.2):                              # « vwoom » du temps qui s'arrête = son inversé
        add(boom[::-1].copy(), tz - len(boom) / RATE + 0.1, 0.35)
    tt = np.arange(int(0.05 * RATE)) / RATE
    tick = (np.sin(2 * math.pi * 1800 * tt) * np.exp(-tt * 80)).astype(np.float32)
    for k in range(6):                                 # tic-tac de l'horloge
        add(tick, 15.0 - 4.0 + k * 0.2, 0.3)
    return np.tanh(buf * 1.2) / math.tanh(1.2) * 0.6


def main(out):
    global BG1, BG2
    BG1 = street(1)
    BG2 = street(5, sun=(0.3, 0.55))
    out = Path(out)
    tmp = out.with_suffix(".raw.mp4")
    ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                           "-pix_fmt", "yuv420p", str(tmp)], stdin=subprocess.PIPE)
    cuts, t0 = [], 0.0
    prev = None
    for fn, T in SCENES:
        cuts.append(t0)
        for i in range(int(T * FPS)):
            t = i / FPS
            im, sub = fn(t, T)
            im = im.convert("RGB")
            if prev is not None and t < 0.25:              # fondu enchaîné court entre les scènes
                im = Image.blend(prev, im, t / 0.25)
            zoom = 1 + 0.03 * (t / T)                      # caméra qui avance doucement
            if zoom > 1:
                cw, ch = int(W / zoom), int(H / zoom)
                im = im.crop(((W - cw) // 2, (H - ch) // 2, (W + cw) // 2, (H + ch) // 2)).resize((W, H), Image.BILINEAR)
            subtitle(im, sub)
            ff.stdin.write(im.tobytes())
            last = im
        prev = last
        t0 += T
    ff.stdin.close()
    ff.wait()
    wav = out.with_suffix(".wav")
    fusion.write_wav(wav, soundtrack(t0, cuts))
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(tmp), "-i", str(wav), "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", str(out)], check=True)
    tmp.unlink(); wav.unlink()
    render.stamp_video(out)
    return out


if __name__ == "__main__":
    print(main(sys.argv[1]))
