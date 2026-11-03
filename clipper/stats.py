"""`clipper stats` : bilan des Shorts de la chaîne après 24 h, d'après la méthode vidIQ « View Jail ».

Pour chaque Short publié depuis plus de `--min-hours` heures :
  vues, vues engagées, % regardé, likes, commentaires, abonnés gagnés, courbe de rétention (API YouTube Analytics).
Puis :
  - la « prison » où il est bloqué (0 / 1k / 10k / 30k vues) et la piste d'évasion correspondante ;
  - la FUITE : la seconde exacte où la courbe chute le plus (ouverture / milieu / fin).

Lecture seule. Jeton séparé (data/stats_token.json), créé une fois par `clipper stats-auth` (ouvre le navigateur).
Rapport écrit dans library/_stats/rapport_<date>.txt (+ .json pour que Claude compare d'un jour à l'autre).
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import config
from .slides import library
from .util import log

SCOPES = ["https://www.googleapis.com/auth/youtube.readonly",
          "https://www.googleapis.com/auth/yt-analytics.readonly"]


def _token_path() -> Path:
    return config.data_dir() / "stats_token.json"


def auth() -> str:
    from google_auth_oauthlib.flow import InstalledAppFlow

    secrets = Path(config.secret("YOUTUBE_CLIENT_SECRETS"))
    if not secrets.is_absolute():
        secrets = config.ROOT / secrets
    if not secrets.exists():
        raise RuntimeError(f"Fichier OAuth introuvable : {secrets} (le même client_secret.json que pour `clipper auth`).")
    flow = InstalledAppFlow.from_client_secrets_file(str(secrets), SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")
    _token_path().write_text(creds.to_json(), encoding="utf-8")
    return str(_token_path())


def _creds():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    p = _token_path()
    if not p.exists():
        raise RuntimeError("Pas encore connecté : lance `clipper stats-auth` une fois (choisis la chaîne animelorehq).")
    creds = Credentials.from_authorized_user_info(json.loads(p.read_text(encoding="utf-8")), SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            p.write_text(creds.to_json(), encoding="utf-8")
        else:
            raise RuntimeError("Jeton invalide : relance `clipper stats-auth`.")
    return creds


def _dur(iso: str) -> float:
    m = re.fullmatch(r"P(?:\d+D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return 0.0
    h, mi, s = (int(x or 0) for x in m.groups())
    return h * 3600 + mi * 60 + s


# ---------------------------------------------------------------- diagnostic (pur, testable)

def jail(views: int) -> tuple[str, str]:
    """Prison vidIQ + piste d'évasion."""
    if views < 100:
        return ("0 vue", "Vérifier restrictions/droits dans Studio. Sinon l'ouverture fait swiper : refaire la 1re image "
                         "et la 1re phrase. Contenu « produit en masse » = prison 0 (vidIQ).")
    if views < 2500:
        return ("1k", "Les inconnus ne mordent pas. Ne pas juste poster plus : changer une chose qui compte "
                      "(format OU sujet) et rendre la prémisse de la chaîne évidente.")
    if views < 15000:
        return ("10k", "Le public de niche aime, le grand public non. Donner une raison de rester SANS connaître l'anime : "
                       "mystère, question, choix, nostalgie. Puis regarder la courbe (milieu).")
    return ("30k", "Le sujet et le format marchent : chercher la FUITE à la seconde près et resserrer.")


def leak(curve: list[tuple[float, float]], duration: float) -> dict | None:
    """Plus forte chute de la courbe (ratio de durée, part de spectateurs) → seconde + zone."""
    pts = sorted((r, w) for r, w in curve if r <= 1.0)
    if len(pts) < 3 or duration <= 0:
        return None
    best, at = 0.0, None
    for (r0, w0), (r1, w1) in zip(pts, pts[1:]):
        drop = w0 - w1
        if drop > best:
            best, at = drop, (r0, r1, w0, w1)
    if at is None:
        return None
    r0, r1, w0, w1 = at
    sec = (r0 + r1) / 2 * duration
    zone = "OUVERTURE" if sec < 3 else ("FIN" if r1 >= 0.8 else "MILIEU")
    fix = {"OUVERTURE": "l'accroche fuit : 1re image / VS plus fort, action dès la 1re seconde",
           "MILIEU": "un passage mou : couper ou accélérer autour de cette seconde",
           "FIN": "la fin annonce qu'elle finit : couper plus tôt, pas d'écran qui traîne"}[zone]
    start = pts[0][1]
    end = pts[-1][1]
    return {"second": round(sec, 1), "drop": round(best, 3), "zone": zone, "fix": fix,
            "start": round(start, 3), "end": round(end, 3)}


# ---------------------------------------------------------------- collecte

