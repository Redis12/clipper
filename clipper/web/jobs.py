"""Files de travail en arrière-plan : une par « voie », traitées chacune dans l'ordre par son propre fil.
Deux voies : les vidéos (ffmpeg lourd) et les slideshows (rapides), pour qu'une longue vidéo ne bloque pas
la génération d'idées ou de slides."""
from __future__ import annotations

import queue
import threading
import traceback
from typing import Any, Callable

from ..util import log

LANES = ("video", "slides")
_queues: dict[str, "queue.Queue[tuple[str, Callable[[], Any]]]"] = {l: queue.Queue() for l in LANES}
current: dict[str, str | None] = {l: None for l in LANES}
_started = False


def enqueue(label: str, fn: Callable[[], Any], lane: str = "video") -> None:
    _queues[lane].put((label, fn))


def waiting() -> int:
    return sum(q.qsize() for q in _queues.values())


def busy_label() -> str | None:
    return " · ".join(c for c in current.values() if c) or None


def _worker(lane: str) -> None:
    q = _queues[lane]
    while True:
        label, fn = q.get()
        current[lane] = label
        try:
            fn()
        except Exception as e:
            log.error("tâche « %s » : %s\n%s", label, e, traceback.format_exc())
        finally:
            current[lane] = None
            q.task_done()


def start() -> None:
    global _started
    if _started:
        return
    _started = True
    for lane in LANES:
        threading.Thread(target=_worker, args=(lane,), daemon=True).start()
