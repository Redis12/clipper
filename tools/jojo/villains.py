"""JoJo Villain Transformations (15/11) : 9 méchants qui fusionnent, chacun son son et son pouvoir (fusion_powers).
python3 tools/jojo/villains.py sortie.mp4 [graine]"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from clipper.slides import fusion, fusion_powers  # noqa: E402

S = ROOT / "library/_sounds/jojo_villains"
POWERS = {          # 1re apparition (son) + pouvoir
    "DIO": {"power": "timestop", "power_sound": S / "za warudo.mp3", "power_dur": 2.6, "delay": 0.05, "freeze": 1.0},
    "Yoshikage Kira": {"sound": S / "kira speech.mp3", "dur": 2.9, "fout": 0.5, "power": "bites_the_dust",
                       "delay": 0.4, "boom_sound": S / "killer queen kaboom.mp3",
                       "power_sound": S / "yattazo bites the dust.mp3"},
    "Diavolo": {"sound": S / "kono diavolo da.mp3", "power": "king_crimson", "delay": 2.9,
                "power_sound": S / "king crimson skip.mp3", "skip": 5.0},
    "Valentine": {"sound": S / "dojyaan.mp3", "fout": 0.3},
    "Pucci": {"power": "made_in_heaven", "power_sound": S / "made in heaven.mp3", "power_dur": 7.5, "delay": 0.3,
              "speed": 2.5},
}
# son à CHAQUE fusion de deux persos de ce niveau (15/11 : « 1 seconde, à chaque fusion ») : (fichier, début, durée, écart min)
MERGE = {
    0: (S / "kono dio da.mp3", 0.4, 1.0, 0.6),
    1: (S / "pillar men.mp3", 0.1, 1.0, 0.6),
    2: (S / "pillar men.mp3", 0.1, 1.0, 0.6),
    3: (S / "pillar men.mp3", 0.1, 1.0, 0.6),
    4: (S / "dio time stop.mp3", 0.0, 1.2, 0.6),
    5: (S / "killer queen kaboom.mp3", 0.0, 1.0, 0.6),
    6: (S / "king crimson skip.mp3", 0.0, 0.62, 0.4),
    7: (S / "made in heaven.mp3", 0.8, 1.0, 0.6),
}
if __name__ == "__main__":
    tiers = fusion.tiers_from_chain("JoJo Villains")
    out = Path(sys.argv[1])
    seed = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 7
    if "--reset" in sys.argv:            # v3 (15/11) : Made in Heaven accélère jusqu'à faire recommencer l'univers
        POWERS["Pucci"].update(reset=True, speed=6.0, reset_after=3.2, ff_seconds=2.2, after_speed=1.3)
    print(fusion_powers.generate(tiers, "JOJO VILLAIN TRANSFORMATIONS", POWERS, seed=seed, out=out,
                                 opts={"drop_every": 0.7, "drop_every_min": 0.45}, merge_sounds=MERGE))
