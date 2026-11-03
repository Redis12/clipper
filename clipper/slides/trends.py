"""Veille : ce qui marche en ce moment dans la niche, pour inspirer les idées de slideshows.

Sources légales uniquement :
- YouTube : API officielle (search.list + videos.list), Shorts récents les plus vus.
- Instagram : API officielle de recherche par hashtag (compte pro + app Meta), carrousels populaires.
- YouTube « lu en vrai » : pour les meilleurs Shorts, Claude regarde la couverture (miniature officielle)
  et lit les commentaires les plus pertinents (commentThreads.list) : accroche réelle + ce que le public réclame.
- AniList : API GraphQL publique, gratuite et sans clé : animes en tendance cette semaine et persos préférés.
- TikTok / autres : captures d'écran déposées par l'utilisateur, lues par Claude (pas de scraping).
"""
from __future__ import annotations

import re
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import json

import httpx

from .. import config, db, llm, quota, youtube
from ..util import log

TREND_FIELDS = {"anime", "format", "topic", "hook", "why", "slideshow_like"}


def tcfg() -> dict:
    return config.get()["slides"]["trends"]


def scfg() -> dict:
    return config.get()["slides"]


def _iso_duration_s(d: str) -> int:
    m = re.match(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", d or "")
    if not m:
        return 0
    days, h, mi, s = (int(x or 0) for x in m.groups())
    return days * 86400 + h * 3600 + mi * 60 + s


def parse_count(s) -> int | None:
    """« 1.2M », « 845K », « 12 345 », « 1,2 M » → entier."""
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return int(s)
    t = str(s).strip().upper().replace(" ", "").replace(" ", "")
    m = re.match(r"^([\d.,]+)([KMB]?)$", t)
    if not m:
        return None
    num, suf = m.groups()
    if suf and "," in num and "." not in num:
        num = num.replace(",", ".")
    num = num.replace(",", "")
    try:
        v = float(num)
    except ValueError:
        return None
    return int(v * {"": 1, "K": 1e3, "M": 1e6, "B": 1e9}[suf])


def score(views: int | None, likes: int | None, published_at: str | None) -> float:
    """Vues par jour (bonus d'engagement) : favorise ce qui décolle vite."""
    v = views or 0
    days = 3.0
    if published_at:
        try:
            age = datetime.now(timezone.utc) - datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            days = max(0.5, age.total_seconds() / 86400)
        except ValueError:
            pass
    eng = (likes or 0) / v if v else 0
    return round(v / days * (1 + min(eng, 0.2) * 2), 1)


# --- YouTube ------------------------------------------------------------------------

def youtube_queries() -> list[str]:
    y = tcfg()["youtube"]
    qs = list(y.get("queries", []))
    if y.get("add_anime_queries", True):
        animes = scfg()["animes"]
        start = int(datetime.now(timezone.utc).timestamp() // 86400) % max(1, len(animes))   # tourne chaque jour
        qs += [f"{a} facts" for a in (animes[start:] + animes[:start])]
    return qs[: int(y.get("queries_per_run", 6))]


def fetch_youtube() -> int:
    y = tcfg()["youtube"]
    yt = youtube.service()
    after = (datetime.now(timezone.utc) - timedelta(days=int(y.get("days", 7)))).strftime("%Y-%m-%dT%H:%M:%SZ")
    added = 0
    for q in youtube_queries():
        why = quota.affordable(["search.list", "videos.list"])
        if why:
            log.warning("veille YouTube interrompue : %s", why)
            break
        res = youtube._call("search.list", None, lambda q=q: yt.search().list(
            part="id", q=q, type="video", videoDuration="short", order="viewCount", publishedAfter=after,
            maxResults=25, regionCode=y.get("region", "US"), relevanceLanguage="en").execute())
        ids = [it["id"]["videoId"] for it in res.get("items", []) if it.get("id", {}).get("videoId")]
        if not ids:
            continue
        vids = youtube._call("videos.list", None, lambda ids=ids: yt.videos().list(
            part="snippet,statistics,contentDetails", id=",".join(ids), maxResults=50).execute())
        for v in vids.get("items", []):
            st, sn = v.get("statistics", {}), v.get("snippet", {})
            views = int(st.get("viewCount", 0))
            if views < int(y.get("min_views", 0)) or _iso_duration_s(v.get("contentDetails", {}).get("duration")) > 180:
                continue
            if db.one("SELECT 1 AS x FROM trends WHERE external_id=?", (f"yt:{v['id']}",)):
                db.execute("UPDATE trends SET views=?, likes=?, comments=?, score=? WHERE external_id=?",
                           (views, int(st.get("likeCount", 0)), int(st.get("commentCount", 0)),
                            score(views, int(st.get("likeCount", 0)), sn.get("publishedAt")), f"yt:{v['id']}"))
                continue
            db.insert("trends", platform="youtube", origin="api", external_id=f"yt:{v['id']}",
                      url=f"https://youtube.com/shorts/{v['id']}", author=sn.get("channelTitle"),
                      title=sn.get("title"), caption=(sn.get("description") or "")[:1000],
                      thumb_url=f"https://i.ytimg.com/vi/{v['id']}/mqdefault.jpg",
                      views=views, likes=int(st.get("likeCount", 0)), comments=int(st.get("commentCount", 0)),
                      published_at=sn.get("publishedAt"), query=q,
                      score=score(views, int(st.get("likeCount", 0)), sn.get("publishedAt")))
            added += 1
    log.info("veille YouTube : %d nouvelle(s) tendance(s)", added)
    return added


# --- Instagram (API officielle, recherche par hashtag) -----------------------------------

def fetch_instagram() -> int:
    ig = tcfg()["instagram"]
    base = ig.get("graph_base", "https://graph.facebook.com/v23.0").rstrip("/")
    uid, token = config.secret("IG_USER_ID"), config.secret("IG_FB_ACCESS_TOKEN")
    added = 0
    with httpx.Client(timeout=30) as c:
        for tag in ig.get("hashtags", []):
            r = c.get(f"{base}/ig_hashtag_search", params={"user_id": uid, "q": tag, "access_token": token})
            data = r.json().get("data") or []
            if r.status_code >= 400 or not data:
                log.warning("Instagram #%s : %s", tag, r.text[:200])
                continue
            r = c.get(f"{base}/{data[0]['id']}/top_media", params={
                "user_id": uid, "access_token": token, "limit": 50,
                "fields": "id,caption,media_type,like_count,comments_count,permalink,timestamp"})
            for m in r.json().get("data", []):
                if m.get("media_type") != "CAROUSEL_ALBUM":
                    continue
                ext = f"ig:{m['id']}"
                if db.one("SELECT 1 AS x FROM trends WHERE external_id=?", (ext,)):
                    continue
                likes = m.get("like_count")
                db.insert("trends", platform="instagram", origin="api", external_id=ext, url=m.get("permalink"),
                          caption=(m.get("caption") or "")[:1500], likes=likes, comments=m.get("comments_count"),
                          published_at=m.get("timestamp"), query=f"#{tag}",
                          score=score((likes or 0) * 30, likes, m.get("timestamp")))   # pas de vues : likes × 30
                added += 1
    log.info("veille Instagram : %d nouvelle(s) tendance(s)", added)
    return added


# --- captures d'écran (TikTok & co) ---------------------------------------------------

SHOT_SYSTEM = """You analyse a screenshot of a social media post (usually a TikTok, Instagram or YouTube \
Shorts photo slideshow) for an anime slideshow account doing trend research.
Read everything visible: the slide text (hook), caption, hashtags, account name, and the view/like/comment \
counts if shown (copy them exactly as displayed, e.g. "1.2M"). Identify the anime if you can. Describe the \
FORMAT generically (ranking, facts, recommendations, quiz, comparison, story, meme…) and summarise the topic \
in one line. Never invent numbers that are not visible."""

SHOT_SCHEMA = {"type": "object", "properties": {
    "is_post": {"type": "boolean"}, "platform": {"type": "string", "enum": ["tiktok", "instagram", "youtube", "other"]},
    "slideshow_like": {"type": "boolean", "description": "photo carousel / slideshow (vs. video edit, live…)"},
    "anime": {"type": "string"}, "format": {"type": "string"}, "topic": {"type": "string"},
    "hook": {"type": "string", "description": "text on the first visible slide"},
    "caption": {"type": "string"}, "author": {"type": "string"},
    "views": {"type": "string"}, "likes": {"type": "string"}, "comments": {"type": "string"},
    "why": {"type": "string", "description": "one sentence: why it probably performs"}},
    "required": ["is_post", "platform", "slideshow_like", "format", "topic"]}


def shots_dir() -> Path:
    d = config.data_dir() / "trends"
    d.mkdir(parents=True, exist_ok=True)
    return d


def import_screenshot(src: Path, original_name: str = "") -> int:
    """Copie la capture, la fait lire par Claude, l'enregistre comme tendance. Rend l'id."""
    tid = db.insert("trends", platform="other", origin="screenshot", status="new", title=original_name or src.name)
    dest = shots_dir() / f"{tid}{src.suffix.lower() or '.png'}"
    shutil.copyfile(src, dest)
    db.update("trends", tid, image_path=str(dest))
    analyze_screenshot(tid)
    return tid


def analyze_screenshot(tid: int) -> None:
    t = db.get("trends", tid)
    try:
        out = llm.structured(model=scfg()["model"], system=SHOT_SYSTEM,
                             user=[llm.image_block(t["image_path"], max_side=1400),
                                   {"type": "text", "text": "Analyse this post."}],
                             tool_name="store_post", tool_desc="Store what the post shows.", schema=SHOT_SCHEMA,
                             max_tokens=800)
    except Exception as e:
        db.update("trends", tid, status="failed", error=str(e)[:1000])
        raise
    if not out.get("is_post"):
        db.update("trends", tid, status="irrelevant", why="pas un post reconnu")
        return
    views, likes = parse_count(out.get("views")), parse_count(out.get("likes"))
    db.update("trends", tid, status="analyzed", platform=out.get("platform", "other"),
              slideshow_like=int(bool(out.get("slideshow_like"))), anime=out.get("anime") or None,
              format=out.get("format"), topic=out.get("topic"), hook=out.get("hook"), why=out.get("why"),
              caption=out.get("caption"), author=out.get("author"), views=views, likes=likes,
              comments=parse_count(out.get("comments")),
              score=score(views or (likes or 0) * 30, likes, None) if (views or likes) else None)


# --- analyse des tendances API (titres / légendes) ------------------------------------

BATCH_SYSTEM = """You classify trending short-form anime posts for an English anime PHOTO-SLIDESHOW account.
For each post (title/caption + stats) say: the anime (or "Mixed"/"" if none), the content format \
(ranking, facts, recommendations, quiz, comparison, story, edit, meme, news, other), a one-line topic, the \
hook pattern it uses (generic, e.g. "Top N … — #1 will surprise you"), whether its IDEA could be turned into a \
photo slideshow (slideshow_like), and why it performs (one short sentence)."""

BATCH_SCHEMA = {"type": "object", "properties": {"items": {"type": "array", "items": {"type": "object", "properties": {
    "id": {"type": "integer"}, "anime": {"type": "string"}, "format": {"type": "string"}, "topic": {"type": "string"},
    "hook": {"type": "string"}, "slideshow_like": {"type": "boolean"}, "why": {"type": "string"}},
    "required": ["id", "format", "topic", "slideshow_like"]}}}, "required": ["items"]}


def analyze_pending(batch: int = 30) -> int:
    rows = db.query("SELECT * FROM trends WHERE status='new' AND origin='api' ORDER BY score DESC LIMIT ?", (batch,))
    if not rows:
        return 0
    lines = [f"[{r['id']}] {r['platform']} · {r['views'] or '?'} views · {r['likes'] or '?'} likes\n"
             f"title: {r['title'] or ''}\ncaption: {(r['caption'] or '')[:300]}" for r in rows]
    out = llm.structured(model=scfg()["model"], system=BATCH_SYSTEM, user="\n\n".join(lines),
                         tool_name="classify_posts", tool_desc="Store the classification.", schema=BATCH_SCHEMA,
                         max_tokens=6000)
    by_id = {int(i["id"]): i for i in out.get("items", []) if "id" in i}
    for r in rows:
        i = by_id.get(r["id"])
        if not i:
            continue
        rel = bool(i.get("slideshow_like"))
        db.update("trends", r["id"], status="analyzed" if rel else "irrelevant", anime=i.get("anime") or None,
                  format=i.get("format"), topic=i.get("topic"), hook=i.get("hook"), why=i.get("why"),
                  slideshow_like=int(rel))
    return len(by_id)


# --- YouTube « lu en vrai » : couverture + commentaires ----------------------------------

DEEP_SYSTEM = """You study ONE trending YouTube Short for an English anime PHOTO-SLIDESHOW account.
You get its cover image (the official thumbnail, usually the first frame), title, description, stats and \
the most relevant viewer comments. Read the text visible on the cover: that is the real hook. Then say \
what the audience reacts to in the comments: what they agree with, argue about, ask for next, or say is \
missing — this is the gold for our own posts. Be concrete (names, claims), never invent."""

DEEP_SCHEMA = {"type": "object", "properties": {
    "hook": {"type": "string", "description": "text on the cover, or the title hook if the cover has no text"},
    "format": {"type": "string"}, "topic": {"type": "string"},
    "slideshow_like": {"type": "boolean", "description": "could its idea be a photo slideshow"},
    "why": {"type": "string", "description": "one sentence: why it performs"},
    "audience": {"type": "string", "description": "1-2 sentences: what viewers react to, debate or request"}},
    "required": ["hook", "format", "topic", "slideshow_like", "why", "audience"]}


def _yt_id(row: dict) -> str:
    return (row.get("external_id") or "").removeprefix("yt:")


def fetch_comments(video_id: str, n: int = 20) -> list[str]:
    from googleapiclient.errors import HttpError

    if quota.affordable(["commentThreads.list"]):
        return []
    yt = youtube.service()
    try:
        res = youtube._call("commentThreads.list", None, lambda: yt.commentThreads().list(
            part="snippet", videoId=video_id, order="relevance", maxResults=n, textFormat="plainText").execute())
    except HttpError as e:                     # commentaires désactivés, vidéo retirée…
        log.info("commentaires %s indisponibles : %s", video_id, youtube._reason(e) or e)
        return []
    out = []
    for it in res.get("items", []):
        sn = it.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
        txt = " ".join(str(sn.get("textDisplay", "")).split())
        if txt:
            out.append(f"({sn.get('likeCount', 0)} likes) {txt[:300]}")
    return out


def fetch_cover(video_id: str, dest: Path) -> Path | None:
    """Miniature officielle du Short (verticale si dispo). Rien n'est téléchargé de la vidéo elle-même."""
    with httpx.Client(timeout=20, follow_redirects=True) as c:
        for name in ("oardefault.jpg", "hqdefault.jpg"):
            try:
                r = c.get(f"https://i.ytimg.com/vi/{video_id}/{name}")
            except httpx.HTTPError:
                continue
            if r.status_code == 200 and len(r.content) > 2000:
                dest.write_bytes(r.content)
                return dest
    return None


def deep_analyze(tid: int) -> None:
    t = db.get("trends", tid)
    vid = _yt_id(t)
    cover = fetch_cover(vid, shots_dir() / f"yt_{tid}.jpg")
    comments = fetch_comments(vid)
    text = (f"Title: {t['title'] or ''}\nDescription: {(t['caption'] or '')[:500]}\n"
            f"Stats: {t['views'] or '?'} views, {t['likes'] or '?'} likes, {t['comments'] or '?'} comments\n\n"
            "Top comments:\n" + ("\n".join(f"- {c}" for c in comments) or "(none available)"))
    user = ([llm.image_block(cover, max_side=900)] if cover else []) + [{"type": "text", "text": text}]
    out = llm.structured(model=scfg()["model"], system=DEEP_SYSTEM, user=user, tool_name="store_study",
                         tool_desc="Store the study.", schema=DEEP_SCHEMA, max_tokens=900)
    rel = bool(out.get("slideshow_like"))
    db.update("trends", tid, deep=1, image_path=str(cover) if cover else t["image_path"],
              hook=out.get("hook") or t["hook"], format=out.get("format") or t["format"],
              topic=out.get("topic") or t["topic"], why=out.get("why") or t["why"],
              audience=out.get("audience"), slideshow_like=int(rel), status="analyzed" if rel else "irrelevant")


def deep_pending(k: int | None = None) -> int:
    k = int(k if k is not None else tcfg()["youtube"].get("deep", 8))
    rows = db.query("SELECT id FROM trends WHERE platform='youtube' AND status='analyzed' AND slideshow_like=1 "
                    "AND deep=0 ORDER BY COALESCE(score,0) DESC LIMIT ?", (k,))
    n = 0
    for r in rows:
        try:
            deep_analyze(r["id"])
            n += 1
        except quota.QuotaBlocked:
            break
        except Exception as e:
            log.warning("étude du Short %s : %s", r["id"], e)
            db.update("trends", r["id"], deep=1, error=str(e)[:500])
    return n


# --- AniList : ce que les fans regardent cette semaine -----------------------------------

ANILIST_QUERY = """query ($n: Int) { Page(perPage: $n) { media(type: ANIME, sort: TRENDING_DESC, isAdult: false) {
  title { english romaji } trending popularity
  characters(sort: FAVOURITES_DESC, perPage: 5) { nodes { name { full } } } } } }"""


def fetch_anilist() -> int:
    a = tcfg().get("anilist", {})
    r = httpx.post("https://graphql.anilist.co", json={"query": ANILIST_QUERY, "variables": {"n": int(a.get("top", 15))}},
                   headers={"Accept": "application/json"}, timeout=30)
    r.raise_for_status()
    items = []
    for m in (r.json().get("data") or {}).get("Page", {}).get("media", []):
        t = m.get("title") or {}
        items.append({"anime": t.get("english") or t.get("romaji") or "?", "trending": m.get("trending") or 0,
                      "characters": [c["name"]["full"] for c in (m.get("characters") or {}).get("nodes", [])
                                     if (c.get("name") or {}).get("full")]})
    db.meta_set("anilist", json.dumps({"at": db.now(), "items": items}))
    return len(items)


def anilist() -> dict:
    raw = db.meta_get("anilist")
    return json.loads(raw) if raw else {"at": None, "items": []}


def anilist_prompt() -> str:
    items = anilist()["items"]
    if not items:
        return ""
    return "\n".join(f"- {i['anime']}" + (f" (fan favourites: {', '.join(i['characters'])})" if i["characters"] else "")
                     for i in items)


def refresh() -> list[str]:
    """Actualise toutes les sources configurées puis analyse. Rend un petit rapport."""
    rep = []
    if tcfg()["youtube"].get("enabled", True):
        try:
            rep.append(f"YouTube : {fetch_youtube()} nouvelle(s)")
        except Exception as e:
            rep.append(f"YouTube : {e}")
    if tcfg()["instagram"].get("enabled"):
        try:
            rep.append(f"Instagram : {fetch_instagram()} nouvelle(s)")
        except Exception as e:
            rep.append(f"Instagram : {e}")
    if tcfg().get("anilist", {}).get("enabled", True):
        try:
            rep.append(f"AniList : {fetch_anilist()} animes en tendance")
        except Exception as e:
            rep.append(f"AniList : {e}")
    n = 0
    while True:
        k = analyze_pending()
        n += k
        if not k:
            break
    rep.append(f"{n} analysée(s) par Claude")
    if tcfg()["youtube"].get("enabled", True):
        rep.append(f"{deep_pending()} Short(s) lus en vrai (couverture + commentaires)")
    db.meta_set("trends_refresh", db.now())
    return rep


def last_refresh() -> str | None:
    return db.meta_get("trends_refresh")


def due_for_refresh() -> bool:
    last = last_refresh()
    if not last:
        return True
    return datetime.now(timezone.utc) - datetime.fromisoformat(last) > timedelta(hours=float(tcfg()["refresh_hours"]))


def top(n: int | None = None, anime: str | None = None) -> list[dict]:
    since = (datetime.now(timezone.utc) - timedelta(days=int(tcfg().get("keep_days", 30)))).isoformat()
    rows = db.query("SELECT * FROM trends WHERE status='analyzed' AND slideshow_like=1 AND created_at >= ? "
                    "ORDER BY COALESCE(score, 0) DESC, id DESC", (since,))
    if anime:
        from .library import norm
        rows = [r for r in rows if norm(r["anime"]) == norm(anime)] or rows
    return rows[: int(n or tcfg().get("inspire_top", 15))]


def as_prompt(rows: list[dict]) -> str:
    out = []
    for r in rows:
        stats = ", ".join(x for x in [f"{r['views']:,} views" if r["views"] else "",
                                      f"{r['likes']:,} likes" if r["likes"] else ""] if x)
        out.append(f"- [{r['platform']}] {r['anime'] or '?'} · {r['format']} · {r['topic']}"
                   f"{' · hook: ' + r['hook'] if r['hook'] else ''}{' (' + stats + ')' if stats else ''}"
                   f"{' · audience: ' + r['audience'] if r.get('audience') else ''}")
    return "\n".join(out)
