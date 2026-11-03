"""Cinématique d'ulti (03/11, demandé : « inspire-toi des ultis des jeux Naruto Storm et des jeux gacha »).

Sans IA : l'image officielle du perso est animée par déformation (cheveux au vent, main qui tourne au poignet,
respiration — façon écran de perso d'un gacha), dans un panneau en diagonale, avec :
  bandes noires + flash (Storm) → nom + attaque qui glissent (gacha) → yeux qui s'illuminent → énergie qui se forme
  à la main → impact frames + flash → l'attaque avale l'écran → fondu blanc.

Le « rig » de l'image (où sont les yeux, la main, le poignet, le bas des cheveux) est en fractions de l'image
recadrée 9:16, dans `<image>.rig.json` à côté de l'image (écrit une fois, à la main ou par Claude) ; sans rig :
valeurs par défaut (yeux au tiers, main en bas au centre).

`clipper ulti "Satoru Gojo" --image cine/Satoru Gojo/Ulti.png --move "Hollow Purple"` → petite vidéo de test,
sans lancer de combat.
"""
from __future__ import annotations

import json
import math
import random
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from ..util import require_bin
from . import fxengine, render

DEFAULT_RIG = {"crop_cx": 0.5, "eyes": [[0.36, 0.33], [0.64, 0.33]], "hair_bottom": 0.32,
               "hand": [0.55, 0.76], "wrist": [0.66, 0.98], "energy": [0.55, 0.66]}


def load_rig(image: Path) -> dict:
    rig = dict(DEFAULT_RIG)
    p = Path(str(image) + ".rig.json")
    if p.is_file():
        try:
            rig.update(json.loads(p.read_text(encoding="utf-8")))
        except ValueError:
            pass
    return rig


