"""Edit « sosies » (11/11, référence de l'utilisateur : Sukuna / Grimmjow) : 2 persos qui se ressemblent, on alterne
sur chaque temps de la musique, images calées sur les YEUX (même endroit, même écart) → le changement de perso est
fluide. Transitions : zoom « punch », flash, whip (flou), tremblement. Accroche et fin : visage moitié A / moitié B.
Images de la bibliothèque (fournies par l'utilisateur) ; position des yeux mesurée à la main (fractions de l'image).
python3 tools/edit/twins.py sortie.mp4
"""
import math
import random
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from camedit import beats, hblur, SFX, W, H, FPS  # noqa: E402

LIB = ROOT / "library"
ANTON = str(ROOT / "tools/money_sim/fonts/anton.woff2")
PW, PH, PY = 1080, 1000, 470          # panneau principal (l'image), le reste = fond flou
EYE_Y = 430                           # hauteur des yeux dans le panneau
EYE_D = 250                           # écart entre les yeux (px)
G = LIB / "Jujutsu Kaisen/Satoru Gojo"
K = LIB / "_fusion/Kakashi"

# perso → [(image, centre des yeux (x, y en fractions), écart des yeux en fraction de la largeur)]
PAIR = {
    "GOJO": {"col": (110, 190, 255), "shots": [
        (G / "Gojo.jpg", (0.48, 0.35), 0.16),
        (G / "wallpaperflare.com_wallpaper(1).jpg", (0.495, 0.39), 0.13),
        (G / "gojo.png", (0.46, 0.39), 0.12),
        (G / "goj.jpg", (0.50, 0.36), 0.22),
        (G / "gojotaro.jpg", (0.47, 0.39), 0.10)]},
    "KAKASHI": {"col": (220, 70, 70), "shots": [
        (K / "3 MANGEKYO.jpg", (0.51, 0.48), 0.28),
        (LIB / "Naruto/Kakashi/Kakashi.jpg", (0.505, 0.45), 0.15),
        (K / "2 SHARINGAN.jpg", (0.21, 0.47), 0.26),
        (K / "1 BASE.jpg", (0.36, 0.27), 0.12)]},
}


def ease(x):
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


class Shot:
    def __init__(self, path, eye, dist):
        self.im = Image.open(path).convert("RGB")
        self.ex, self.ey = eye[0] * self.im.width, eye[1] * self.im.height
        self.dpx = dist * self.im.width

    def panel(self, zoom=1.0, dx=0.0, dy=0.0, rot=0.0, w=PW, h=PH):
        """vue w×h : les yeux à (w/2, EYE_Y), écart EYE_D × zoom ; agrandie au besoin pour couvrir le panneau"""
        sc = EYE_D * zoom / self.dpx
        sc = max(sc, w / self.im.width, h / self.im.height)
        cw, ch = w / sc, h / sc
        x0 = self.ex - (w / 2 + dx) / sc
        y0 = self.ey - (EYE_Y * h / PH + dy) / sc
        x0 = min(max(x0, 0), self.im.width - cw)
        y0 = min(max(y0, 0), self.im.height - ch)
        crop = self.im.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch)))
        out = crop.resize((w, h), Image.BILINEAR)
        if abs(rot) > 0.05:
            out = out.rotate(rot, resample=Image.BILINEAR, expand=False).resize((w, h))
        return out


def split(a, b, k=1.0, zoom=1.0):
    """visage moitié A (gauche) / moitié B (droite), raccord fondu ; k = avancée de la coupure (0 → 1)"""
    pa, pb = a.panel(zoom), b.panel(zoom)
    m = np.zeros((PH, PW), np.float32)
    cut = PW / 2
    xx = np.arange(PW)[None, :]
    m[:] = np.clip((xx - cut) / 30 + 0.5, 0, 1)
    if k < 1:                                                          # la moitié B glisse en place
        m *= (xx >= PW - PW / 2 * ease(k) - 1)
    out = np.asarray(pa, np.float32) * (1 - m[..., None]) + np.asarray(pb, np.float32) * m[..., None]
    img = Image.fromarray(out.astype(np.uint8))
    d = ImageDraw.Draw(img)
    d.line((cut, 0, cut, PH), fill=(255, 255, 255), width=4)
    return img


