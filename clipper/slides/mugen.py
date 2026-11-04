"""Lecture des persos MUGEN (demandé le 04/11 : « utiliser les attaques d'un jeu MUGEN »).

- SFF v1 (sprites PCX 8 bits + axe) → images RGBA + axe (point d'ancrage, souvent les pieds).
- AIR (animations) → liste d'images (groupe, numéro, décalage x/y, durée en ticks de 1/60 s, miroir).
- SND (sons) → WAV par (groupe, numéro).

Les persos viennent du jeu MUGEN installé par l'utilisateur (library/One Piece/one-piece-mugen/…/chars/).
"""
from __future__ import annotations

import io
import re
import struct
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image


@dataclass
class Sprite:
    group: int
    number: int
    axis: tuple[int, int]
    image: Image.Image          # RGBA, couleur 0 transparente


@dataclass
class Frame:
    group: int
    number: int
    dx: int
    dy: int
    ticks: int                  # 1 tick = 1/60 s ; -1 = infini
    flip: str = ""              # "", "H", "V", "HV"


@dataclass
class Action:
    number: int
    name: str
    frames: list[Frame] = field(default_factory=list)
    loopstart: int = 0

    @property
    def length(self) -> int:
        return sum(max(1, f.ticks) for f in self.frames)


def read_act(path: Path) -> list[tuple[int, int, int]]:
    """Palette .act de MUGEN (256 couleurs, stockées à l'envers)."""
    b = Path(path).read_bytes()[:768]
    cols = [tuple(b[i:i + 3]) for i in range(0, 768, 3)]
    return cols[::-1]


def read_sff(path: Path, act: Path | None = None) -> dict[tuple[int, int], Sprite]:
    """SFF v1 : en-tête 512 o, puis sous-fichiers chaînés (en-tête 32 o + PCX)."""
    data = Path(path).read_bytes()
    if data[:12] != b"ElecbyteSpr\x00":
        raise ValueError("pas un fichier SFF")
    ver = data[12:16]
    if ver[3] != 1 and ver[2] != 1:     # v1.01 / v1.10 : (0,1,0,1)
        if data[15] == 2 or data[14] == 2:
            raise NotImplementedError("SFF v2 pas encore géré")
    n_img = struct.unpack_from("<I", data, 20)[0]
    off = struct.unpack_from("<I", data, 24)[0]
    shared_pal = None
    if act and Path(act).is_file():
        shared_pal = read_act(act)
    sprites: dict[tuple[int, int], Sprite] = {}
    by_index: list[tuple[int, int] | None] = []
    last_pal = None
    for idx in range(n_img):
        if off <= 0 or off + 32 > len(data):
            break
        nxt, length, ax, ay, grp, num, link, samepal = struct.unpack_from("<IIhhHHHB", data, off)
        key = (grp, num)
        if length == 0:                                   # sprite lié (copie d'un autre)
            src = by_index[link] if link < len(by_index) else None
            if src and src in sprites:
                s0 = sprites[src]
                sprites[key] = Sprite(grp, num, (ax, ay), s0.image)
            by_index.append(key)
            off = nxt
            continue
        pcx = data[off + 32: off + 32 + length]
        try:
            im = Image.open(io.BytesIO(pcx))
            im.load()
        except Exception:
            by_index.append(None)
            off = nxt
            continue
        if im.mode in ("P", "L"):
            import numpy as np
            idx = np.array(im)
            has_own = len(pcx) > 769 and pcx[-769] == 12
            if has_own and not samepal:
                last_pal = list(pcx[-768:])
            pal = last_pal
            if pal is None or (shared_pal is not None and grp < 9000 and samepal):
                pal = [c for rgb in (shared_pal or []) for c in rgb] or pal
            if pal is None:
                pal = list(range(256)) * 3
            lut = np.array(pal[:768], dtype=np.uint8).reshape(-1, 3)
            rgb = lut[idx]
            a = ((idx != 0) * 255).astype(np.uint8)
            rgba = Image.fromarray(np.dstack([rgb, a]), "RGBA")
        else:
            rgba = im.convert("RGBA")
        sprites[key] = Sprite(grp, num, (ax, ay), rgba)
        by_index.append(key)
        off = nxt
    return sprites


