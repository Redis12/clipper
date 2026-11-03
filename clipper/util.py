"""Petits outils partagés : ffmpeg, timecodes, verrous de fichiers, journalisation."""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

log = logging.getLogger("clipper")


def setup_logging(verbose: bool = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-5s %(message)s",
        datefmt="%H:%M:%S",
    )


def require_bin(name: str) -> str:
    p = shutil.which(name)
    if not p:
        raise RuntimeError(f"{name} introuvable dans le PATH. Installe-le (voir README).")
    return p


def run(cmd: list[str], *, capture: bool = True, check: bool = True) -> subprocess.CompletedProcess:
    log.debug("$ %s", " ".join(cmd))
    p = subprocess.run(cmd, capture_output=capture, text=True, encoding="utf-8", errors="replace")
    if check and p.returncode != 0:
        tail = (p.stderr or "")[-1500:]
        raise RuntimeError(f"{Path(cmd[0]).name} a échoué (code {p.returncode}) :\n{tail}")
    return p


def ffprobe(path: Path) -> dict:
    p = run([require_bin("ffprobe"), "-v", "error", "-print_format", "json",
             "-show_format", "-show_streams", str(path)])
    return json.loads(p.stdout)


def video_stream(info: dict) -> dict | None:
    return next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)


def tc(seconds: float, ms: bool = False) -> str:
    """12.3 -> '0:12' ; 3725.4 -> '1:02:05'."""
    s = max(0.0, float(seconds))
    h, rem = divmod(int(s), 3600)
    m, sec = divmod(rem, 60)
    base = f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"
    if ms:
        base += f".{int(round((s - int(s)) * 10)) % 10}"
    return base


def pid_alive(pid: int) -> bool:
    """Le processus existe-t-il encore ? (Sans le tuer : sous Windows, os.kill(pid, 0) le terminerait.)"""
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        k32 = ctypes.windll.kernel32
        h = k32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        code = ctypes.c_ulong()
        ok = k32.GetExitCodeProcess(h, ctypes.byref(code))
        k32.CloseHandle(h)
        return bool(ok) and code.value == 259  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _lock_is_stale(path: Path, stale_after: float) -> bool:
    if time.time() - path.stat().st_mtime > stale_after:
        return True
    try:
        pid = int(path.read_text(encoding="utf-8").strip() or 0)
    except (OSError, ValueError):
        return True
    # Laissé par un processus arrêté (Ctrl+C, PC éteint…), ou par nous-mêmes avant un redémarrage.
    return not pid_alive(pid)


@contextmanager
def file_lock(path: Path, stale_after: float = 6 * 3600) -> Iterator[bool]:
    """Verrou exclusif par fichier. Rend False si un autre processus vivant travaille déjà dessus."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and _lock_is_stale(path, stale_after):
        path.unlink(missing_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        yield False
        return
    try:
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        yield True
    finally:
        path.unlink(missing_ok=True)


def safe_replace(tmp: Path, target: Path, attempts: int = 20, wait: float = 0.25) -> None:
    """os.replace qui tolère Windows : un fichier ouvert ailleurs (lecteur vidéo, navigateur, antivirus)
    ne peut pas être remplacé. On réessaie quelques secondes avant d'abandonner avec un message clair."""
    for i in range(attempts):
        try:
            os.replace(tmp, target)
            return
        except PermissionError:
            if i == attempts - 1:
                raise PermissionError(
                    f"Impossible de remplacer {target.name} : le fichier est ouvert ailleurs "
                    "(lecteur, onglet du navigateur, antivirus). Ferme-le puis réessaie.") from None
            time.sleep(wait)


def atomic_write_json(path: Path, data) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    safe_replace(tmp, path)
