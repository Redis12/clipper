"""Golden Spin v2 (21/11, « augmente le terrain, plus de temps avant l'Infinite Spin ») : terrain géant (rectangle d'or
de 2 200 px, 2,5 écrans de large) et caméra qui suit la balle en zoomant dans la spirale d'or au rythme des carrés
(chaque carré a l'air de la même taille à l'écran) → la spirale ne finit jamais : 22 carrés, ×1.618 de rotation à
chacun, de plus en plus vite, jusqu'à l'INFINITE ROTATION. Tout est dessiné à l'écran à chaque image (net à tous les
zooms).

python3 tools/kame/golden_ball2.py <sortie.mp4>
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
from golden_ball import GOLD, GREEN, PHI, golden_squares  # noqa: E402
from spiral import load, note  # noqa: E402

W, H, FPS = 1080, 1920, 30
L = ROOT / "library"
ANTON = str(ROOT / "tools/money_sim/fonts/anton.woff2")
MONT = str(ROOT / "tools/money_sim/fonts/mont800.woff2")
SHADES = [(232, 196, 140), (214, 172, 116), (240, 210, 158), (200, 156, 104)]


def font(p, s):
    return ImageFont.truetype(p, int(s))


def main():
    out = Path(sys.argv[1])
    rnd = random.Random(4)
    k = W / 1080
    NSQ = 22
    RW = 2200.0
    RH = RW * PHI
    squares, arcs, eye = golden_squares(0.0, 0.0, RW, RH, NSQ)
    side = [b[2] - b[0] for b in squares]
    # chemin dense : 360 points par quart d'arc, rayon du sillon proportionnel au carré (lissé)
    P, R_, SQ = [], [], []
    for i, (C, r, a0, da) in enumerate(arcs):
        m = 360
        for j in range(m):
            u = j / m
            a = a0 + da * u
            P.append((C[0] + r * math.cos(a), C[1] + r * math.sin(a)))
            R_.append(0.085 * side[i] * (1 / PHI) ** u)
            SQ.append(i + u)
    P = np.array(P, np.float64)
    R_ = np.array(R_, np.float64)
    SQ = np.array(SQ, np.float64)

    # ------------------------------------------------ temps par carré : lent au début, fou à la fin
    THROW = 0.8
    T = []
    for i in range(NSQ):
        T.append(3.9 * 0.86 ** i if i < 10 else 3.9 * 0.86 ** 9 * 0.70 ** (i - 9))
    tb = np.concatenate([[THROW], THROW + np.cumsum(T)])
    t_inf = float(tb[-1])
    total = t_inf + 2.6
    print(f"durée {total:.1f} s, infini à {t_inf:.1f} s")

    def prog(t):
        """Position en « carrés » (2.5 = moitié du 3e carré)."""
        if t < THROW:
            return 0.0
        i = int(np.searchsorted(tb, t, side="right") - 1)
        i = min(max(i, 0), NSQ - 1)
        return min(NSQ - 1e-6, i + (t - tb[i]) / T[i])

    def at(q):
        idx = q * 360
        i0 = int(min(max(idx, 0), len(P) - 2))
        f = idx - i0
        return P[i0] * (1 - f) + P[i0 + 1] * f, R_[i0] * (1 - f) + R_[i0 + 1] * f

    # ------------------------------------------------ calques fixes (écran)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    top, bot = np.array([30, 16, 48], np.float32), np.array([120, 50, 30], np.float32)
    bg = top + (bot - top) * (yy / H)[..., None]
    g = np.exp(-(((xx - W * 0.5) ** 2) / (W * 0.6) ** 2 + ((yy - H * 0.95) ** 2) / (H * 0.25) ** 2))
    bg = np.clip(bg + g[..., None] * np.array([120, 70, 20], np.float32), 0, 255).astype(np.uint8)
    grain = (0.9 + 0.2 * cv2.resize(np.random.RandomState(1).rand(H // 5, W // 5).astype(np.float32), (W, H),
                                    interpolation=cv2.INTER_CUBIC) + 0.06 * np.random.RandomState(2).rand(H, W)).astype(np.float32)
    gyro = fusion.icon(str(L / "Jojo's Bizarre Adventure/Gyro Zeppeli/wallpaperflare.com_wallpaper(1).jpg"), int(190 * k),
                       GREEN)
    ball_src = Image.open(L / "_sbr/steel_ball.jpg").convert("RGB")
    bs = min(ball_src.size)
    ball_src = ball_src.crop(((ball_src.width - bs) // 2, (ball_src.height - bs) // 2, (ball_src.width + bs) // 2,
                              (ball_src.height + bs) // 2)).resize((256, 256), Image.LANCZOS)
    m4 = Image.new("L", (1024, 1024), 0)
    ImageDraw.Draw(m4).ellipse((4, 4, 1020, 1020), fill=255)
    bmask = m4.resize((256, 256), Image.LANCZOS)

    def ball_img(r, ang):
        dsz = max(8, int(r * 2))
        im = ball_src.rotate(ang, resample=Image.BICUBIC).convert("RGBA")
        im.putalpha(bmask)
        return im.resize((dsz, dsz), Image.LANCZOS)

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

    def mult_txt(i):
        v = PHI ** i
        return f"x{v:.1f}" if v < 10 else (f"x{v:,.0f}" if v < 1e5 else f"x{v:.1e}".replace("e+0", "e").replace("e+", "e"))
    badges = [None] + [badge(mult_txt(i)) for i in range(1, NSQ)]
    fT = font(ANTON, 88 * k)
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                             "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                             "-pix_fmt", "yuv420p", str(out.with_suffix(".silent.mp4"))], stdin=subprocess.PIPE)
    rect_c = np.array([RW / 2, RH * 0.47])
    eye = np.array(eye)
    cam = rect_c.copy()
    vw = RW * 1.18
    ang = 0.0
    rpm_disp = 0.0
    parts = []
    cps = []
    last_i = 0
    for fr in range(int(total * FPS)):
        t = fr / FPS
        q = prog(min(t, t_inf - 1e-4))
        i = int(q)
        if i > last_i:
            cps.append((t, i))
            last_i = i
        bpos, br_w = at(q)
        # caméra : la largeur de vue suit la taille du carré (zoom continu dans la spirale)
        s_now = side[0] * (1 / PHI) ** q
        # 21/11 : on part TRÈS dézoomé (tout le rectangle d'or) et on zoome de plus en plus sur la balle : la vue
        # rétrécit un peu plus vite que les carrés → la balle et le sillon grossissent jusqu'à la fin
        fit = RW * 1.18
        vw_t = fit * (s_now / side[0]) ** 1.12
        u = min(1.0, max(0.0, (t - 0.6) / 2.6))
        u = u * u * (3 - 2 * u)
        c_t = rect_c * (1 - u) + (bpos * 0.8 + eye * 0.2) * u
        vw = vw_t if fr == 0 else math.exp(math.log(vw) + (math.log(vw_t) - math.log(vw)) * 0.25)
        cam = c_t if fr == 0 else cam + (c_t - cam) * (0.25 + 0.7 * min(1.0, q / 13))   # suit mieux quand ça va vite
        sc = W / vw

        def tr(p):
            return ((p[..., 0] - cam[0]) * sc + W / 2, (p[..., 1] - cam[1]) * sc + H / 2)
        frame = bg.copy()
        # ---- les carrés de Fibonacci visibles
        for j in range(NSQ):
            x0_, y0_, x1_, y1_ = squares[j]
            X0, Y0 = tr(np.array([x0_, y0_]))
            X1, Y1 = tr(np.array([x1_, y1_]))
            if X1 < 0 or Y1 < 0 or X0 > W or Y0 > H or (X1 - X0) < 1.5:
                continue
            cv2.rectangle(frame, (int(max(-5, X0)), int(max(-5, Y0))), (int(min(W + 5, X1)), int(min(H + 5, Y1))),
                          SHADES[j % 4], -1)
        tmask = np.zeros((H, W), np.uint8)
        X0, Y0 = tr(np.array([0.0, 0.0]))
        X1, Y1 = tr(np.array([RW, RH]))
        cv2.rectangle(tmask, (int(max(-5, X0)), int(max(-5, Y0))), (int(min(W + 5, X1)), int(min(H + 5, Y1))), 255, -1)
        tm = tmask.astype(np.float32)[..., None] / 255
        frame = (frame.astype(np.float32) * (1 - tm + tm * grain[..., None])).clip(0, 255).astype(np.uint8)
        for j in range(NSQ):                              # traits des carrés
            x0_, y0_, x1_, y1_ = squares[j]
            X0, Y0 = tr(np.array([x0_, y0_]))
            X1, Y1 = tr(np.array([x1_, y1_]))
            if X1 < -50 or Y1 < -50 or X0 > W + 50 or Y0 > H + 50 or (X1 - X0) < 3:
                continue
            cv2.rectangle(frame, (int(X0), int(Y0)), (int(X1), int(Y1)), (120, 84, 50), max(2, int(5 * k)), cv2.LINE_AA)
        # ---- chemin : la spirale d'or à venir (pointillé doré), le sillon déjà creusé
        n_done = int(q * 360) if t >= THROW else 0
        XY = np.stack(tr(P), axis=1)
        RS = R_ * sc
        vis = (XY[:, 0] > -RS - 20) & (XY[:, 0] < W + RS + 20) & (XY[:, 1] > -RS - 20) & (XY[:, 1] < H + RS + 20)
        ahead = np.where(vis & (np.arange(len(P)) >= n_done))[0]
        if len(ahead) > 1:
            pts_ = XY[ahead].astype(np.int32)
            breaks = np.where(np.diff(ahead) > 1)[0] + 1
            for chunk in np.split(pts_, breaks):
                if len(chunk) > 1:
                    cv2.polylines(frame, [chunk], False, GOLD, max(2, int(4 * k)), cv2.LINE_AA)
        done = np.where(vis[:n_done])[0]
        if len(done):
            step = 1
            for j in done[::step]:                        # bord vert lumineux
                cv2.circle(frame, (int(XY[j, 0]), int(XY[j, 1])), int(RS[j] * 1.12 + 3), (140, 255, 90), -1, cv2.LINE_AA)
            for j in done[::step]:
                cv2.circle(frame, (int(XY[j, 0]), int(XY[j, 1])), int(RS[j]), (42, 24, 14), -1, cv2.LINE_AA)
        img = Image.fromarray(frame).convert("RGBA")
        d = ImageDraw.Draw(img, "RGBA")
        X0, Y0 = tr(np.array([0.0, 0.0]))
        X1, Y1 = tr(np.array([RW, RH]))
        d.rounded_rectangle((X0 - 6 * k, Y0 - 6 * k, X1 + 6 * k, Y1 + 6 * k), radius=int(18 * k), outline=(255, 220, 140),
                            width=int(6 * k))
        # ---- prochains checkpoints
        for j in range(max(1, i + 1), min(NSQ, i + 3)):
            pj, _ = at(float(j))
            cx, cy = tr(pj)
            if -60 < cx < W + 60 and -60 < cy < H + 60:
                bm = badges[j]
                img.alpha_composite(bm, (int(cx - bm.width / 2), int(cy - bm.height / 2)))
        d = ImageDraw.Draw(img, "RGBA")
        for (tc, j) in cps:                                 # checkpoint franchi : anneau + « x2.6! »
            age = t - tc
            if 0 <= age < 0.5:
                pj, _ = at(float(j))
                cx, cy = tr(pj)
                rr = 50 * k + 180 * k * age / 0.5
                d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=GOLD + (int(255 * (1 - age / 0.5)),), width=int(8 * k))
        # ---- la balle
        rps = 1.2 * PHI ** q
        ang = (ang - min(rps, 9.5) * 360 / FPS * 0.97) % 360   # au-delà, l'image tournerait trop vite pour se voir
        bx, by = tr(bpos)
        brs = br_w * sc
        if t < THROW:
            gx, gy = tr(np.array(P[0]))
            bx, by = gx + 70 * k * (1 - t / THROW), gy - 60 * k * (1 - t / THROW)
        shake = max(0.0, (q - 12) / 10) * 12 * k
        if shake:
            bx += rnd.uniform(-shake, shake)
            by += rnd.uniform(-shake, shake)
        trail = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        td = ImageDraw.Draw(trail)
        for j in range(1, 10):
            pj, rj = at(max(0.0, q - j * 0.018))
            px, py = tr(pj)
            rr = brs * (1 - j * 0.085)
            td.ellipse((px - rr, py - rr, px + rr, py + rr), fill=GREEN + (int(120 - j * 11),))
        inten = min(1.0, q / 10)
        for j in range(3):
            a0 = (t * 360 * (0.6 + q * 0.5) + j * 120) % 360
            rr = brs * (1.35 + 0.22 * j)
            td.arc((bx - rr, by - rr, bx + rr, by + rr), a0, a0 + 110, fill=GOLD + (int(230 * inten),), width=int(6 * k))
        img.alpha_composite(trail.filter(ImageFilter.GaussianBlur(2)))
        if rps > 4:
            for j in range(3):
                bi = ball_img(brs, ang + j * 30)
                bi.putalpha(bi.getchannel("A").point(lambda v: int(v * 0.33)))
                img.alpha_composite(bi, (int(bx - bi.width / 2), int(by - bi.height / 2)))
        bi = ball_img(brs, ang)
        img.alpha_composite(bi, (int(bx - bi.width / 2), int(by - bi.height / 2)))
        d = ImageDraw.Draw(img, "RGBA")
        if t >= THROW and fr % 2 == 0:                    # grains de sable
            for j in range(3):
                parts.append([bx, by, rnd.uniform(-1, 1) * 320 * k, rnd.uniform(-1, 1) * 320 * k - 150 * k, t,
                              SHADES[i % 4], rnd.uniform(4, 9) * k])
        alive = []
        for p_ in parts:
            age = t - p_[4]
            if age > 0.6:
                continue
            x = p_[0] + p_[2] * age
            y = p_[1] + p_[3] * age + 700 * k * age * age
            s_ = p_[6] * (1 - age / 0.6)
            d.ellipse((x - s_, y - s_, x + s_, y + s_), fill=p_[5] + (255,))
            alive.append(p_)
        parts[:] = alive
        # ---- Gyro au lancer
        if t < 2.6:
            a_ = 1.0 if t < 1.8 else max(0.0, 1 - (t - 1.8) / 0.8)
            gx, gy = tr(np.array(P[0]))
            gi = gyro.copy()
            gi.putalpha(gi.getchannel("A").point(lambda v: int(v * a_)))
            img.alpha_composite(gi, (int(gx + 40 * k - gi.width / 2), int(gy - 100 * k - gi.height / 2)))
        d = ImageDraw.Draw(img, "RGBA")
        # ---- textes
        d.text((W / 2, H * 0.045), "HOW FAST CAN GYRO'S", font=fT, anchor="mm", fill=(255, 255, 255),
               stroke_width=int(6 * k), stroke_fill=(0, 0, 0))
        d.text((W / 2, H * 0.045 + 96 * k), "STEEL BALL SPIN?", font=fT, anchor="mm", fill=GREEN, stroke_width=int(6 * k),
               stroke_fill=(0, 0, 0))
        rpm = rps * 60 if t >= THROW else 0
        rpm_disp += (rpm - rpm_disp) * 0.3
        txt = f"{rpm_disp:,.0f} RPM" if t < t_inf else "INFINITE RPM"
        d.rounded_rectangle((W / 2 - 250 * k, H * 0.118, W / 2 + 250 * k, H * 0.118 + 74 * k), radius=int(37 * k),
                            fill=(20, 12, 8, 190), outline=GOLD + (255,), width=int(3 * k))
        d.text((W / 2, H * 0.118 + 37 * k), txt, font=font(ANTON, 56 * k), anchor="mm", fill=GOLD)
        d.text((W / 2, H * 0.955), "EVERY SQUARE = SPIN x1.618", font=font(ANTON, 44 * k), anchor="mm", fill=(255, 235, 190),
               stroke_width=int(4 * k), stroke_fill=(0, 0, 0))
        for (tc, j) in cps[-1:]:                          # seulement le dernier (à la fin ils s'enchaînent)
            age = t - tc
            if 0 <= age < 0.65:
                s_ = 1 + 0.5 * max(0.0, 1 - age / 0.12)
                d.text((bx, by - brs - 70 * k - 40 * k * age), mult_txt(j) + "!", font=font(ANTON, 70 * k * s_), anchor="mm",
                       fill=GOLD + (int(255 * min(1, (0.65 - age) / 0.2)),), stroke_width=int(6 * k), stroke_fill=(0, 0, 0))
        if t >= t_inf:
            age = t - t_inf
            fl = max(0.0, 1 - age / 0.45)
            if fl > 0:
                img.alpha_composite(Image.new("RGBA", (W, H), (255, 240, 190, int(245 * fl))))
                d = ImageDraw.Draw(img, "RGBA")
            s_ = 1 + 0.5 * max(0.0, 1 - age / 0.2)
            d.text((W / 2, H * 0.43), "INFINITE", font=font(ANTON, 150 * k * s_), anchor="mm", fill=GOLD,
                   stroke_width=int(9 * k), stroke_fill=(0, 0, 0))
            d.text((W / 2, H * 0.43 + 150 * k), "ROTATION", font=font(ANTON, 150 * k * s_), anchor="mm", fill=GREEN,
                   stroke_width=int(9 * k), stroke_fill=(0, 0, 0))
            render.draw_rich(img, (W / 2, H * 0.43 + 260 * k), "Could anything stop it? 👇", font(MONT, 46 * k),
                             (255, 255, 255), "ma", int(4 * k), (0, 0, 0))
        proc.stdin.write(img.convert("RGB").tobytes())
    proc.stdin.close()
    proc.wait()

    # ------------------------------------------------ son
    rate = 44100
    N = int(total * rate) + rate
    au = np.zeros(N, np.float32)
    tl = np.arange(N) / rate
    qs = np.array([prog(min(x, t_inf - 1e-4)) for x in np.linspace(0, total, int(total * 50))])
    q_s = np.interp(tl, np.linspace(0, total, len(qs)), qs)
    freq = 60 + 26 * q_s + 2.2 * q_s ** 2
    ph = np.cumsum(2 * np.pi * freq / rate)
    amp = np.clip((tl - THROW) / 0.2, 0, 1) * (tl < t_inf)
    au += ((np.sin(ph) * 0.5 + 0.22 * np.sin(ph * 2.01)) * amp * 0.2).astype(np.float32)

    def put(t0, x, gn):
        i0 = int(t0 * rate)
        if x is not None and 0 <= i0 < N:
            sg = x[: N - i0]
            au[i0:i0 + len(sg)] += sg * gn
    AS = ROOT / "clipper/assets/sfx"
    crunch = [load(AS / f"explosion_crunch_00{j}.ogg", rate) for j in (0, 1, 3, 4)]
    rr_ = np.random.RandomState(9)
    tc = THROW + 0.1
    while tc < t_inf:                                     # le sable qui se fait creuser
        c_ = crunch[rr_.randint(len(crunch))]
        if c_ is not None:
            sg = c_[: int(0.3 * rate)].copy()
            sg[-int(0.1 * rate):] *= np.linspace(1, 0, int(0.1 * rate))
            st = int(rr_.uniform(0.8, 1.3) * len(sg))
            sg = np.interp(np.linspace(0, len(sg) - 1, st), np.arange(len(sg)), sg).astype(np.float32)
            put(tc, sg, 0.32)
        tc += rr_.uniform(0.09, 0.15) * max(0.25, 0.93 ** prog(tc))
    SC = [0, 2, 4, 7, 9]
    for j in range(1, NSQ):                               # chaque checkpoint : une note plus haute
        semi = SC[(j - 1) % 5] + 12 * ((j - 1) // 5)
        put(float(tb[j]), note(392.0 * 2 ** (min(semi, 40) / 12), rate, 0.5), 0.42)
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
