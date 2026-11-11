"""Jeux de caméra façon « edit » TikTok (11/11, référence de l'utilisateur : présentation de persos JJK puis Sukuna).
Effets : whip pan (la caméra file d'un perso au suivant, flou de mouvement + traits de vitesse), étalonnage d'une couleur
par perso, lente avancée de caméra, particules, zoom « punch » + tremblement + aberration chromatique sur les temps forts,
flash blanc, passage au noir, nom écrit lettre par lettre (Cinzel, lueur). Coupes calées sur les temps de la musique.
Images fixes de la bibliothèque (pas d'extraits d'anime).
python3 tools/edit/camedit.py sortie.mp4
"""
import math
import random
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
W, H, FPS = 1080, 1920, 30
LIB = ROOT / "library"
J = LIB / "Jujutsu Kaisen"
FONT = str(ROOT / "tools/money_sim/fonts/cinzel900.woff2")
SFX = ROOT / "clipper/assets/sfx"

# (image, centre du visage en fractions, nom, couleur d'étalonnage)
SHOTS = [
    (J / "Yuji Itadori/Yuji.jpg", (0.33, 0.40), "YUJI", (230, 70, 70)),
    (J / "Megumi Fushiguro/megumi.jpg", (0.52, 0.32), "MEGUMI", (170, 90, 230)),
    (J / "Toji Fushiguro/toji.jpg", (0.47, 0.32), "TOJI", (80, 210, 150)),
    (J / "Satoru Gojo/gojo.png", (0.42, 0.42), "GOJO", (90, 180, 255)),
    (J / "Sukuna/sukuna.jpg", (0.62, 0.40), "SUKUNA", (255, 60, 40)),
]


# ------------------------------------------------------------------------------------------------ musique / temps
def beats(music, start, dur):
    """temps des battements (s, depuis `start`) : flux spectral + tempo par autocorrélation, grille calée sur les attaques"""
    sr = 22050
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(start), "-t", str(dur + 1), "-i", str(music), "-ac", "1",
                          "-ar", str(sr), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32)
    hop, n = 512, 2048
    frames = np.lib.stride_tricks.sliding_window_view(x, n)[::hop] * np.hanning(n)
    S = np.log1p(np.abs(np.fft.rfft(frames, axis=1)))
    flux = np.maximum(0, np.diff(S, axis=0)).sum(1)
    flux = (flux - flux.mean()) / (flux.std() + 1e-9)
    fr = sr / hop
    ac = np.correlate(flux, flux, "full")[len(flux) - 1:]
    lo, hi = int(fr * 60 / 180), int(fr * 60 / 70)
    period = lo + int(np.argmax(ac[lo:hi]))
    phase = max(range(period), key=lambda p: flux[p::period].sum())
    return [(phase + k * period) / fr for k in range(int(len(flux) / period) + 1)], period / fr


# ------------------------------------------------------------------------------------------------ image
def ease(x):
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


def grade(im, col, amount=0.6):
    """étalonnage : la luminance passe par noir → couleur → blanc, mélangée à l'image, contraste + vignette"""
    a = np.asarray(im, np.float32) / 255.0
    lum = a @ np.array([0.299, 0.587, 0.114], np.float32)
    lum = np.clip((lum - 0.08) * 1.25, 0, 1)
    c = np.array(col, np.float32) / 255.0
    lo = np.clip(lum * 2, 0, 1)[..., None] * c
    hi = np.clip(lum * 2 - 1, 0, 1)[..., None]
    tone = lo + hi * (1 - c)
    out = a * (1 - amount) + tone * amount
    yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]]
    v = ((xx / a.shape[1] - 0.5) ** 2 * 1.2 + (yy / a.shape[0] - 0.45) ** 2) ** 0.5
    out *= np.clip(1.25 - v * 1.3, 0.25, 1)[..., None]
    return np.clip(out, 0, 1)


class Shot:
    def __init__(self, path, face, name, col):
        src = Image.open(path).convert("RGB")
        k = H * 1.14 / src.height                                   # marge pour avancer / trembler
        self.im = src.resize((round(src.width * k), round(src.height * k)), Image.LANCZOS)
        self.fx, self.fy = face[0] * self.im.width, face[1] * self.im.height
        self.name, self.col = name, col
        self.base = grade(self.im, col)                              # étalonné une fois (float 0-1)

    def frame(self, zoom, dx=0.0, dy=0.0):
        """vue 1080×1920 centrée sur le visage, zoom ≥ 1 (1 = la hauteur de l'image source agrandie)"""
        h, w = self.base.shape[:2]
        cw, ch = W / 1.14 / zoom * (h / H), H / 1.14 / zoom * (h / H)
        cx = min(max(self.fx + dx, cw / 2), w - cw / 2)
        cy = min(max(self.fy + H * 0.08 / zoom + dy, ch / 2), h - ch / 2)
        box = (int(cx - cw / 2), int(cy - ch / 2), int(cx + cw / 2), int(cy + ch / 2))
        crop = Image.fromarray((self.base[box[1]:box[3], box[0]:box[2]] * 255).astype(np.uint8))
        return np.asarray(crop.resize((W, H), Image.BILINEAR), np.float32) / 255.0