def text(img, xy, s, size, fill, stroke=8, anchor="mm"):
    f = ImageFont.truetype(ANTON, size)
    d = ImageDraw.Draw(img)
    d.text(xy, s, font=f, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=(8, 8, 12))


def compose(panel, t, title_k=1.0, label=None, label_col=(255, 255, 255)):
    """cadre 9:16 : fond = l'image floue et sombre, panneau au centre, titre en haut, nom du perso en bas"""
    small = panel.resize((54, 50), Image.BILINEAR).resize((W, H), Image.BILINEAR)
    bg = small.filter(ImageFilter.GaussianBlur(30))
    bg = Image.blend(bg, Image.new("RGB", (W, H), (0, 0, 0)), 0.55).convert("RGBA")
    bg.paste(panel, (0, PY))
    d = ImageDraw.Draw(bg)
    d.line((0, PY, W, PY), fill=(255, 255, 255), width=3)
    d.line((0, PY + PH, W, PY + PH), fill=(255, 255, 255), width=3)
    a_, b_ = list(PAIR)
    if title_k > 0:
        f = ImageFont.truetype(ANTON, 118)
        wa, wv, wb = f.getlength(a_), f.getlength(" VS "), f.getlength(b_)
        x = W / 2 - (wa + wv + wb) / 2
        y = 230
        for s, c in ((a_, PAIR[a_]["col"]), (" VS ", (255, 255, 255)), (b_, PAIR[b_]["col"])):
            d.text((x, y), s, font=f, fill=c, anchor="lm", stroke_width=8, stroke_fill=(8, 8, 12))
            x += f.getlength(s)
        text(bg, (W / 2, 360), "SAME ENERGY?", 70, (255, 230, 90), stroke=6)
    if label:
        text(bg, (W / 2, PY + PH + 185), label, 92, label_col)
    return bg.convert("RGB")


