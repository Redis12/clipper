"""Gauntlets Base Goku (04/11) : One Piece et Naruto, avec gags (Sanji cuisine, Hiraishin, Kamui, Talk no Jutsu)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from clipper.slides import gauntlet  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
L = "library/"
OP = "library/One Piece/"
N = "library/Naruto/"
GOKU = {"name": "Goku", "image_path": L + "_fusion/Goku/1 Base.png"}
one_piece = [{"name": n, "image_path": f"{OP}{n}/{n}.jpg"} for n in ["Nami", "Sanji", "Crocodile", "Hody Jones",
                                                                   "Doflamingo", "Jack"]]
one_piece[1].update(gag=True, gag_s=1.6, say="Wait! Let me cook for you first 🍳", gag_label="SANJI IS COOKING...")
one_piece += [{"name": "Zoro", "image_path": L + "_fusion/Luffy/7 Zoro.jpeg"},
              {"name": "Kizaru", "image_path": OP + "Kizaru/Kizaru.jpg"},
              {"name": "Akainu", "image_path": OP + "Akainu/Akainu.jpg"},
              {"name": "Luffy Gear 4", "image_path": L + "_fusion/Luffy/4 Gear 4 BoundMan.jpg"},
              {"name": "Kaido", "image_path": L + "_domain/forms/Kaido/3 Hybrid.jpg"},
              {"name": "Luffy Gear 5", "image_path": L + "_fusion/Luffy/6 Gear 5.jpg"}]
naruto = [("Ichiraku", "Teuchi/Teuchi.jpg"), ("TenTen", "TenTen/TenTen.jpg"), ("Sakura", "Sakura/Sakura.jpg"),
          ("Jiraiya", "Jiraya/Jiraya.png"), ("Orochimaru", "Orochimaru/Orochimaru.jpg"),
          ("Kakashi", "Kakashi/Kakashi.jpg"), ("Raikage", "Raikage/Raikage.jpg"), ("Minato", "Minato/Minato.jpg"),
          ("Itachi", "Itachi/Itachi.jpg"), ("Pain", "Pain/Pain.jpg"), ("Obito", "Obito/Obito.png"),
          ("Madara", "Madara/Madara.jpg")]
naruto = [{"name": n, "image_path": N + p} for n, p in naruto]
naruto[7]["tp"] = True
naruto[10]["kamui"] = True
naruto.append({"name": "Naruto", "image_path": L + "_fusion/Naruto/8 SIX PATH.jpg", "gag": True, "gag_s": 1.2,
               "say": "Listen Goku... I know your pain, believe it—", "gag_label": "TALK NO JUTSU!"})
if "op" in sys.argv or "all" in sys.argv:
    print(gauntlet.generate(GOKU, one_piece, universe="One Piece", seed=4, base_hits=1, step_hits=0,
                            out=OUT / "Gauntlet - Goku vs One Piece.mp4"))
if "naruto" in sys.argv or "all" in sys.argv:
    print(gauntlet.generate(GOKU, naruto, universe="Naruto", seed=4, base_hits=1, step_hits=0,
                            out=OUT / "Gauntlet - Goku vs Naruto.mp4"))
