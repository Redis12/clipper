"""Agrandissement IA des petites images (Real-ESRGAN, modèle anime), pour qu'elles restent nettes en plein écran.

Moteur : l'exécutable `realesrgan-ncnn-vulkan` (github.com/xinntao/Real-ESRGAN, release « ncnn-vulkan ») ou
`upscayl-bin` (livré avec Upscayl). Les deux acceptent les mêmes options (-i -o -n -s [-m]). Tourne sur la carte
graphique (Vulkan), sans Internet. Sans moteur installé : rien n'est modifié (on prévient seulement).

L'original est gardé dans library/_originals/ (dossier ignoré par la bibliothèque).
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from .. import config
from ..util import log


def ucfg() -> dict:
    return config.get()["slides"].get("upscale", {})


def binary() -> Path | None:
    """Chemin du moteur : config, sinon tools/realesrgan/, sinon le PATH."""
    c = ucfg()
    cands = [c.get("bin") or ""]
    base = config.ROOT
    for name in ("realesrgan-ncnn-vulkan", "upscayl-bin"):
        for ext in ("", ".exe"):
            cands.append(str(base / "tools" / "realesrgan" / f"{name}{ext}"))
            w = shutil.which(name + ext)
            if w:
                cands.append(w)
    for p in cands:
        if p and Path(p).is_file():
            return Path(p)
    return None


def needed(width: int, height: int) -> bool:
    c = ucfg()
    return bool(c.get("enabled", True)) and min(width, height) < int(c.get("min_side", 1080))


def upscale_file(path: Path) -> bool:
    """Agrandit l'image en place (original sauvegardé). Rend True si agrandie."""
    from PIL import Image

    from . import library

    with Image.open(path) as im:
        w, h = im.size
    if not needed(w, h):
        return False
    exe = binary()
    if not exe:
        log.warning("image %s trop petite (%dx%d) : installe Real-ESRGAN pour l'agrandir (voir CLAUDE.md)", path.name, w, h)
        return False
    c = ucfg()
    target = int(c.get("target_side", 1440))
    model = c.get("model", "realesrgan-x4plus-anime")
    # Les modèles « x4plus » ne savent faire que ×4 (on redescend ensuite à la taille visée).
    scale = 4 if "x4plus" in model or min(w, h) * 2 < target else 2
    with tempfile.TemporaryDirectory() as td:
        src, out = Path(td) / "in.png", Path(td) / "out.png"
        with Image.open(path) as im:
            im.convert("RGB").save(src)
        cmd = [str(exe), "-i", str(src), "-o", str(out), "-n", model, "-s", str(scale)]
        models = c.get("models_dir") or (exe.parent / "models" if (exe.parent / "models").is_dir() else "")
        if models:                                     # le moteur cherche « models » dans le dossier courant sinon
            cmd += ["-m", str(models)]
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=300, cwd=str(exe.parent))
        except (OSError, subprocess.TimeoutExpired) as e:
            log.warning("agrandissement de %s impossible : %s", path.name, e)
            return False
        if r.returncode != 0 or not out.exists():
            log.warning("agrandissement de %s échoué : %s", path.name, (r.stderr or b"").decode(errors="ignore")[-300:])
            return False
        backup = library.root() / "_originals" / path.relative_to(library.root())
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            shutil.copy2(path, backup)
        with Image.open(out) as big:
            big = big.convert("RGB")
            k = target / min(big.size)
            if k < 1:                                         # 4× peut dépasser : on redescend à la cible
                big = big.resize((round(big.width * k), round(big.height * k)), Image.LANCZOS)
            fmt = "PNG" if path.suffix.lower() == ".png" else "JPEG"
            big.save(path, fmt, **({"quality": 93} if fmt == "JPEG" else {}))
    log.info("image agrandie ×%d : %s (%dx%d → %s)", scale, path.name, w, h, "ok")
    return True


def upscale_library() -> dict:
    """Agrandit toutes les petites images de la bibliothèque (hors captures d'épisodes). Rend un compte rendu."""
    from .. import db
    from . import library

    done = skipped = 0
    if not binary():
        return {"done": 0, "skipped": 0, "error": "moteur Real-ESRGAN introuvable"}
    for r in db.query("SELECT * FROM images WHERE origin='library'"):
        p = Path(r["path"])
        if not p.exists() or not needed(r["width"] or 0, r["height"] or 0):
            continue
        if upscale_file(p):
            m = library.measure(p)
            if m:
                db.update("images", r["id"], width=m["width"], height=m["height"], sharp=m["sharp"])
            done += 1
        else:
            skipped += 1
    return {"done": done, "skipped": skipped}
