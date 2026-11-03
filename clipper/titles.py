"""Étape 5 : titres, description, tags, texte de miniature."""
from __future__ import annotations

import re

from . import config, db, llm, prompts
from .transcript import load_words, sentences, text_between
from .util import log, tc

FORBIDDEN = re.compile(r"[<>]")


def clean(s: str) -> str:
    return FORBIDDEN.sub("", re.sub(r"\s+", " ", s)).strip().strip('"«»“”').strip()


def shorten(title: str, n: int) -> str:
    """Coupe à n caractères sur une frontière de mot, sans points de suspension."""
    if len(title) <= n:
        return title
    cut = title[:n + 1].rsplit(" ", 1)[0].rstrip(" ,;:-–—")
    return cut or title[:n]


def problems(out: dict, n_titles: int, max_chars: int, n_tags: int) -> list[str]:
    p = []
    titles = [clean(t) for t in out.get("titles", [])]
    if len(titles) < n_titles:
        p.append(f"il faut {n_titles} titres, tu en as donné {len(titles)}")
    for t in titles:
        if len(t) > max_chars:
            p.append(f"« {t} » fait {len(t)} caractères (max {max_chars})")
    if len(out.get("tags", [])) != n_tags:
        p.append(f"il faut exactement {n_tags} tags, tu en as donné {len(out.get('tags', []))}")
    nw = len(clean(out.get("thumbnail_text", "")).split())
    if not 3 <= nw <= 4:
        p.append(f"le texte de miniature doit faire 3 ou 4 mots, il en fait {nw}")
    return p


def source_link(video: dict, start: float) -> str:
    return f"https://youtu.be/{video['id']}?t={int(start)}"


def build_description(body: str, video: dict, start: float) -> str:
    footer = (config.get()["titles"].get("description_footer") or "").strip()
    parts = [clean_multiline(body),
             f"▶ Extrait de « {clean(video.get('title') or '')} », à partir de {tc(start)} :\n{source_link(video, start)}"]
    if footer:
        parts.append(footer)
    return "\n\n".join(parts)[:4900]


def refresh_link(desc: str, video: dict, start: float) -> str:
    """Après un ajustement de bornes : remet le timecode et le lien source à jour dans la description."""
    desc = re.sub(r"(https://youtu\.be/[\w-]{11}\?t=)\d+", lambda m: f"{m.group(1)}{int(start)}", desc)
    return re.sub(r"(à partir de )\d+(:\d{2}){1,2}", lambda m: f"{m.group(1)}{tc(start)}", desc)


def clean_multiline(s: str) -> str:
    return "\n".join(FORBIDDEN.sub("", line).rstrip() for line in s.strip().splitlines())


def fit_tags(tags: list[str], n: int) -> list[str]:
    seen, out = set(), []
    for t in tags:
        t = clean(t).lower().lstrip("#")
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    out = out[:n]
    while sum(len(t) + 2 for t in out) > 480:  # limite YouTube : 500 caractères au total
        out.pop()
    return out


def generate(clip_id: int) -> None:
    c = db.get_clip(clip_id)
    if c["titles"]:
        return
    v = db.get_video(c["video_id"])
    tc_cfg = config.get()["titles"]
    n_titles, max_chars, n_tags = int(tc_cfg["n_titles"]), int(tc_cfg["max_title_chars"]), int(tc_cfg["n_tags"])
    sents = sentences(load_words(v["transcript_path"]))
    system = prompts.TITLES_SYSTEM.format(n_titles=n_titles, max_chars=max_chars, n_tags=n_tags)
    base = dict(source_title=v.get("title") or "", channel=v.get("channel") or "", topic=c["topic"],
                reason=c["reason"], duration=tc(c["end"] - c["start"]),
                text=text_between(sents, c["start"], c["end"]))
    feedback = ""
    out: dict = {}
    for attempt in range(2):
        out = llm.structured(model=tc_cfg["model"], system=system,
                             user=prompts.TITLES_USER.format(**base, feedback=feedback),
                             tool_name="metadonnees", tool_desc="Enregistre les métadonnées YouTube du clip.",
                             schema=prompts.TITLES_SCHEMA, max_tokens=2000)
        errs = problems(out, n_titles, max_chars, n_tags)
        if not errs:
            break
        log.info("clip %s : correction demandée (%s)", clip_id, "; ".join(errs))
        feedback = "\n\nTa réponse précédente avait ces problèmes, corrige-les :\n- " + "\n- ".join(errs)
    titles = [shorten(clean(t), max_chars) for t in out.get("titles", [])][:n_titles] or [shorten(clean(c["topic"]), max_chars)]
    db.update_clip(
        clip_id, titles=titles, title_idx=0,
        description=build_description(out.get("description", ""), v, c["start"]),
        tags=fit_tags(out.get("tags", []), n_tags),
        thumb_text=" ".join(clean(out.get("thumbnail_text", "")).split()[:4]),
    )
