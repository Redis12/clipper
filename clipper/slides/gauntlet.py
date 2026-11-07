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


def simulate(seed: int, S: float, n_foes: int, hits_for, dt: float = 1 / 240, specials: list | None = None,
             lose_at: int | None = None, lose_after: float = 3.0):
    """Rend les positions image par image et les chocs. Le boss change après `hits_for(i)` coups (+ pause K.O.)."""
    rnd = random.Random(seed)
    rh = S * 0.075
    frames, hits, kos, events = [], [], [], []
    specials = specials or [None] * n_foes
    used = set()
    gag_until = 0.0
    phase_until = 0.0
    foe, got, t, next_frame, cool, pause = 0, 0, 0.0, 0.0, 0.0, 0.0

    def new_boss(i):
        RB = S * (0.15 + 0.07 * i / max(1, n_foes - 1))
        return RB, rnd.uniform(RB, S - RB), rnd.uniform(RB, S * 0.45), rnd.uniform(-1, 1) * S * 0.12, S * 0.05
    RB, bx, by, bvx, bvy = new_boss(0)
    if (specials[0] or {}).get("gag"):
        gag_until = float(specials[0].get("gag_s", 1.3))
        events.append(("gag", 0, 0.0, gag_until))
    hx, hy = S * 0.5, S * 0.85
    a = rnd.uniform(-2.4, -0.7)
    hv = S * 1.05
    hvx, hvy = math.cos(a) * hv, math.sin(a) * hv
    foe_t0 = 0.0
    while foe < n_foes:
        if lose_at is not None and foe == lose_at and t - foe_t0 >= lose_after:   # gauntlet inversé : il tombe
            events.append(("lose", foe, t, hx, hy))
            break
        if pause > 0:                                     # K.O. : tout s'arrête un instant
            pause -= dt
            if pause <= 0:
                foe += 1
                if foe >= n_foes:
                    break
                RB, bx, by, bvx, bvy = new_boss(foe)
                got = 0
                foe_t0 = t
                sp = specials[foe] or {}
                if sp.get("gag"):                         # gag au début (Sanji cuisine, Talk no Jutsu…)
                    gag_until = t + float(sp.get("gag_s", 1.3))
                    events.append(("gag", foe, t, gag_until))
                if math.hypot(hx - bx, hy - by) < RB + rh + 4:
                    hy = min(S - rh, by + RB + rh + 10)
        elif t < gag_until:
            pass                                          # tout le monde attend la fin du gag
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
            sp = specials[foe] or {}
            if dist < RB + rh and t >= phase_until and sp.get("tp") and ("tp", foe) not in used:
                used.add(("tp", foe))                     # Minato : Hiraishin, il disparaît et réapparaît plus loin
                ox_, oy_ = bx, by
                bx = S - bx if abs(S - 2 * bx) > RB * 2 else rnd.uniform(RB, S - RB)
                by = min(max(S - by, RB), S - RB)
                events.append(("tp", foe, t, ox_, oy_, bx, by))
                dx, dy = hx - bx, hy - by
                dist = math.hypot(dx, dy) or 1
            elif dist < RB + rh and sp.get("fake") and ("fake", foe) not in used:
                used.add(("fake", foe))                   # Itachi : genjutsu, il « meurt »… et revient derrière Goku
                gag_until = t + 1.3
                hv_ = math.hypot(hvx, hvy) or 1
                nbx = min(max(hx - hvx / hv_ * (RB + rh + 30), RB), S - RB)
                nby = min(max(hy - hvy / hv_ * (RB + rh + 30), RB), S - RB)
                events.append(("fake", foe, t, gag_until, bx, by))
                bx, by = nbx, nby
                hx, hy = hx + hvx / hv_ * 40, hy + hvy / hv_ * 40
                hx, hy = min(max(hx, rh), S - rh), min(max(hy, rh), S - rh)
                continue
            elif dist < RB + rh and sp.get("kamui") and ("kamui", foe) not in used:
                used.add(("kamui", foe))                  # Obito : Kamui, Goku passe à travers
                phase_until = t + 0.6
                events.append(("kamui", foe, t, phase_until))
            if dist < RB + rh and t < phase_until:
                pass
            elif dist < RB + rh:
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
    return {"frames": frames, "hits": hits, "kos": kos, "events": events}