def _sm(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def _back_out(x):
    c1 = 1.70158
    x = min(1.0, max(0.0, x))
    return 1 + (c1 + 1) * (x - 1) ** 3 + c1 * (x - 1) ** 2


class Puppet:
    """Image du perso animée par champ de déformation (pas de 3D, pas d'IA : le dessin d'origine reste)."""

    def __init__(self, image: Path, W: int, H: int, rig: dict):
        from scipy.ndimage import map_coordinates
        self._map = map_coordinates
        src = Image.open(image).convert("RGB")
        if src.width / src.height > W / H:                      # paysage → bande 9:16 autour de crop_cx
            cw = int(src.height * W / H)
            x0 = int(min(max(0, rig["crop_cx"] * src.width - cw / 2), src.width - cw))
            src = src.crop((x0, 0, x0 + cw, src.height))
        else:
            ch = int(src.width * H / W)
            src = src.crop((0, 0, src.width, min(src.height, ch)))
        self.A = np.asarray(src.resize((W, H), Image.LANCZOS)).astype(np.float32)
        self.W, self.H = W, H
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        self.yy, self.xx = yy, xx
        yn, xn = yy / H, xx / W
        hb = float(rig["hair_bottom"])
        self.hair = np.clip(_sm(hb, hb * 0.2, yn) * _sm(0, .12, xn) * _sm(1, .88, xn)
                            + .6 * _sm(hb + .06, hb - .02, yn) * (_sm(.30, .18, xn) + _sm(.72, .84, xn)), 0, 1)
        hx, hy = rig["hand"]
        self.hand = np.exp(-(((xn - hx) / .17) ** 2 + ((yn - hy) / .12) ** 2))
        self.body = _sm(hb + .12, hb + .42, yn)
        self.wx, self.wy = rig["wrist"][0] * W, rig["wrist"][1] * H

    def frame(self, t: float, wind: float = 1.0, hand_amp: float = 5.0) -> Image.Image:
        P = 2 * math.pi / 4
        yn, xn = self.yy / self.H, self.xx / self.W
        dx = self.hair * wind * (12 * np.sin(P * 3 * t - yn * 12 + xn * 4) + 4 * np.sin(P * 7 * t - yn * 25))
        dy = self.hair * wind * 4 * np.cos(P * 3 * t - yn * 12) + self.body * 7 * math.sin(P * t)
        ang = math.radians(hand_amp * math.sin(P * 1.5 * t))
        ca, sa = math.cos(ang), math.sin(ang)
        rx, ry = self.xx - self.wx, self.yy - self.wy
        dx = dx + self.hand * ((ca * rx - sa * ry) - rx)
        dy = dy + self.hand * ((sa * rx + ca * ry) - ry)
        fr = np.stack([self._map(self.A[..., c], [self.yy - dy, self.xx - dx], order=1, mode="nearest")
                       for c in range(3)], -1)
        return Image.fromarray(fr.clip(0, 255).astype(np.uint8)).convert("RGBA")


STYLE_ORBS = {"purple": [((60, 130, 255), -1), ((255, 50, 60), 1)],      # Hollow Purple : Bleu + Rouge
              "final": [((255, 215, 60), -1), ((60, 170, 255), 1)],       # Final Kamehameha : Final Flash + Kamehameha
              "rainbow": [((255, 90, 120), -1), ((90, 200, 255), 1), ((255, 235, 110), 0)]}   # Stardust Breaker


def generate(name: str, image: str | Path, move: str, out: Path, color=(175, 70, 255), style: str | None = None,
             subtitle: str = "SECRET TECHNIQUE", W: int = 1080, H: int = 1920, fps: int = 30, seconds: float = 4.2,
             seed: int = 7, clip: str | Path | None = None, clip_crop=None, clip_reverse: bool = False,
             clip_fit: str = "fill", energy=None, sounds: str = "anime", franchise: str | None = None,
             voice: str | Path | None = None, voice_at: float = 0.45, clip_fps: float | None = None,
             clip_start: float = 0.0, clip_end: float | None = None, clip_hit: float | None = None,
             clip_loop=None, clip_fx: bool = False, attack_sound: str | Path | None = None,
             attack_at: float = 0.0) -> Path:
    """Vidéo de l'ulti seul (pour juger le rendu sans lancer de combat). Renvoie le .mp4.
    `clip` = vidéo du perso animé par une IA (image vers vidéo) : remplace l'animation par déformation, tout le
    reste (bandes, panneau, textes, énergie, impact frames, flashs) ne change pas.
    Synchro avec un GIF d'attaque qui a déjà ses effets (`clip_fx=True`) : le clip est lu à `clip_fps` (défaut =
    vitesse du GIF) à partir de `clip_start` s (1re image tenue avant), coupé à `clip_end` s du clip ; `clip_hit` = s
    du clip où l'attaque touche (impact frames + flash) ; `clip_loop` = (i0, i1) images rejouées en aller-retour si
    l'ulti dure plus que le clip ; nos orbes et l'écran « avalé » sont retirés. `attack_sound` = fichier posé à
    `attack_at` s (négatif = on coupe le début), `voice_at` = départ de la réplique."""
    image = Path(image)
    rig = load_rig(image)
    pup = Puppet(image, W, H, rig)
    if energy:                                                   # point où se forme l'énergie (fractions du cadre)
        rig = dict(rig, energy=list(energy))
    clip_frames = []
    if clip:
        # clip_crop (fractions x0, y0, x1, y1) retire un filigrane ; clip_reverse : lu à l'envers (l'IA fait
        # souvent le geste « à rebours ») ; clip_fit « width » : clip paysage gardé en entier, en bande au milieu
        for fr in fxengine.flipbook(Path(clip), max_frames=200):
            if clip_crop:
                x0, y0, x1, y1 = clip_crop
                fr = fr.crop((int(x0 * fr.width), int(y0 * fr.height), int(x1 * fr.width), int(y1 * fr.height)))
            if clip_fit == "width":
                h = int(fr.height * W / fr.width)
                band = fr.convert("RGBA").resize((W, h), Image.LANCZOS)
                m = Image.new("L", (W, h), 255)                  # bords haut/bas fondus dans le panneau
                md = ImageDraw.Draw(m)
                fade = max(1, h // 8)
                for i in range(fade):
                    md.line((0, i, W, i), fill=int(255 * i / fade))
                    md.line((0, h - 1 - i, W, h - 1 - i), fill=int(255 * i / fade))
                band.putalpha(m)
                fr = (band, int(H * 0.40 - h / 2))               # collé à la volée (mémoire)
            else:
                if fr.width / fr.height > W / H:                # recadré en 9:16 comme l'image
                    cw = int(fr.height * W / H)
                    x0 = int(min(max(0, rig["crop_cx"] * fr.width - cw / 2), fr.width - cw))
                    fr = fr.crop((x0, 0, x0 + cw, fr.height))
                fr = fr.convert("RGBA").resize((W, H), Image.LANCZOS)
            clip_frames.append(fr)
        if clip_reverse:
            clip_frames.reverse()
        try:                                                     # vitesse d'origine du GIF
            d = Image.open(clip).info.get("duration") or 0
            native_fps = 1000 / d if d else 24
        except Exception:
            native_fps = 24
        clip_fps = clip_fps or native_fps
        if clip_end is not None:
            clip_frames = clip_frames[:max(1, int(clip_end * native_fps))]

    def clip_at(t):
        i = int(max(0.0, t - clip_start) * clip_fps)
        n = len(clip_frames)
        if i >= n and clip_loop:
            a, b = clip_loop
            span = max(1, b - a)
            k = (i - n) % (2 * span)
            return clip_frames[b - k if k <= span else a + (k - span)]
        return clip_frames[min(n - 1, i)]
    k = W / 1080
    col = tuple(int(c) for c in color[:3])
    light = tuple(min(255, int(c * 0.5 + 128)) for c in col)
    tex = fxengine.TexFX(seed)
    rr = random.Random(seed)
    lines = [(rr.random(), rr.uniform(0.3, 1), rr.uniform(2, 7)) for _ in range(46)]
    fbig, fmid, fsm = render.font(int(150 * k)), render.font(int(70 * k)), render.font(int(46 * k))
    words = move.upper().split()
    mlines = [" ".join(words[:len(words) // 2 or 1]), " ".join(words[len(words) // 2 or 1:])] if len(words) > 1 else [move.upper()]
    mlines = [m for m in mlines if m]
    while fbig.size > 60 and any(render.text_width(ImageDraw.Draw(Image.new("RGB", (4, 4))), m, fbig) > W * 0.88
                                 for m in mlines):
        fbig = render.font(fbig.size - 6)
    orbs = STYLE_ORBS.get(style or "", [(col, 0)])
    ex, ey = rig["energy"][0] * W, rig["energy"][1] * H
    cam = fxengine.Camera()

    def speedlines(img, t, c, cx, cy, a=1.0):
        d = ImageDraw.Draw(img)
        for an, ln, wd in lines:
            ang = an * 2 * math.pi + t * 0.3
            r0 = W * (0.35 + 0.5 * ((t * 2.2 + ln) % 1))
            d.line((cx + math.cos(ang) * r0, cy + math.sin(ang) * r0, cx + math.cos(ang) * (r0 + W * .6 * ln),
                    cy + math.sin(ang) * (r0 + W * .6 * ln)), fill=c + (int(170 * a),), width=int(wd * k))

    proc = subprocess.Popen([require_bin("ffmpeg"), "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
                             "-crf", "22", "-pix_fmt", "yuv420p", str(out)], stdin=subprocess.PIPE)
    life = 3.5 / fps
    t_orb, t_hit, t_out = seconds * 0.36, seconds * 0.66, seconds * 0.70
    if clip_fx and clip_frames:
        t_hit = clip_start + (clip_hit or 0) * native_fps / clip_fps     # temps du GIF → temps de l'ulti
        t_orb, t_out = t_hit, seconds + 1                        # pas d'écran « avalé » : le GIF a son explosion
    try:
        for f in range(int(seconds * fps)):
            t = f / fps
            img = Image.new("RGBA", (W, H), (8, 4, 18, 255))
            energy = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            if t < t_out:
                bg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                ImageDraw.Draw(bg).polygon(((0, H * .08), (W, 0), (W, H * .92), (0, H)),
                                           fill=tuple(int(c * 0.18) for c in col) + (255,))
                img.alpha_composite(bg)
                speedlines(img, t, light, W / 2, H * .38, a=0.7)
                s = _back_out((t - 0.05) / 0.35)                 # le perso arrive de la droite (gacha)
                if clip_frames:                                  # clip IA : 24 i/s, on garde la dernière image
                    ch = clip_at(t) if clip_fx else clip_frames[min(len(clip_frames) - 1, int(t * 24))]
                    if isinstance(ch, tuple):
                        band, by = ch
                        ch = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                        ch.alpha_composite(band, (0, by))
                else:
                    ch = pup.frame(t, wind=1.0 + (1.5 if t > t_orb + 0.4 else 0))
                if clip_fx:                                      # après l'impact : le clip grossit, plein cadre
                    z = 1.0 + 0.04 * t + (0.55 * min(1, (t - t_hit) / 0.3) if t > t_hit else 0)
                else:
                    z = 1.0 + 0.05 * t + (0.12 * ((t - t_orb - .4) / 1.0) ** 2 if t > t_orb + .4 else 0)
                ch = ch.resize((int(W * z), int(H * z)), Image.BILINEAR)
                mask = Image.new("L", (W, H), 0)
                ImageDraw.Draw(mask).polygon(((0, H * .10), (W, H * .02), (W, H * .90), (0, H * .98)), fill=255)
                layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                layer.paste(ch, (int((W - ch.width) / 2 + W * (1 - s) * 0.9), int((H - ch.height) * 0.35)))
                layer.putalpha(Image.composite(layer.getchannel("A"), Image.new("L", (W, H), 0), mask))
                img.alpha_composite(layer)
                if t > t_orb:
                    speedlines(img, t * 2, light, ex, ey, a=min(0.6, (t - t_orb) * 0.6))
                d = ImageDraw.Draw(img)
                d.line((0, H * .10, W, H * .02), fill=col + (255,), width=int(10 * k))
                d.line((0, H * .98, W, H * .90), fill=col + (255,), width=int(10 * k))
                if t > 0.35 and not (clip_fx and t > t_hit):     # nom + attaque qui glissent (gacha)
                    q = _back_out((t - .35) / .3)
                    y0 = H * .70
                    d.text((W * .06 - (1 - q) * W, y0), name.upper(), font=fmid, fill=(255, 255, 255),
                           stroke_width=int(5 * k), stroke_fill=(0, 0, 0))
                    y = y0 + fmid.size * 1.05
                    for i, m in enumerate(mlines):
                        d.text((W * .06 - (1 - q) * W * (1.3 + .3 * i), y), m, font=fbig,
                               fill=light if i == 0 else col, stroke_width=int(8 * k), stroke_fill=(0, 0, 0))
                        y += fbig.size * 0.98
                    d.text((W * .07 - (1 - q) * W * 1.9, y + 10 * k), subtitle.upper(), font=fsm,
                           fill=(225, 220, 245), stroke_width=int(3 * k), stroke_fill=(0, 0, 0))
                if t > seconds * 0.26 and not clip_fx:           # yeux qui s'illuminent
                    g = min(1, (t - seconds * .26) / .3)
                    for x_, y_ in rig["eyes"]:
                        tex.spawn("light_03", W * x_, H * y_, 260 * k * g, life, light, hot=1.0)
                if t_orb < t < t_hit and not clip_fx:            # l'énergie se forme à la main
                    q = min(1, (t - t_orb) / (t_hit - t_orb - 0.15))
                    dd = W * 0.30 * (1 - q * q)
                    for c_, sg in orbs:
                        x, y = ex + sg * dd, ey - 40 * k * math.sin(q * math.pi) * abs(sg)
                        sz = 420 * k * (1 if sg else 0.5 + 0.7 * q)
                        tex.spawn("light_03", x, y, sz, life, c_, hot=0.9)
                        tex.spawn("twirl_02", x, y, sz * 0.8, life, c_, rot=(t * 900 * (sg or 1)) % 360, hot=0.6)
                        tex.spawn("spark_03", x + rr.uniform(-60, 60) * k, y + rr.uniform(-60, 60) * k, 90 * k, .1, c_,
                                  rot=rr.uniform(0, 360), hot=1)
                    if f % 2 == 0:
                        cam.punch(t, ex, ey, 0.02, 0.2)
            if t_hit <= t < min(t_out, t_hit + (0.13 if clip_fx else 9)):   # impact frames (2 tons)
                img = fxengine.impact_frame(img, col if f % 2 else (255, 255, 255), invert=f % 2 == 0)
            if t >= t_out:                                       # l'attaque avale l'écran
                q = (t - t_out) / (seconds - t_out)
                img = Image.new("RGBA", (W, H), tuple(int(c * 0.04) for c in col) + (255,))
                speedlines(img, t * 3, col, W / 2, H / 2, a=1.0)
                R = W * (0.18 + 1.1 * q ** 1.6)
                tex.spawn("light_03", W / 2, H / 2, R * 3.2, life, col, hot=0.5)
                tex.spawn("twirl_02", W / 2, H / 2, R * 2.4, life, col, rot=(t * 600) % 360, hot=0.35)
                tex.spawn("circle_05", W / 2, H / 2, R * 1.6, life, light, hot=0.5)
                if style == "purple":                            # le Violet efface : cœur noir
                    tex.spawn("circle_05", W / 2, H / 2, R * 0.8, life, (14, 0, 26), glow=False, hot=0, alpha=.95)
                for _ in range(4):
                    an, r_ = rr.uniform(0, 6.28), R * rr.uniform(1.0, 2.0)
                    tex.spawn("trace_01", W / 2 + math.cos(an) * r_, H / 2 + math.sin(an) * r_, 40 * k, .2, light,
                              vx=-math.cos(an) * r_ * 3, vy=-math.sin(an) * r_ * 3, rot=math.degrees(an) + 90,
                              stretch=4, hot=1)
            tex.step(1 / fps)
            tex.draw(energy, glow=True)
            ng = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            tex.draw(ng, glow=False)
            img.alpha_composite(ng)
            img = fxengine.bloom(img, energy, 1.0, 26)
            if clip_fx:
                shake = 22 * k * max(0.0, 1 - (t - t_hit) / 0.8) if t > t_hit else 0
            else:
                shake = 22 * k if t_hit - .15 < t < t_out + .45 else (6 * k if t > t_orb else 0)
            img = cam.apply(img, t, shake=shake, seed=f)
            if t_out <= t < t_out + .2:
                img = fxengine.chroma(img, int(14 * k))
            bars = int(H * 0.11 * min(1, t / 0.15))              # bandes noires (cinéma)
            d = ImageDraw.Draw(img)
            d.rectangle((0, 0, W, bars), fill=(0, 0, 0, 255))
            d.rectangle((0, H - bars, W, H), fill=(0, 0, 0, 255))
            for t0, dur in ((0.0, .12), (t_hit if clip_fx else t_out, .18)):   # flashs
                if t0 <= t < t0 + dur:
                    img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(255 * (1 - (t - t0) / dur)))))
            if t > seconds - 0.25:
                img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(255 * (t - (seconds - .25)) / .25))))
            proc.stdin.write(img.convert("RGB").tobytes())
        proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError("ffmpeg a échoué")
    finally:
        if proc.poll() is None:
            proc.kill()
    _soundtrack(out, seconds, t_orb, t_hit, t_out, move, sounds, franchise, voice, seed,
                voice_at=voice_at, attack_sound=attack_sound if clip_fx or attack_sound else None, attack_at=attack_at)
    return out


