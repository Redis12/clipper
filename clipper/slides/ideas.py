"""Idées de slideshows (Claude) et script détaillé d'un slideshow."""
from __future__ import annotations

import re

from .. import config, db, llm
from ..util import log
from . import library, prompts


def cfg() -> dict:
    return config.get()["slides"]


def allowed_animes() -> list[str]:
    """Animes autorisés ; si demandé, seulement ceux qui ont des images dans la bibliothèque."""
    names = list(cfg()["animes"])
    if cfg().get("only_library_animes", True):
        have = set(library.animes_with_images())
        with_imgs = [a for a in names if library.norm(a) in have]
        if with_imgs:
            return with_imgs
        log.warning("Bibliothèque vide : idées proposées sur tous les animes de config.yaml")
    return names


def canonical_anime(name: str) -> str:
    n = library.norm(name)
    for a in cfg()["animes"]:
        if library.norm(a) == n:
            return a
    return "Mixed" if n in ("mixed", "various", "multiple") else name.strip()


def _trend_lines(rows: list[dict]) -> str:
    from . import trends
    return "\n".join(f"[{r['id']}] {line[2:]}" for r, line in zip(rows, trends.as_prompt(rows).splitlines()))


def generate_ideas(n: int | None = None, focus_trend: int | None = None) -> list[int]:
    from . import trends
    c = cfg()
    n = int(n or (3 if focus_trend else c.get("ideas_per_batch", 12)))
    animes = allowed_animes()
    formats = [f for f in c["formats"] if f in prompts.FORMATS and f not in ("ratings", "news")]   # notes / actu fournies à la main
    existing = [r["topic"] for r in db.query("SELECT topic FROM slideshows ORDER BY id DESC LIMIT 200")]
    if focus_trend:
        rows = [db.get("trends", focus_trend)]
        trend_block = prompts.FOCUS_BLOCK.format(row=_trend_lines(rows))
    else:
        rows = trends.top()
        trend_block = prompts.TRENDS_BLOCK.format(rows=_trend_lines(rows)) if rows else ""
        al = trends.anilist_prompt()
        trend_block += prompts.ANILIST_BLOCK.format(rows=al) if al else ""
    trend_by_id = {r["id"]: r for r in rows}
    out = llm.structured(
        model=c["model"],
        system=prompts.IDEAS_SYSTEM.format(min_s=c["min_slides"], max_s=c["max_slides"],
                                           animes=", ".join(animes), formats=", ".join(formats)),
        user=prompts.IDEAS_USER.format(n=n, existing="\n".join(f"- {t}" for t in existing) or "(none yet)",
                                       trends=trend_block),
        tool_name="propose_ideas", tool_desc="Store slideshow ideas.", schema=prompts.IDEAS_SCHEMA,
        max_tokens=8000)
    ids, seen = [], {library.norm(t) for t in existing}
    for i in out.get("ideas", []):
        topic = " ".join(str(i.get("topic", "")).split())
        if not topic or library.norm(topic) in seen:
            continue
        fmt = i.get("format") if i.get("format") in formats else formats[0]
        seen.add(library.norm(topic))
        src = [trend_by_id[t] for t in i.get("inspired_by", []) if t in trend_by_id] or (
            list(trend_by_id.values()) if focus_trend else [])
        inspiration = " | ".join(f"{t['platform']}: {t['topic']}" + (f" ({t['url']})" if t.get("url") else "")
                                 for t in src[:3]) or None
        ids.append(db.insert("slideshows", anime=canonical_anime(i.get("anime", "")), format=fmt, topic=topic,
                             hook=i.get("hook", "").strip(), angle=i.get("angle", "").strip(),
                             why=i.get("why", "").strip(), score=max(0, min(100, int(i.get("score", 50)))),
                             origin="claude", status="idea", inspiration=inspiration))
    log.info("%d idées ajoutées", len(ids))
    return ids


def add_user_topic(topic: str, anime: str = "", fmt: str = "", notes: str = "", use_logo: bool = True) -> int:
    """Sujet perso. `notes` = consignes libres transmises telles quelles à Claude (persos imposés, ton…)."""
    fmt = fmt if fmt in prompts.FORMATS else guess_format(topic)
    notes = " ".join(notes.split())
    return db.insert("slideshows", anime=canonical_anime(anime) if anime else "Mixed", format=fmt,
                     topic=" ".join(topic.split()), hook="", angle=f"MANDATORY instructions from the creator: {notes}"
                     if notes else "", origin="user", status="queued", use_logo=int(bool(use_logo)))