def render(out, music=LIB / "_music/Delirious.mp3", m_start=40.0, dur=15.0):
    bt, per = beats(music, m_start, dur + 2)
    names = list(PAIR)
    shots = {n: [Shot(*s) for s in PAIR[n]["shots"]] for n in names}
    HOOK = 1.1
    cuts = [b for b in bt if b > HOOK - 0.05 and b < dur - 2.0]
    slow = cuts[:8:2]                                                  # d'abord tous les 2 temps, puis à chaque temps
    cuts = slow + [c for c in cuts if c > slow[-1]]
    t_end = cuts[-1] + per * 2
    end = t_end + 2.2
    plan = []                                                          # (début, perso, image, zoom, effet)
    rnd = random.Random(7)
    idx = {n: 0 for n in names}
    fxs = ["punch", "whip", "flash", "punch", "shake", "whip"]
    for j, c in enumerate(cuts):
        n = names[j % 2]
        s = shots[n][idx[n] % len(shots[n])]
        idx[n] += 1
        zoom = 1.0 if j % 4 < 2 else 1.32                              # parfois plus serré sur les yeux
        plan.append((c, n, s, zoom, fxs[j % len(fxs)], rnd.choice((-1, 1))))
    A0, B0 = shots[names[0]][0], shots[names[1]][0]
    tmp = Path(tempfile.mkdtemp())
    events = []
    for fi in range(int(end * FPS)):
        t = fi / FPS
        if t < HOOK:                                                   # accroche : visage moitié / moitié
            p = split(A0, B0, k=min(1, t / 0.35), zoom=1.0 + 0.04 * t)
            frame = compose(p, t, label="?", label_col=(255, 230, 90))
        elif t >= t_end:                                               # fin : de nouveau moitié / moitié
            u = t - t_end
            p = split(A0, B0, k=min(1, u / 0.3), zoom=1.08 + 0.03 * u)
            frame = compose(p, t, label="WHO DID IT BETTER?", label_col=(255, 230, 90))
            if u < 0.12:
                a = np.asarray(frame, np.float32)
                frame = Image.fromarray(np.clip(a + (255 - a) * 0.8 * (1 - u / 0.12), 0, 255).astype(np.uint8))
        else:
            k = max(j for j in range(len(plan)) if plan[j][0] <= t + 1e-6) if t >= plan[0][0] else 0
            c, n, s, zoom, fx, sd = plan[k]
            e = t - c
            z = zoom * (1.0 + 0.05 * e)
            dx = dy = rot = 0.0
            if fx == "punch":
                z *= 1 + 0.16 * math.exp(-e * 11)
            if fx == "whip":
                dx = sd * 420 * (1 - ease(e / 0.14))
            if fx == "shake":
                r = random.Random(fi)
                amp = 22 * math.exp(-e * 8)
                dx, dy = r.uniform(-amp, amp), r.uniform(-amp, amp)
                rot = r.uniform(-1.2, 1.2) * math.exp(-e * 8)
            p = s.panel(z, dx, dy, rot)
            if fx == "whip" and e < 0.14:
                full = np.pad(np.asarray(p, np.float32) / 255.0, ((0, H - PH), (0, 0), (0, 0)), mode="edge")
                a = hblur(full, int(240 * (1 - e / 0.14)))[:PH]            # hblur travaille en H×W
                p = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
            if fx in ("flash", "punch") and e < 0.1:
                a = np.asarray(p, np.float32)
                p = Image.fromarray(np.clip(a + (255 - a) * (0.75 if fx == "flash" else 0.35) * (1 - e / 0.1), 0, 255)
                                    .astype(np.uint8))
            frame = compose(p, t, label=n, label_col=PAIR[n]["col"])
        frame.save(tmp / f"{fi:05d}.jpg", quality=92)
    for c, n, s, zoom, fx, sd in plan:
        if fx == "whip":
            events.append(c)
    # --- audio : musique + whoosh sur les whips + boum à la fin
    sr = 44100
    tot = int(end * sr) + sr
    mix = np.zeros(tot, np.float32)

    def pcm(path, ss=0.0, d_=None, gain=1.0):
        cmd = ["ffmpeg", "-v", "error", "-ss", str(ss)] + (["-t", str(d_)] if d_ else []) + \
              ["-i", str(path), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"]
        return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32) * gain

    def put(t, s_):
        a_ = int(t * sr)
        s_ = s_[:max(0, tot - a_)]
        mix[a_:a_ + len(s_)] += s_

    mu = pcm(music, m_start, end + 1, 0.6)
    fade = int(1.0 * sr)
    if len(mu) > int(end * sr):
        mu[int(end * sr) - fade:int(end * sr)] *= np.linspace(1, 0, fade)
    put(0, mu)
    rng = np.random.default_rng(2)
    Lw = int(0.3 * sr)
    env = np.exp(-np.linspace(0, 7, Lw)) * (1 - np.exp(-np.linspace(0, 80, Lw)))
    wh = np.convolve(rng.standard_normal(Lw).astype(np.float32), np.ones(12) / 12, "same") * env * 0.45
    for c in events:
        put(c, wh)
    put(t_end, pcm(SFX / "low_frequency_explosion_000.ogg", gain=0.45))
    mix = np.tanh(mix[:int(end * sr)] * 1.1) * 0.9
    wav = tmp / "a.wav"
    with wave.open(str(wav), "wb") as w_:
        w_.setnchannels(1)
        w_.setsampwidth(2)
        w_.setframerate(sr)
        w_.writeframes((mix * 32767).astype(np.int16).tobytes())
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", str(tmp / "%05d.jpg"), "-i", str(wav),
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", str(out)], check=True)
    from clipper.slides import render as R
    R.stamp_video(Path(out))
    print(out, round(end, 2), "s", len(plan), "coupes", "tempo", round(60 / per))


if __name__ == "__main__":
    render(sys.argv[1])
