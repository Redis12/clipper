"""Étape 2 : transcription horodatée au mot avec locuteurs. Résultat mis en cache, jamais refait.

Format normalisé (transcript.json) :
  {"engine": "...", "language": "fr", "words": [{"w": "Bonjour,", "s": 0.12, "e": 0.48, "spk": 0}, ...]}
"""
from __future__ import annotations

from pathlib import Path

import httpx

from . import config, db
from .util import atomic_write_json, log, require_bin, run, safe_replace


def extract_audio(video_id: str) -> Path:
    vdir = config.video_dir(video_id)
    out = vdir / "audio.ogg"
    if out.exists() and out.stat().st_size > 0:
        return out
    src = db.get_video(video_id)["source_path"]
    tmp = vdir / "audio.tmp.ogg"
    # Mono 16 kHz Opus 32 kb/s : ~14 Mo/heure, idéal pour l'upload vers l'API.
    run([require_bin("ffmpeg"), "-y", "-v", "error", "-i", src, "-vn", "-ac", "1", "-ar", "16000",
         "-c:a", "libopus", "-b:a", "32k", str(tmp)])
    safe_replace(tmp, out)
    return out


def _deepgram(audio: Path) -> dict:
    c = config.get()["transcription"]
    params = {
        "model": c.get("deepgram_model", "nova-3"),
        "language": c.get("language", "fr"),
        "diarize": "true",
        "punctuate": "true",
        "smart_format": "true",
    }
    headers = {"Authorization": f"Token {config.secret('DEEPGRAM_API_KEY')}", "Content-Type": "audio/ogg"}
    size_mb = audio.stat().st_size / 1e6
    log.info("Deepgram : envoi de %.1f Mo…", size_mb)
    with open(audio, "rb") as f:
        r = httpx.post("https://api.deepgram.com/v1/listen", params=params, headers=headers,
                       content=f, timeout=httpx.Timeout(1800, connect=30))
    if r.status_code >= 400:
        raise RuntimeError(f"Deepgram {r.status_code} : {r.text[:500]}")
    alt = r.json()["results"]["channels"][0]["alternatives"][0]
    words = [
        {"w": w.get("punctuated_word") or w["word"], "s": float(w["start"]), "e": float(w["end"]),
         "spk": int(w.get("speaker", 0))}
        for w in alt.get("words", [])
    ]
    return {"engine": f"deepgram:{params['model']}", "language": params["language"], "words": words}


def _whisperx(audio: Path) -> dict:
    """Option locale (GPU conseillé). Importée à la demande : dépendance lourde."""
    try:
        import whisperx  # type: ignore
    except ImportError as e:
        raise RuntimeError("WhisperX non installé : pip install -e '.[whisperx]'") from e
    c = config.get()["transcription"]
    device = c.get("whisperx_device", "cuda")
    lang = c.get("language", "fr")
    model = whisperx.load_model(c.get("whisperx_model", "large-v3"), device,
                                compute_type="float16" if device == "cuda" else "int8", language=lang)
    data = whisperx.load_audio(str(audio))
    result = model.transcribe(data, batch_size=16, language=lang)
    align_model, meta = whisperx.load_align_model(language_code=lang, device=device)
    result = whisperx.align(result["segments"], align_model, meta, data, device)
    hf = config.secret("HF_TOKEN", required=False)
    if hf:
        from whisperx.diarize import DiarizationPipeline  # type: ignore
        diar = DiarizationPipeline(use_auth_token=hf, device=device)(data)
        result = whisperx.assign_word_speakers(diar, result)
    words, last_e = [], 0.0
    for seg in result["segments"]:
        for w in seg.get("words", []):
            s = float(w.get("start", last_e))
            e = float(w.get("end", s))
            spk = w.get("speaker") or seg.get("speaker") or "SPEAKER_00"
            words.append({"w": w["word"], "s": s, "e": e,
                          "spk": int(str(spk).rsplit("_", 1)[-1]) if str(spk)[-1:].isdigit() else 0})
            last_e = e
    return {"engine": "whisperx", "language": lang, "words": words}


def transcribe(video_id: str) -> Path:
    vdir = config.video_dir(video_id)
    out = vdir / "transcript.json"
    if out.exists():
        db.update_video(video_id, transcript_path=str(out))
        return out
    db.update_video(video_id, step="transcription")
    audio = extract_audio(video_id)
    engine = config.get()["transcription"].get("engine", "deepgram")
    data = _whisperx(audio) if engine == "whisperx" else _deepgram(audio)
    if not data["words"]:
        raise RuntimeError("Transcription vide (pas de parole détectée ?)")
    atomic_write_json(out, data)
    db.update_video(video_id, transcript_path=str(out))
    log.info("[%s] transcrit : %d mots, %d locuteurs", video_id, len(data["words"]),
             len({w["spk"] for w in data["words"]}))
    return out