def guess_format(topic: str) -> str:
    t = topic.lower()
    if re.search(r"\b(imdb|ratings?|rated|mal score)\b", t):
        return "ratings"
    if re.search(r"\b(news|announced|announcement|release date|premieres?|out on)\b|\b\d{1,2}(st|nd|rd|th)\s+"
                 r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)", t):
        return "news"
    if re.search(r"\b(top|best|strongest|ranked|ranking|worst|saddest)\b", t):
        return "ranking"
    if re.search(r"\b(zodiac|star sign)", t):
        return "zodiac"
    if re.search(r"\b(birth ?month|birthday|your month|first letter|= ?your|which .* are you)", t):
        return "assign"
    if re.search(r"red ?flags?", t):
        return "redflags"
    if re.search(r"\bwallpapers?|lockscreen", t):
        return "wallpaper"
    if re.search(r"unpopular|opinions?|hot takes?", t):
        return "opinions"
    if re.search(r"characters as\b", t):
        return "as_people"
    if re.search(r"\b(guess|quiz|who said)\b", t):
        return "quiz"
    if re.search(r"\b(if you (liked|loved)|watch|recommend)", t):
        return "recommendations"
    return "facts"


# --- script ---------------------------------------------------------------------

def _slide(item: dict, kind: str, default_anime: str, facts: bool = True) -> dict:
    return {
        "kind": kind,
        "label": " ".join(str(item.get("label", "")).split())[:16] if kind == "body" else "",
        "text": " ".join(str(item.get("text", "")).split()),
        "anime": canonical_anime(item.get("anime") or default_anime),
        "character": " ".join(str(item.get("character", "")).split()),
        "scene": " ".join(str(item.get("scene", "")).split()),
        "confidence": int(item.get("confidence", 100)) if kind == "body" and facts else 100,
        "image_path": None, "alts": [], "character_match": None,
    }


EP_RE = re.compile(r"\b(?:EP|E|EPISODE|ÉPISODE)\s*\.?\s*(\d{1,4})\s*[:=\-–—)]?\s*(\d{1,2}(?:[.,]\d{1,2})?)\b", re.I)
SCORE_RE = re.compile(r"\b(?:overall|score|global|average|moyenne|note|season|saison|series|rating|rated|imdb|mal)"
                      r"\D{0,20}?(\d{1,2}[.,]\d)\b", re.I)
SOURCE_RE = re.compile(r"\b(IMDb|MyAnimeList|MAL|AniList|Rotten Tomatoes)\b", re.I)


def parse_chart(notes: str) -> dict | None:
    """Notes d'épisodes tirées des consignes : « EP1 8.1, EP2 7.9 … overall 8.6 (IMDb) »."""
    if not notes:
        return None
    pairs = [(int(n), float(v.replace(",", "."))) for n, v in EP_RE.findall(notes)]
    pairs = [(n, v) for n, v in pairs if 0 <= v <= 10]
    seen, uniq = set(), []
    for n, v in pairs:
        if n not in seen:
            seen.add(n)
            uniq.append((n, v))
    m = SCORE_RE.search(EP_RE.sub(" ", notes))
    src = SOURCE_RE.search(notes)
    srcname = ({"mal": "MyAnimeList"}.get(src.group(1).lower(), src.group(1)) + " rating") if src else ""
    if not uniq:
        if not m:
            return None
        v = float(m.group(1).replace(",", "."))      # seulement la note de la série : une carte, pas de graphique
        return {"labels": [""], "values": [v], "score": f"{v:.1f}", "score_given": True, "source": srcname,
                "overall": True}
    uniq.sort()
    return {"labels": [f"EP {n}" for n, _ in uniq], "values": [v for _, v in uniq],
            "score": m.group(1).replace(",", ".") if m else f"{sum(v for _, v in uniq) / len(uniq):.1f}",
            "score_given": bool(m), "source": srcname}


SEASON_RE = re.compile(r"\b(?:S|SEASON|SAISON)\s*(\d{1,2})\b\s*[:\-–]?", re.I)


