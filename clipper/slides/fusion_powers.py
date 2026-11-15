"""Fusion « avec pouvoirs » (15/11, « JoJo Villain Transformations », idée de l'utilisateur).
Même jeu que la Fusion (chaîne de persos qui fusionnent), mais chaque perso a SON son à sa 1re apparition
(au lieu du même bruitage à chaque fusion, qui reste en plus, discret) et certains ont un POUVOIR qui agit sur la vidéo :
- `timestop` (DIO) : sphère inversée qui part de lui, puis la vidéo se FIGE (temps arrêté, image désaturée bleutée)
- `bites_the_dust` (Kira) : Killer Queen marque des balles qui EXPLOSENT, puis la vidéo REMBOBINE (Bites the Dust)
- `king_crimson` (Diavolo) : flash rouge, 5 s de la partie EFFACÉES (on saute), « TIME ERASED »
- `made_in_heaven` (Pucci) : la partie ACCÉLÈRE (un peu : ×1,5) jusqu'à la fin
Les pouvoirs décalent la vidéo : le son suit le temps de SORTIE (`out_t`), pas le temps de la simulation.
    generate(tiers, powers={"DIO": {"sound": ..., "power": "timestop"}, ...}, start_sound=...)
"""
from __future__ import annotations

import io
import json
import math
import random
import subprocess
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageOps

from .. import db
from ..util import log, require_bin
from . import fusion, render
from .fusion import RATE

EXPLOSION = Path(__file__).resolve().parents[2] / "library/_sfx/Helton Yan's Old-School Shonen SFX/EXPLDsgn_Anime Explosion 3.ogg"


def _pcm(path, start=0.0, dur=None):
    ff = require_bin("ffmpeg")
    cmd = [ff, "-loglevel", "error", "-ss", str(start)] + (["-t", str(dur)] if dur else []) + \
          ["-i", str(path), "-ac", "1", "-ar", str(RATE), "-f", "f32le", "-"]
    r = subprocess.run(cmd, capture_output=True)
    a = np.frombuffer(r.stdout, dtype=np.float32).copy()
    pk = float(np.max(np.abs(a))) if len(a) else 1.0
    return a / (pk or 1.0)


def _fade(a, fin=0.02, fout=0.4):
    a = a.copy()
    i, o = int(fin * RATE), int(fout * RATE)
    if i:
        a[:i] *= np.linspace(0, 1, min(i, len(a)))[:len(a[:i])]
    if o and len(a) > o:
        a[-o:] *= np.linspace(1, 0, o)
    return a


