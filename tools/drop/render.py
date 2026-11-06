"""Power Drop : rendu vidéo 1080x1920 + son.

python3 tools/drop/render.py <graine> <sortie.mp4> "Naruto=_fusion/Naruto/3 Base.jpg" "Luffy=..." ...
(lancer depuis la racine du dépôt clipper)
"""
import json
import math
import random
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import sim  # noqa: E402
from clipper.slides import fusion, render  # noqa: E402

W, H, FPS = sim.W, sim.H, 30
ROOT = Path(__file__).resolve().parents[2]
FD = ROOT / "tools/money_sim/fonts/"
F = lambda n, s: ImageFont.truetype(str(FD / n), s)          # noqa: E731
COLS = [(255, 140, 30), (255, 60, 70), (60, 150, 255), (175, 95, 255)]
BIN_COL = {10: (255, 200, 40), 5: (255, 120, 40), 2: (255, 70, 140), 1.5: (170, 90, 255), 1: (70, 130, 255),
           0.5: (230, 40, 50)}
END_S = 1.7
SR = 44100


def compact(v):
    if v >= 1e6:
        return f"{v / 1e6:.2f}M"
    if v >= 1e4:
        return f"{v / 1e3:.0f}K"
    if v >= 1e3:
        return f"{v / 1e3:.1f}K"
    return f"{v:.0f}"


def glow_dot(r, col, blur):
    s = int(r * 2 + blur * 4)
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((s / 2 - r, s / 2 - r, s / 2 + r, s / 2 + r), fill=col + (255,))
    return im.filter(ImageFilter.GaussianBlur(blur))


def background():
    """Fond A (06/11) : dégradé vif façon jeu (rose → violet → bleu), rayons, étoiles, vitre sombre sous la planche."""
    y = np.linspace(0, 1, H)[:, None, None]
    x = np.linspace(0, 1, W)[None, :, None]
    c0, c1, c2 = (np.array(v, np.float32) for v in ((255, 92, 170), (140, 60, 255), (40, 110, 255)))
    a = np.where(y < 0.5, c0 * (1 - y * 2) + c1 * (y * 2), c1 * (2 - y * 2) + c2 * (y * 2 - 1))
    a = a * (0.92 + 0.16 * x)
    bg = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA")
    ray = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ray)
    cx, cy = W / 2, 250
    for k in range(20):
        ang = k * math.tau / 20
        rd.polygon([(cx, cy), (cx + math.cos(ang - 0.07) * 2600, cy + math.sin(ang - 0.07) * 2600),
                    (cx + math.cos(ang + 0.07) * 2600, cy + math.sin(ang + 0.07) * 2600)], fill=(255, 255, 255, 26))
    bg.alpha_composite(ray)
    st = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(st)
    r = random.Random(3)
    for _ in range(70):
        sx, sy, rr = r.uniform(0, W), r.uniform(0, H), r.uniform(1.5, 4.5)
        sd.ellipse((sx - rr, sy - rr, sx + rr, sy + rr), fill=(255, 255, 255, r.randint(90, 200)))
    bg.alpha_composite(st.filter(ImageFilter.GaussianBlur(0.6)))
    # bandeau sombre sous le titre + les barres (lisibilité)
    pan = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pd = ImageDraw.Draw(pan)
    pd.rounded_rectangle((28, 282, W - 28, 576), 30, fill=(20, 8, 45, 150))
    bg.alpha_composite(pan)
    # cadre néon de la planche
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay)
    top_y = sim.SPAWN[1] - 50
    pts = [(540 - 70, top_y), (540 + 70, top_y), (sim.BOTTOM_X[-1] + 40, sim.BIN_TOP - 30),
           (sim.BOTTOM_X[-1] + 40, sim.BIN_BOT + 8), (sim.BOTTOM_X[0] - 40, sim.BIN_BOT + 8),
           (sim.BOTTOM_X[0] - 40, sim.BIN_TOP - 30)]
    ld.polygon(pts, fill=(20, 8, 45, 170))
    for i in range(len(pts)):
        a0, b0 = pts[i], pts[(i + 1) % len(pts)]
        hue = i / len(pts)
        col = tuple(int(c) for c in np.array([120, 255, 160]) * (1 - hue) + np.array([200, 110, 255]) * hue)
        ld.line((a0, b0), fill=col + (255,), width=6)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).line(pts + [pts[0]], fill=(255, 255, 255, 255), width=14)
    bg.alpha_composite(glow.filter(ImageFilter.GaussianBlur(12)))
    bg.alpha_composite(lay)
    return bg


