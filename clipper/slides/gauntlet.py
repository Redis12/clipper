"""« Gauntlet » (04/11, idée de l'utilisateur : « Can Base Goku pass the One Piece gauntlet? ») : un héros trop fort
pour l'univers adverse enchaîne les K.O. SANS se transformer. Boîte quadrillée façon Power Up : le héros (petite
balle) rebondit et frappe l'adversaire du moment (grosse balle) ; chaque adversaire a plus de PV ; K.O. = explosion
+ « K.O.! », l'adversaire suivant tombe dans la boîte. Échelle des adversaires sous la boîte (barrés une fois battus).
Fin : « <HÉROS> CLEARED THE GAUNTLET » + « Who should he face next? Comment 👇 ».

`generate(hero={"name","image_path"}, foes=[{"name","image_path"}…], universe="One Piece")`."""
from __future__ import annotations

import json
import math
import random
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from .. import config, db
from ..util import log, require_bin
from . import fusion, render

W, H, FPS = 1080, 1920, 30
HERO_COL, BOSS_COL, YELLOW = (255, 150, 40), (235, 60, 70), (255, 214, 10)


def simulate(seed: int, S: float, n_foes: int, hits_for, dt: float = 1 / 240):
    """Rend les positions image par image et les chocs. Le boss change après `hits_for(i)` coups (+ pause K.O.)."""
    rnd = random.Random(seed)
    rh = S * 0.075
    frames, hits, kos = [], [], []
    foe, got, t, next_frame, cool, pause = 0, 0, 0.0, 0.0, 0.0, 0.0

    def new_boss(i):
        RB = S * (0.15 + 0.07 * i / max(1, n_foes - 1))
        return RB, rnd.uniform(RB, S - RB), rnd.uniform(RB, S * 0.45), rnd.uniform(-1, 1) * S * 0.12, S * 0.05
    RB, bx, by, bvx, bvy = new_boss(0)
    hx, hy = S * 0.5, S * 0.85
    a = rnd.uniform(-2.4, -0.7)
    hv = S * 1.05
    hvx, hvy = math.cos(a) * hv, math.sin(a) * hv
    while foe < n_foes:
        if pause > 0:                                     # K.O. : tout s'arrête un instant
            pause -= dt
            if pause <= 0:
                foe += 1
                if foe >= n_foes:
                    break
                RB, bx, by, bvx, bvy = new_boss(foe)
                got = 0
                if math.hypot(hx - bx, hy - by) < RB + rh + 4:
                    hy = min(S - rh, by + RB + rh + 10)
        else:
            hx += hvx * dt
            hy += hvy * dt
            bx += bvx * dt
            by += bvy * dt
            for p, v, r in ((0, 0, rh), (1, 1, RB)):
                pass
            if hx < rh or hx > S - rh:
                hvx = -hvx
                hx = min(max(hx, rh), S - rh)
            if hy < rh or hy > S - rh:
                hvy = -hvy
                hy = min(max(hy, rh), S - rh)
            if bx < RB or bx > S - RB:
                bvx = -bvx
                bx = min(max(bx, RB), S - RB)
            if by < RB or by > S - RB:
                bvy = -bvy
                by = min(max(by, RB), S - RB)
            dx, dy = hx - bx, hy - by
            dist = math.hypot(dx, dy) or 1
            cool -= dt
            if dist < RB + rh:
                nx, ny = dx / dist, dy / dist
                hx, hy = bx + nx * (RB + rh + 0.5), by + ny * (RB + rh + 0.5)
                dot = hvx * nx + hvy * ny
                if dot < 0:
                    hvx -= 2 * dot * nx
                    hvy -= 2 * dot * ny
                    ang = math.atan2(hvy, hvx) + rnd.uniform(-0.25, 0.25)   # un peu de hasard : pas de boucle
                    hvx, hvy = math.cos(ang) * hv, math.sin(ang) * hv
                    bvx -= nx * S * 0.05
                    bvy -= ny * S * 0.05
                    sp = math.hypot(bvx, bvy) or 1
                    lim = S * 0.16
                    if sp > lim:
                        bvx, bvy = bvx / sp * lim, bvy / sp * lim
                if cool <= 0:
                    cool = 0.12
                    got += 1
                    hits.append((t, bx + nx * RB, by + ny * RB, foe))
                    if got >= hits_for(foe):
                        kos.append((t, bx, by, foe))
                        pause = 1.1
        t += dt
        if t >= next_frame:
            frames.append((bx, by, RB, hx, hy, rh, foe, pause > 0))
            next_frame += 1 / FPS
        if t > 300:
            break
    return {"frames": frames, "hits": hits, "kos": kos}


