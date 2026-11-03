"""Étape 3 (+4) : Claude propose des clips, on calcule les bornes, on fusionne et on enregistre."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from . import bounds as B
from . import config, db, llm, prompts
from .transcript import Sentence, load_words, render, sentences
from .util import log, tc


@dataclass
class Candidate:
    first: int
    last: int
    topic: str
    score: int
    reason: str
    start: float = 0.0
    end: float = 0.0
    reject: str | None = None
    chunks: set[int] = field(default_factory=set)


def plan_chunks(sents: list[Sentence], single_max_chars: int, chunk_s: float, overlap_s: float) -> list[tuple[int, int]]:
    """Blocs [first, last] d'index de phrases. Un seul bloc si la transcription tient d'un coup."""
    if not sents:
        return []
    if len(render(sents)) <= single_max_chars:
        return [(0, len(sents) - 1)]
    step = chunk_s - overlap_s
    if step <= 0:
        raise ValueError("chunk_minutes doit dépasser chunk_overlap_minutes")
    total = sents[-1].end
    out, t0 = [], sents[0].start
    while True:
        t1 = t0 + chunk_s
        idx = [s.idx for s in sents if s.start >= t0 and s.start < t1]
        if idx:
            out.append((idx[0], idx[-1]))
        if t1 >= total:
            break
        t0 += step
    return out


def merge(cands: list[Candidate], max_overlap: float, max_n: int) -> list[Candidate]:
    """Glouton par note décroissante : on garde un clip s'il chevauche peu tous ceux déjà gardés."""
    kept: list[Candidate] = []
    for c in sorted(cands, key=lambda c: (-c.score, c.start)):
        if len(kept) >= max_n:
            break
        if all(B.overlap_ratio((c.start, c.end), (k.start, k.end)) < max_overlap for k in kept):
            kept.append(c)
    return sorted(kept, key=lambda c: c.start)


def _ask(video: dict, sents: list[Sentence], first: int, last: int, n_min: int, n_max: int,
         part: str) -> tuple[list[Candidate], str]:
    cfg = config.get()
    sc, bc = cfg["selection"], cfg["bounds"]
    chapters = video.get("chapters") or []
    chap_txt = ("Chapitres : " + " ; ".join(f"{tc(c['start_time'])} {c['title']}" for c in chapters)) if chapters else ""
    system = prompts.SELECTION_SYSTEM.format(
        min_s=int(bc["min_duration"]), max_s=int(bc["max_duration"]),
        overlap_pct=int(sc["max_overlap"] * 100))
    user = prompts.SELECTION_USER.format(
        title=video.get("title") or "?", channel=video.get("channel") or "?",
        duration=tc(video.get("duration") or sents[-1].end), chapters=chap_txt, scope=part,
        n_min=n_min, n_max=n_max, transcript=render(sents, first, last))
    out = llm.structured(model=sc["model"], system=system, user=user, tool_name="proposer_clips",
                         tool_desc="Enregistre les clips candidats.", schema=prompts.SELECTION_SCHEMA,
                         max_tokens=8000)
    res = []
    for c in out.get("clips", []):
        f, l = int(c["first_sentence"]), int(c["last_sentence"])
        if not (first <= f <= l <= last):
            log.warning("Clip ignoré : index hors bloc (%s-%s)", f, l)
            continue
        res.append(Candidate(f, l, c["topic"].strip(), max(0, min(100, int(c["score"]))), c["reason"].strip()))
    return res, out.get("note", "")


def select(video_id: str) -> int:
    """Rend le nombre de clips valides. Ne refait rien si la sélection existe déjà."""
    v = db.get_video(video_id)
    if db.clips_for(video_id):
        return len(db.clips_for(video_id, ["pending", "review", "approved", "uploaded"]))
    db.update_video(video_id, step="sélection")
    cfg = config.get()
    sc, bc = cfg["selection"], cfg["bounds"]
    words = load_words(v["transcript_path"])
    sents = sentences(words)
    chunks = plan_chunks(sents, int(sc["single_pass_max_chars"]),
                         float(sc["chunk_minutes"]) * 60, float(sc["chunk_overlap_minutes"]) * 60)
    total = sents[-1].end - sents[0].start
    cands: list[Candidate] = []
    notes = []
    for i, (f, l) in enumerate(chunks):
        if len(chunks) == 1:
            n_min, n_max, part = int(sc["min_clips"]), int(sc["max_clips"]), ""
        else:
            share = (sents[l].end - sents[f].start) / total
            n_max = max(2, math.ceil(int(sc["max_clips"]) * share) + 2)
            n_min = 1
            part = (f"Ceci est le bloc {i + 1}/{len(chunks)} de la transcription "
                    f"({tc(sents[f].start)} → {tc(sents[l].end)}). Les blocs se recouvrent ; "
                    "ignore un clip qui serait coupé par le bord du bloc.")
        log.info("[%s] sélection bloc %d/%d (s%d-s%d)", video_id, i + 1, len(chunks), f, l)
        got, note = _ask(v, sents, f, l, n_min, n_max, part)
        for c in got:
            c.chunks.add(i)
        cands += got
        if note:
            notes.append(note)

    for c in cands:
        b = B.compute(sents, words, c.first, c.last, v.get("duration") or 0,
                      float(bc["margin"]), float(bc["min_duration"]), float(bc["max_duration"]))
        c.start, c.end, c.reject = b.start, b.end, b.reject

    valid = merge([c for c in cands if not c.reject], float(sc["max_overlap"]), int(sc["max_clips"]))
    # Rejets auto : on garde une trace (dédoublonnée) pour pouvoir les repêcher dans la revue.
    rejected = merge([c for c in cands if c.reject], 0.8, 50)

    for rank, c in enumerate(sorted(valid, key=lambda c: -c.score), start=1):
        db.insert_clip(video_id, rank=rank, start=c.start, end=c.end, sel_start=c.start, sel_end=c.end,
                       first_sentence=c.first, last_sentence=c.last, topic=c.topic, score=c.score,
                       reason=c.reason, status="pending")
    for c in rejected:
        db.insert_clip(video_id, start=c.start, end=c.end, sel_start=c.start, sel_end=c.end,
                       first_sentence=c.first, last_sentence=c.last, topic=c.topic, score=c.score,
                       reason=c.reason, status="rejected_auto", reject_reason=c.reject)
    msg = f"{len(valid)} clips retenus, {len(rejected)} rejetés aux bornes"
    if len(valid) < int(sc["min_clips"]):
        msg += f" (moins de {sc['min_clips']} : " + ("; ".join(notes) or "pas assez de matière autonome") + ")"
    db.update_video(video_id, status="selected", error=None if valid else msg)
    log.info("[%s] %s", video_id, msg)
    return len(valid)
