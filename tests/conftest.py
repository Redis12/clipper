import copy
import os
import json
import subprocess
from pathlib import Path

import pytest
import yaml

from clipper import config, db

ROOT = Path(__file__).resolve().parents[1]
os.environ["CLIPPER_TESTING"] = "1"
BASE_CFG = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))


@pytest.fixture()
def cfg(tmp_path, monkeypatch):
    c = copy.deepcopy(BASE_CFG)
    c["paths"]["data"] = str(tmp_path / "data")
    c["cut"]["preset"] = "ultrafast"
    c["slides"]["library"] = str(tmp_path / "library")
    c["slides"]["video"]["music_dir"] = str(tmp_path / "library" / "_music")
    c["slides"]["video"]["auto"] = True            # les tests couvrent aussi la vidéo
    config.set_for_tests(c)
    db.reset_connection()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    yield c
    db.reset_connection()


def fake_words(n_sentences=120, words_per=12, spk_every=40):
    """Transcription synthétique : phrases ponctuées de ~4 s, pause de 0,4 s entre phrases."""
    words, t = [], 0.0
    for s in range(n_sentences):
        spk = (s // spk_every) % 2
        for w in range(words_per):
            last = w == words_per - 1
            words.append({"w": f"mot{s}_{w}" + ("." if last else ""), "s": round(t, 2), "e": round(t + 0.28, 2), "spk": spk})
            t += 0.32
        t += 0.4
    return words


@pytest.fixture(scope="session")
def sample_video(tmp_path_factory):
    """Vidéo 720p de 8 min : mire + bip à −30 dBFS (pour vérifier la normalisation à −14 LUFS)."""
    p = tmp_path_factory.mktemp("media") / "source.mkv"
    subprocess.run(["ffmpeg", "-y", "-v", "error",
                    "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=25:duration=480",
                    "-f", "lavfi", "-i", "sine=frequency=440:duration=480,volume=-24dB",
                    "-c:v", "libx264", "-preset", "ultrafast", "-crf", "35", "-c:a", "aac", "-shortest", str(p)],
                   check=True)
    return p


@pytest.fixture()
def video_in_db(cfg, sample_video):
    from clipper import config as C
    vid = "abcdefghijk"
    words = fake_words()
    vdir = C.video_dir(vid)
    tp = vdir / "transcript.json"
    tp.write_text(json.dumps({"engine": "test", "language": "fr", "words": words}), encoding="utf-8")
    db.insert_video(vid, f"https://www.youtube.com/watch?v={vid}", title="Vidéo test", channel="Chaîne",
                    channel_id="UCtest", duration=480.0, source_path=str(sample_video),
                    proxy_path=str(sample_video), transcript_path=str(tp), status="transcribed", chapters=[])
    return vid