def hblur(a, k):
    """flou de mouvement horizontal (boîte de k px), calculé à mi-résolution"""
    if k < 3:
        return a
    small = a[::2, ::2]
    k2 = max(1, int(k / 2))
    c = np.cumsum(np.pad(small, ((0, 0), (k2, k2), (0, 0)), mode="edge"), axis=1)
    out = (c[:, 2 * k2:] - c[:, :-2 * k2]) / (2 * k2)
    out = out[:, :small.shape[1]]
    return np.repeat(np.repeat(out, 2, 0), 2, 1)[:H, :W]


def chroma(a, s):
    if s < 1:
        return a
    s = int(s)
    out = a.copy()
    out[:, s:, 0] = a[:, :-s, 0]
    out[:, :-s, 2] = a[:, s:, 2]
    return out


def speed_lines(a, n, alpha, seed):
    rnd = random.Random(seed)
    lay = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(lay)
    for _ in range(n):
        y = rnd.uniform(0, H)
        x = rnd.uniform(-200, W)
        L = rnd.uniform(200, 700)
        d.line((x, y, x + L, y), fill=int(255 * alpha * rnd.uniform(0.4, 1)), width=rnd.choice((2, 3, 4)))
    m = np.asarray(lay, np.float32)[..., None] / 255.0
    return a * (1 - m) + m


def particles(img, t, col, seed):
    d = ImageDraw.Draw(img, "RGBA")
    rnd = random.Random(seed)
    for _ in range(70):
        x0, y0 = rnd.uniform(0, W), rnd.uniform(0, H)
        sp = rnd.uniform(40, 160)
        y = (y0 - t * sp) % H
        x = x0 + math.sin(t * 1.5 + x0) * 20
        L = rnd.uniform(4, 18)
        c = tuple(min(255, int(v * 0.6 + 120)) for v in col)
        d.line((x, y, x + L * 0.3, y + L), fill=c + (int(rnd.uniform(90, 200)),), width=2)


def name_text(img, text, n_letters, y, size, col=(255, 255, 255), glow=(255, 255, 255)):
    if n_letters <= 0:
        return
    f = ImageFont.truetype(FONT, size)
    full_w = f.getlength(text)
    x0 = W / 2 - full_w / 2
    s = text[:n_letters]
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(lay).text((x0, y), s, font=f, fill=glow + (255,), anchor="lm")
    g = lay.filter(ImageFilter.GaussianBlur(size * 0.18))
    img.alpha_composite(g)
    img.alpha_composite(g)
    ImageDraw.Draw(img).text((x0, y), s, font=f, fill=col, anchor="lm")