def _banner(img, text, y, size, col=(255, 255, 255), alpha=1.0):
    if alpha <= 0:
        return img
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    while size > 40 and render.font(size).getlength(text) > img.width * 0.9:   # trop long : plus petit
        size -= 4
    render.draw_rich(lay, (img.width / 2, y), text, render.font(size), col + (int(255 * alpha),), anchor="mm",
                     stroke_width=max(4, size // 12), stroke_fill=(0, 0, 0, int(255 * alpha)))
    base = img.convert("RGBA")
    base.alpha_composite(lay)
    return base.convert("RGB")


def _tint(img, rgb, k):
    over = Image.new("RGB", img.size, rgb)
    return Image.blend(img, over, k)


def _index(im, painter, sim, W, H, icons):
    """rangée des formes sous le bol : vues = icône ronde, pas encore vues = « ? » (on ne spoile pas la suite)"""
    n = len(sim.radii)
    size = min(96, int((W - 120) / n) - 12)
    gap = size + 12
    x0 = W / 2 - gap * (n - 1) / 2
    y = int(H * 0.87)
    im = im.convert("RGBA")
    d = ImageDraw.Draw(im)
    for k in range(n):
        x = x0 + k * gap
        box = (x - size / 2, y - size / 2, x + size / 2, y + size / 2)
        if k <= sim.best:
            if k not in icons:
                icons[k] = fusion.icon(painter.tiers[k].get("image_path"), size, (90, 90, 120)).convert("RGBA")
            im.alpha_composite(icons[k], (int(box[0]), int(box[1])))
            d.ellipse(box, outline=(255, 214, 60, 255) if k == sim.best else (200, 200, 210, 255), width=4)
        else:
            d.ellipse(box, fill=(25, 25, 34, 255), outline=(90, 90, 110, 255), width=3)
            d.text((x, y), "?", font=render.font(int(size * 0.55)), anchor="mm", fill=(160, 160, 180, 255))
    return im.convert("RGB")


def _ball_of(sim, tier):
    bs = [b for b in sim.balls if b.alive and b.tier == tier]
    return max(bs, key=lambda b: b.born) if bs else None


def generate(tiers: list[dict], title: str, powers: dict, start_sound: str | None = None, seed: int | None = None,
             out: Path | None = None, opts: dict | None = None, merge_gain: float = 0.35,
             merge_sounds: dict | None = None, index: bool = True) -> Path:
    """`merge_sounds` = {niveau: (fichier, début, durée)} : son joué à CHAQUE fusion de deux persos de ce niveau
    (15/11 : « chaque fusion des Pillar Men = le ay ay ay, 1 s ») ; sans entrée → petit « bloop ».
    `index` = rangée des formes sous le bol : déjà vues = icône, suivantes = « ? » (pas de spoil)."""
    c = dict(fusion.fcfg())
    c.update(opts or {})
    tiers = tiers[:16]
    names = [t["name"] for t in tiers]
    W, H = (int(v) for v in c.get("size", [1080, 1920]))
    fps = int(c.get("fps", 30))
    seed = int(seed if seed is not None else random.randrange(1_000_000))
    sim = fusion.setup(len(tiers), W, H, seed, bounce=str(c.get("style", "bounce")) != "pile",
                       speed=float(c.get("speed", 0.6)))
    sim.chase = bool(c.get("chase", len(tiers) > 10))   # chaînes longues : progression linéaire
    painter = fusion.Painter(sim, tiers, W, H, title)
    feeder = fusion.Feeder(sim, painter.funnel_top, c)
    out = out or fusion.out_dir() / f"fusion_powers_{seed}.mp4"
    tmp_video = out.with_suffix(".video.mp4")
    ff = require_bin("ffmpeg")
    proc = subprocess.Popen([ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                             "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                             "-pix_fmt", "yuv420p", str(tmp_video)], stdin=subprocess.PIPE)
    sub = int(c.get("substeps", 6))
    dt = 1 / fps
    n_out = 0
    merges_out = []                       # (temps de sortie, niveau) → petit bruitage de fusion
    sfx = []                              # (temps de sortie, tableau audio, gain)
    ring = deque(maxlen=int(2.6 * fps))   # dernières images (JPEG) pour le rembobinage
    history = []                          # toutes les images (JPEG, 1/2) si un pouvoir « reset » existe
    keep_all = any(v.get("reset") for v in powers.values())
    appear = {}                           # niveau → image de sortie de sa 1re apparition
    reset = {}                            # Made in Heaven « reset » : {"at": t_sortie, "frame": n, "p": spec}
    seen = 0                              # dernier niveau déjà « présenté »
    queue = []                            # pouvoirs en attente : [t_sim_déclenchement, nom, niveau]
    speed = 1.0
    speed_target = 1.0
    banners = []                          # (t_sortie_début, durée, texte, couleur)
    bombs = []                            # balles marquées par Killer Queen
    booms = []                            # (x, y, t_sim) explosions
    playing = {}                          # son → fin (temps de sortie) : pas deux fois le même en même temps

    def emit(im):
        nonlocal n_out
        t_out = n_out / fps
        buf = io.BytesIO()                       # image SANS bandeau pour le rembobinage
        im.resize((W // 2, H // 2)).save(buf, "JPEG", quality=80)
        ring.append(buf.getvalue())
        if keep_all:
            history.append(buf.getvalue())
        for (b0, bd, txt, col) in banners:
            if b0 <= t_out < b0 + bd:
                a = min(1.0, (t_out - b0) / 0.12, (b0 + bd - t_out) / 0.25)
                im = _banner(im, txt, H * 0.2, 96, col, a)
        proc.stdin.write(im.tobytes())
        n_out += 1

    def play(path, gain=1.0, start=0.0, dur=None, fout=0.4, at=None):
        if not path:
            return
        key = str(path)
        t_out = n_out / fps if at is None else at
        if playing.get(key, -1) > t_out:
            return
        a = _fade(_pcm(path, start, dur), fout=fout)
        playing[key] = t_out + len(a) / RATE
        sfx.append((t_out, a, gain))

    def advance(steps=1.0):
        """avance la simulation de `steps` images (vitesse comprise) et note les fusions au temps de sortie"""
        n0 = len(sim.events)
        feeder.tick(dt * steps, sub)
        for (_, tier) in sim.events[n0:]:
            merges_out.append((n_out / fps, tier))

    def draw():
        im = painter.frame(feeder.drop, feeder.waiting, feeder.tube)
        if bombs or booms:
            im = im.convert("RGBA")
            d = ImageDraw.Draw(im)
            for b in bombs:
                if b.alive:
                    r = sim.radii[b.tier] * (1.25 + 0.15 * math.sin(sim.t * 18))
                    d.ellipse((b.x - r, b.y - r, b.x + r, b.y + r), outline=(255, 70, 160, 255), width=8)
                    bx_, by_ = b.x, b.y - r - 34               # petite bombe dessinée (pas d'emoji : police)
                    d.ellipse((bx_ - 20, by_ - 20, bx_ + 20, by_ + 20), fill=(25, 20, 30, 255), outline=(255, 70, 160, 255), width=3)
                    d.line((bx_ + 10, by_ - 16, bx_ + 22, by_ - 30), fill=(200, 170, 120, 255), width=4)
                    if int(sim.t * 12) % 2:
                        d.ellipse((bx_ + 18, by_ - 36, bx_ + 30, by_ - 24), fill=(255, 220, 60, 255))
            for (x, y, t0) in booms:
                q = (sim.t - t0) / 0.6
                if 0 <= q < 1:
                    for k_, colr in ((1.0, (255, 120, 40)), (0.75, (255, 200, 80)), (0.45, (255, 250, 220))):
                        r = 30 + 170 * (q ** 0.5) * k_
                        d.ellipse((x - r, y - r, x + r, y + r), fill=colr + (int(200 * (1 - q) ** 1.5),))
                    r = 40 + 260 * q                                   # onde de choc
                    d.ellipse((x - r, y - r, x + r, y + r), outline=(255, 230, 200, int(220 * (1 - q))), width=6)
            im = im.convert("RGB")
        if index:
            im = _index(im, painter, sim, W, H, icons)
        if speed > 1.15 and prev_im[0] is not None:                 # Made in Heaven : images fantômes
            im = Image.blend(im, prev_im[0], min(0.55, (speed - 1) * 0.4))
        prev_im[0] = im
        return im

    icons = {}
    prev_im = [None]
    if start_sound:
        play(start_sound, 1.0, at=0.25)
    try:
        while True:
            # --- 1re apparition d'un niveau : son du perso + pouvoir programmé
            while seen < sim.best:
                seen += 1
                appear[seen] = n_out
                p = powers.get(names[seen], {})
                if p.get("sound"):
                    play(p["sound"], p.get("gain", 1.0), p.get("start", 0.0), p.get("dur"), p.get("fout", 0.5))
                if p.get("power"):
                    queue.append([sim.t + p.get("delay", 0.6), p["power"], seen])
            # --- pouvoirs dont c'est l'heure
            for item in [q for q in queue if sim.t >= q[0]]:
                queue.remove(item)
                _, power, tier = item
                p = powers.get(names[tier], {})
                ball = _ball_of(sim, tier)
                bx, by = (ball.x, ball.y) if ball else (sim.cx, sim.cy)
                if power == "timestop":                    # ZA WARUDO : sphère inversée puis tout se fige
                    play(p.get("power_sound"), 1.0, 0.0, p.get("power_dur", 2.6), 0.6)
                    banners.append((n_out / fps, 1.9, "ZA WARUDO!", (255, 214, 60)))
                    grow = int(0.45 * fps)
                    for i in range(grow):                  # la sphère grandit (la partie continue encore)
                        advance()
                        im = draw()
                        r = (i + 1) / grow * max(W, H) * 1.1
                        m = Image.new("L", im.size, 0)
                        ImageDraw.Draw(m).ellipse((bx - r, by - r, bx + r, by + r), fill=255)
                        im = Image.composite(ImageOps.invert(im), im, m)
                        emit(im)
                    frozen = draw()
                    still = ImageEnhance.Color(frozen).enhance(0.15)
                    still = _tint(still, (40, 60, 120), 0.25)
                    for i in range(int(p.get("freeze", 1.0) * fps)):   # le temps est arrêté (1 s, demandé)
                        emit(still)
                    for i in range(int(0.15 * fps)):       # le temps reprend
                        emit(Image.blend(still, draw(), (i + 1) / (0.15 * fps)))
                elif power == "bites_the_dust":            # Killer Queen : bombes, puis on rembobine
                    small = [b for b in sim.balls if b.alive and b.tier <= max(1, tier - 3)]
                    sim.rnd.shuffle(small)
                    bombs[:] = small[:4]
                    queue.append([sim.t + 1.4, "kq_boom", tier])
                    banners.append((n_out / fps, 1.3, "KILLER QUEEN", (255, 110, 190)))
                elif power == "kq_boom":
                    for b in bombs:
                        if b.alive:
                            b.alive = False
                            booms.append((b.x, b.y, sim.t))
                    bombs.clear()
                    sim.balls = [b for b in sim.balls if b.alive]
                    play(p.get("boom_sound") or (EXPLOSION if EXPLOSION.is_file() else None), 1.0, 0.0, None, 0.2)
                    queue.append([sim.t + 1.0, "kq_rewind", tier])
                elif power == "kq_rewind":
                    play(p.get("power_sound"), 1.0, 0.0, 3.6, 0.4)
                    frames = list(ring)[::-1]
                    banners.append((n_out / fps, len(frames[::2]) / fps + 0.3, "BITES THE DUST", (220, 120, 255)))
                    for j, raw in enumerate(frames[::2]):  # rembobinage ×2 : violet, lignes
                        im = Image.open(io.BytesIO(raw)).convert("RGB").resize((W, H))
                        im = _tint(im, (120, 40, 160), 0.28)
                        d = ImageDraw.Draw(im)
                        for yy in range((j * 23) % 40, H, 40):
                            d.line((0, yy, W, yy), fill=(20, 0, 40), width=3)
                        emit(im)
                    flash = Image.new("RGB", (W, H), (255, 255, 255))
                    for i in range(4):
                        emit(Image.blend(flash, draw(), (i + 1) / 4))
                elif power == "king_crimson":              # le temps est effacé : on saute 5 s
                    play(p.get("power_sound"), 1.0, 0.0, None, 0.1)
                    banners.append((n_out / fps, 0.4, "KING CRIMSON", (255, 60, 60)))
                    for i in range(int(0.35 * fps)):
                        im = draw()
                        im = _tint(ImageOps.posterize(im, 2), (200, 0, 30), 0.45 * (i + 1) / (0.35 * fps))
                        emit(im)
                        advance()
                    skip = int(p.get("skip", 5.0) * fps)
                    for i in range(skip):                  # 5 s simulées, jamais montrées (ni entendues)
                        feeder.tick(dt * speed, sub)
                    banners.append((n_out / fps + 0.05, 1.0, "TIME ERASED", (255, 90, 90)))
                    for i in range(int(0.25 * fps)):
                        emit(_tint(draw(), (200, 0, 30), 0.35 * (1 - i / (0.25 * fps))))
                elif power == "made_in_heaven":            # le temps accélère (un peu)
                    play(p.get("power_sound"), 0.9, 0.0, p.get("power_dur"), 1.0)
                    banners.append((n_out / fps, 1.8, "MADE IN HEAVEN", (170, 230, 255)))
                    speed_target = float(p.get("speed", 1.5))
                    if p.get("reset"):                     # le temps accélère tellement que l'univers recommence
                        reset.update(at=n_out / fps + float(p.get("reset_after", 3.0)), frame=appear.get(tier, n_out), p=p)
            # --- Made in Heaven : l'univers recommence → retour au début, puis jusqu'à l'apparition de Pucci
            if reset.get("at") is not None and n_out / fps >= reset["at"]:
                rp = reset.pop("p")
                reset.pop("at")
                play(rp.get("reset_sound"), 1.0, 0.0, None, 0.3)
                white = Image.new("RGB", (W, H), (255, 255, 255))
                last = draw()
                for i in range(int(0.35 * fps)):         # tout devient blanc
                    emit(Image.blend(last, white, (i + 1) / (0.35 * fps)))
                frames = history[:reset["frame"]]
                def old(j):
                    return Image.open(io.BytesIO(frames[j])).convert("RGB").resize((W, H))
                banners.append((n_out / fps + 0.2, 1.6, "THE UNIVERSE RESET", (190, 235, 255)))
                for i in range(int(0.25 * fps)):         # le blanc s'efface sur la toute 1re image
                    emit(Image.blend(white, old(0), (i + 1) / (0.25 * fps)))
                for i in range(int(0.6 * fps)):          # le début, comme au 1er jour
                    emit(old(min(len(frames) - 1, i)))
                ff_n = int(float(rp.get("ff_seconds", 2.2)) * fps)
                start = int(0.6 * fps)
                for i in range(ff_n):                    # avance rapide jusqu'au moment où Pucci est apparu
                    j = start + int((len(frames) - 1 - start) * ((i + 1) / ff_n) ** 1.4)
                    emit(_tint(old(j), (200, 235, 255), 0.12))
                speed = speed_target = float(rp.get("after_speed", 1.0))
                prev_im[0] = None
                for i in range(int(0.2 * fps)):
                    emit(Image.blend(white, draw(), 0.5 + 0.5 * (i + 1) / (0.2 * fps)))
            # --- image normale
            speed += (speed_target - speed) * 0.05
            advance(speed)
            emit(draw())
            if sim.done_at >= 0 and sim.t - sim.done_at >= 0.5 and not queue:
                break
            if sim.t > float(c.get("max_seconds", 120)) * 2.5:
                log.warning("fusion_powers : dernier niveau pas atteint")
                break
        for f in range(int(fps * float(c.get("final_seconds", 1.5)))):
            emit(painter.final(f / fps))
        proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError("ffmpeg a échoué")
    finally:
        if proc.poll() is None:
            proc.kill()
    duration = n_out / fps
    vol = float(fusion.fcfg().get("volume", 0.13))
    audio = fusion.mix_events(merges_out, duration, len(tiers), None) * merge_gain * 0.0 \
        if merge_sounds else fusion.mix_events(merges_out, duration, len(tiers), None) * merge_gain
    if merge_sounds:                                       # un son par perso, à chaque fusion (pas deux en même temps)
        bloop = fusion.mix_events  # noqa
        cache, last = {}, {}
        for (t, tier) in merges_out:
            src = tier - 1                                 # le niveau des 2 persos qui fusionnent
            spec = merge_sounds.get(src)
            if not spec:
                continue
            if t - last.get(src, -9) < spec[3] if len(spec) > 3 else t - last.get(src, -9) < 0.3:
                continue
            last[src] = t
            if src not in cache:
                cache[src] = _fade(_pcm(spec[0], spec[1], spec[2]), fout=min(0.25, spec[2] / 3))
            a = cache[src]
            i = int(t * RATE)
            seg = a[: max(0, len(audio) - i)] * vol * 1.2
            audio[i:i + len(seg)] += seg
    for (t, a, g) in sfx:
        i = int(t * RATE)
        seg = a[: max(0, len(audio) - i)] * g * vol * 1.6
        audio[i:i + len(seg)] += seg
    audio = np.tanh(audio / max(vol * 1.6, 1e-6)) * vol * 1.6
    wav = out.with_suffix(".wav")
    fusion.write_wav(wav, audio)
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(tmp_video), "-i", str(wav), "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "160k", "-shortest", str(out)], check=True)
    tmp_video.unlink(missing_ok=True)
    wav.unlink(missing_ok=True)
    meta = {"kind": "fusion", "title": title, "seed": seed, "seconds": round(duration, 1), "tiers": names,
            "reached": names[sim.best], "complete": sim.best >= sim.top, "powers": {k: v.get("power") for k, v in powers.items()},
            "created_at": db.now()}
    out.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    fusion._brand_video(out)
    log.info("fusion_powers : %s en %.0f s → %s", meta["reached"], duration, out.name)
    return out
