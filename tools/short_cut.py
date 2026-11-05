"""Version courte TikTok / Instagram (05/11) : vidéo accélérée pour viser ~25 s (rétention des comptes neufs),
musique de fond déjà mixée (Buffer automatique : pas de son tendance ajouté à la main). YouTube garde l'original."""
import json
import subprocess
import sys
from pathlib import Path

MUSIC = {"naruto": "library/_music/Naruto Shippuden OST 1 - Track 26 - Keisei Gyakuten ( Reverse Situation ).mp3",
         "one piece": "library/_music/Drums of Liberation x Overtaken (Gear 5 cover).mp3",
         "default": "library/_music/Delirious.mp3"}


def duration(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                                capture_output=True, text=True).stdout)


def short(src: Path, dst: Path, franchise: str = "default", target: float = 26.0, music_vol: float = 0.22):
    d = duration(src)
    sp = min(1.6, max(1.0, d / target))
    m = MUSIC.get(franchise, MUSIC["default"])
    out_d = d / sp
    fc = (f"[0:v]setpts=PTS/{sp:.3f}[v];[0:a]atempo={sp:.3f},volume=1.6[a0];"
          f"[1:a]volume={music_vol},afade=t=in:d=0.5,afade=t=out:st={max(0, out_d - 1.2):.2f}:d=1.2[a1];"
          f"[a0][a1]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.9[a]")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(src), "-stream_loop", "-1", "-i", m,
                    "-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-t", f"{out_d:.2f}", "-c:v", "libx264",
                    "-preset", "veryfast", "-crf", "24", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
                    str(dst)], check=True)
    return out_d, sp


if __name__ == "__main__":
    jobs = json.loads(sys.argv[1])
    for src, dst, fr in jobs:
        print(dst, *[round(x, 2) for x in short(Path(src), Path(dst), fr)])