def parse_charts(notes: str) -> list[dict]:
    """Une ou plusieurs saisons : « S1: EP1 7.9 … S2: EP1 8.0 … (IMDb) ». Rend un graphique par saison."""
    if not notes:
        return []
    marks = [m for m in SEASON_RE.finditer(notes)]
    src = SOURCE_RE.search(notes)
    tail = f" {src.group(1)}" if src else ""
    charts = []
    for i, m in enumerate(marks):
        part = notes[m.end(): marks[i + 1].start() if i + 1 < len(marks) else len(notes)]
        ch = parse_chart(part + tail)
        if ch:
            ch["season"] = int(m.group(1))
            charts.append(ch)
    if len(charts) >= 2:
        return charts
    one = parse_chart(notes)
    return [one] if one else []


def parse_news_extras(notes: str) -> list[dict]:
    """Slides en plus pour le format news : lignes « > TAG | titre avec *mots en jaune* | sous-titre »."""
    out = []
    for line in (notes or "").splitlines():
        line = line.strip()
        if not line.startswith(">"):
            continue
        parts = [p.strip() for p in line[1:].split("|")]
        if len(parts) == 1:
            parts = ["", parts[0]]
        out.append({"tag": parts[0] or "FUN FACT", "text": parts[1], "sub": parts[2] if len(parts) > 2 else ""})
    return out


def slide_limits(fmt: str, c: dict) -> dict:
    """Bornes du nombre de slides et de mots, selon le format (« assign » = 12 slides fixes)."""
    n = prompts.FIXED_SLIDES.get(fmt)
    return {**c, "min_slides": n or c["min_slides"], "max_slides": n or c["max_slides"],
            "max_words_per_slide": max(c["max_words_per_slide"], 16) if n else c["max_words_per_slide"]}


def script_problems(out: dict, c: dict) -> list[str]:
    p = []
    n = len(out.get("slides", []))
    if not c["min_slides"] <= n <= c["max_slides"]:
        p.append(f"there must be {c['min_slides']}-{c['max_slides']} content slides, you gave {n}")
    for i, s in enumerate(out.get("slides", []), 1):
        w = len(str(s.get("text", "")).split())
        if w > c["max_words_per_slide"]:
            p.append(f"slide {i} has {w} words (max {c['max_words_per_slide']})")
    if len(str(out.get("cover", {}).get("text", "")).split()) > 10:
        p.append("cover text is longer than 9 words")
    if len(out.get("yt_title", "")) > 70:
        p.append("yt_title is longer than 70 characters")
    return p


