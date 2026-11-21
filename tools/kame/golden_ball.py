"""« How fast can Gyro's Steel Ball spin? » (21/11) : même principe que One Kamehameha, mais le terrain est un
RECTANGLE D'OR découpé en carrés de Fibonacci et la balle suit la spirale d'or (la Golden Rotation de Gyro, Steel Ball
Run). Chaque carré passé = checkpoint « ×1.618 » : la rotation est multipliée par le nombre d'or. Quand la spirale devient
plus petite que la balle, elle tourne sur place de plus en plus vite jusqu'à l'INFINITE ROTATION.

python3 tools/kame/golden_ball.py <sortie.mp4>
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
from spiral import load, note  # noqa: E402

W, H, FPS = 1080, 1920, 30
PHI = (1 + 5 ** 0.5) / 2
L = ROOT / "library"
ANTON = str(ROOT / "tools/money_sim/fonts/anton.woff2")
MONT = str(ROOT / "tools/money_sim/fonts/mont800.woff2")
GREEN = (120, 235, 80)
GOLD = (255, 205, 60)


def font(p, s):
    return ImageFont.truetype(p, int(s))


def golden_squares(x0, y0, x1, y1, n):
    """Carrés de Fibonacci d'un rectangle d'or vertical (coupes : haut, droite, bas, gauche…) + arc de la spirale dans
    chacun (centre, rayon, angle de départ, angle d'arrivée), enchaînés sans à-coup."""
    sq, arcs = [], []
    P = (x0, y0)
    for i in range(n):
        side = i % 4
        if side == 0:                                     # carré en haut
            s = x1 - x0
            box = (x0, y0, x1, y0 + s)
            inner = [(x0, y0 + s), (x1, y0 + s)]
            y0 += s
        elif side == 1:                                   # à droite
            s = y1 - y0
            box = (x1 - s, y0, x1, y1)
            inner = [(x1 - s, y0), (x1 - s, y1)]
            x1 -= s
        elif side == 2:                                   # en bas
            s = x1 - x0
            box = (x0, y1 - s, x1, y1)
            inner = [(x1, y1 - s), (x0, y1 - s)]
            y1 -= s
        else:                                             # à gauche
            s = y1 - y0
            box = (x0, y0, x0 + s, y1)
            inner = [(x0 + s, y1), (x0 + s, y0)]
            x0 += s
        C = min(inner, key=lambda c: min(abs(c[0] - P[0]), abs(c[1] - P[1])) + 0 * s)
        C = [c for c in inner if abs(c[0] - P[0]) < 1e-3 or abs(c[1] - P[1]) < 1e-3][0]
        Q = inner[1] if C == inner[0] else inner[0]
        a0 = math.atan2(P[1] - C[1], P[0] - C[0])
        a1 = math.atan2(Q[1] - C[1], Q[0] - C[0])
        da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        sq.append(box)
        arcs.append((C, s, a0, da))
        P = Q
    return sq, arcs, P


def main():
    out = Path(sys.argv[1])
    rnd = random.Random(4)
    k = W / 1080
    RW = 900 * k
    RH = RW * PHI
    X0, Y0 = (W - RW) / 2, H * 0.165
    NSQ = 9
    squares, arcs, eye = golden_squares(X0, Y0, X0 + RW, Y0 + RH, NSQ)
    # chemin : points le long des arcs (avec la longueur cumulée), et le carré de chaque point
    pts, sid = [], []
    for i, (C, r, a0, da) in enumerate(arcs):
        m = max(8, int(abs(da) * r / 3))
        for j in range(m):
            a = a0 + da * j / m
            pts.append((C[0] + r * math.cos(a), C[1] + r * math.sin(a)))
            sid.append(i)
    pts.append(eye)
    sid.append(NSQ - 1)
    P = np.array(pts, np.float32)
    S = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(P, axis=0).T))])
    cp_s = [S[sid.index(i)] for i in range(1, NSQ)]          # début de chaque carré = checkpoint

    def at(s):
        s = min(max(s, 0.0), S[-1])
        return float(np.interp(s, S, P[:, 0])), float(np.interp(s, S, P[:, 1]))

    # ------------------------------------------------ temps : la vitesse ×1.18 à chaque carré, puis rotation sur place
    THROW = 0.9
    seg_t = []
    v = 215 * k
    bounds = [0] + cp_s + [S[-1]]
    for i in range(NSQ):
        seg_t.append((bounds[i + 1] - bounds[i]) / (v * 1.18 ** i))
    tt = np.concatenate([[THROW], THROW + np.cumsum(seg_t)])
    t_eye = float(tt[-1])
    SPINUP = 4.2                                          # au centre : accélération folle
    t_inf = t_eye + SPINUP
    total = t_inf + 2.4
    print(f"durée {total:.1f} s, centre à {t_eye:.1f} s")

    def s_at(t):
        if t < THROW:
            return 0.0, 0
        for i in range(NSQ):
            if t < tt[i + 1]:
                return bounds[i] + (t - tt[i]) / seg_t[i] * (bounds[i + 1] - bounds[i]), i
        return float(S[-1]), NSQ - 1

    # rotation de la balle (tours/s) : ×φ à chaque carré, puis exponentielle au centre
    def rps(t):
        _, i = s_at(t)
        base = 1.2 * PHI ** i
        if t > t_eye:
            base *= math.exp(min(t, t_inf) - t_eye) ** 1.6
        return base

    # ------------------------------------------------ décor : désert au crépuscule + terrain en carrés de sable
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    top, bot = np.array([30, 16, 48], np.float32), np.array([120, 50, 30], np.float32)
    bg = top + (bot - top) * (yy / H)[..., None]
    g = np.exp(-(((xx - W * 0.5) ** 2) / (W * 0.6) ** 2 + ((yy - H * 0.95) ** 2) / (H * 0.25) ** 2))
    bg += g[..., None] * np.array([120, 70, 20], np.float32)
    bg = np.clip(bg, 0, 255).astype(np.uint8)
    ix0, iy0, ix1, iy1 = int(X0), int(Y0), int(X0 + RW), int(Y0 + RH)
    tw, th = ix1 - ix0, iy1 - iy0
    terr = np.zeros((th, tw, 3), np.float32)
    noise = cv2.resize(np.random.RandomState(1).rand(th // 6 + 1, tw // 6 + 1).astype(np.float32), (tw, th),
                       interpolation=cv2.INTER_CUBIC)
    fine = np.random.RandomState(2).rand(th, tw).astype(np.float32)
    shades = [(232, 196, 140), (214, 172, 116), (240, 210, 158), (200, 156, 104)]
    for i, (a, b_, c, d_) in enumerate(squares):
        col = np.array(shades[i % 4], np.float32)
        terr[int(b_ - Y0):int(d_ - Y0), int(a - X0):int(c - X0)] = col
    terr *= (0.88 + 0.18 * noise[..., None] + 0.06 * fine[..., None])
    terr = np.clip(terr, 0, 255)
    lines = np.zeros((th, tw), np.uint8)
    for (a, b_, c, d_) in squares:                         # les carrés de Fibonacci
        cv2.rectangle(lines, (int(a - X0), int(b_ - Y0)), (int(c - X0) - 1, int(d_ - Y0) - 1), 255, max(2, int(4 * k)),
                      cv2.LINE_AA)
    lines_f = (lines.astype(np.float32) / 255)[..., None]
    terr = terr * (1 - lines_f * 0.55)
    gp = np.array([(x - X0, y - Y0) for (x, y) in pts[::2]], np.int32)
    guide = np.zeros((th, tw), np.uint8)                   # la spirale d'or en pointillés dorés (le chemin à venir)
    cv2.polylines(guide, [gp], False, 255, max(2, int(5 * k)), cv2.LINE_AA)
    guide_f = (cv2.GaussianBlur(guide, (0, 0), 1.2).astype(np.float32) / 255)[..., None]
    eaten = np.zeros((th, tw), np.uint8)
    gyro = fusion.icon(str(L / "Jojo's Bizarre Adventure/Gyro Zeppeli/wallpaperflare.com_wallpaper(1).jpg"), int(190 * k),
                       GREEN)
    ball_src = Image.open(L / "_sbr/steel_ball.jpg").convert("RGB")
    bs = min(ball_src.size)
    ball_src = ball_src.crop(((ball_src.width - bs) // 2, (ball_src.height - bs) // 2, (ball_src.width + bs) // 2,
                              (ball_src.height + bs) // 2))
    BR0 = 60 * k

    def ball_img(r, ang):
        dsz = max(8, int(r * 2))
        im = ball_src.resize((dsz, dsz), Image.LANCZOS).rotate(ang, resample=Image.BICUBIC)
        m = Image.new("L", (dsz * 4, dsz * 4), 0)
        ImageDraw.Draw(m).ellipse((2, 2, dsz * 4 - 2, dsz * 4 - 2), fill=255)
        im = im.convert("RGBA")
        im.putalpha(m.resize((dsz, dsz), Image.LANCZOS))
        return im

    def badge(txt):
        SS = 4
        r_ = 46 * k
        size = int(r_ * 3.2)
        big = Image.new("RGBA", (size * SS, size * SS), (0, 0, 0, 0))
        dd = ImageDraw.Draw(big)
        c0 = size * SS / 2
        R4 = r_ * SS
        dd.ellipse((c0 - R4, c0 - R4, c0 + R4, c0 + R4), fill=(255, 253, 245, 255), outline=(255, 200, 70, 255),
                   width=int(3 * k * SS))
        f_ = font(ANTON, 36 * k * SS)
        while dd.textlength(txt, font=f_) > R4 * 1.55:
            f_ = font(ANTON, f_.size - 4)
        dd.text((c0, c0 + SS), txt, font=f_, anchor="mm", fill=(60, 35, 10))
        sm = big.resize((size, size), Image.LANCZOS)
        gl = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        ImageDraw.Draw(gl).ellipse((size / 2 - r_ * 1.3, size / 2 - r_ * 1.3, size / 2 + r_ * 1.3, size / 2 + r_ * 1.3),
                                   fill=GOLD + (150,))
        gl = gl.filter(ImageFilter.GaussianBlur(r_ * 0.35))
        gl.alpha_composite(sm)
        return gl
    badges = [badge(f"x{PHI ** (i + 1):.1f}" if PHI ** (i + 1) < 10 else f"x{PHI ** (i + 1):.0f}") for i in range(NSQ - 1)]
    fT = font(ANTON, 88 * k)
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                             "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                             "-pix_fmt", "yuv420p", str(out.with_suffix(".silent.mp4"))], stdin=subprocess.PIPE)
    s_done = 0.0
    ang = 0.0
    parts = []
    rpm_disp = 0.0
    events = []                                           # pour le son
    passed = 0
    for fr in range(int(total * FPS)):
        t = fr / FPS
        s_, sq_i = s_at(t)
        br = max(30 * k, BR0 * (0.93 ** sq_i))
        if s_ > s_done:                                   # la balle creuse son sillon
            for ss in np.arange(max(0, s_done - 2), s_ + 1e-6, 3.0):
                x, y = at(ss)
                cv2.circle(eaten, (int(x - X0), int(y - Y0)), int(br * 1.05), 255, -1, cv2.LINE_AA)
            x, y = at(s_)
            for j in range(3):
                parts.append([x, y, rnd.uniform(-1, 1) * 300 * k, rnd.uniform(-1, 1) * 300 * k - 120 * k, t,
                              tuple(int(c) for c in terr[int(min(max(y - Y0, 0), th - 1)), int(min(max(x - X0, 0), tw - 1))]),
                              rnd.uniform(4, 9) * k])
            s_done = s_
        while passed < len(cp_s) and s_ >= cp_s[passed]:
            events.append(("cp", t, passed))
            passed += 1
        sp_ = rps(t)
        ang = (ang - sp_ * 360 / FPS) % 360
        # ---- terrain
        frame = bg.astype(np.float32).copy()
        e_ = eaten.astype(np.float32) / 255
        sub = frame[iy0:iy1, ix0:ix1]
        trench = np.array([40, 22, 12], np.float32)
        sub[...] = terr * (1 - e_[..., None]) + trench * e_[..., None]
        gf = guide_f * (1 - e_[..., None])
        sub[...] = sub * (1 - gf * 0.75) + np.array(GOLD, np.float32) * gf * 0.75
        edge = cv2.GaussianBlur(cv2.dilate(eaten, np.ones((7, 7), np.uint8)) - cv2.erode(eaten, np.ones((3, 3), np.uint8)),
                                (0, 0), 2.5).astype(np.float32) / 255
        sub[...] = np.clip(sub + edge[..., None] * np.array([140, 255, 90], np.float32) * 0.9, 0, 255)
        img = Image.fromarray(frame.astype(np.uint8)).convert("RGBA")
        d = ImageDraw.Draw(img, "RGBA")
        # cadre du rectangle d'or
        d.rounded_rectangle((X0 - 6 * k, Y0 - 6 * k, X0 + RW + 6 * k, Y0 + RH + 6 * k), radius=int(18 * k),
                            outline=(255, 220, 140), width=int(6 * k))
        # ---- checkpoints
        for i, cs in enumerate(cp_s):
            cx, cy = at(cs)
            if s_ < cs and squares[i + 1][2] - squares[i + 1][0] >= 120 * k:   # pas de pastille dans les tout petits carrés
                bimg = badges[i]
                scl = max(0.45, min(1.0, (squares[i + 1][2] - squares[i + 1][0]) / (220 * k)))
                if scl < 1:
                    bimg = bimg.resize((int(bimg.width * scl), int(bimg.height * scl)), Image.LANCZOS)
                img.alpha_composite(bimg, (int(cx - bimg.width / 2), int(cy - bimg.height / 2)))
            else:
                age = t - tt[i + 1]
                if 0 <= age < 0.4:
                    q = age / 0.4
                    rr = 50 * k + 160 * k * q
                    d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=GOLD + (int(255 * (1 - q)),), width=int(8 * k))
        d = ImageDraw.Draw(img, "RGBA")
        # ---- éclats
        alive = []
        for p_ in parts:
            age = t - p_[4]
            if age > 0.6:
                continue
            x = p_[0] + p_[2] * age
            y = p_[1] + p_[3] * age + 700 * k * age * age
            sz = p_[6] * (1 - age / 0.6)
            d.ellipse((x - sz, y - sz, x + sz, y + sz), fill=p_[5] + (255,))
            alive.append(p_)
        parts[:] = alive
        # ---- Gyro
        img.alpha_composite(gyro, (int(X0 + 40 * k - gyro.width / 2), int(Y0 - 40 * k - gyro.height / 2 + 20 * k)))
        d = ImageDraw.Draw(img, "RGBA")
        # ---- la balle
        if t < THROW:                                     # Gyro la lance
            q = t / THROW
            gx, gy = X0 + 40 * k, Y0 - 10 * k
            bx, by = gx + (X0 - gx) * q, gy + (Y0 - gy) * q
        else:
            bx, by = at(s_)
        shake = 0.0
        if t > t_eye:
            shake = min(1.0, (t - t_eye) / SPINUP) * 10 * k
            bx += rnd.uniform(-shake, shake)
            by += rnd.uniform(-shake, shake)
        # traînée verte + anneaux de rotation qui s'intensifient
        trail = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        td = ImageDraw.Draw(trail)
        for j in range(1, 9):
            ps = at(max(0.0, s_ - j * 14 * k))
            rr = br * (1 - j * 0.09)
            td.ellipse((ps[0] - rr, ps[1] - rr, ps[0] + rr, ps[1] + rr), fill=GREEN + (int(110 - j * 11),))
        inten = min(1.0, math.log(1 + sp_) / 5)
        for j in range(3):
            a0 = (t * sp_ * 360 * 0.15 + j * 120) % 360
            rr = br * (1.35 + 0.2 * j)
            td.arc((bx - rr, by - rr, bx + rr, by + rr), a0, a0 + 100, fill=GOLD + (int(220 * inten),), width=int(6 * k))
        img.alpha_composite(trail.filter(ImageFilter.GaussianBlur(2)))
        if sp_ > 6:                                       # flou de rotation
            for j in range(3):
                bi = ball_img(br, ang + j * 25)
                bi.putalpha(bi.getchannel("A").point(lambda v: int(v * 0.35)))
                img.alpha_composite(bi, (int(bx - bi.width / 2), int(by - bi.height / 2)))
        bi = ball_img(br, ang)
        img.alpha_composite(bi, (int(bx - bi.width / 2), int(by - bi.height / 2)))
        d = ImageDraw.Draw(img, "RGBA")
        if t > t_eye:                                     # au centre : onde d'or, la balle s'emballe
            q = min(1.0, (t - t_eye) / SPINUP)
            for j in range(4):
                ph = ((t * (1.5 + 4 * q)) + j / 4) % 1
                rr = br * (1.4 + 5 * ph)
                d.ellipse((bx - rr, by - rr, bx + rr, by + rr), outline=GOLD + (int(200 * (1 - ph) * q),), width=int(5 * k))
        # ---- textes
        d.text((W / 2, H * 0.045), "HOW FAST CAN GYRO'S", font=fT, anchor="mm", fill=(255, 255, 255), stroke_width=int(6 * k),
               stroke_fill=(0, 0, 0))
        d.text((W / 2, H * 0.045 + 96 * k), "STEEL BALL SPIN?", font=fT, anchor="mm", fill=GREEN, stroke_width=int(6 * k),
               stroke_fill=(0, 0, 0))
        rpm = sp_ * 60
        rpm_disp += (rpm - rpm_disp) * 0.3
        txt = f"{rpm_disp:,.0f} RPM" if t < t_inf else "INFINITE RPM"
        d.text((W * 0.62, H * 0.138), txt, font=font(ANTON, 58 * k), anchor="mm", fill=GOLD, stroke_width=int(5 * k),
               stroke_fill=(0, 0, 0))
        lbl = "GOLDEN SPIN  ·  EVERY SQUARE x1.618"
        d.text((W / 2, Y0 + RH + 42 * k), lbl, font=font(ANTON, 40 * k), anchor="mm", fill=(255, 235, 190),
               stroke_width=int(4 * k), stroke_fill=(0, 0, 0))
        for (kind, te, i) in events:
            age = t - te
            if kind == "cp" and 0 <= age < 0.7:           # « x2.6! » qui claque près de la balle
                sc = 1 + 0.5 * max(0.0, 1 - age / 0.12)
                v_ = PHI ** (i + 1)
                lab = f"x{v_:.1f}!" if v_ < 10 else f"x{v_:.0f}!"
                d.text((bx, by - br - 60 * k - 40 * k * age), lab, font=font(ANTON, 70 * k * sc), anchor="mm",
                       fill=GOLD + (int(255 * min(1, (0.7 - age) / 0.2)),), stroke_width=int(6 * k), stroke_fill=(0, 0, 0))
        if t >= t_inf:                                    # fin
            age = t - t_inf
            fl = max(0.0, 1 - age / 0.4)
            if fl > 0:
                img.alpha_composite(Image.new("RGBA", (W, H), (255, 240, 190, int(240 * fl))))
                d = ImageDraw.Draw(img, "RGBA")
            sc = 1 + 0.5 * max(0.0, 1 - age / 0.2)
            d.text((W / 2, H * 0.45), "INFINITE", font=font(ANTON, 150 * k * sc), anchor="mm", fill=GOLD,
                   stroke_width=int(9 * k), stroke_fill=(0, 0, 0))
            d.text((W / 2, H * 0.45 + 150 * k), "ROTATION", font=font(ANTON, 150 * k * sc), anchor="mm", fill=GREEN,
                   stroke_width=int(9 * k), stroke_fill=(0, 0, 0))
            render.draw_rich(img, (W / 2, H * 0.45 + 260 * k), "Could anything stop it? 👇", font(MONT, 46 * k),
                             (255, 255, 255), "ma", int(4 * k), (0, 0, 0))
        proc.stdin.write(img.convert("RGB").tobytes())
    proc.stdin.close()
    proc.wait()

    # ------------------------------------------------ son : un ronflement qui monte avec la rotation, ding aux carrés
    rate = 44100
    N = int(total * rate) + rate
    au = np.zeros(N, np.float32)
    tline = np.arange(N) / rate
    rp = np.array([rps(min(x, t_inf)) for x in np.linspace(0, total, int(total * 100))], np.float32)
    rp_s = np.interp(tline, np.linspace(0, total, len(rp)), rp)
    freq = 70 + 32 * np.log1p(rp_s) ** 1.6
    phase = np.cumsum(2 * np.pi * freq / rate)
    hum = (np.sin(phase) * 0.5 + 0.25 * np.sin(phase * 2.01) + 0.12 * np.sign(np.sin(phase * 0.5))).astype(np.float32)
    amp = np.clip((tline - THROW) / 0.2, 0, 1) * (tline < t_inf)
    au += hum * amp * 0.22
    nz = np.random.RandomState(3).randn(N).astype(np.float32)
    nz = np.convolve(nz, np.ones(30) / 30, mode="same")
    au += nz * amp * (0.15 + 0.5 * np.clip((tline - t_eye) / SPINUP, 0, 1)) * 0.6

    def put(t0, x, gn):
        i = int(t0 * rate)
        if x is not None and 0 <= i < N:
            sg = x[: N - i]
            au[i:i + len(sg)] += sg * gn
    SC = [0, 4, 7, 12, 16, 19, 24, 28, 31]
    for (kind, te, i) in events:
        put(te, note(523.25 * 2 ** (SC[i % len(SC)] / 12), rate, 0.45), 0.45)
    boom = load(L / "_sfx/Dragon Ball SFX/Dragon Ball Z Sounds/Voicy_DBZ Explosion Sound Effect 1.mp3", rate)
    if boom is not None:
        boom = boom[: int(2.2 * rate)]
        boom[-int(0.7 * rate):] *= np.linspace(1, 0, int(0.7 * rate))
    put(t_inf, boom, 0.9)
    put(t_inf, note(1046.5, rate, 1.2), 0.5)
    au = np.tanh(au * 1.2) * 0.85
    wav = out.with_suffix(".wav")
    with wave.open(str(wav), "wb") as w_:
        w_.setnchannels(1)
        w_.setsampwidth(2)
        w_.setframerate(rate)
        w_.writeframes((np.clip(au, -1, 1) * 32767).astype(np.int16).tobytes())
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out.with_suffix(".silent.mp4")), "-i", str(wav),
                    "-c:v", "copy", "-af", "loudnorm=I=-21:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "160k", "-shortest",
                    str(out)], check=True)
    render.stamp_video(out)
    print(out)


if __name__ == "__main__":
    main()
