"""Dragon Ball → DBZ Villain Transformations (15/11) : 15 méchants, de Tao Pai Pai à Kid Buu (fusion_powers, mode « chasse »).
python3 tools/jojo/db_villains.py sortie.mp4 [graine]"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from clipper.slides import fusion, fusion_powers  # noqa: E402

S = ROOT / "library/_sounds/db_villains"
POWERS = {}            # sons / pouvoirs à brancher quand l'utilisateur envoie les sons
MERGE = {}
if __name__ == "__main__":
    tiers = fusion.tiers_from_chain("DB to DBZ Villains")
    out = Path(sys.argv[1])
    seed = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 7
    print(fusion_powers.generate(tiers, "DRAGON BALL → DBZ VILLAINS", POWERS, seed=seed, out=out,
                                 opts={"drop_every": 1.4, "drop_every_min": 0.8}, merge_sounds=MERGE or None))
