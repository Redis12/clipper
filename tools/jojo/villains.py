"""JoJo Villain Transformations (15/11) : 9 méchants qui fusionnent, chacun son son et son pouvoir (fusion_powers).
python3 tools/jojo/villains.py sortie.mp4 [graine]"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from clipper.slides import fusion, fusion_powers  # noqa: E402

S = ROOT / "library/_sounds/jojo_villains"
POWERS = {
    "Wamuu": {"sound": S / "pillar men.mp3", "dur": 13.0, "fout": 1.5, "gain": 0.8},
    "Esidisi": {"sound": S / "pillar men.mp3", "dur": 6.0, "fout": 1.0, "gain": 0.8},
    "Kars": {"sound": S / "pillar men.mp3", "start": 6.0, "dur": 7.0, "fout": 1.5, "gain": 0.8},
    "DIO": {"power": "timestop", "power_sound": S / "za warudo.mp3", "power_dur": 2.6, "delay": 0.5, "freeze": 1.0},
    "Yoshikage Kira": {"sound": S / "kira speech.mp3", "dur": 3.6, "fout": 0.6, "power": "bites_the_dust",
                       "delay": 0.4, "boom_sound": S / "killer queen kaboom.mp3",
                       "power_sound": S / "yattazo bites the dust.mp3"},
    "Diavolo": {"sound": S / "kono diavolo da.mp3", "power": "king_crimson", "delay": 2.9,
                "power_sound": S / "king crimson skip.mp3", "skip": 5.0},
    "Valentine": {"sound": S / "dojyaan.mp3", "fout": 0.3},
    "Pucci": {"power": "made_in_heaven", "power_sound": S / "made in heaven.mp3", "delay": 0.3, "speed": 1.5},
}
if __name__ == "__main__":
    tiers = fusion.tiers_from_chain("JoJo Villains")
    out = Path(sys.argv[1])
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    print(fusion_powers.generate(tiers, "JOJO VILLAIN TRANSFORMATIONS", POWERS, start_sound=S / "kono dio da.mp3",
                                 seed=seed, out=out, opts={"drop_every": 0.7, "drop_every_min": 0.45}))