_ACT = re.compile(r"^\s*\[\s*begin\s+action\s+(-?\d+)\s*\]", re.I)


def read_air(path: Path) -> dict[int, Action]:
    acts: dict[int, Action] = {}
    cur = None
    last_comment = ""
    for raw in Path(path).read_text(encoding="latin-1").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith(";"):
            last_comment = line.lstrip("; ").strip()
            continue
        m = _ACT.match(line)
        if m:
            cur = Action(int(m.group(1)), last_comment)
            acts[cur.number] = cur
            continue
        if cur is None:
            continue
        low = line.lower()
        if low.startswith("loopstart"):
            cur.loopstart = len(cur.frames)
            continue
        if low.startswith(("clsn", "interpolate")):
            continue
        line = line.split(";")[0]
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 5 and re.fullmatch(r"-?\d+", parts[0] or "x"):
            try:
                g, n, dx, dy, tk = (int(float(p)) for p in parts[:5])
            except ValueError:
                continue
            flip = parts[5].upper() if len(parts) > 5 else ""
            cur.frames.append(Frame(g, n, dx, dy, tk, flip))
    return acts


def read_snd(path: Path) -> dict[tuple[int, int], bytes]:
    """SND v1 : en-tête 512 o, sous-fichiers (en-tête 16 o + WAV)."""
    data = Path(path).read_bytes()
    if data[:12] != b"ElecbyteSnd\x00":
        raise ValueError("pas un fichier SND")
    n = struct.unpack_from("<I", data, 16)[0]
    off = struct.unpack_from("<I", data, 20)[0]
    out = {}
    for _ in range(n):
        if off <= 0 or off + 16 > len(data):
            break
        nxt, length, grp, num = struct.unpack_from("<IIII", data, off)
        out[(grp, num)] = data[off + 16: off + 16 + length]
        off = nxt
    return out


class Char:
    """Un perso MUGEN : sprites + animations, rendu d'une action à un instant donné."""

    def __init__(self, folder: Path, name: str):
        folder = Path(folder)
        self.sprites = read_sff(folder / f"{name}.sff", folder / "1.act")
        self.actions = read_air(folder / f"{name}.air")
        snd = folder / f"{name}.snd"
        self.sounds = read_snd(snd) if snd.is_file() else {}

    def frame_at(self, action: int, t: float, loop: bool = True) -> Frame | None:
        a = self.actions.get(action)
        if not a or not a.frames:
            return None
        tick = int(t * 60)
        total = a.length
        if tick >= total:
            if not loop or any(f.ticks == -1 for f in a.frames):
                return a.frames[-1]
            pre = sum(max(1, f.ticks) for f in a.frames[:a.loopstart])
            span = max(1, total - pre)
            tick = pre + (tick - pre) % span
        acc = 0
        for f in a.frames:
            acc += max(1, f.ticks) if f.ticks != -1 else 10 ** 9
            if tick < acc:
                return f
        return a.frames[-1]

    def duration(self, action: int) -> float:
        a = self.actions.get(action)
        return (a.length / 60.0) if a else 0.0

    def draw(self, img: Image.Image, action: int, t: float, x: float, y: float, scale: float = 1.0,
             facing: int = 1, loop: bool = True, tint=None) -> bool:
        """Dessine l'action à l'instant t, pieds (axe) en (x, y). facing = 1 droite, -1 gauche."""
        f = self.frame_at(action, t, loop)
        if f is None:
            return False
        sp = self.sprites.get((f.group, f.number))
        if sp is None:
            return False
        im = sp.image
        ax, ay = sp.axis
        flipH = ("H" in f.flip) != (facing < 0)
        if flipH:
            im = im.transpose(Image.FLIP_LEFT_RIGHT)
            ax = im.width - ax
        if "V" in f.flip:
            im = im.transpose(Image.FLIP_TOP_BOTTOM)
            ay = im.height - ay
        if scale != 1:
            im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.NEAREST)
        if tint is not None:
            w = Image.new("RGBA", im.size, tint + (255,))
            w.putalpha(im.getchannel("A"))
            im = Image.blend(im, w, 0.7)
        dx = f.dx * facing
        px = x - ax * scale + dx * scale
        py = y - ay * scale + f.dy * scale
        img.alpha_composite(im, (int(px), int(py)))
        return True
