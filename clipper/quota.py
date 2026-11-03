"""Comptabilité du quota YouTube par seau, en jour Pacifique (remise à zéro YouTube à minuit PT)."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from . import config, db

PT = ZoneInfo("America/Los_Angeles")


class QuotaBlocked(Exception):
    """Plus assez de quota aujourd'hui : on s'arrête, la file reste intacte."""


def pt_day(at: datetime | None = None) -> str:
    return (at or datetime.now(PT)).astimezone(PT).date().isoformat()


def cost(method: str) -> tuple[str, int]:
    bucket, units = config.get()["quota"]["costs"][method]
    return str(bucket), int(units)


def limit(bucket: str) -> int:
    return int(config.get()["quota"]["buckets"][bucket])


def used(bucket: str, day: str | None = None) -> int:
    r = db.one("SELECT COALESCE(SUM(units),0) AS u FROM quota_log WHERE pt_day=? AND bucket=?",
               (day or pt_day(), bucket))
    return int(r["u"])


def blocked(bucket: str, day: str | None = None) -> bool:
    return db.one("SELECT 1 AS x FROM quota_block WHERE pt_day=? AND bucket=?", (day or pt_day(), bucket)) is not None


def remaining(bucket: str) -> int:
    return 0 if blocked(bucket) else max(0, limit(bucket) - used(bucket))


def record(method: str, clip_id: int | None = None, ok: bool = True) -> None:
    bucket, units = cost(method)
    db.execute("INSERT INTO quota_log (pt_day,bucket,method,units,clip_id,ok,at) VALUES (?,?,?,?,?,?,?)",
               (pt_day(), bucket, method, units, clip_id, int(ok), db.now()))


def block(bucket: str) -> None:
    db.execute("INSERT OR IGNORE INTO quota_block (pt_day,bucket,at) VALUES (?,?,?)", (pt_day(), bucket, db.now()))


def uploads_today() -> int:
    r = db.one("SELECT COUNT(*) AS n FROM quota_log WHERE pt_day=? AND method='videos.insert' AND ok=1", (pt_day(),))
    return int(r["n"])


def per_clip_methods(with_playlist: bool) -> list[str]:
    return ["videos.insert", "thumbnails.set"] + (["playlistItems.insert"] if with_playlist else [])


def affordable(methods: list[str]) -> str | None:
    """None si on peut payer ces appels, sinon la raison en clair."""
    need: dict[str, int] = {}
    for m in methods:
        b, u = cost(m)
        need[b] = need.get(b, 0) + u
    for b, u in need.items():
        if blocked(b):
            return f"YouTube a signalé le quota « {b} » épuisé aujourd'hui"
        if remaining(b) < u:
            return f"quota « {b} » insuffisant : {remaining(b)} restant, {u} nécessaire"
    return None


def clips_left_today(with_playlist: bool = True) -> int:
    """Combien de clips complets on peut encore uploader aujourd'hui (quota YouTube + plafond perso)."""
    need: dict[str, int] = {}
    for m in per_clip_methods(with_playlist):
        b, u = cost(m)
        need[b] = need.get(b, 0) + u
    by_quota = min(remaining(b) // u for b, u in need.items())
    cap = int(config.get()["publish"].get("max_uploads_per_day", 10**6))
    return max(0, min(by_quota, cap - uploads_today()))


def summary() -> dict:
    day = pt_day()
    buckets = {b: {"limit": limit(b), "used": used(b, day), "remaining": remaining(b), "blocked": blocked(b, day)}
               for b in config.get()["quota"]["buckets"]}
    return {"pt_day": day, "buckets": buckets, "uploads_today": uploads_today(),
            "cap": int(config.get()["publish"].get("max_uploads_per_day", 0)),
            "clips_left_today": clips_left_today()}
