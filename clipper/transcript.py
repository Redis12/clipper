"""Découpage d'une transcription au mot en phrases numérotées, et rendu texte pour Claude."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .util import tc

END_PUNCT = (".", "?", "!", "…", "»")
MAX_WORDS = 60     # garde-fou : une « phrase » sans ponctuation ne dépasse pas ça
GAP_SPLIT = 1.2    # silence (s) qui coupe une phrase même sans ponctuation


@dataclass
class Sentence:
    idx: int
    start: float
    end: float
    spk: int
    text: str
    w0: int  # index du premier mot
    w1: int  # index du dernier mot (inclus)


def load_words(path: str | Path) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))["words"]


def sentences(words: list[dict]) -> list[Sentence]:
    out: list[Sentence] = []
    start_i = 0

    def flush(end_i: int) -> None:
        nonlocal start_i
        if end_i < start_i:
            return
        ws = words[start_i:end_i + 1]
        out.append(Sentence(
            idx=len(out), start=ws[0]["s"], end=ws[-1]["e"],
            spk=max(set(w["spk"] for w in ws), key=[w["spk"] for w in ws].count),
            text=" ".join(w["w"] for w in ws).strip(), w0=start_i, w1=end_i,
        ))
        start_i = end_i + 1

    for i, w in enumerate(words):
        last = i == len(words) - 1
        if last:
            flush(i)
            break
        nxt = words[i + 1]
        token = w["w"].rstrip('"\')')
        if (
            token.endswith(END_PUNCT)
            or nxt["spk"] != w["spk"]
            or nxt["s"] - w["e"] > GAP_SPLIT
            or i - start_i + 1 >= MAX_WORDS
        ):
            flush(i)
    return out


def render(sents: list[Sentence], first: int = 0, last: int | None = None) -> str:
    """Une ligne par phrase : « [s42 12:03.4 S1] texte ». Le locuteur n'est répété qu'au changement."""
    last = len(sents) - 1 if last is None else last
    lines, prev_spk = [], None
    for s in sents[first:last + 1]:
        spk = f" S{s.spk}" if s.spk != prev_spk else ""
        lines.append(f"[s{s.idx} {tc(s.start, ms=True)}{spk}] {s.text}")
        prev_spk = s.spk
    return "\n".join(lines)


def text_between(sents: list[Sentence], start: float, end: float) -> str:
    return " ".join(s.text for s in sents if s.end > start and s.start < end)
