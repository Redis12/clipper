"""Dragon Ball → DBZ Villain Transformations (15/11) : 15 méchants, de Tao Pai Pai à Kid Buu (fusion_powers, mode « chasse »).
python3 tools/jojo/db_villains.py sortie.mp4 [graine]"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from clipper.slides import fusion, fusion_powers  # noqa: E402

S = ROOT / "library/_sounds/db_villains"
POWERS = {}            # 15/11 : pas de pouvoirs (« trop de persos ») : son de fusion DBZ + musique
MERGE = {}
DB = ROOT / "library/_sfx/Dragon Ball SFX/Dragon Ball Z Sounds"
FUSION_SOUND = [str(DB / f) for f in ("Voicy_ki blast.mp3", "DBZ Sound effect Strong Punch.mp3",
                "Voicy_Small Aura Burst (DBZ Sound Effect).mp3", "Voicy_Instant transmission re-upload.mp3",
                "Voicy_super sayian aura sound effect.mp3", "Voicy_DBZ Explosion Sound Effect 1.mp3")]
MUSIC = ROOT / "library/_music/Dragon Ball Z - Solid State Scouter.mp3"
if __name__ == "__main__":
    tiers = fusion.tiers_from_chain("DB to DBZ Villains")
    out = Path(sys.argv[1])
    seed = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 7
    print(fusion_powers.generate(tiers, "DRAGON BALL → DBZ VILLAINS", POWERS, seed=seed, out=out,
                                 opts={"drop_every": 1.4, "drop_every_min": 0.8}, merge_sounds=MERGE or None,
                                 merge_sound=FUSION_SOUND, music=str(MUSIC), music_start=0.0, music_gain=0.55))