# ------------------------------------------------------------------------------------------------ montage
def render(out, music=LIB / "_music/Delirious.mp3", m_start=40.0):
    bt, per = beats(music, m_start, 12)
    bt = [b for b in bt if b > 0.25]
    # 4 présentations d'un temps chacune (2 temps si tempo rapide), puis Sukuna sur un temps fort
    step = 2 if per < 0.45 else 1
    cuts = [0.0] + [bt[i * step] for i in range(1, 5)]
    t_suk = cuts[4]
    sk_beats = [b for b in bt if b > t_suk + 0.05][:8]                  # temps forts pendant Sukuna
    end = (sk_beats[-1] if sk_beats else t_suk + 3) + per * 1.2
    shots = [Shot(*s) for s in SHOTS]
    WH = 0.2                                                            # durée d'un whip pan
    tmp = Path(tempfile.mkdtemp())
    n = int(end * FPS)
    whips, hits = [], []
    for i in range(n):
        t = i / FPS
        k = max(j for j in range(5) if cuts[j] <= t + 1e-6)
        # --- whip pan entre deux présentations (centré sur la coupe)
        nxt = next((c for c in cuts[1:4] if abs(t - c) < WH / 2), None)
        if nxt is not None:
            j = cuts.index(nxt)
            p = (t - (nxt - WH / 2)) / WH                               # 0 → 1
            if p < 0.5:
                sh, off = shots[j - 1], -ease(p * 2) * W * 0.9
                a = sh.frame(1.0 + 0.05 * (nxt - cuts[j - 1]), dx=0)
            else:
                sh, off = shots[j], (1 - ease((p - 0.5) * 2)) * W * 0.9
                a = sh.frame(1.0)
            a = np.roll(a, int(off), axis=1)
            sp = math.sin(p * math.pi)
            a = hblur(a, 260 * sp)
            a = speed_lines(a, 26, 0.5 * sp, i)
            img = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
            if abs(p - 0.5) < 0.5 / (WH * FPS):
                whips.append(t)
        elif k < 4:
            # --- présentation : lente avancée + dérive latérale
            u = t - cuts[k]
            sh = shots[k]
            a = sh.frame(1.0 + 0.05 * u, dx=-30 * u)
            img = Image.fromarray((a * 255).astype(np.uint8)).convert("RGBA")
            particles(img, t, sh.col, k)
            letters = int(u / 0.05)
            name_text(img, sh.name, letters, H * 0.71, 120, glow=sh.col)
        else:
            # --- Sukuna : passage au noir, flash, zooms brusques sur les temps forts, tremblement, chroma
            u = t - t_suk
            sh = shots[4]
            last = max([b for b in sk_beats if b <= t] or [t_suk])
            e = t - last
            punch = 0.16 * math.exp(-e * 9)
            zoom = 1.02 + 0.03 * u + punch + (0.12 if len([b for b in sk_beats if b <= t]) >= 4 else 0)
            rnd = random.Random(i)
            sk = 26 * math.exp(-e * 10)
            a = sh.frame(zoom, dx=rnd.uniform(-sk, sk), dy=rnd.uniform(-sk, sk))
            a = chroma(a, 16 * math.exp(-e * 12))
            if e < 0.12:                                                # flou radial bref sur l'impact
                a = a * 0.6 + hblur(a, 60) * 0.4
            a = a + (1 - a) * (0.85 * math.exp(-e * 14))                # flash blanc
            if u < 0.12:
                a = a * (u / 0.12) * 0.2                                # passage au noir juste avant
            img = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
            particles(img, t, sh.col, 9)
            n_hit = len([b for b in sk_beats if b <= t])
            name_text(img, "SUKUNA", min(6, max(0, n_hit - 1)), H * 0.66, 190, glow=(255, 90, 60))
            if e < 1 / FPS and t > t_suk:
                hits.append(t)
        img.convert("RGB").save(tmp / f"{i:05d}.jpg", quality=92)
    hits = [t_suk] + hits
    # --- audio : musique + whoosh à chaque whip + impacts sur Sukuna
    sr = 44100
    tot = int(end * sr) + sr
    mix = np.zeros(tot, np.float32)

    def load(path, gain=1.0):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                             capture_output=True, check=True).stdout
        return np.frombuffer(raw, np.float32) * gain

    def put(t, s):
        a = int(t * sr)
        s = s[:max(0, tot - a)]
        mix[a:a + len(s)] += s

    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(m_start), "-t", str(end + 1), "-i", str(music), "-ac", "1",
                          "-ar", str(sr), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    mu = np.frombuffer(raw, np.float32) * 0.55
    put(0, mu)
    rng = np.random.default_rng(1)
    L = int(0.35 * sr)
    noise = rng.standard_normal(L).astype(np.float32)
    env = np.sin(np.linspace(0, math.pi, L)) ** 2
    sweep = np.cumsum(np.linspace(0.02, 0.35, L))                          # bruit filtré qui monte = whoosh
    wh = np.convolve(noise, np.ones(18) / 18, "same") * env * (0.6 + 0.4 * np.sin(sweep)) * 0.5
    for t in whips:
        put(max(0, t - 0.17), wh)
    boom = load(SFX / "low_frequency_explosion_000.ogg", 0.55)
    punch = load(SFX / "impact_punch_heavy_000.ogg", 0.45)
    put(t_suk, boom)
    for t in hits[1:]:
        put(t, punch)
    mix = np.tanh(mix * 1.1) * 0.9
    wav = tmp / "a.wav"
    import wave
    with wave.open(str(wav), "wb") as w_:
        w_.setnchannels(1)
        w_.setsampwidth(2)
        w_.setframerate(sr)
        w_.writeframes((mix[:int(end * sr)] * 32767).astype(np.int16).tobytes())
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", str(tmp / "%05d.jpg"), "-i", str(wav),
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", str(out)], check=True)
    from clipper.slides import render as R
    R.stamp_video(Path(out))
    print(out, round(end, 2), "s", "cuts", [round(c, 2) for c in cuts], "tempo", round(60 / per))


if __name__ == "__main__":
    render(sys.argv[1])