def generate(hero: dict, foes: list[dict], universe: str = "One Piece", out: Path | None = None,
             seed: int | None = None, base_hits: int = 3, step_hits: int = 2, dmg: int = 9001,
             lose_at: int | None = None, lose_after: float = 3.0, title: tuple | None = None,
             lose_move: str | None = None) -> Path:
    from . import fxengine, vfxgen
    k = W / 1080
    n = len(foes)
    S = W * 0.86
    ox, oy = (W - S) / 2, H * 0.215
    hits_for = lambda i: (10 ** 6 if i == lose_at else base_hits + step_hits * i)        # noqa: E731
    seed = seed if seed is not None else random.randrange(1_000_000)
    specials = [{k_: v for k_, v in f.items() if k_ in ("gag", "gag_s", "tp", "kamui", "say", "fake")} or None for f in foes]
    sim = simulate(seed, S, n, hits_for, specials=specials, lose_at=lose_at, lose_after=lose_after)
    lost = next((e for e in sim["events"] if e[0] == "lose"), None)
    evs = sim["events"]
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
    panels: dict = {}
    by_ = [0.0]

    def banner(img_, text, age, col):
        if age > 1.0:
            return
        s_ = 1 + 0.35 * max(0.0, 1 - age / 0.15)
        yb_ = oy + 70 * k if by_[0] > S * 0.4 else oy + S - 70 * k      # loin du perso (pas sur son nom)
        ImageDraw.Draw(img_).text((W / 2, yb_), text, font=render.font(int(64 * k * s_)), anchor="mm",
                                  fill=col, stroke_width=int(6 * k), stroke_fill=(0, 0, 0))

    def bubble(img_, x, y, text):
        f_ = render.font(int(40 * k))
        dd = ImageDraw.Draw(img_)
        lines = render.wrap(text, f_, int(W * 0.6), dd) or [text]
        lh = int(48 * k)
        bw = max(render.text_width(dd, ln, f_) for ln in lines) + 50 * k
        bh = lh * len(lines) + 30 * k
        x0 = min(max(ox + 10 * k, x - bw / 2), ox + S - bw - 10 * k)
        y0 = max(oy + 120 * k, y - bh)
        dd.rounded_rectangle((x0, y0, x0 + bw, y0 + bh), radius=int(24 * k), fill=(255, 255, 255),
                             outline=(0, 0, 0), width=int(5 * k))
        tx = min(max(x, x0 + 30 * k), x0 + bw - 30 * k)
        dd.polygon([(tx - 18 * k, y0 + bh - 3), (tx + 18 * k, y0 + bh - 3), (tx, y0 + bh + 26 * k)], fill=(255, 255, 255))
        for i_, ln in enumerate(lines):
            render.draw_rich(img_, (x0 + bw / 2, y0 + 15 * k + i_ * lh), ln, f_, (20, 20, 20), "ma", 0, (0, 0, 0))
    hit_t, ko_t = [], []
    end_frames = int(FPS * (2.0 + (1.4 if lost else 0)))
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
            t1, t2 = title or (f"Can Base {hero['name']} beat", f"the {universe.upper()} GAUNTLET?")
            render.draw_rich(img, (W / 2, H * 0.04), t1, tf, (255, 255, 255), "ma",
                             int(4 * k), (0, 0, 0))
            d = ImageDraw.Draw(img)
            f2 = render.font(int(70 * k))
            while f2.size > 30 and render.text_width(d, t2, f2) > W * 0.94:
                f2 = render.font(f2.size - 3)
            d.text((W / 2, H * 0.04 + 76 * k), t2, font=f2,
                   anchor="ma", fill=BOSS_COL, stroke_width=int(5 * k), stroke_fill=(0, 0, 0))
            kills = sum(1 for x in ko_at)
            d.text((W / 2, oy - 34 * k), f"KILLS {kills}/{n}", font=render.font(int(44 * k)), anchor="mm",
                   fill=YELLOW, stroke_width=int(4 * k), stroke_fill=(0, 0, 0))
            # adversaire du moment (pas pendant le K.O.)
            if not ended and not paused:
                gnow = [e for e in evs if e[0] in ("gag", "fake") and e[1] == foe and e[2] <= t < e[3]]
                fxk = foes[foe].get("fx")
                sc_, dx_ = 1.0, 0.0
                hide = False
                if gnow:
                    q = (t - gnow[0][2]) / max(0.1, gnow[0][3] - gnow[0][2])
                    if fxk == "inflate":                         # Gear 5 : gonfle comme un ballon
                        sc_ = 1 + 0.45 * math.sin(min(1.0, q) * math.pi / 2) + 0.05 * math.sin(t * 30)
                    elif fxk == "lost":                          # Zoro arrive par le mauvais côté
                        dx_ = (1 - min(1.0, q / 0.6)) * (S * 0.6)
                    if gnow[0][0] == "fake" and q < 0.5:
                        hide = True
                RBd = int(RB * 2 * sc_)
                ic = foe_icons[foe].resize((RBd, RBd), Image.LANCZOS)
                if hide:
                    ic.putalpha(0)
                if any(e[0] == "kamui" and e[1] == foe and e[2] <= t < e[3] for e in evs):
                    ic.putalpha(ic.getchannel("A").point(lambda v: v * 35 // 100))   # intangible
                if hit_by_frame.get(fi) or hit_by_frame.get(fi - 1):
                    red = Image.new("RGBA", ic.size, (255, 40, 40, 255))
                    red.putalpha(ic.getchannel("A").point(lambda v: v // 2))
                    ic = Image.alpha_composite(ic, red)
                img.alpha_composite(ic, (int(ox + bx + dx_ - RBd / 2), int(oy + by - RBd / 2)))
                d = ImageDraw.Draw(img)
                hp = 1 - dealt[foe] / hits_for(foe)
                bw = RB * 1.6
                x0, y0 = ox + bx + dx_ - bw / 2, oy + by - RBd / 2 - 26 * k
                if y0 < oy + 50 * k:                              # trop haut (sous « KILLS ») : sous la balle
                    y0 = oy + by + RBd / 2 + 46 * k
                if not hide:
                    d.rectangle((x0 - 3, y0 - 3, x0 + bw + 3, y0 + 16 * k + 3), fill=(0, 0, 0))
                    d.rectangle((x0, y0, x0 + bw * hp, y0 + 16 * k), fill=(235, 60, 70))
                if not hide:
                  d.text((ox + bx + dx_, y0 - 8 * k), foes[foe]["name"].upper(), font=render.font(int(30 * k)), anchor="md",
                       fill=(255, 255, 255), stroke_width=int(3 * k), stroke_fill=(0, 0, 0))
            # héros
            hs = int(rh * 2)
            au = Image.new("RGBA", (hs * 3, hs * 3), (0, 0, 0, 0))
            ImageDraw.Draw(au).ellipse((hs * 0.7, hs * 0.7, hs * 2.3, hs * 2.3), fill=(255, 200, 80, 90))
            au = au.filter(ImageFilter.GaussianBlur(hs * 0.25))
            img.alpha_composite(au, (int(ox + hx - au.width / 2), int(oy + hy - au.height / 2)))
            img.alpha_composite(hero_icon.resize((hs, hs), Image.LANCZOS), (int(ox + hx - hs / 2), int(oy + hy - hs / 2)))
            by_[0] = by
            for ev in evs:                                       # gags et pouvoirs (Hiraishin, Kamui, Talk no Jutsu…)
                kind, ef, t0 = ev[0], ev[1], ev[2]
                age = t - t0
                if kind == "tp" and 0 <= age < 0.9:              # image rémanente + éclair jaune
                    _, _, _, x0_, y0_, x1_, y1_ = ev
                    gh = foe_icons[ef].resize((int(RB * 2), int(RB * 2)))
                    gh.putalpha(gh.getchannel("A").point(lambda v: int(v * 0.5 * (1 - age / 0.9))))
                    img.alpha_composite(gh, (int(ox + x0_ - RB), int(oy + y0_ - RB)))
                    dl = ImageDraw.Draw(img)
                    if age < 0.25:
                        dl.line((ox + x0_, oy + y0_, ox + x1_, oy + y1_), fill=(255, 230, 90), width=int(14 * k))
                    banner(img, foes[ef].get("tp_name", "FLYING RAIJIN!"), age, (255, 225, 80))
                    if age < 0.6:
                        dl.text((ox + hx, oy + hy - 70 * k), "MISS!", font=render.font(int(44 * k)), anchor="mm",
                                fill=(255, 255, 255), stroke_width=int(4 * k), stroke_fill=(0, 0, 0))
                elif kind == "kamui" and 0 <= age < 1.1:
                    dl = ImageDraw.Draw(img)
                    for j in range(5):                           # tourbillon violet autour d'Obito
                        rr = RB * (1.05 + 0.12 * j)
                        a0 = (age * 520 + j * 70) % 360
                        dl.arc((ox + bx - rr, oy + by - rr, ox + bx + rr, oy + by + rr), a0, a0 + 200,
                               fill=(150, 80, 230), width=int(6 * k))
                    banner(img, foes[ef].get("kamui_name", "KAMUI!"), age, (175, 110, 255))
                    if age < 0.7:
                        dl.text((ox + hx, oy + hy - 70 * k), "MISS!", font=render.font(int(44 * k)), anchor="mm",
                                fill=(255, 255, 255), stroke_width=int(4 * k), stroke_fill=(0, 0, 0))
                elif kind == "fake" and t0 <= t < ev[3] + 0.4:   # genjutsu : corbeaux, écran rouge, il revient
                    q = age / (ev[3] - t0)
                    tint = Image.new("RGBA", (W, H), (140, 0, 0, int(110 * max(0.0, 1 - abs(q - 0.4) * 1.6))))
                    img.alpha_composite(tint)
                    dl = ImageDraw.Draw(img)
                    if q < 0.7:                                  # corbeaux qui s'envolent de l'ancienne place
                        rc = random.Random(ef)
                        for j in range(16):
                            ang = rc.uniform(0, 2 * math.pi)
                            dd_ = RB * (0.3 + 2.2 * q) * rc.uniform(0.6, 1.2)
                            cx_ = ox + ev[4] + math.cos(ang) * dd_
                            cy_ = oy + ev[5] + math.sin(ang) * dd_ - 60 * k * q
                            w_ = 22 * k
                            dl.polygon([(cx_ - w_, cy_), (cx_, cy_ - w_ * 0.4), (cx_ + w_, cy_), (cx_, cy_ + w_ * 0.25)],
                                       fill=(10, 10, 14))
                    if q < 0.45:
                        dl.text((ox + ev[4], oy + ev[5]), "K.O.?", font=render.font(int(90 * k)), anchor="mm",
                                fill=YELLOW, stroke_width=int(6 * k), stroke_fill=(0, 0, 0))
                    else:
                        banner(img, foes[ef].get("fake_label", "GENJUTSU!"), age - (ev[3] - t0) * 0.45, (230, 40, 40))
                        dl.text((ox + bx, max(oy + 40 * k, oy + by - RB - 70 * k)), "Behind you.", font=render.font(int(44 * k)), anchor="mm",
                                fill=(255, 255, 255), stroke_width=int(4 * k), stroke_fill=(0, 0, 0))
                elif kind == "gag" and t0 <= t < ev[3] and foes[ef].get("fx") == "strings":
                    dl = ImageDraw.Draw(img)                     # Doflamingo : fils de marionnette qui ratent
                    q = age / (ev[3] - t0)
                    for j in range(6):
                        ex_ = ox + hx + (j - 2.5) * 30 * k + 60 * k * math.sin(j + t * 5)
                        ey_ = oy + hy - 80 * k
                        fx_ = ox + bx + (ex_ - ox - bx) * min(1.0, q * 1.5)
                        fy_ = oy + by + (ey_ - oy - by) * min(1.0, q * 1.5)
                        dl.line((ox + bx, oy + by, fx_, fy_), fill=(240, 240, 255), width=int(3 * k))
                    bubble(img, ox + bx, oy + by - RB - 40 * k, foes[ef].get("say", ""))
                    banner(img, foes[ef].get("gag_label", ""), age, (255, 150, 220))
                elif kind == "gag" and t0 <= t < ev[3] and foes[ef].get("panel"):
                    # case de manga plein écran (07/11 : « Nah, I'd win » de Gojo juste avant Sukuna)
                    pim = panels.get(ef)
                    if pim is None:
                        src = Image.open(foes[ef]["panel"]).convert("RGBA")
                        sc_ = min(W * 0.86 / src.width, H * 0.5 / src.height)
                        pim = panels[ef] = src.resize((int(src.width * sc_), int(src.height * sc_)), Image.LANCZOS)
                    dur_ = ev[3] - t0
                    fade = min(1.0, age / 0.12, max(0.0, (dur_ - age) / 0.2))
                    img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(190 * fade))))
                    pop = 1 + 0.18 * max(0.0, 1 - age / 0.18)
                    pz = pim.resize((int(pim.width * pop), int(pim.height * pop)))
                    if fade < 1:
                        pz.putalpha(pz.getchannel("A").point(lambda v, f_=fade: int(v * f_)))
                    fr_ = Image.new("RGBA", (pz.width + int(16 * k), pz.height + int(16 * k)), (255, 255, 255, int(255 * fade)))
                    img.alpha_composite(fr_, (int(W / 2 - fr_.width / 2), int(H * 0.47 - fr_.height / 2)))
                    img.alpha_composite(pz, (int(W / 2 - pz.width / 2), int(H * 0.47 - pz.height / 2)))
                    if foes[ef].get("gag_label"):
                        banner(img, foes[ef]["gag_label"], age, (255, 255, 255))
                elif kind == "gag" and t0 <= t < ev[3]:          # bulle de dialogue, texte qui s'écrit
                    say = foes[ef].get("say", "...")
                    nch = max(1, int(len(say) * min(1.0, age / max(0.3, (ev[3] - t0) * 0.7))))
                    bx_b = bx + (S * 0.6 * (1 - min(1.0, (age / (ev[3] - t0)) / 0.6)) if foes[ef].get("fx") == "lost" else 0)
                    bubble(img, ox + bx_b, oy + by - RB - 40 * k, say[:nch])
                    if foes[ef].get("gag_label"):
                        banner(img, foes[ef]["gag_label"], age, (255, 255, 255))
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
            if ended and lost and t - len(frames) / FPS < 1.4:  # il tombe : écran rouge, icône grise qui tremble
                e = t - len(frames) / FPS
                img.alpha_composite(Image.new("RGBA", (W, H), (150, 0, 0, int(120 * min(1.0, e / 0.2)))))
                lb = frames[-1]                                   # le vainqueur reste à sa place
                bic = foe_icons[lost[1]].resize((int(lb[2] * 2), int(lb[2] * 2)), Image.LANCZOS)
                img.alpha_composite(bic, (int(ox + lb[0] - lb[2]), int(oy + lb[1] - lb[2])))
                hs = int(rh * 2)
                g = hero_icon.resize((hs, hs)).convert("LA").convert("RGBA")
                g.putalpha(hero_icon.resize((hs, hs)).getchannel("A"))
                sh_ = 10 * k * max(0.0, 1 - e / 0.8) * math.sin(e * 70)
                img.alpha_composite(g, (int(ox + lost[3] - hs / 2 + sh_), int(oy + lost[4] - hs / 2)))
                d = ImageDraw.Draw(img)
                banner(img, lose_move or f"{foes[lost[1]]['name'].upper()}!", e, (255, 60, 60))
                d.text((ox + lost[3], oy + lost[4] - hs), "DOWN!", font=render.font(int(60 * k)), anchor="mm",
                       fill=(255, 255, 255), stroke_width=int(5 * k), stroke_fill=(0, 0, 0))
            elif ended and lost:                                  # écran de défaite
                e = t - len(frames) / FPS - 1.4
                img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(205 * min(1.0, e / 0.3)))))
                big = int(W * 0.46)
                img.alpha_composite(foe_icons[lost[1]].resize((big, big), Image.LANCZOS),
                                    (int(W / 2 - big / 2), int(H * 0.36)))
                d = ImageDraw.Draw(img)
                d.text((W / 2, H * 0.24), f"SURVIVED {lost[1]}/{n}", font=render.font(int(86 * k)), anchor="mm",
                       fill=YELLOW, stroke_width=int(5 * k), stroke_fill=(0, 0, 0))
                d.text((W / 2, H * 0.24 + 92 * k), f"STOPPED BY {foes[lost[1]]['name'].upper()}",
                       font=render.font(int(58 * k)), anchor="mm", fill=(255, 80, 80), stroke_width=int(5 * k),
                       stroke_fill=(0, 0, 0))
                render.draw_rich(img, (W / 2, H * 0.36 + big + 40 * k), "Did he deserve to lose? Comment 👇",
                                 render.font(int(46 * k)), (255, 255, 255), "ma", int(3 * k), (0, 0, 0))
            elif ended:                                           # écran de fin
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
        put(tt, hs_[i % 4], 0.3)
    for tt in ko_t:
        put(tt, domain.sfx("ko", mode="anime", franchise=franchise), 0.9)
        put(tt + 0.05, domain.sfx("bomb", mode="anime", seed=3, franchise=franchise), 0.8)
    for ev in evs:
        if ev[0] in ("tp", "kamui", "fake"):
            put(ev[2], domain.sfx("vanish", mode="anime", franchise=franchise), 0.7)
    if lost:
        put(lost[2], domain.sfx("ko", mode="anime", franchise=franchise), 1.0)
        put(lost[2] + 0.05, domain.sfx("bomb", mode="anime", seed=2, franchise=franchise), 0.8)
    put(len(frames) / FPS + (1.4 if lost else 0), domain.sfx("win"), 0.8)
    lvl = float(np.percentile(np.abs(audio), 99.7)) or 1.0
    audio = audio * min(1.0, 0.75 / lvl)
    wav = out.with_suffix(".wav")
    fusion.write_wav(wav, np.tanh(audio * 1.1) / math.tanh(1.1) * 0.24)   # ≈ −24 LUFS comme les autres formats
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(tmp), "-i", str(wav), "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "160k", "-shortest", str(out)], check=True)
    tmp.unlink(missing_ok=True)
    wav.unlink(missing_ok=True)
    meta = {"kind": "gauntlet", "title": " ".join(title) if title else f"Can Base {hero['name']} beat the {universe} gauntlet?",
            "lost_to": foes[lost[1]]["name"] if lost else None,
            "hero": hero["name"], "names": [hero["name"]] + [f["name"] for f in foes], "universe": universe,
            "seed": seed, "seconds": round(dur, 1), "created_at": db.now()}
    out.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    from .domain import _brand_video
    _brand_video(out)
    log.info("gauntlet : %s vs %d adversaires, %.0f s → %s", hero["name"], n, dur, out.name)
    return out
