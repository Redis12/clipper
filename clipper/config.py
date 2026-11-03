"""Chargement de config.yaml et .env. Un seul objet global, rechargé à la demande."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(os.environ.get("CLIPPER_ROOT", Path.cwd()))
_cfg: dict[str, Any] | None = None


def load(path: Path | None = None) -> dict[str, Any]:
    """Lit config.yaml (et .env) depuis le dossier courant ou CLIPPER_ROOT."""
    global _cfg
    load_dotenv(ROOT / ".env")
    p = path or Path(os.environ.get("CLIPPER_CONFIG", ROOT / "config.yaml"))
    if not p.exists():
        raise FileNotFoundError(f"config.yaml introuvable : {p}. Lance clipper depuis le dossier du projet.")
    with open(p, encoding="utf-8") as f:
        _cfg = yaml.safe_load(f) or {}
    return _cfg


def get() -> dict[str, Any]:
    return _cfg if _cfg is not None else load()


def set_for_tests(cfg: dict[str, Any]) -> None:
    global _cfg
    _cfg = cfg


def data_dir() -> Path:
    d = Path(get()["paths"]["data"])
    if not d.is_absolute():
        d = ROOT / d
    d.mkdir(parents=True, exist_ok=True)
    return d


def video_dir(video_id: str) -> Path:
    d = data_dir() / "videos" / video_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def clip_dir(clip_id: int) -> Path:
    d = data_dir() / "clips" / str(clip_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def secret(name: str, required: bool = True) -> str:
    v = os.environ.get(name, "").strip()
    if required and not v:
        raise RuntimeError(f"{name} manquant dans .env")
    return v
