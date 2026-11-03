"""Étape 4 : bornes propres. Frontières de phrase, marge sans mordre sur les mots voisins, durée bornée."""
from __future__ import annotations

from dataclasses import dataclass

from .transcript import Sentence
from .util import tc


@dataclass
class Bounds:
    start: float
    end: float
    reject: str | None = None


def compute(sents: list[Sentence], words: list[dict], first: int, last: int, video_duration: float,
            margin: float = 0.3, min_d: float = 120, max_d: float = 300) -> Bounds:
    a, b = sents[first], sents[last]
    raw_s, raw_e = a.start, b.end

    # Début : jusqu'à `margin` avant le premier mot, sans dépasser le milieu du silence qui précède.
    start = raw_s - margin
    if a.w0 > 0:
        start = max(start, (words[a.w0 - 1]["e"] + raw_s) / 2)
    start = max(0.0, start)

    # Fin : jusqu'à `margin` après le dernier mot, sans dépasser le milieu du silence qui suit.
    end = raw_e + margin
    if b.w1 + 1 < len(words):
        end = min(end, (raw_e + words[b.w1 + 1]["s"]) / 2)
    if video_duration:
        end = min(end, video_duration)

    start, end = round(start, 3), round(end, 3)
    d = end - start
    if d < min_d:
        return Bounds(start, end, f"Trop court : {tc(d)} (minimum {tc(min_d)})")
    if d > max_d:
        return Bounds(start, end, f"Trop long : {tc(d)} (maximum {tc(max_d)})")
    return Bounds(start, end)


def overlap_ratio(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Chevauchement rapporté au plus court des deux segments (0 = disjoints, 1 = l'un contient l'autre)."""
    inter = min(a[1], b[1]) - max(a[0], b[0])
    if inter <= 0:
        return 0.0
    return inter / max(1e-6, min(a[1] - a[0], b[1] - b[0]))
