"""Luffy vs Kaido (DOMAIN WAR, jeu. 05/11 13h) : scénario « chute » — Luffy tombe, Gear 5, Zoro perdu vient aider."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from clipper.slides import domain  # noqa: E402

SFX = "_sfx/One Piece/One Piece SFX/"
STORY = {
    "hero": 0,
    "helper": {"dir": "One Piece/one-piece-mugen/One Piece MUGEN/chars/G6_Zoro", "char": "Zoro", "name": "ZORO",
               "move": "SANZEN SEKAI", "voice": [0, 3]},
    "sounds": {
        "stage dragon": [(0, SFX + "Terror.mp3", 0.9), (0.8, SFX + "Big explosion.mp3", 0.6)],
        "ragnaraku": [(0, SFX + "conqueror's Haki (Haoshoku Haki) v1.mp3", 0.8), (2.7, SFX + "Big explosion.mp3", 1.0),
                      (3.1, SFX + "explosion with debris.mp3", 0.8)],
        "clash": [(0, SFX + "conqueror's haki (Haoshoku Haki) v2.mp3", 0.9), (0.05, SFX + "Big explosion.mp3", 0.7)],
        "gear 5": [(3.0, SFX + "conqueror's haki (Haoshoku Haki) v2.mp3", 0.6), (5.3, SFX + "Whoosh hit.mp3", 0.8),
                   (6.6, SFX + "explosion.mp3", 0.8)],
        "down": [(0, SFX + "at death's door.mp3", 0.8), (1.35, "_sounds/domain/Gear 5 drums.mp3", 1.1)],
        "helper": [(0, SFX + "Zoro's run gait.mp3", 0.7)],
        "helper_hit": [(-0.05, SFX + "big sword cutting.mp3", 1.0)],
    },
}
L = domain.library.root()
fighters = [{"name": "Monkey D. Luffy", "image_path": str(L / "_domain/forms/Luffy/1 Base.jpg")},
            {"name": "Kaido", "image_path": str(L / "_domain/forms/Kaido/1 Base.jpg")}]
low = "--low" in sys.argv
out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else None
print(domain.generate(fighters, seconds=28, title="DOMAIN WAR #6", story=STORY, out=out, W=540 if low else 1080, H=960 if low else 1920,
                      fps=24 if low else 30, cine="card"))
