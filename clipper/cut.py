"""Étape 6 : découpe précise à la frame, 16:9, loudnorm deux passes à −14 LUFS, fondus audio."""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import config, db
from .util import ffprobe, log, require_bin, run, safe_replace, video_stream


def target_size(src_w: int, src_h: int, max_h: int = 1080) -> tuple[int, int]:
    """16:9 sans upscale : hauteur = min(max_h, hauteur source), dimensions paires."""
    h = min(max_h, src_h)
    h -= h % 2
    w = round(h * 16 / 9)
    w -= w % 2
    return w, h


def measure_loudness(src: str, start: float, dur: float, I: float, TP: float, LRA: float) -> dict | None:
    p = run([require_bin("ffmpeg"), "-hide_banner", "-nostats", "-ss", f"{start:.3f}", "-i", src,
             "-t", f"{dur:.3f}", "-vn", "-af", f"loudnorm=I={I}:TP={TP}:LRA={LRA}:print_format=json",
             "-f", "null", "-"], check=True)
    m = re.findall(r"\{[^{}]*\"input_i\"[^{}]*\}", p.stderr, re.S)
    if not m:
        return None
    data = json.loads(m[-1])
    if data.get("input_i") in ("-inf", "inf") or float(data["input_i"]) < -70:
        return None  # silence : la 2e passe linéaire n'a pas de sens
    return data


def render(clip_id: int, force: bool = False) -> Path:
    c = db.get_clip(clip_id)
    out = config.clip_dir(clip_id) / "clip.mp4"
    if out.exists() and not c["render_needed"] and not force:
        return out
    v = db.get_video(c["video_id"])
    cfg = config.get()["cut"]
    src = v["source_path"]
    info = ffprobe(Path(src))
    vs = video_stream(info)
    has_audio = any(s.get("codec_type") == "audio" for s in info["streams"])
    W, H = target_size(int(vs["width"]), int(vs["height"]), int(cfg["max_height"]))
    start, dur = float(c["start"]), float(c["end"]) - float(c["start"])
    fade = float(cfg["audio_fade"])
    L = cfg["loudness"]
    I, TP, LRA = float(L["integrated"]), float(L["true_peak"]), float(L["lra"])

    vf = (f"scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos,"
          f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:black,setsar=1,format=yuv420p")
    cmd = [require_bin("ffmpeg"), "-y", "-v", "error", "-ss", f"{start:.3f}", "-i", src, "-t", f"{dur:.3f}",
           "-map", "0:v:0", "-vf", vf, "-c:v", "libx264", "-preset", str(cfg["preset"]), "-crf", str(cfg["crf"]),
           "-profile:v", "high"]
    if has_audio:
        m = measure_loudness(src, start, dur, I, TP, LRA)
        ln = f"loudnorm=I={I}:TP={TP}:LRA={LRA}"
        if m:
            ln += (f":measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
                   f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
        af = (f"{ln},aresample=48000,afade=t=in:st=0:d={fade},"
              f"afade=t=out:st={max(0.0, dur - fade):.3f}:d={fade}")
        cmd += ["-map", "0:a:0", "-af", af, "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]
    tmp = out.with_name("clip.tmp.mp4")
    cmd += ["-movflags", "+faststart", str(tmp)]
    log.info("clip %s : rendu %dx%d, %.1f s", clip_id, W, H, dur)
    run(cmd)
    safe_replace(tmp, out)
    now = db.get_clip(clip_id)
    # Si les bornes ont bougé pendant le rendu, le fichier est déjà périmé : on le laisse marqué à refaire.
    fresh = (now["start"], now["end"]) == (c["start"], c["end"])
    db.update_clip(clip_id, clip_path=str(out), render_needed=0 if fresh else 1)
    return out


def integrated_loudness(path: Path) -> float:
    """Mesure EBU R128 du fichier (pour les tests et la vérification)."""
    p = run([require_bin("ffmpeg"), "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128",
             "-f", "null", "-"])
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", p.stderr)
    return float(m[-1])
