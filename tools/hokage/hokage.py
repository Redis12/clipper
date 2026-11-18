"""First Hokage → Eighth Hokage (18/11) : les 8 Hokage (Shikamaru = 8e, Boruto Two Blue Vortex) qui fusionnent (fusion_powers), chacun son pouvoir.
python3 tools/hokage/hokage.py sortie.mp4 [graine]"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from clipper.slides import fusion, fusion_powers  # noqa: E402

NS = ROOT / "library/_sfx/Naruto SFX"
HY = ROOT / "library/_sfx/Helton Yan's Old-School Shonen SFX"
HANDS = NS / "Naruto hand signs - QuickSounds.com.mp3"
POWERS = {
    "Hashirama": {"power": "wood", "delay": 0.25, "power_sound": HANDS, "power_dur": 1.2, "banner": "WOOD STYLE!"},
    "Tobirama": {"power": "hiraishin", "delay": 0.5, "power_sound": NS / "Kunai Throw Sound Effect.mp3", "power_dur": 1.0},
    "Hiruzen": {"power": "shiki_fujin", "delay": 0.6, "power_sound": HY / "EXPLDsgn_Anime Explosion 9.ogg", "power_gain": 0.7},
    "Minato": {"power": "hiraishin", "delay": 0.4, "power_sound": NS / "Kunai Throw Sound Effect.mp3", "power_dur": 1.0,
               "banner": "YELLOW FLASH!"},
    "Tsunade": {"power": "quake", "delay": 0.5, "power_sound": HY / "EXPLDsgn_Anime Explosion 3.ogg"},
    "Kakashi": {"power": "kamui", "delay": 0.5, "power_sound": NS / "sharingan.mp3"},
    "Naruto": {"power": "kurama", "delay": 0.1, "power_sound": NS / "yooooooooooooooooooooooooo-mp3cut_0lMDWCd.mp3",
               "power_dur": 2.0, "banner": "SEVENTH HOKAGE!"},
    "Shikamaru": {"power": "shadow", "delay": 0.2, "power_sound": HANDS, "power_dur": 1.2, "banner": "EIGHTH HOKAGE!"},
}
MERGE_SOUND = [str(HY / f) for f in ("FGHTImpt_Anime Melee 1.ogg", "FGHTImpt_Anime Melee 3.ogg", "FGHTImpt_Anime Melee 5.ogg",
                                     "EXPLDsgn_Anime Explosion 1.ogg", "EXPLDsgn_Anime Explosion 4.ogg")]
# 18/11 : « trop de son à l'infini » → comme JoJo : un son court par fusion, jamais plus d'un toutes les 0,9 s
_SOFT = [HY / "FGHTImpt_Anime Melee 1.ogg", HY / "FGHTImpt_Anime Melee 3.ogg", HY / "FGHTImpt_Anime Melee 5.ogg",
         HY / "EXPLDsgn_Anime Explosion 1.ogg"]
MERGE = {t: (_SOFT[min(3, t * 4 // 8)], 0.0, 0.45, 0.9) for t in range(8)}
MUSIC = ROOT / "library/_music/Naruto Shippuden OST 1 - Track 26 - Keisei Gyakuten ( Reverse Situation ).mp3"
if __name__ == "__main__":
    tiers = fusion.tiers_from_chain("Hokage")
    out = Path(sys.argv[1])
    seed = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 7
    print(fusion_powers.generate(tiers, "FIRST HOKAGE → EIGHTH HOKAGE", POWERS, seed=seed, out=out,
                                 opts={"drop_every": 0.7, "drop_every_min": 0.42}, merge_sounds=MERGE,
                                 music=str(MUSIC), music_gain=0.5))
