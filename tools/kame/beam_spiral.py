"""« One Kamehameha » (21/11, v2 demandée) : Goku tire UN seul Kamehameha, un vrai rayon continu (traînée complète
de ses mains jusqu'à la tête) qui tourne et tourne en spirale dans une planète et la creuse jusqu'au centre, où est le
boss. À chaque 10 % creusés, Goku passe à la forme suivante : le rayon change de couleur, grossit et accélère.
Terrain clair (planète rocheuse procédurale) contre le vide noir étoilé : on voit tout de suite ce qui est détruit.

python3 tools/kame/beam_spiral.py <sortie.mp4> [boss_image] [NOM]
"""
from __future__ import annotations

import math
import random
import subprocess
import sys
import wave
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))
from clipper.slides import fusion, render  # noqa: E402
from spiral import FORMS, Spiral, load, note  # noqa: E402

W, H, FPS = 1080, 1920, 30
L = ROOT / "library"
ANTON = str(ROOT / "tools/money_sim/fonts/anton.woff2")
MONT = str(ROOT / "tools/money_sim/fonts/mont800.woff2")
SFX = L / "_sfx/Dragon Ball SFX/Dragon Ball Z Sounds"
CHARGE = 1.1                                              # « KA-ME-HA-ME… » avant le tir


def font(p, s):
    return ImageFont.truetype(p, int(s))


