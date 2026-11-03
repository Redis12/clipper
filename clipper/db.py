"""État persistant en SQLite. Accès simple par fonctions, une connexion par thread."""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any, Iterable

from . import config

MIGRATIONS: list[str] = [
    # 1 : schéma initial
    """
    CREATE TABLE videos (
        id TEXT PRIMARY KEY,
        url TEXT NOT NULL,
        title TEXT, channel TEXT, channel_id TEXT,
        duration REAL, upload_date TEXT, description TEXT,
        chapters TEXT,                -- JSON
        source_path TEXT, proxy_path TEXT, transcript_path TEXT,
        status TEXT NOT NULL DEFAULT 'new',   -- new|ingested|transcribed|selected|review|failed
        step TEXT,                    -- étape en cours (pour l'affichage)
        error TEXT,
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    );
    CREATE TABLE clips (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        video_id TEXT NOT NULL REFERENCES videos(id),
        rank INTEGER,
        start REAL NOT NULL, end REAL NOT NULL,
        sel_start REAL, sel_end REAL,   -- bornes proposées par la sélection (avant ajustement manuel)
        first_sentence INTEGER, last_sentence INTEGER,
        topic TEXT, score INTEGER, reason TEXT,
        status TEXT NOT NULL DEFAULT 'pending',
        reject_reason TEXT,
        titles TEXT,                    -- JSON list[str]
        title_idx INTEGER DEFAULT 0,
        description TEXT, tags TEXT,    -- tags : JSON list[str]
        thumb_text TEXT,
        frames TEXT,                    -- JSON list[{path,t,sharp,face}]
        frame_idx INTEGER,
        clip_path TEXT, thumb_path TEXT,
        render_needed INTEGER NOT NULL DEFAULT 1,
        publish_at TEXT,                -- UTC ISO
        youtube_id TEXT, thumb_done INTEGER DEFAULT 0, playlist_done INTEGER DEFAULT 0,
        error TEXT,
        approved_at TEXT, uploaded_at TEXT,
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    );
    CREATE INDEX clips_video ON clips(video_id);
    CREATE INDEX clips_status ON clips(status);
    CREATE TABLE quota_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pt_day TEXT NOT NULL,           -- jour en heure du Pacifique (remise à zéro YouTube)
        bucket TEXT NOT NULL, method TEXT NOT NULL, units INTEGER NOT NULL,
        clip_id INTEGER, ok INTEGER NOT NULL DEFAULT 1, at TEXT NOT NULL
    );
    CREATE INDEX quota_day ON quota_log(pt_day, bucket);
    CREATE TABLE quota_block (          -- YouTube a répondu quotaExceeded : seau bloqué pour le jour
        pt_day TEXT NOT NULL, bucket TEXT NOT NULL, at TEXT NOT NULL,
        PRIMARY KEY (pt_day, bucket)
    );
    """,
    # 2 : slideshows
    """
    CREATE TABLE slideshows (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        anime TEXT, format TEXT,
        topic TEXT NOT NULL, hook TEXT, angle TEXT, why TEXT,
        score INTEGER, origin TEXT NOT NULL DEFAULT 'claude',   -- claude | user
        status TEXT NOT NULL DEFAULT 'idea',  -- idea|queued|drafting|review|approved|rejected|failed|published
        step TEXT,
        slides TEXT,                 -- JSON [{kind, label, text, character, scene, confidence, image_path, alts}]
        caption TEXT, hashtags TEXT, -- hashtags : JSON list
        yt_title TEXT, yt_description TEXT,
        video_path TEXT, render_needed INTEGER NOT NULL DEFAULT 1,
        publish_at TEXT,
        error TEXT,
        approved_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    );
    CREATE INDEX slideshows_status ON slideshows(status);
    CREATE TABLE posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slideshow_id INTEGER NOT NULL REFERENCES slideshows(id),
        platform TEXT NOT NULL,      -- youtube | instagram | tiktok
        mode TEXT NOT NULL,          -- auto | manual (pack à poster soi-même)
        status TEXT NOT NULL DEFAULT 'scheduled',  -- scheduled | done | failed | cancelled
        publish_at TEXT, remote_id TEXT, url TEXT, error TEXT, attempts INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        UNIQUE (slideshow_id, platform)
    );
    CREATE TABLE images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        path TEXT NOT NULL UNIQUE,
        anime TEXT NOT NULL, character TEXT,    -- personnage = sous-dossier (NULL pour les captures)
        origin TEXT NOT NULL,                   -- library | frames
        width INTEGER, height INTEGER, sharp REAL, ahash TEXT,
        use_count INTEGER NOT NULL DEFAULT 0, last_used_at TEXT,
        created_at TEXT NOT NULL
    );
    CREATE INDEX images_anime ON images(anime);
    CREATE TABLE sources (              -- épisodes / trailers dont on extrait des images
        id TEXT PRIMARY KEY, url TEXT NOT NULL, anime TEXT NOT NULL, title TEXT,
        status TEXT NOT NULL DEFAULT 'new', n_frames INTEGER, error TEXT,
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    );
    """,
    # 3 : veille des tendances
    """
    CREATE TABLE trends (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform TEXT NOT NULL,          -- youtube | instagram | tiktok | autre
        origin TEXT NOT NULL,            -- api | screenshot
        external_id TEXT UNIQUE,         -- id YouTube / Instagram (NULL pour les captures)
        url TEXT, author TEXT, title TEXT, caption TEXT, thumb_url TEXT, image_path TEXT,
        views INTEGER, likes INTEGER, comments INTEGER, published_at TEXT,
        query TEXT,                      -- recherche ou hashtag d'origine
        status TEXT NOT NULL DEFAULT 'new',   -- new | analyzed | irrelevant | failed
        anime TEXT, format TEXT, topic TEXT, hook TEXT, why TEXT, slideshow_like INTEGER,
        score REAL, error TEXT,
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    );
    CREATE INDEX trends_status ON trends(status);
    ALTER TABLE slideshows ADD COLUMN inspiration TEXT;
    CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
    """,
    # 4 : tri automatique des captures par personnage
    """
    ALTER TABLE images ADD COLUMN tagged INTEGER NOT NULL DEFAULT 0;
    """,
    # 5 : analyse approfondie des tendances (couverture + commentaires)
    """
    ALTER TABLE trends ADD COLUMN audience TEXT;
    ALTER TABLE trends ADD COLUMN deep INTEGER NOT NULL DEFAULT 0;
    """,
    # 6 : logo de l'anime sur le graphique des notes (case à cocher)
    """
    ALTER TABLE slideshows ADD COLUMN use_logo INTEGER NOT NULL DEFAULT 1;
    """,
]