def _soundtrack(out: Path, seconds, t_orb, t_hit, t_out, move, sounds, franchise, voice, seed, voice_at=0.45,
                attack_sound=None, attack_at=0.0) -> None:
    """Son de l'ulti : flash d'entrée, montée d'énergie, charge à la main, choc, explosion finale (+ réplique)."""
    import numpy as np
    from . import domain, fusion
    R = fusion.RATE
    audio = np.zeros(int((seconds + 0.5) * R), dtype=np.float32)

    def put(t, snd, vol=1.0):
        if snd is None or len(snd) == 0:
            return
        i = int(t * R)
        n = min(len(snd), len(audio) - i)
        if n > 0:
            audio[i:i + n] += np.asarray(snd[:n], dtype=np.float32) * vol

    S = lambda fam, mv=None: domain.sfx(fam, move=mv, mode=sounds, seed=seed, franchise=franchise)
    put(0.0, S("vanish"), 0.8)                                   # flash + bandes noires
    if attack_sound:                                             # vrai son de l'attaque, calé sur le GIF
        snd = fusion.load_sound(Path(attack_sound))
        if attack_at < 0:
            snd, attack_at = snd[int(-attack_at * R):], 0.0
        put(attack_at, snd, 1.0)
        put(0.30, S("transform"), 0.35)
    else:
        put(0.30, S("transform"), 0.9)                           # le perso arrive, l'énergie monte
        put(t_orb, S("beam", move), 0.9)                         # l'attaque se charge à la main
        put(t_hit - 0.05, S("clash"), 0.8)                       # impact frames
        put(t_out, S("ko"), 1.0)                                 # l'attaque avale l'écran
    if voice:
        v = domain.voice_file(str(voice)) if not Path(str(voice)).is_file() else Path(str(voice))
        if v is not None:
            put(voice_at, fusion.load_sound(v), 1.1)
    peak = float(np.percentile(np.abs(audio), 99.7)) or 1.0
    audio = np.tanh(audio * (0.75 / peak) * 1.2)
    wav = out.with_suffix(".wav")
    fusion.write_wav(wav, audio)
    tmp = out.with_suffix(".tmp.mp4")
    subprocess.run([require_bin("ffmpeg"), "-y", "-loglevel", "error", "-i", str(out), "-i", str(wav), "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "160k", "-shortest", str(tmp)], check=True)
    tmp.replace(out)
    wav.unlink(missing_ok=True)
