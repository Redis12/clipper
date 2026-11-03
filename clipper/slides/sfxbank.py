"""Banque de bruitages : tous les fichiers son de library/_sfx/ (packs déposés par l'utilisateur), rangés
automatiquement par rôle d'après leur nom, et découpés en prises (un fichier « Anime Melee 3.wav » contient
souvent plusieurs coups séparés par des silences → chaque coup devient une variante).

Rôles : explosion, punch, beam, charge, blast, teleport, aura, release, whoosh, spark, dodge.

Deux sortes de packs :
- libres (ex. « Helton Yan's Old-School Shonen SFX », CC BY 4.0 → créditer l'auteur dans la description) ;
- « anime » : dossier dont le nom contient dragon ball / dbz / naruto / jjk… = sons officiels → bien pour
  TikTok / Insta, risqué sur YouTube (Content ID). Mode `safe` = jamais ceux-là.
"""
from __future__ import annotations

import random
import re
import subprocess
from functools import lru_cache
from pathlib import Path

import numpy as np

from ..util import log, require_bin
from . import library

RATE = 44100
EXT = {".wav", ".mp3", ".ogg", ".flac", ".m4a", ".aac"}
# pack « anime » → franchise (un combat Naruto ne prend pas les sons Dragon Ball, et inversement)
FRANCHISE_DIR = {"dragon ball": r"dragon ?ball|dbz|xenoverse", "naruto": r"naruto|boruto|shippuden",
                 "jujutsu kaisen": r"jujutsu|jjk", "one piece": r"one ?piece", "bleach": r"bleach",
                 "demon slayer": r"demon ?slayer|kimetsu"}
NAMED_MOVES = r"kunai|shuriken|chidori|rasengan|kamehameha|galick|final flash|big bang|masenko|special beam|getsuga|rasenshuriken"
ANIME_DIR = re.compile(r"dragon ?ball|dbz|naruto|jujutsu|jjk|one ?piece|bleach|demon ?slayer|xenoverse", re.I)

# mot-clé dans le nom du fichier → rôle (le 1er qui correspond)
RULES = [
    (r"charge|hand sign|handsign|signs", "charge"),
    (r"chidori|rasengan|kamehameha|beam cannon|omega blaster|beam|galick|final flash|laser", "beam"),
    (r"explosion|explod|boom", "explosion"),
    (r"instant transmission|teletransport|teleport|vanish", "teleport"),
    (r"punch|melee|impact|land|hit|kick", "punch"),
    (r"ki blast|ball fire|throw|projectile|shot", "blast"),
    (r"saiyan|sayian|aura|power ?up|ready|shenron", "aura"),
    (r"release", "release"),
    (r"dodge", "dodge"),
    (r"spark|blade|elec", "spark"),
    (r"fly|swing|wind|whoosh|swsh|falling|whis", "whoosh"),
]
MAX_LEN = {"punch": 0.9, "blast": 0.9, "dodge": 0.8, "whoosh": 1.2, "spark": 1.2, "teleport": 1.2,
           "explosion": 2.8, "beam": 3.2, "charge": 2.2, "aura": 2.6, "release": 2.6}


def root() -> Path:
    return library.root() / "_sfx"


def classify(name: str) -> str | None:
    n = name.lower().replace("_", " ")
    for pat, role in RULES:
        if re.search(pat, n):
            return role
    return None


def decode(path: Path) -> np.ndarray:
    r = subprocess.run([require_bin("ffmpeg"), "-loglevel", "error", "-i", str(path), "-ac", "1", "-ar", str(RATE),
                        "-f", "f32le", "-"], capture_output=True)
    return np.frombuffer(r.stdout, dtype=np.float32).copy()


def takes(x: np.ndarray, role: str) -> list[np.ndarray]:
    """Découpe aux silences (> 0,25 s sous 2 % du pic) ; garde les prises assez fortes, coupées à la durée max du
    rôle avec un fondu."""
    if not len(x):
        return []
    pk = float(np.abs(x).max()) or 1.0
    hop = int(0.01 * RATE)
    env = np.array([np.abs(x[i:i + hop]).max() for i in range(0, len(x), hop)])
    loud = env > pk * 0.02
    out, start, quiet = [], None, 0
    for i, on in enumerate(list(loud) + [False] * 30):
        if on:
            if start is None:
                start = i
            quiet = 0
        elif start is not None:
            quiet += 1
            if quiet >= 25:
                seg = x[start * hop:(i - quiet + 3) * hop]
                if len(seg) > 0.06 * RATE and np.abs(seg).max() > pk * 0.25:
                    out.append(seg)
                start, quiet = None, 0
    res = []
    for seg in out:
        n = min(len(seg), int(MAX_LEN.get(role, 2.0) * RATE))
        seg = seg[:n].astype(np.float32)
        f = min(n, int(0.25 * RATE))
        seg[-f:] *= np.linspace(1, 0, f)
        res.append(seg / (np.abs(seg).max() or 1) * 0.9)
    return res