def write_script(slideshow_id: int) -> None:
    s = db.get("slideshows", slideshow_id)
    if s["slides"]:
        return
    charts = parse_charts(s["angle"] or "") if s["format"] == "ratings" else []
    chart = charts[0] if charts else None
    if s["format"] == "ratings" and not chart:
        raise RuntimeError("Format « ratings » : mets les notes dans les consignes, ex. « EP1 8.1, EP2 7.9, … "
                           "overall 8.6 (IMDb) »")
    c = slide_limits(s["format"], cfg())
    if s["format"] == "wallpaper":              # 4 à 6 wallpapers (chacun en aperçu + version seule)
        n_wall = len(library.candidates(s["anime"] or "", "", set(), wallpaper=True)[1])
        n = min(6, max(1, n_wall - 1)) if n_wall else 4   # wallpapers dispo (1 sert à la couverture), max 6
        c = {**c, "min_slides": n, "max_slides": n}
    if len(charts) > 1:                         # plusieurs saisons : top 5 des épisodes, toutes saisons
        c = {**c, "min_slides": 5, "max_slides": 5}
    single = bool(chart) and len(charts) == 1 and len(chart["values"]) == 1
    extras = parse_news_extras(s["angle"].replace("MANDATORY instructions from the creator: ", "\n")
                                .replace(" > ", "\n> ")) if s["format"] == "news" else []
    if s["format"] == "news":
        single = True
    if extras:                                  # une slide par ligne « > … » (Claude choisit juste le perso)
        c = {**c, "min_slides": len(extras), "max_slides": len(extras)}
    elif single:                                  # une seule note : le post = la carte, rien d'autre
        c = {**c, "min_slides": 0, "max_slides": 0}
    elif chart:                                 # une slide par épisode
        c = {**c, "min_slides": min(len(chart["values"]), c["max_slides"]),
             "max_slides": max(len(chart["values"]), c["min_slides"])}
    chars = library.characters_for(s["anime"]) if s["anime"] and s["anime"] != "Mixed" else []
    char_line = (f"- Characters with images available (prefer them, exact spelling): {', '.join(chars)}\n"
                 if chars else "")
    system = prompts.SCRIPT_SYSTEM.format(min_s=c["min_slides"], max_s=c["max_slides"],
                                          max_words=c["max_words_per_slide"], characters=char_line)
    base = dict(format_desc=prompts.FORMATS.get(s["format"], prompts.FORMATS["facts"]), anime=s["anime"] or "Mixed",
                topic=s["topic"], hook=s["hook"] or "(write one)", angle=s["angle"] or "(your call)")
    feedback, out = "", {}
    for _ in range(2):
        out = llm.structured(model=c["model"], system=system, user=prompts.SCRIPT_USER.format(**base, feedback=feedback),
                             tool_name="write_slideshow", tool_desc="Store the slideshow script.",
                             schema=prompts.SCRIPT_SCHEMA, max_tokens=12000)
        errs = script_problems(out, c)
        if not errs:
            break
        feedback = "\n\nYour previous answer had these problems, fix them:\n- " + "\n- ".join(errs)
    anime = s["anime"] or "Mixed"
    slides = [_slide(out["cover"], "cover", anime)]
    if chart:
        from . import render
        lp = render.logo_path(anime)
        logo = str(lp) if s.get("use_logo", 1) and lp.exists() else None
        for ch in charts:
            if logo and (len(charts) == 1 or ch is charts[-1]):
                ch["logo"] = logo                       # logo (souvent celui de la dernière saison) : dernière saison
        slides[0]["chart"] = chart
        extra = [{**slides[0], "kind": "body", "label": "", "chart": ch, "confidence": 100,
                  "text": f"Season {ch['season']}"}
                 for ch in charts[1:]]
        if len(charts) > 1:
            slides[0]["text"] = slides[0]["text"] or f"Season {charts[0]['season']}"
        slides[1:1] = extra
    facts = s["format"] not in prompts.NO_FACTS
    slides += [_slide(x, "body", anime, facts) for x in out.get("slides", [])[: c["max_slides"]]]
    if s["format"] == "wallpaper":              # couverture « JJK wallpapers >>> » telle quelle, texte simple
        slides[0]["text"], slides[0]["plain"] = s["topic"], True
        for x in slides:
            x["wallpaper"] = True                   # images prises dans library/wallpaper/<anime>/
        if not re.search(r"(?i)no\s*lock\s*screen|sans aper", s["angle"] or ""):
            # Chaque wallpaper deux fois : d'abord l'aperçu écran de verrouillage, puis le wallpaper seul (même image).
            from datetime import datetime
            when = datetime.now()
            lock = {"date": when.strftime("%A, %B ") + str(when.day), "time": "9:41"}
            paired = [slides[0]]
            for x in slides[1:]:
                if x["kind"] == "body":
                    paired += [{**x, "lock": lock, "wallpaper": True}, {**x, "twin": True, "wallpaper": True}]
                else:
                    paired.append(x)
            slides = paired
    if s["format"] == "news":                   # titre = exactement ce que tu as écrit (« | » = retour à la ligne)
        slides[0]["text"] = s["topic"]
        slides[0]["news"] = {}
        m = re.search(r"(?i)\bsub\s*:\s*(.+?)(?=\s*\n|\s+>\s|$)", s["angle"] or "")
        if m:                                   # « SUB: SWIPE FOR MORE → » remplace « more details… ▼ »
            slides[0]["news"] = {"sub": m.group(1).strip().upper(), "arrow": False}
        body = slides[1:]
        slides = slides[:1]
        for i, ex in enumerate(extras):
            base = body[i] if i < len(body) else _slide({}, "body", anime)
            slides.append({**base, "label": "", "text": ex["text"], "confidence": 100,
                           "news": {"tag": ex["tag"], "sub": ex["sub"], "arrow": False}})
    if not (s["format"] in ("ratings", "news") and single):
        slides.append(_slide(out["end"], "end", anime))
        if s["format"] == "wallpaper":
            slides[-1]["wallpaper"] = True
    tags = []
    for h in out.get("hashtags", []):
        h = re.sub(r"[^\w]", "", str(h).lower())
        if h and h not in tags:
            tags.append(h)
    db.update("slideshows", slideshow_id, slides=slides, caption=" ".join(out.get("caption", "").split()),
              hashtags=tags[:5], yt_title=" ".join(out.get("yt_title", "").split())[:100] or s["topic"][:100],
              yt_description=out.get("yt_description", "").strip(), hook=s["hook"] or slides[0]["text"])