def PASTE(img, im, pos):
    if img.mode == "RGB" and im.mode == "RGBA":
        img.paste(im, (int(pos[0]), int(pos[1])), im)
    else:
        img.alpha_composite(im, (int(pos[0]), int(pos[1])))


SONG = [None, 0.0]


def main():
    seed, out = int(sys.argv[1]), Path(sys.argv[2])
    chars = []
    for a in sys.argv[3:]:
        if a.startswith("song="):
            p_, _, st_ = a[5:].partition("@")
            SONG[0], SONG[1] = str(ROOT / "library" / p_), float(st_ or 0)
            continue
        name, p = a.split("=", 1)
        chars.append((name, str(ROOT / "library" / p)))
    gap, pct = 0.75, 0.03
    res = sim.simulate(seed, gap=gap, peg_pct=pct)
    frames, events, win = res["frames"], res["events"], res["winner"]
    T = res["win_t"]
    n_total = len(frames) + int(END_S * FPS)
    print("course", round(T, 1), "s, gagnant", chars[win][0], flush=True)

    icons = [fusion.icon(p, int(sim.R * 2.5), COLS[i]) for i, (_, p) in enumerate(chars)]
    icons_row = [fusion.icon(p, 64, COLS[i]) for i, (_, p) in enumerate(chars)]
    big = fusion.icon(chars[win][1], 420, COLS[win])
    bg = background()
    peg_dot = glow_dot(7, (235, 235, 255), 1)
    peg_glow = {i: glow_dot(16, COLS[i], 6) for i in range(len(chars))}
    fT1, fT2 = F("anton.woff2", 92), F("anton.woff2", 128)
    fName, fVal = F("mont900.woff2", 34), F("anton.woff2", 44)
    fBin, fFloat, fBig = F("anton.woff2", 40), F("mont900.woff2", 30), F("anton.woff2", 110)
    fPick = F("mont900.woff2", 52)

    peg_hit = {}           # k -> (t, c)
    floats = []            # (t0, x, y, txt, col, size)
    bursts = []            # (t0, x, y, col, n, power)
    bin_hit = {}           # bin -> (t, c)
    shakes = []            # (t0, amp)
    pos = {}               # id -> dernière position
    ev_i = 0
    disp = [sim.START] * len(chars)
    rng = random.Random(seed)
    pf = None

    def ffmpeg():
        return subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s",
                                 f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
                                 "-crf", "18", "-pix_fmt", "yuv420p", str(out.with_suffix(".video.mp4"))],
                                stdin=subprocess.PIPE)
    proc = ffmpeg()
    trails = {}
    row_y = [None] * len(chars)
    cur_lead, lead_t, lead_times = [None], [None], []
    for fi in range(n_total):
        t = fi / FPS
        f = frames[min(fi, len(frames) - 1)]
        while ev_i < len(events) and events[ev_i][0] <= t:
            et, kind, dd = events[ev_i]
            if kind == "peg":
                k = dd["k"]
                px, py = sim.PEGS[k]
                peg_hit[k] = (et, dd["c"])
                if dd["n"] % 2 == 1:
                    floats.append((et, px + rng.uniform(-10, 10), py - 24, "+" + compact(dd["gain"]), COLS[dd["c"]], 0))
            elif kind == "land":
                bi, m = dd["bin"], dd["m"]
                x = (sim.BOTTOM_X[bi] + sim.BOTTOM_X[bi + 1]) / 2
                bin_hit[bi] = (et, dd["c"])
                txt = "÷2" if m == 0.5 else f"x{m:g}"
                floats.append((et, x, sim.BIN_TOP - 30, txt, BIN_COL[m] if m != 1 else (200, 210, 255), 1))
                bursts.append((et, x, sim.BIN_TOP + 40, BIN_COL[m], 26 if m >= 5 else 14, 1.6 if m >= 5 else 1.0))
                if m >= 5:
                    shakes.append((et, 14 if m == 10 else 8))
            ev_i += 1
        for i in range(len(chars)):
            disp[i] += (f["power"][i] - disp[i]) * 0.35
        # ---- dessin
        img = bg.convert("RGB")
        d = ImageDraw.Draw(img, "RGBA")
        # titre
        d.text((W / 2, 40), "WHO HITS", font=fT1, fill="white", anchor="mt", stroke_width=5, stroke_fill=(60, 10, 70))
        d.text((W / 2, 128), "1,000,000 FIRST?", font=fT2, fill=(255, 210, 60), anchor="mt", stroke_width=6,
               stroke_fill=(60, 10, 70))
        # lignes de score : liste dynamique, le nouveau 1er remonte en haut (demandé le 06/11)
        p_ = f["power"]
        best = max(range(len(chars)), key=lambda i: p_[i])
        if cur_lead[0] is None:
            cur_lead[0] = best
        elif best != cur_lead[0] and p_[best] > p_[cur_lead[0]] * 1.02 and t > 0.8:
            cur_lead[0] = best
            lead_t[0] = t
            lead_times.append(t)
        lead = cur_lead[0]
        order = [lead] + [i for i in range(len(chars)) if i != lead]
        for rank, i in enumerate(order):
            target = 300 + rank * 70
            row_y[i] = target if row_y[i] is None else row_y[i] + (target - row_y[i]) * 0.28
        fl = max(0.0, 1 - (t - lead_t[0]) / 0.45) if lead_t[0] is not None else 0.0
        for i in sorted(range(len(chars)), key=lambda i: (i == lead, -row_y[i])):
            name = chars[i][0]
            y = row_y[i]
            is_lead = i == lead and t > 0.8
            if is_lead:
                mix = 0.35 + 0.4 * fl
                fillc = tuple(int(30 * (1 - mix) + c * mix) for c in COLS[i]) + (255,)
                d.rounded_rectangle((40, y - 6, W - 40, y + 62), 16, fill=fillc,
                                    outline=(255, 255, 255, int(180 + 75 * fl)) if fl > 0 else COLS[i] + (200,),
                                    width=3 + int(3 * fl))
            elif abs(row_y[i] - (300 + order.index(i) * 70)) > 3:      # en train de descendre
                d.rounded_rectangle((40, y - 6, W - 40, y + 62), 16, fill=(52, 22, 92, 255))
            PASTE(img, icons_row[i], (52, y - 6))
            d.text((128, y + 28), name.upper(), font=fName, fill="white", anchor="lm")
            x0, x1 = 330, 840
            d.rounded_rectangle((x0, y + 14, x1, y + 42), 14, fill=(255, 255, 255, 30))
            fr = min(1.0, math.log10(max(disp[i], sim.START) / sim.START) / math.log10(sim.GOAL / sim.START))
            if fr > 0.01:
                d.rounded_rectangle((x0, y + 14, x0 + max(28, (x1 - x0) * fr), y + 42), 14, fill=COLS[i] + (255,))
            d.text((W - 54, y + 28), compact(disp[i]), font=fVal, fill="white", anchor="rm")
            if is_lead:                                              # couronne qui rebondit au changement
                cx, cy = 84, y - 12 - 14 * math.sin(min(1.0, 1 - fl) * math.pi) * (fl > 0)
                d.polygon([(cx - 22, cy + 12), (cx - 22, cy - 6), (cx - 11, cy + 3), (cx, cy - 12), (cx + 11, cy + 3),
                           (cx + 22, cy - 6), (cx + 22, cy + 12)], fill=(255, 205, 50), outline=(120, 70, 0))
        # clous
        for k, (px, py) in enumerate(sim.PEGS):
            h = peg_hit.get(k)
            if h and t - h[0] < 0.35:
                a = 1 - (t - h[0]) / 0.35
                g = peg_glow[h[1]]
                gi = g.copy()
                gi.putalpha(gi.getchannel("A").point(lambda v, a=a: int(v * a)))
                PASTE(img, gi, (int(px - g.width / 2), int(py - g.height / 2)))
                rr = 9 + 16 * (1 - a)
                d.ellipse((px - rr, py - rr, px + rr, py + rr), outline=COLS[h[1]] + (int(220 * a),), width=3)
            PASTE(img, peg_dot, (int(px - peg_dot.width / 2), int(py - peg_dot.height / 2)))
        # bacs
        for bi, m in enumerate(sim.MULTS):
            xa, xb = sim.BOTTOM_X[bi] + 8, sim.BOTTOM_X[bi + 1] - 8
            col = BIN_COL[m]
            h = bin_hit.get(bi)
            pop = 0.0
            if h and t - h[0] < 0.3:
                pop = math.sin((t - h[0]) / 0.3 * math.pi)
            ya = sim.BIN_TOP + 34 - pop * 12
            d.rounded_rectangle((xa, ya, xb, sim.BIN_BOT), 12, fill=col + (int(150 + 100 * pop),))
            d.text(((xa + xb) / 2, (ya + sim.BIN_BOT) / 2), "÷2" if m == 0.5 else f"x{m:g}", font=fBin,
                   fill="white", anchor="mm", stroke_width=2, stroke_fill=(0, 0, 0))
        for sx in sim.BOTTOM_X:
            d.rounded_rectangle((sx - 4, sim.BIN_TOP, sx + 4, sim.BIN_BOT), 4, fill=(230, 230, 255, 220))
        # balles + traînées
        alive = set()
        for c, x, y, bid in f["balls"]:
            alive.add(bid)
            tr = trails.setdefault(bid, [])
            tr.append((x, y))
            del tr[:-7]
            for j, (tx, ty) in enumerate(tr[:-1]):
                rr = sim.R * (0.35 + 0.08 * j)
                d.ellipse((tx - rr, ty - rr, tx + rr, ty + rr), fill=COLS[c] + (25 + 12 * j,))
            ic = icons[c]
            PASTE(img, ic, (int(x - ic.width / 2), int(y - ic.height / 2)))
        for bid in list(trails):
            if bid not in alive:
                del trails[bid]
        # balle en attente (accroche : on la voit dès l'image 0)
        if t < T:
            nxt = int((t - 0.25) / gap) + 1 if t >= 0.25 else 0
            c = nxt % len(chars)
            ph = ((t - 0.25) % gap) / gap if t >= 0.25 else 1.0
            sc = min(1.0, ph * 3)
            if sc > 0.05:
                ic = icons[c].resize((max(2, int(icons[c].width * sc)),) * 2)
                PASTE(img, ic, (int(sim.SPAWN[0] - ic.width / 2), int(sim.SPAWN[1] - 6 - ic.height / 2)))
        # éclats
        for (t0, x, y, col, n, pw) in bursts:
            a = (t - t0) / 0.6
            if 0 <= a < 1:
                r2 = random.Random(int(t0 * 1000))
                for j in range(n):
                    ang = r2.uniform(math.pi, 2 * math.pi)
                    sp = r2.uniform(140, 420) * pw
                    px = x + math.cos(ang) * sp * a
                    py = y + math.sin(ang) * sp * a + 500 * a * a
                    rr = (1 - a) * r2.uniform(5, 11)
                    d.ellipse((px - rr, py - rr, px + rr, py + rr), fill=col + (int(255 * (1 - a)),))
        # textes flottants
        for (t0, x, y, txt, col, kind) in floats:
            a = (t - t0) / (0.6 if kind == 0 else 0.9)
            if 0 <= a < 1:
                if kind == 0:
                    d.text((x, y - 40 * a), txt, font=fFloat, fill=col + (int(255 * (1 - a)),), anchor="mm",
                           stroke_width=2, stroke_fill=(0, 0, 0, int(200 * (1 - a))))
                else:
                    s = 1 + 0.6 * math.sin(min(1, a * 4) * math.pi / 2) - 0.2 * a
                    fz = F("anton.woff2", int(64 * s))
                    d.text((x, y - 90 * a), txt, font=fz, fill=col + (int(255 * (1 - a * a)),), anchor="mm",
                           stroke_width=4, stroke_fill=(0, 0, 0, int(230 * (1 - a * a))))
        # « Pick one » + Like & Follow (accroche)
        pa = 1.0 if t < 3 else max(0.0, 1 - (t - 3) / 0.4)
        pulse = 1 + 0.06 * math.sin(t * 7)
        fp = F("mont900.woff2", int(52 * (pulse if t < 3 else 1)))
        img = img.convert("RGBA")
        render.draw_rich(img, (W / 2, sim.BIN_BOT + 46), "Pick one before the end 👇", fp, (255, 255, 255),
                         anchor="ma", stroke_width=3, stroke_fill=(0, 0, 0))
        if t < 3.2:
            render.like_follow(img, W / 2, sim.BIN_BOT + 130, pa)
        img = img.convert("RGB")
        d = ImageDraw.Draw(img, "RGBA")
        # fin
        if t >= T:
            e = t - T
            d.rectangle((0, 0, W, H), fill=(8, 6, 16, int(min(220, e / 0.15 * 220))))
            if e < 0.12:
                d.rectangle((0, 0, W, H), fill=(255, 255, 255, int(255 * (1 - e / 0.12))))
            dd = ImageDraw.Draw(img, "RGBA")
            cx, cy = W / 2, H * 0.44
            for k in range(16):
                ang = k * math.tau / 16 + e * 0.8
                dd.polygon([(cx, cy), (cx + math.cos(ang - 0.08) * 1400, cy + math.sin(ang - 0.08) * 1400),
                            (cx + math.cos(ang + 0.08) * 1400, cy + math.sin(ang + 0.08) * 1400)],
                           fill=COLS[win] + (40,))
            s = min(1.0, e / 0.25)
            s = 1 + 0.15 * math.sin(s * math.pi) if s < 1 else 1
            bi_ = big.resize((int(big.width * s * min(1, e / 0.2 + 0.3)),) * 2)
            PASTE(img, bi_, (int(cx - bi_.width / 2), int(cy - bi_.height / 2)))
            dd.text((cx, cy - 330), chars[win][0].upper(), font=fBig, fill=COLS[win], anchor="mm", stroke_width=5,
                    stroke_fill=(0, 0, 0))
            dd.text((cx, cy + 290), "HIT 1,000,000 FIRST", font=F("anton.woff2", 84), fill=(255, 210, 60),
                    anchor="mm", stroke_width=4, stroke_fill=(0, 0, 0))
            img = img.convert("RGBA")
            render.draw_rich(img, (cx, cy + 370), "Did you pick him? 👇", fPick, (255, 255, 255), anchor="ma",
                             stroke_width=3, stroke_fill=(0, 0, 0))
        # secousse
        amp = sum(a * max(0, 1 - (t - t0) / 0.3) for t0, a in shakes if t >= t0)
        if amp > 0.5:
            dx, dy = int(rng.uniform(-amp, amp)), int(rng.uniform(-amp, amp))
            sh = Image.new("RGB", (W, H), (10, 9, 22))
            sh.paste(img.convert("RGB"), (dx, dy))
            img = sh
        proc.stdin.write(img.convert("RGB").tobytes())
        if fi % 150 == 0:
            print("image", fi, "/", n_total, flush=True)
    proc.stdin.close()
    proc.wait()
    dur = n_total / FPS
    wav = out.with_suffix(".wav")
    audio(events, T, dur, wav, len(chars), song=SONG[0], song_start=SONG[1], lead_times=lead_times)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out.with_suffix(".video.mp4")), "-i", str(wav),
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-af", "loudnorm=I=-16:TP=-1.5", "-shortest",
                    str(out.with_suffix(".raw.mp4"))], check=True)
    render.stamp_video(out.with_suffix(".raw.mp4"), out)
    json.dump(dict(kind="powerdrop", seed=seed, chars=[c[0] for c in chars], winner=chars[win][0],
                   seconds=round(dur, 1)), open(out.with_suffix(".json"), "w"))
    print("OUT", out, flush=True)


