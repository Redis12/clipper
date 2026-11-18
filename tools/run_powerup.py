"""Power Up « Can <héros> beat <boss> in under 60 seconds? » — rendu en ligne de commande.
python3 tools/run_powerup.py <sortie.mp4> <chaîne _fusion> <boss (forme ou chemin)> <nom du boss> [forme max] [graine]"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from clipper.slides import powerup  # noqa: E402

out, chain, boss, boss_name = sys.argv[1:5]
max_form = sys.argv[5] if len(sys.argv) > 5 and sys.argv[5] != "-" else None
seed = int(sys.argv[6]) if len(sys.argv) > 6 else None
print(powerup.generate(chain, boss, boss_name=boss_name, max_form=max_form, seed=seed, out=Path(out)))
