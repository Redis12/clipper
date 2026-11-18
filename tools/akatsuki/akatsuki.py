"""Akatsuki, du plus faible au plus fort (18/11) : Zetsu → Madara, chacun son pouvoir (fusion_powers).
python3 tools/akatsuki/akatsuki.py sortie.mp4 [graine]"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from clipper.slides import fusion, fusion_powers  # noqa: E402

NS = ROOT / "library/_sfx/Naruto SFX"
HY = ROOT / "library/_sfx/Helton Yan's Old-School Shonen SFX"
HANDS = NS / "Naruto hand signs - QuickSounds.com.mp3"
EXP = HY / "EXPLDsgn_Anime Explosion 3.ogg"
POWERS = {
    "Hidan": {"power": "jashin", "delay": 0.4, "power_sound": HY / "FGHTImpt_Anime Melee 7.ogg"},
    "Sasori": {"power": "puppet", "delay": 0.4, "power_sound": HANDS, "power_dur": 1.0},
    "Kakuzu": {"power": "grudge", "delay": 0.4, "power_sound": HY / "FGHTImpt_Anime Melee 3.ogg"},
    "Deidara": {"power": "clay", "delay": 0.3, "power_sound": EXP, "power_start": 0.0},
    "Kisame": {"power": "shark", "delay": 0.4, "power_sound": HY / "EXPLDsgn_Anime Explosion 6.ogg", "power_gain": 0.8},
    "Konan": {"power": "paper", "delay": 0.4, "power_sound": NS / "Kunai Throw Sound Effect.mp3", "power_dur": 1.0},
    "Itachi": {"power": "tsukuyomi", "delay": 0.3, "power_sound": NS / "sharingan.mp3"},
    "Pain": {"power": "quake", "delay": 0.3, "banner": "SHINRA TENSEI!", "power_sound": EXP},
    "Nagato": {"power": "chibaku", "delay": 0.3, "power_sound": HY / "EXPLDsgn_Anime Explosion 9.ogg"},
    "Obito": {"power": "kamui", "delay": 0.3, "power_sound": NS / "sharingan.mp3"},
    "Madara": {"power": "meteor", "delay": 0.1, "power_sound": NS / "mangekyo sharingan madara.ogg"},
}
MERGE_SOUND = [str(HY / f) for f in ("FGHTImpt_Anime Melee 1.ogg", "FGHTImpt_Anime Melee 3.ogg", "FGHTImpt_Anime Melee 5.ogg",
                                     "EXPLDsgn_Anime Explosion 1.ogg", "EXPLDsgn_Anime Explosion 4.ogg")]
# 18/11 : « trop de son à l'infini » → comme JoJo : un son court par fusion, jamais plus d'un toutes les 0,9 s
_SOFT = [HY / "FGHTImpt_Anime Melee 1.ogg", HY / "FGHTImpt_Anime Melee 3.ogg", HY / "FGHTImpt_Anime Melee 5.ogg",
         HY / "EXPLDsgn_Anime Explosion 1.ogg"]
MERGE = {t: (_SOFT[min(3, t * 4 // 12)], 0.0, 0.45, 0.9) for t in range(12)}
MUSIC = ROOT / "library/_music/Naruto Shippuden OST 1 - Track 26 - Keisei Gyakuten ( Reverse Situation ).mp3"
if __name__ == "__main__":
    tiers = fusion.tiers_from_chain("Akatsuki")
    out = Path(sys.argv[1])
    seed = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 3
    print(fusion_powers.generate(tiers, "EVERY AKATSUKI MEMBER", POWERS, seed=seed, out=out,
                                 opts={"drop_every": 1.4, "drop_every_min": 0.8}, merge_sounds=MERGE,
                                 music=str(MUSIC), music_gain=0.5))