def collect(min_hours: float = 24.0, max_videos: int = 30) -> list[dict]:
    from googleapiclient.discovery import build

    creds = _creds()
    yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
    ya = build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)
    ch = yt.channels().list(part="contentDetails,snippet", mine=True).execute()["items"][0]
    uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    ids, tok = [], None
    while len(ids) < max_videos:
        r = yt.playlistItems().list(part="contentDetails", playlistId=uploads, maxResults=50, pageToken=tok).execute()
        ids += [i["contentDetails"]["videoId"] for i in r.get("items", [])]
        tok = r.get("nextPageToken")
        if not tok:
            break
    ids = ids[:max_videos]
    now = datetime.now(timezone.utc)
    out = []
    for k in range(0, len(ids), 50):
        vids = yt.videos().list(part="snippet,contentDetails,statistics,status", id=",".join(ids[k:k + 50])).execute()
        for v in vids.get("items", []):
            pub = datetime.fromisoformat(v["snippet"]["publishedAt"].replace("Z", "+00:00"))
            age_h = (now - pub).total_seconds() / 3600
            dur = _dur(v["contentDetails"]["duration"])
            if age_h < min_hours or v["status"].get("privacyStatus") != "public" or dur > 180:
                continue
            out.append({"id": v["id"], "title": v["snippet"]["title"], "published": v["snippet"]["publishedAt"],
                        "age_h": round(age_h, 1), "duration": dur,
                        "views": int(v["statistics"].get("viewCount", 0)),
                        "likes": int(v["statistics"].get("likeCount", 0)),
                        "comments": int(v["statistics"].get("commentCount", 0))})
    start = (now - timedelta(days=90)).date().isoformat()
    end = now.date().isoformat()
    for v in out:
        f = f"video=={v['id']}"
        for metrics in ("views,engagedViews,averageViewPercentage,averageViewDuration,subscribersGained",
                        "views,averageViewPercentage,averageViewDuration,subscribersGained"):
            try:
                r = ya.reports().query(ids="channel==MINE", startDate=start, endDate=end, metrics=metrics,
                                       filters=f).execute()
                if r.get("rows"):
                    row = dict(zip([h["name"] for h in r["columnHeaders"]], r["rows"][0]))
                    v["analytics_views"] = row.pop("views", 0)       # 0 alors que la vidéo a des vues = pas encore calculé
                    v.update(row)
                break
            except Exception as e:                                   # engagedViews pas dispo partout
                log.debug("analytics %s : %s", metrics, e)
        try:
            r = ya.reports().query(ids="channel==MINE", startDate=start, endDate=end,
                                   dimensions="elapsedVideoTimeRatio",
                                   metrics="audienceWatchRatio,relativeRetentionPerformance", filters=f).execute()
            v["curve"] = [(row[0], row[1]) for row in r.get("rows", [])]
            v["relative"] = [(row[0], row[2]) for row in r.get("rows", [])]
        except Exception as e:
            log.warning("courbe de rétention indisponible pour %s : %s", v["title"], e)
            v["curve"] = []
        try:
            r = ya.reports().query(ids="channel==MINE", startDate=start, endDate=end,
                                   dimensions="insightTrafficSourceType", metrics="views", filters=f).execute()
            v["sources"] = {row[0]: row[1] for row in r.get("rows", [])}
        except Exception:
            v["sources"] = {}
    return out


def report(videos: list[dict]) -> str:
    L = [f"BILAN SHORTS @animelorehq — {datetime.now().strftime('%d/%m/%Y %H:%M')}", "Méthode : vidIQ « View Jail »", ""]
    for v in sorted(videos, key=lambda x: x["published"], reverse=True):
        jn, fix = jail(v["views"])
        L.append(f"■ {v['title']}  ({v['age_h']:.0f} h, {v['duration']:.0f} s)")
        ready = bool(v.get("averageViewPercentage")) and bool(v.get("analytics_views"))   # Analytics : 48-72 h de retard
        ev = f", vues engagées {int(v['engagedViews'])}" if ready and "engagedViews" in v else ""
        pct = f"{v['averageViewPercentage']:.0f} % regardé" if ready else "% regardé pas encore calculé (48-72 h)"
        subs = f" · +{int(v.get('subscribersGained', 0))} abonnés" if ready else ""
        lr = f" ({v['likes'] / v['views'] * 100:.1f} % de likes)" if v["views"] else ""
        L.append(f"  {v['views']} vues{ev} · {pct} · {v['likes']} likes{lr} · {v['comments']} comm.{subs}")
        if v.get("sources"):
            L.append("  sources : " + ", ".join(f"{k} {n}" for k, n in sorted(v["sources"].items(), key=lambda x: -x[1])))
        L.append(f"  PRISON {jn} → {fix}")
        lk = leak(v.get("curve") or [], v["duration"])
        if lk:
            L.append(f"  FUITE à {lk['second']} s ({lk['zone']}, -{lk['drop'] * 100:.0f} pts) → {lk['fix']}")
            L.append(f"  rétention : début {lk['start'] * 100:.0f} % → fin {lk['end'] * 100:.0f} %"
                     + ("  (>100 % = les gens revoient : boucle réussie)" if lk['end'] > 1 else ""))
        else:
            L.append("  courbe de rétention pas encore calculée par YouTube (48-72 h après la publication)")
        L.append("")
    L.append("Règle vidIQ : changer UNE chose qui compte par vidéo, pas juste poster plus.")
    return "\n".join(L)


def run(min_hours: float = 24.0) -> Path:
    videos = collect(min_hours)
    d = library.root() / "_stats"
    d.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%Hh%M")
    txt = d / f"rapport_{stamp}.txt"
    txt.write_text(report(videos), encoding="utf-8")
    (d / f"rapport_{stamp}.json").write_text(json.dumps(videos, ensure_ascii=False, indent=1), encoding="utf-8")
    return txt