JSON_FIELDS = {"titles", "tags", "frames", "chapters", "slides", "hashtags"}
_local = threading.local()


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def conn() -> sqlite3.Connection:
    c = getattr(_local, "conn", None)
    path = config.data_dir() / "clipper.sqlite"
    if c is None or getattr(_local, "path", None) != path:
        c = sqlite3.connect(path, timeout=30, isolation_level=None)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA foreign_keys=ON")
        c.execute("PRAGMA busy_timeout=30000")
        _local.conn, _local.path = c, path
        migrate(c)
    return c


def reset_connection() -> None:
    c = getattr(_local, "conn", None)
    if c is not None:
        c.close()
    _local.conn = None


def migrate(c: sqlite3.Connection) -> None:
    v = c.execute("PRAGMA user_version").fetchone()[0]
    for i, sql in enumerate(MIGRATIONS[v:], start=v + 1):
        c.executescript("BEGIN;" + sql + f";PRAGMA user_version={i};COMMIT;")


def _decode(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    d = dict(row)
    for k in JSON_FIELDS & d.keys():
        if d[k] is not None:
            d[k] = json.loads(d[k])
    return d


def _encode(values: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for k, v in values.items():
        out[k] = json.dumps(v, ensure_ascii=False) if k in JSON_FIELDS and v is not None else v
    return out


def query(sql: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
    return [_decode(r) for r in conn().execute(sql, tuple(params)).fetchall()]


def one(sql: str, params: Iterable[Any] = ()) -> dict[str, Any] | None:
    return _decode(conn().execute(sql, tuple(params)).fetchone())


def execute(sql: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
    return conn().execute(sql, tuple(params))


# --- vidéos -------------------------------------------------------------------

def get_video(video_id: str) -> dict[str, Any] | None:
    return one("SELECT * FROM videos WHERE id=?", (video_id,))


def insert_video(video_id: str, url: str, **fields: Any) -> bool:
    """Retourne False si la vidéo existe déjà (jamais retraitée)."""
    if get_video(video_id):
        return False
    t = now()
    vals = _encode({"id": video_id, "url": url, "created_at": t, "updated_at": t, **fields})
    cols = ",".join(vals)
    execute(f"INSERT INTO videos ({cols}) VALUES ({','.join('?' * len(vals))})", vals.values())
    return True


def update_video(video_id: str, **fields: Any) -> None:
    vals = _encode({**fields, "updated_at": now()})
    sets = ",".join(f"{k}=?" for k in vals)
    execute(f"UPDATE videos SET {sets} WHERE id=?", [*vals.values(), video_id])


# --- clips --------------------------------------------------------------------

def get_clip(clip_id: int) -> dict[str, Any] | None:
    return one("SELECT * FROM clips WHERE id=?", (clip_id,))


def clips_for(video_id: str, statuses: Iterable[str] | None = None) -> list[dict[str, Any]]:
    if statuses:
        st = list(statuses)
        return query(
            f"SELECT * FROM clips WHERE video_id=? AND status IN ({','.join('?' * len(st))}) ORDER BY score DESC, start",
            [video_id, *st],
        )
    return query("SELECT * FROM clips WHERE video_id=? ORDER BY score DESC, start", (video_id,))


def insert_clip(video_id: str, **fields: Any) -> int:
    t = now()
    vals = _encode({"video_id": video_id, "created_at": t, "updated_at": t, **fields})
    cur = execute(
        f"INSERT INTO clips ({','.join(vals)}) VALUES ({','.join('?' * len(vals))})", vals.values()
    )
    return int(cur.lastrowid)


def update_clip(clip_id: int, **fields: Any) -> None:
    vals = _encode({**fields, "updated_at": now()})
    sets = ",".join(f"{k}=?" for k in vals)
    execute(f"UPDATE clips SET {sets} WHERE id=?", [*vals.values(), clip_id])


# --- helpers génériques ---------------------------------------------------------

def insert(table: str, **fields: Any) -> int:
    t = now()
    vals = _encode({"created_at": t, **({"updated_at": t} if table != "images" else {}), **fields})
    cur = execute(f"INSERT INTO {table} ({','.join(vals)}) VALUES ({','.join('?' * len(vals))})", vals.values())
    return int(cur.lastrowid)


def update(table: str, row_id: Any, **fields: Any) -> None:
    vals = _encode({**fields, **({"updated_at": now()} if table != "images" else {})})
    execute(f"UPDATE {table} SET {','.join(f'{k}=?' for k in vals)} WHERE id=?", [*vals.values(), row_id])


def get(table: str, row_id: Any) -> dict[str, Any] | None:
    return one(f"SELECT * FROM {table} WHERE id=?", (row_id,))


def meta_get(key: str) -> str | None:
    r = one("SELECT value FROM meta WHERE key=?", (key,))
    return r["value"] if r else None


def meta_set(key: str, value: str) -> None:
    execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (key, value))