def fbm(n, seed, octaves=6):
    rng = np.random.RandomState(seed)
    out = np.zeros((n, n), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        g = 4 * 2 ** o
        base = rng.rand(g, g).astype(np.float32)
        out += amp * cv2.resize(base, (n, n), interpolation=cv2.INTER_CUBIC)
        tot += amp
        amp *= 0.55
    return (out / tot - 0.5) * 2


def planet(n, seed=3):
    """Planète rocheuse claire : bruit fractal, cratères, éclairage sphérique, liseré lumineux."""
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    c = (n - 1) / 2
    dx, dy = (xx - c) / c, (yy - c) / c
    rr = np.sqrt(dx * dx + dy * dy)
    nz = fbm(n, seed)
    c1 = np.array([238, 206, 160], np.float32)            # sable clair
    c2 = np.array([186, 128, 84], np.float32)             # roche
    tcol = c1[None, None] * (0.5 + 0.5 * nz[..., None]) + c2[None, None] * (0.5 - 0.5 * nz[..., None])
    rng = random.Random(seed)
    shade = np.ones((n, n), np.float32)
    for _ in range(26):                                   # cratères
        cx, cy = rng.uniform(0.08, 0.92) * n, rng.uniform(0.08, 0.92) * n
        r = rng.uniform(0.02, 0.085) * n
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / r
        shade -= 0.22 * np.clip(1 - d, 0, 1) ** 0.6
        shade += 0.18 * np.exp(-((d - 1.0) / 0.12) ** 2) * ((xx - cx) * -0.7 + (yy - cy) * -0.7 > 0)
    z = np.sqrt(np.clip(1 - rr * rr, 0, 1))
    light = np.clip(0.35 + 0.75 * (z * 0.7 + (-dx * 0.45 - dy * 0.55) * 0.45), 0.25, 1.15)
    col = tcol * (shade * light)[..., None]
    rim = np.exp(-((rr - 0.985) / 0.02) ** 2)[..., None] * np.array([255, 230, 190], np.float32)
    col = np.clip(col + rim * 0.6, 0, 255).astype(np.uint8)
    a = (np.clip((1 - rr) * n * 0.5, 0, 1) * 255).astype(np.uint8)
    return np.dstack([col, a])


def main():
    out = Path(sys.argv[1])
    boss_path = Path(sys.argv[2]) if len(sys.argv) > 2 else L / "_fusion/DB Super Villains/10 JIREN.jpg"
    boss_name = sys.argv[3] if len(sys.argv) > 3 else "JIREN"
    rnd = random.Random(5)
    k = W / 1080
    CX, CY = W / 2, H * 0.545
    b = 86 * k                                            # largeur du sillon
    RD = 470 * k                                          # rayon de la planète
    core_r = 92 * k                                       # le boss au centre
    sp = Spiral(CX, CY, RD - b * 0.5, b, core_r + b * 0.55)
    GOKU = (W * 0.15, H * 0.265)
    HAND = (GOKU[0] + 75 * k, GOKU[1] + 60 * k)
    entry = sp.at(0)
    pre = math.hypot(entry[0] - HAND[0], entry[1] - HAND[1])   # bout de rayon des mains jusqu'à la planète

    # ------------------------------------------------ vitesse : une forme par dixième du chemin, chaque forme plus rapide
    nF = len(FORMS)
    Ltot = pre + sp.L
    seg = Ltot / nF
    v0 = 125 * k
    times = [CHARGE]
    for f in range(nF):
        times.append(times[-1] + seg / (v0 * 1.13 ** f))
    t_hit = times[-1]
    total = t_hit + 2.6

    def head(t):
        if t < CHARGE:
            return 0.0, 0
        for f in range(nF):
            if t < times[f + 1]:
                return seg * f + (t - times[f]) * v0 * 1.13 ** f, f
        return Ltot, nF - 1
    print(f"durée {total:.1f} s, chemin {Ltot:.0f}px, impact {t_hit:.1f} s")

    # ------------------------------------------------ calques fixes
    bg = np.zeros((H, W, 3), np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    bg[...] = np.array([4, 5, 16], np.float32)
    for (px, py, rr, col) in [(0.2, 0.2, 520, (30, 60, 170)), (0.85, 0.75, 560, (100, 30, 160)), (0.5, 0.98, 420, (20, 90, 160))]:
        g = np.exp(-(((xx - W * px) ** 2 + (yy - H * py) ** 2) / (rr * k) ** 2))
        bg += g[..., None] * np.array(col, np.float32) * 0.45
    srnd = np.random.RandomState(2)
    for _ in range(420):                                  # étoiles
        x, y = srnd.randint(0, W), srnd.randint(0, H)
        v = srnd.uniform(90, 255)
        cv2.circle(bg, (x, y), int(srnd.choice([1, 1, 1, 2])), (v, v, v), -1, cv2.LINE_AA)
    bg = np.clip(bg, 0, 255).astype(np.uint8)
    n = int(2 * RD)
    pl = planet(n)
    terrain = pl[..., :3].astype(np.float32)
    alpha0 = pl[..., 3].astype(np.float32) / 255
    eaten = np.zeros((n, n), np.uint8)
    x0, y0 = int(CX - RD), int(CY - RD)
    boss_ic = fusion.icon(str(boss_path), int(core_r * 2), (235, 50, 60))
    icons = [fusion.icon(str(L / "_fusion/Goku" / f[0]), int(200 * k), f[2]) for f in FORMS]
    fT = font(ANTON, 92 * k)

    def carve(s0, s1):
        for s_ in np.arange(s0, s1 + 1e-6, 3.0):
            x, y = sp.at(s_)
            cv2.circle(eaten, (int(round(x - x0)), int(round(y - y0))), int(b * 0.53), 255, -1, cv2.LINE_AA)

    s_carved = 0.0
    parts = []                                            # éclats de roche : x, y, vx, vy, t0, col, size
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                             "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                             "-pix_fmt", "yuv420p", str(out.with_suffix(".silent.mp4"))], stdin=subprocess.PIPE)
    notes_at = []
    next_note = 0.0
    hp_disp = 1.0
    for fr in range(int(total * FPS)):
        t = fr / FPS
        s_h, f = head(t)
        col = FORMS[f][2]
        s_path = max(0.0, s_h - pre)                      # position de la tête sur la spirale
        if s_path > s_carved:
            carve(max(0, s_carved - 3), s_path)
            hx_, hy_ = sp.at(s_path)
            ix = int(min(max(hx_ - x0, 0), n - 1))
            iy = int(min(max(hy_ - y0, 0), n - 1))
            for j in range(int(2 + (s_path - s_carved) / 6)):
                c_ = tuple(int(v) for v in terrain[iy, ix]) if j % 4 else (255, 200, 120)
                an = rnd.uniform(0, 2 * math.pi)
                spd = rnd.uniform(150, 620) * k
                parts.append([hx_, hy_, math.cos(an) * spd, math.sin(an) * spd - 150 * k, t, c_, rnd.uniform(4, 11) * k])
            s_carved = s_path
            if s_path >= next_note:
                notes_at.append((t, f, len(notes_at)))
                next_note += 150 * k
        # ---- terrain (moins le sillon) + bords en fusion
        e_ = eaten.astype(np.float32) / 255
        a_ = alpha0 * (1 - e_)
        er = cv2.erode(eaten, np.ones((5, 5), np.uint8))
        edge = cv2.GaussianBlur(cv2.dilate(eaten, np.ones((11, 11), np.uint8)) - er, (0, 0), 3).astype(np.float32) / 255
        edge *= alpha0
        frame = bg.astype(np.float32).copy()
        sub = frame[y0:y0 + n, x0:x0 + n]
        sub[...] = sub * (1 - a_[..., None]) + terrain * a_[..., None]
        hot = np.array([255, 120, 30], np.float32)
        sub[...] = np.clip(sub + edge[..., None] * hot * 1.1, 0, 255)
        # ---- boss au centre
        img = Image.fromarray(frame.astype(np.uint8)).convert("RGBA")
        if t < t_hit:
            shake = (1 - min(1.0, (t_hit - t) / 3)) * 6 * k
            bxs = CX + rnd.uniform(-shake, shake)
            bys = CY + rnd.uniform(-shake, shake)
            img.alpha_composite(boss_ic, (int(bxs - core_r), int(bys - core_r)))
        # ---- le rayon : des mains de Goku à la tête, glow + corps + cœur blanc
        if CHARGE - 0.05 <= t < t_hit + 0.2:
            pts = [HAND]
            if s_h <= pre:
                q = s_h / max(pre, 1)
                pts.append((HAND[0] + (entry[0] - HAND[0]) * q, HAND[1] + (entry[1] - HAND[1]) * q))
            else:
                pts += sp.pts(0, s_path, step=10.0)
            arr = np.array(pts, np.float32)
            wid = b * (0.56 + 0.025 * f) * (1 + 0.06 * math.sin(t * 40))
            glow = np.zeros((H // 4, W // 4, 3), np.uint8)
            cv2.polylines(glow, [(arr / 4).astype(np.int32)], False, col, max(2, int(wid * 1.9 / 4)), cv2.LINE_AA)
            glow = cv2.GaussianBlur(glow, (0, 0), 7)
            glow = cv2.resize(glow, (W, H), interpolation=cv2.INTER_LINEAR)
            base = np.asarray(img.convert("RGB")).astype(np.int16)
            base = np.clip(base + glow.astype(np.int16), 0, 255).astype(np.uint8)
            body = base.copy()
            ip = arr.astype(np.int32)
            cv2.polylines(body, [ip], False, tuple(int(min(255, c * 1.05 + 30)) for c in col), int(wid), cv2.LINE_AA)
            lite = tuple(int(255 - (255 - c) * 0.35) for c in col)
            cv2.polylines(body, [ip], False, lite, int(wid * 0.55), cv2.LINE_AA)
            cv2.polylines(body, [ip], False, (255, 255, 255), max(2, int(wid * 0.26)), cv2.LINE_AA)
            img = Image.fromarray(body).convert("RGBA")
        d = ImageDraw.Draw(img, "RGBA")
        # ---- tête du rayon : boule + éclat qui tourne
        if CHARGE <= t < t_hit + 0.05:
            hx, hy = sp.at(s_path) if s_h > pre else (HAND[0] + (entry[0] - HAND[0]) * s_h / pre,
                                                        HAND[1] + (entry[1] - HAND[1]) * s_h / pre)
            R_ = b * (0.62 + 0.03 * f) * (1 + 0.08 * math.sin(t * 33))
            gl = Image.new("RGBA", (int(R_ * 6), int(R_ * 6)), (0, 0, 0, 0))
            gd = ImageDraw.Draw(gl)
            c0 = R_ * 3
            gd.ellipse((c0 - R_ * 2.2, c0 - R_ * 2.2, c0 + R_ * 2.2, c0 + R_ * 2.2), fill=col + (150,))
            gl = gl.filter(ImageFilter.GaussianBlur(R_ * 0.6))
            gd = ImageDraw.Draw(gl)
            gd.ellipse((c0 - R_, c0 - R_, c0 + R_, c0 + R_), fill=(255, 255, 255, 255))
            for j in range(4):                            # éclat en étoile
                an = t * 3 + j * math.pi / 4
                ln = R_ * (2.4 + 0.5 * math.sin(t * 20 + j))
                gd.line((c0 - math.cos(an) * ln, c0 - math.sin(an) * ln, c0 + math.cos(an) * ln, c0 + math.sin(an) * ln),
                        fill=(255, 255, 255, 220), width=max(2, int(R_ * 0.16)))
            img.alpha_composite(gl, (int(hx - c0), int(hy - c0)))
        d = ImageDraw.Draw(img, "RGBA")
        # ---- éclats de roche
        alive = []
        for p_ in parts:
            age = t - p_[4]
            if age > 0.8:
                continue
            x = p_[0] + p_[2] * age
            y = p_[1] + p_[3] * age + 800 * k * age * age
            s_ = p_[6] * (1 - age / 0.8)
            d.polygon([(x - s_, y), (x, y - s_ * 1.2), (x + s_, y), (x, y + s_ * 0.8)], fill=p_[5] + (255,))
            alive.append(p_)
        parts[:] = alive
        # ---- Goku + aura + charge
        gs = int(200 * k)
        trans = times[f] if f > 0 else -9
        pop = 1 + 0.25 * max(0.0, 1 - (t - trans) / 0.3)
        au = Image.new("RGBA", (gs * 2, gs * 2), (0, 0, 0, 0))
        pul = 1 + 0.07 * math.sin(t * 14)
        ImageDraw.Draw(au).ellipse((gs * (1 - 0.7 * pul * pop), gs * (1 - 0.7 * pul * pop), gs * (1 + 0.7 * pul * pop),
                                    gs * (1 + 0.7 * pul * pop)), fill=col + (190,))
        img.alpha_composite(au.filter(ImageFilter.GaussianBlur(28 * k)), (int(GOKU[0] - gs), int(GOKU[1] - gs)))
        gsz = int(gs * pop)
        img.alpha_composite(icons[f].resize((gsz, gsz), Image.LANCZOS), (int(GOKU[0] - gsz / 2), int(GOKU[1] - gsz / 2)))
        d = ImageDraw.Draw(img, "RGBA")
        if t < CHARGE:                                    # boule qui se charge dans les mains + KA-ME-HA-ME
            q = t / CHARGE
            rr = (14 + 40 * q) * k * (1 + 0.1 * math.sin(t * 50))
            d.ellipse((HAND[0] - rr * 1.8, HAND[1] - rr * 1.8, HAND[0] + rr * 1.8, HAND[1] + rr * 1.8), fill=col + (90,))
            d.ellipse((HAND[0] - rr, HAND[1] - rr, HAND[0] + rr, HAND[1] + rr), fill=(255, 255, 255, 255))
            syl = ["KA", "ME", "HA", "ME"][min(3, int(q * 4))]
            d.text((W * 0.62, H * 0.255), "-".join(["KA", "ME", "HA", "ME"][: min(4, int(q * 4) + 1)]) + "...",
                   font=font(ANTON, 70 * k), anchor="mm", fill=(255, 255, 255), stroke_width=int(6 * k), stroke_fill=(0, 0, 0))
            _ = syl
        elif t < CHARGE + 0.7:
            s_ = 1 + 0.5 * max(0.0, 1 - (t - CHARGE) / 0.15)
            d.text((W * 0.62, H * 0.255), "HAAAA!", font=font(ANTON, 90 * k * s_), anchor="mm", fill=col,
                   stroke_width=int(7 * k), stroke_fill=(0, 0, 0))
        # ---- textes
        d.text((W / 2, H * 0.06), "CAN ONE KAMEHAMEHA", font=fT, anchor="mm", fill=(255, 255, 255), stroke_width=int(6 * k),
               stroke_fill=(0, 0, 0))
        d.text((W / 2, H * 0.06 + 100 * k), f"ERASE {boss_name}?", font=fT, anchor="mm", fill=col, stroke_width=int(6 * k),
               stroke_fill=(0, 0, 0))
        hp = max(0.0, 1 - max(0.0, s_h - pre) / sp.L)
        hp_disp += (hp - hp_disp) * 0.35
        bw = 520 * k
        yb = H * 0.19
        d.text((W * 0.62, yb - 32 * k), f"{boss_name}  {hp_disp * 100:.0f}%", font=font(ANTON, 46 * k), anchor="mm",
               fill=(255, 90, 90), stroke_width=int(4 * k), stroke_fill=(0, 0, 0))
        bx_ = W * 0.62 - bw / 2
        d.rounded_rectangle((bx_, yb, bx_ + bw, yb + 24 * k), radius=int(12 * k), fill=(40, 10, 20), outline=(0, 0, 0),
                            width=int(3 * k))
        if hp_disp > 0.002:
            d.rounded_rectangle((bx_ + 3, yb + 3, bx_ + 3 + (bw - 6) * hp_disp, yb + 24 * k - 3), radius=int(10 * k),
                                fill=(255, 60, 70))
        nm = FORMS[f][1]
        if f > 0 and t - trans < 1.0:
            s_ = 1 + 0.45 * max(0.0, 1 - (t - trans) / 0.15)
            d.text((W / 2, H * 0.905), nm + "!", font=font(ANTON, 78 * k * s_), anchor="mm", fill=col,
                   stroke_width=int(7 * k), stroke_fill=(0, 0, 0))
        else:
            d.text((W / 2, H * 0.905), nm, font=font(ANTON, 52 * k), anchor="mm", fill=col, stroke_width=int(5 * k),
                   stroke_fill=(0, 0, 0))
        if f > 0 and t - trans < 0.12:                    # flash de transformation
            img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(120 * (1 - (t - trans) / 0.12)))))
            d = ImageDraw.Draw(img, "RGBA")
        # ---- fin : le boss explose
        if t >= t_hit:
            age = t - t_hit
            fl = max(0.0, 1 - age / 0.5)
            for j in range(3):
                rr = (60 + 1400 * age * (1 + j * 0.4)) * k
                d.ellipse((CX - rr, CY - rr, CX + rr, CY + rr), outline=col + (int(255 * max(0, 1 - age * 1.2)),),
                          width=int((30 - j * 8) * k))
            if fl > 0:
                img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(235 * fl))))
                d = ImageDraw.Draw(img, "RGBA")
            if age > 0.25:
                s_ = 1 + 0.5 * max(0.0, 1 - (age - 0.25) / 0.2)
                d.text((W / 2, CY - 60 * k), f"{boss_name} ERASED", font=font(ANTON, 124 * k * s_), anchor="mm",
                       fill=(255, 214, 10), stroke_width=int(8 * k), stroke_fill=(0, 0, 0))
                d.text((W / 2, CY + 60 * k), "WITH ONE KAMEHAMEHA", font=font(ANTON, 60 * k), anchor="mm",
                       fill=(255, 255, 255), stroke_width=int(5 * k), stroke_fill=(0, 0, 0))
                render.draw_rich(img, (W / 2, CY + 120 * k), "Who should Goku erase next? 👇", font(MONT, 44 * k),
                                 (255, 255, 255), "ma", int(4 * k), (0, 0, 0))
        proc.stdin.write(img.convert("RGB").tobytes())
    proc.stdin.close()
    proc.wait()

    # ------------------------------------------------ son
    rate = 44100
    N = int(total * rate) + rate
    au_ = np.zeros(N, np.float32)

    def put(t0, x, g):
        if x is None:
            return
        i = int(t0 * rate)
        if 0 <= i < N:
            sg = x[: N - i]
            au_[i:i + len(sg)] += sg * g
    kame = load(SFX / "Dragon Ball Xenoverse - Kamehameha Regular Sound Effect.mp3", rate)
    if kame is not None:
        put(CHARGE - 1.85, kame[: int(1.85 * rate)], 0.6)            # la charge
        loop = kame[int(2.0 * rate):int(3.2 * rate)].copy()          # le rayon, en boucle avec fondus croisés
        xf = int(0.25 * rate)
        t0 = CHARGE
        put(t0, kame[int(1.85 * rate):int(3.2 * rate)], 0.6)
        t0 += 1.35 - 0.25
        win = np.ones(len(loop), np.float32)
        win[:xf] = np.linspace(0, 1, xf)
        win[-xf:] = np.linspace(1, 0, xf)
        while t0 < t_hit:
            put(t0, loop * win, 0.42)
            t0 += (len(loop) - xf) / rate
    aura = load(SFX / "Voicy_Small Aura Burst (DBZ Sound Effect).mp3", rate)
    for f in range(1, nF):
        put(times[f], aura, 0.55)
        put(times[f], note(784.0, rate, 0.4), 0.3)
    SC = [0, 2, 4, 7, 9]
    for (tn, f, i) in notes_at:                                     # une note qui monte tout le long du creusage
        semi = SC[i % 5] + 12 * ((i // 5) % 3)
        put(tn, note(261.6 * 2 ** (semi / 12), rate), 0.22)
        noise = np.random.RandomState(i).randn(int(0.06 * rate)).astype(np.float32) * np.exp(
            -np.arange(int(0.06 * rate)) / rate * 50)
        put(tn, noise, 0.05)
    boom = load(SFX / "Voicy_DBZ Explosion Sound Effect 1.mp3", rate)
    if boom is not None:
        boom = boom[: int(2.6 * rate)]
        boom[-int(0.8 * rate):] *= np.linspace(1, 0, int(0.8 * rate))
    put(t_hit, boom, 1.0)
    au_ = np.tanh(au_ * 1.1) * 0.85
    wav = out.with_suffix(".wav")
    with wave.open(str(wav), "wb") as w_:
        w_.setnchannels(1)
        w_.setsampwidth(2)
        w_.setframerate(rate)
        w_.writeframes((np.clip(au_, -1, 1) * 32767).astype(np.int16).tobytes())
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out.with_suffix(".silent.mp4")), "-i", str(wav),
                    "-c:v", "copy", "-af", "loudnorm=I=-21:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "160k", "-shortest",
                    str(out)], check=True)
    render.stamp_video(out)
    print(out)


if __name__ == "__main__":
    main()