# ------------------------------------------------------------------ son
def load(p, maxs=3.0):
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(p), "-t", str(maxs), "-f", "f32le", "-ac", "1",
                        "-ar", str(SR), "-"], capture_output=True)
    x = np.frombuffer(r.stdout, np.float32).astype(float)
    m = np.abs(x).max() or 1
    return x / m


def pitch(x, semis):
    f = 2 ** (semis / 12)
    idx = np.arange(0, len(x) - 1, f)
    return np.interp(idx, np.arange(len(x)), x)


def audio(events, T, dur, out, n_chars, song=None, song_start=0.0, per_hit=0.045, song_mode="bg", lead_times=()):
    snd = ROOT / "games/bounce_forge/snd"
    K = ROOT / "clipper/assets/sfx"
    mar = load(snd / "marimba.wav", 0.6)
    gpop = load(snd / "gem_pop1.wav", 0.6)
    gmerge = load(snd / "gem_merge.wav", 1.2)
    cash = load(snd / "cash.wav", 1.1)
    cash[-int(0.3 * SR):] *= np.linspace(1, 0, int(0.3 * SR))
    bell = load(K / "impact_bell_heavy_000.ogg", 2.0)
    pup = load(K / "powerUp7.ogg", 1.0)
    boom = load(K / "low_frequency_explosion_000.ogg", 2.0)
    n = int(dur * SR) + SR
    a = np.zeros(n)

    def put(s, t, g):
        i = int(t * SR)
        j = min(n, i + len(s))
        if i < n:
            a[i:j] += g * s[:j - i]
    PENTA = [0, 2, 4, 7, 9, 12, 14, 16, 19, 21, 24, 26, 28, 31]
    cache = {}
    last_peg = -1
    if song and song_mode == "bg":                            # musique de fond continue (choix du 06/11)
        sg = load(song, 400)[int(song_start * SR):][:n]
        env = np.ones(len(sg))
        fi_, fo_ = int(0.3 * SR), int(1.2 * SR)
        env[:fi_] = np.linspace(0, 1, fi_)
        end_i = min(len(sg), int(dur * SR))
        env[max(0, end_i - fo_):end_i] *= np.linspace(1, 0, end_i - max(0, end_i - fo_))
        env[end_i:] = 0
        a[:len(sg)] += 0.28 * sg * env
    elif song:                                                  # « Ma chanson » : chaque clou fait avancer le morceau
        sg = load(song, 400)
        sg = sg[int(song_start * SR):]
        blk = int(0.01 * SR)
        hits = sorted(t for t, k, _ in events if k == "peg")
        budget, sp, hi, g = 0.0, 0, 0, 0.0
        for bi in range(int(min(T + 0.05, dur) / 0.01)):
            tb = bi * 0.01
            while hi < len(hits) and hits[hi] <= tb:
                budget = min(0.4, budget + per_hit)
                hi += 1
            target = 1.0 if budget > 0 else 0.0
            g0 = g
            g += (target - g) * 0.5
            if g > 0.01 and sp + blk < len(sg):
                env = np.linspace(g0, g, blk)
                a[bi * blk:(bi + 1) * blk] += 0.8 * sg[sp:sp + blk] * env
                sp += blk
            budget = max(0.0, budget - 0.01)
    for t, kind, d in events:
        if kind == "peg":
            if song and song_mode != "bg":
                continue
            if t - last_peg < 0.025:                          # pas 2 notes collées
                continue
            last_peg = t
            semi = PENTA[min(len(PENTA) - 1, d["n"] // 2)] - 5 + d["c"] * 2
            if semi not in cache:
                cache[semi] = pitch(mar, semi)
            put(cache[semi], t, 0.16)
        elif kind == "spawn":
            put(pitch(gpop, -5), t, 0.10)
        elif kind == "land":
            m = d["m"]
            if m >= 5:
                put(bell, t, 0.55 if m == 10 else 0.4)
                put(pup, t + 0.02, 0.35)
                put(cash, t + 0.05, 0.45)
            elif m >= 1.5:
                put(pitch(gmerge, 4 if m == 2 else 0), t, 0.35)
                put(cash, t + 0.03, 0.25)
            elif m == 1:
                put(gpop, t, 0.3)
            else:                                              # ÷2 : « wah wah » qui descend
                tt = np.arange(int(0.55 * SR)) / SR
                fr = 330 * 2 ** (-tt * 1.6)
                s = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-tt * 3) * (0.6 + 0.4 * np.sign(np.sin(2 * np.pi * 7 * tt)))
                put(s, t, 0.35)
    # changement de leader : souffle + petit « ding » qui monte
    nz = np.random.default_rng(1).standard_normal(int(0.3 * SR))
    wenv = np.sin(np.linspace(0, np.pi, len(nz))) ** 2
    whoosh = np.convolve(nz, np.ones(30) / 30, "same") * wenv
    for lt in lead_times:
        if lt < T - 0.1:
            put(whoosh, lt, 0.25)
            put(pitch(gpop, 7), lt + 0.05, 0.3)
    # victoire : cloche + boum + accord
    put(bell, T, 0.8)
    put(boom, T, 0.6)
    tt = np.arange(int(1.6 * SR)) / SR
    for k, f0 in enumerate([523.25, 659.25, 783.99, 1046.5]):
        put(np.sin(2 * np.pi * f0 * tt) * np.exp(-tt * 2.2) * (tt > 0), T + 0.1 + k * 0.07, 0.18)
    a = np.tanh(a * 1.2)
    w = wave.open(str(out), "wb")
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((a * 0.9 * 32767).astype(np.int16).tobytes())
    w.close()


if __name__ == "__main__":
    main()