@lru_cache(maxsize=4)
def _bank(rootdir: str, stamp: float) -> dict:
    """{rôle: [(prise, anime?)]} pour tout library/_sfx/."""
    bank: dict = {}
    d = Path(rootdir)
    if not d.is_dir():
        return bank
    for p in sorted(d.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in EXT:
            continue
        role = classify(p.stem)
        if not role:
            continue
        anime = bool(ANIME_DIR.search(str(p.relative_to(d).parent)))
        try:
            for t in takes(decode(p), role):
                bank.setdefault(role, []).append((t, anime, p.stem, str(p.relative_to(d).parent)))
        except Exception as e:
            log.info("son %s illisible (%s)", p.name, e)
    log.info("banque de sons : %s", {k: len(v) for k, v in bank.items()})
    return bank


def bank() -> dict:
    d = root()
    stamp = max((p.stat().st_mtime for p in d.rglob("*") if p.is_file()), default=0) if d.is_dir() else 0
    return _bank(str(d), stamp)


def _same_franchise(item, franchise: str | None) -> bool:
    """Son libre, ou pack anime de la même franchise que le combat (franchise inconnue → tout)."""
    if not item[1] or not franchise:
        return True
    pat = FRANCHISE_DIR.get(franchise.lower())
    return bool(pat and re.search(pat, item[3], re.I))


def pick(role: str, mode: str = "auto", seed: int = 0, prefer: str | None = None,
         franchise: str | None = None) -> np.ndarray | None:
    """Une prise pour ce rôle. mode : « safe » = packs libres seulement ; « anime » = sons officiels d'abord ;
    « auto » = tout. `prefer` = mot à chercher dans le nom (ex. « kamehameha »)."""
    items = [i for i in bank().get(role, []) if _same_franchise(i, franchise)]
    if prefer:                             # le son d'une AUTRE attaque nommée (Chidori pour un Rasengan) : jamais
        own = [i for i in items if prefer.lower() in i[2].lower()]
        items = own or [i for i in items if not re.search(NAMED_MOVES, i[2], re.I)]
    if mode == "safe":
        items = [i for i in items if not i[1]]
    elif mode == "anime" and any(i[1] for i in items):
        items = [i for i in items if i[1]]
    if not items:
        return None
    return random.Random(seed).choice(items)[0]


def credits() -> list[str]:
    """Packs libres à créditer (licence CC BY) : dossiers de premier niveau qui ne sont pas « anime »."""
    d = root()
    if not d.is_dir():
        return []
    return [sub.name for sub in sorted(x for x in d.iterdir() if x.is_dir())
            if not ANIME_DIR.search(sub.name) and any(f.suffix.lower() in EXT for f in sub.rglob("*"))]


def _mix(parts):
    end = max(int(o * RATE) + len(x) for o, x, _ in parts)
    out = np.zeros(end, dtype=np.float32)
    for o, x, g in parts:
        i = int(o * RATE)
        out[i:i + len(x)] += x * g
    return out


def sound(fam: str, mode: str = "auto", seed: int = 0, move: str | None = None,
          franchise: str | None = None) -> np.ndarray | None:
    """Bruitage d'une famille d'effet du Domain War fait avec la banque (None = rien de convenable → son
    retravaillé de sfxdesign)."""
    def p(role, s=0, prefer=None):
        return pick(role, mode, seed * 7 + s, prefer, franchise)

    def first(*roles):
        for r in roles:
            x = p(r)
            if x is not None:
                return x
        return None
    word = None
    if move:
        for w in re.findall(r"[a-z]+", move.lower()):
            if len(w) >= 5:
                word = w
                break
    if fam in ("bomb", "meteor"):
        ex = p("explosion")
        if ex is None:
            return None
        ch = p("charge", 1)
        return _mix([(0, ch[: int(0.5 * RATE)], 0.5), (0.45, ex, 1.0)]) if ch is not None else ex
    if fam in ("domain", "shrine", "giant"):
        rel, ex = first("release", "aura"), p("explosion", 2)
        if rel is None and ex is None:
            return None
        return _mix([x for x in ((0, rel, 0.9) if rel is not None else None,
                                 (0.35, ex, 1.0) if ex is not None else None) if x])
    if fam in ("beam", "mega_beam"):
        b = p("beam", 0, word)
        if b is not None:
            return b
        ch, rel = p("charge"), first("release", "blast")
        if rel is None:
            return None
        return _mix([(0, ch[: int(0.45 * RATE)], 0.6), (0.4, rel, 1.0)]) if ch is not None else rel
    if fam == "shots":
        bl = [p("blast", i, word) for i in range(3)]
        bl = [x for x in bl if x is not None]
        if not bl:
            return None
        return _mix([(i * 0.09, x, 0.8) for i, x in enumerate(bl)])
    if fam in ("teleport", "vanish"):
        return first("teleport", "dodge", "whoosh")
    if fam == "miss":
        return first("dodge", "whoosh")
    if fam == "hit":
        return p("punch")
    if fam == "ko":
        pu, ex = p("punch", 3), p("explosion", 3)
        if pu is None and ex is None:
            return None
        return _mix([x for x in ((0, pu, 1.0) if pu is not None else None,
                                 (0.05, ex, 0.8) if ex is not None else None) if x])
    if fam in ("transform", "powerup"):
        au, rel = p("aura", 4, "saiyan" if fam == "transform" else None), p("release", 4)
        if au is None and rel is None:
            return None
        if fam == "powerup":
            return au if au is not None else rel
        ch = p("charge", 5)
        return _mix([x for x in ((0, ch, 0.7) if ch is not None else None,
                                 (0.6, au, 1.0) if au is not None else None,
                                 (1.1, rel, 0.9) if rel is not None else None) if x])
    if fam == "clash":
        b1, b2 = p("beam", 6), p("beam", 7)
        ex = p("explosion", 8)
        body = [x for x in (b1, b2) if x is not None]
        if not body:
            ch = [p("charge", 9 + i) for i in range(3)]
            body = [x for x in ch if x is not None]
        if not body:
            return None
        parts = [(i * 1.2, x, 0.8) for i, x in enumerate(body + body)][:3]
        if ex is not None:
            parts.append((3.55, ex, 1.0))
        return _mix(parts)
    return None