def generate(hero: dict, foes: list[dict], universe: str = "One Piece", out: Path | None = None,
             seed: int | None = None, base_hits: int = 3, step_hits: int = 2, dmg: int = 9001) -> Path:
    from . import fxengine, vfxgen
    k = W / 1080
    n = len(foes)
    S = W * 0.86
    ox, oy = (W - S) / 2, H * 0.215
    hits_for = lambda i: base_hits + step_hits * i                                      # noqa: E731
    seed = seed if seed is not None else random.randrange(1_000_000)
    sim = simulate(seed, S, n, hits_for)
    frames = sim["frames"]
    hit_by_frame: dict = {}
    for h in sim["hits"]:
        hit_by_frame.setdefault(int(h[0] * FPS), []).append(h)
    ko_by_frame = {int(x[0] * FPS): x for x in sim["kos"]}
    foe_icons = [fusion.icon(f["image_path"], 512, BOSS_COL) for f in foes]
    hero_icon = fusion.icon(hero["image_path"], 256, HERO_COL)
    small = [fusion.icon(f["image_path"], 96, (90, 90, 110)) for f in foes]
    bg = Image.new("RGBA", (W, H), (12, 14, 22, 255))
    bd = ImageDraw.Draw(bg)
    stp = S / 24
    for i in range(25):
        bd.line((ox + i * stp, oy, ox + i * stp, oy + S), fill=(32, 36, 52), width=1)
        bd.line((ox, oy + i * stp, ox + S, oy + i * stp), fill=(32, 36, 52), width=1)
    fl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(fl).rectangle((ox - 6 * k, oy - 6 * k, ox + S + 6 * k, oy + S + 6 * k), outline=YELLOW + (255,),
                                 width=int(8 * k))
    bg.alpha_composite(fl.resize((W // 4, H // 4)).filter(ImageFilter.GaussianBlur(4)).resize((W, H)))
    bg.alpha_composite(fl)
    tf = render.font(int(62 * k))
    explo = list(vfxgen.frames("explosion", 256, BOSS_COL))
    parts = fxengine.Particles(seed)
    out = out or config.data_dir() / "fusions" / f"gauntlet_{seed}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".video.mp4")
    ffmpeg = require_bin("ffmpeg")
    proc = subprocess.Popen([ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
                             "-crf", "20", "-pix_fmt", "yuv420p", str(tmp)], stdin=subprocess.PIPE)
    floats, ko_at, dealt = [], [], [0] * n
    hit_t, ko_t = [], []
    end_frames = int(FPS * 2.0)
    try:
        for fi in range(len(frames) + end_frames):
            t = fi / FPS
            ended = fi >= len(frames)
            bx, by, RB, hx, hy, rh, foe, paused = frames[min(fi, len(frames) - 1)]
            for h in hit_by_frame.get(fi, []):
                dealt[h[3]] += 1
                floats.append((t, ox + h[1], oy + h[2]))
                hit_t.append(t)
                parts.emit(ox + h[1], oy + h[2], 10, speed=(200 * k, 650 * k), col=(255, 220, 150), life=(0.15, 0.35),
                           size=(2 * k, 4 * k))
            if fi in ko_by_frame:
                x = ko_by_frame[fi]
                ko_at.append((t, ox + x[1], oy + x[2], x[3], RB))
                ko_t.append(t)
                parts.emit(ox + x[1], oy + x[2], 70, speed=(300 * k, 1200 * k), col=(255, 190, 140), life=(0.3, 0.9),
                           size=(3 * k, 7 * k))
            parts.step(1 / FPS)
            img = bg.copy()
            d = ImageDraw.Draw(img)
            # titre
            render.draw_rich(img, (W / 2, H * 0.04), f"Can Base {hero['name']} beat", tf, (255, 255, 255), "ma",
                             int(4 * k), (0, 0, 0))
            d = ImageDraw.Draw(img)
            d.text((W / 2, H * 0.04 + 76 * k), f"the {universe.upper()} GAUNTLET?", font=render.font(int(70 * k)),
                   anchor="ma", fill=BOSS_COL, stroke_width=int(5 * k), stroke_fill=(0, 0, 0))
            kills = sum(1 for x in ko_at)
            d.text((W / 2, oy - 34 * k), f"KILLS {kills}/{n}", font=render.font(int(44 * k)), anchor="mm",
                   fill=YELLOW, stroke_width=int(4 * k), stroke_fill=(0, 0, 0))
            # adversaire du moment (pas pendant le K.O.)
            if not ended and not paused:
                ic = foe_icons[foe].resize((int(RB * 2), int(RB * 2)), Image.LANCZOS)
                if hit_by_frame.get(fi) or hit_by_frame.get(fi - 1):
                    red = Image.new("RGBA", ic.size, (255, 40, 40, 255))
                    red.putalpha(ic.getchannel("A").point(lambda v: v // 2))
                    ic = Image.alpha_composite(ic, red)
                img.alpha_composite(ic, (int(ox + bx - RB), int(oy + by - RB)))
                d = ImageDraw.Draw(img)
                hp = 1 - dealt[foe] / hits_for(foe)
                bw = RB * 1.6
                x0, y0 = ox + bx - bw / 2, oy + by - RB - 26 * k
                d.rectangle((x0 - 3, y0 - 3, x0 + bw + 3, y0 + 16 * k + 3), fill=(0, 0, 0))
                d.rectangle((x0, y0, x0 + bw * hp, y0 + 16 * k), fill=(235, 60, 70))
                d.text((ox + bx, y0 - 8 * k), foes[foe]["name"].upper(), font=render.font(int(30 * k)), anchor="md",
                       fill=(255, 255, 255), stroke_width=int(3 * k), stroke_fill=(0, 0, 0))
            # héros
            hs = int(rh * 2)
            au = Image.new("RGBA", (hs * 3, hs * 3), (0, 0, 0, 0))
            ImageDraw.Draw(au).ellipse((hs * 0.7, hs * 0.7, hs * 2.3, hs * 2.3), fill=(255, 200, 80, 90))
            au = au.filter(ImageFilter.GaussianBlur(hs * 0.25))
            img.alpha_composite(au, (int(ox + hx - au.width / 2), int(oy + hy - au.height / 2)))
            img.alpha_composite(hero_icon.resize((hs, hs), Image.LANCZOS), (int(ox + hx - hs / 2), int(oy + hy - hs / 2)))
            # « -9,001 »
            keep = []
            for (ft, fx_, fy_) in floats:
                a = (t - ft) / 0.7
                if a < 1:
                    keep.append((ft, fx_, fy_))
                    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                    al = int(255 * (1 - a))
                    ImageDraw.Draw(lay).text((fx_, fy_ - 60 * k * a), f"-{dmg:,}", font=render.font(int(38 * k)),
                                             anchor="mm", fill=(255, 230, 120, al), stroke_width=int(3 * k),
                                             stroke_fill=(0, 0, 0, al))
                    img.alpha_composite(lay)
            floats[:] = keep[-6:]
            # K.O. : explosion + texte
            for (kt, kx, ky, kf, kR) in ko_at[-1:]:
                a = (t - kt) / 0.9
                if 0 <= a < 1:
                    f_ = explo[min(len(explo) - 1, int(a * len(explo)))]
                    sz = int(kR * 4)
                    img.alpha_composite(f_.resize((sz, sz)), (int(kx - sz / 2), int(ky - sz / 2)))
                    d = ImageDraw.Draw(img)
                    s = 1 + 0.4 * max(0.0, 1 - a / 0.2)
                    d.text((W / 2, oy + S * 0.5), "K.O.!", font=render.font(int(150 * k * s)), anchor="mm",
                           fill=YELLOW, stroke_width=int(7 * k), stroke_fill=(0, 0, 0))
                    d.text((W / 2, oy + S * 0.5 + 110 * k), foes[kf]["name"].upper(), font=render.font(int(54 * k)),
                           anchor="mm", fill=(255, 255, 255), stroke_width=int(4 * k), stroke_fill=(0, 0, 0))
            en = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            parts.draw(en, 1.0)
            img = fxengine.bloom(img, en, 0.7)
            d = ImageDraw.Draw(img)
            # échelle des adversaires sous la boîte
            yb = oy + S + 40 * k
            per_row = min(n, 6)
            sz = int(min(120 * k, (W * 0.9) / per_row - 14 * k))
            for i, sm in enumerate(small):
                row, col = divmod(i, per_row)
                cnt = min(per_row, n - row * per_row)
                x = W / 2 + (col - (cnt - 1) / 2) * (sz + 14 * k) - sz / 2
                y = yb + row * (sz + 20 * k)
                ic = sm.resize((sz, sz), Image.LANCZOS)
                done = any(kf == i for (_, _, _, kf, _) in ko_at)
                if done:
                    g = ic.convert("LA").convert("RGBA")
                    g.putalpha(ic.getchannel("A"))
                    ic = g
                img.alpha_composite(ic, (int(x), int(y)))
                d = ImageDraw.Draw(img)
                if done:
                    d.line((x + 10, y + 10, x + sz - 10, y + sz - 10), fill=(235, 50, 60), width=int(8 * k))
                    d.line((x + sz - 10, y + 10, x + 10, y + sz - 10), fill=(235, 50, 60), width=int(8 * k))
                elif i == foe and not ended:
                    d.ellipse((x - 4, y - 4, x + sz + 4, y + sz + 4), outline=YELLOW, width=int(5 * k))
            if ended:                                             # écran de fin
                e = t - len(frames) / FPS
                dim = Image.new("RGBA", (W, H), (0, 0, 0, int(205 * min(1.0, e / 0.3))))
                img.alpha_composite(dim)
                big = int(W * 0.46)
                img.alpha_composite(hero_icon.resize((big, big), Image.LANCZOS), (int(W / 2 - big / 2), int(H * 0.36)))
                d = ImageDraw.Draw(img)
                d.text((W / 2, H * 0.27), f"{hero['name'].upper()} CLEARED", font=render.font(int(80 * k)), anchor="mm",
                       fill=HERO_COL, stroke_width=int(5 * k), stroke_fill=(0, 0, 0))
                d.text((W / 2, H * 0.27 + 90 * k), "THE GAUNTLET", font=render.font(int(80 * k)), anchor="mm",
                       fill=YELLOW, stroke_width=int(5 * k), stroke_fill=(0, 0, 0))
                render.draw_rich(img, (W / 2, H * 0.36 + big + 40 * k), "Who should he face next? Comment 👇",
                                 render.font(int(46 * k)), (255, 255, 255), "ma", int(3 * k), (0, 0, 0))
            proc.stdin.write(img.convert("RGB").tobytes())
        proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError("ffmpeg a échoué")
    finally:
        if proc.poll() is None:
            proc.kill()
    import numpy as np
    from . import domain
    dur = (len(frames) + end_frames) / FPS
    rate = fusion.RATE
    na = int(dur * rate) + rate
    audio = np.zeros(na, dtype=np.float32)

    def put(tt, x, g):
        i = int(tt * rate)
        if x is not None and 0 <= i < na:
            seg = x[: na - i]
            audio[i:i + len(seg)] += seg * g
    try:
        from . import seo
        fr = seo.anime_of(hero["name"])
        franchise = fr[0].lower() if fr else None
    except Exception:
        franchise = None
    hs_ = [domain.sfx("hit", mode="anime", seed=i, franchise=franchise) for i in range(4)]
    for i, tt in enumerate(hit_t):
        put(tt, hs_[i % 4], 0.45)
    for tt in ko_t:
        put(tt, domain.sfx("ko", mode="anime", franchise=franchise), 0.9)
        put(tt + 0.05, domain.sfx("bomb", mode="anime", seed=3, franchise=franchise), 0.8)
    put(len(frames) / FPS, domain.sfx("win"), 0.8)
    lvl = float(np.percentile(np.abs(audio), 99.7)) or 1.0
    audio = audio * min(1.0, 0.75 / lvl)
    wav = out.with_suffix(".wav")
    fusion.write_wav(wav, np.tanh(audio * 1.1) / math.tanh(1.1))
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(tmp), "-i", str(wav), "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "160k", "-shortest", str(out)], check=True)
    tmp.unlink(missing_ok=True)
    wav.unlink(missing_ok=True)
    meta = {"kind": "gauntlet", "title": f"Can Base {hero['name']} beat the {universe} gauntlet?",
            "hero": hero["name"], "names": [hero["name"]] + [f["name"] for f in foes], "universe": universe,
            "seed": seed, "seconds": round(dur, 1), "created_at": db.now()}
    out.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    from .domain import _brand_video
    _brand_video(out)
    log.info("gauntlet : %s vs %d adversaires, %.0f s → %s", hero["name"], n, dur, out.name)
    return out
