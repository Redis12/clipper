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
one_piece[4].update(gag=True, gag_s=1.4, fx="strings", say="Fufufu... you're my puppet now!", gag_label="STRING!")
one_piece += [{"name": "Zoro", "image_path": L + "_fusion/Luffy/7 Zoro.jpeg", "gag": True, "gag_s": 1.7, "fx": "lost",
               "say": "Where am I? 🗺️", "gag_label": "ZORO GOT LOST..."},
              {"name": "Kizaru", "image_path": OP + "Kizaru/Kizaru.jpg", "gag": True, "gag_s": 1.5,
               "say": "Have you ever been kicked at the speed of light?"},
              {"name": "Akainu", "image_path": OP + "Akainu/Akainu.jpg"},
              {"name": "Luffy Gear 4", "image_path": L + "_fusion/Luffy/4 Gear 4 BoundMan.jpg"},
              {"name": "Kaido", "image_path": L + "_domain/forms/Kaido/3 Hybrid.jpg"},
              {"name": "Luffy Gear 5", "image_path": L + "_fusion/Luffy/6 Gear 5.jpg", "gag": True, "gag_s": 1.5,
               "fx": "inflate", "say": "HAHAHA! 😂", "gag_label": "GEAR 5!"}]
naruto = [("Ichiraku", "Teuchi/Teuchi.jpg"), ("TenTen", "TenTen/TenTen.jpg"), ("Sakura", "Sakura/Sakura.jpg"),
          ("Jiraiya", "Jiraya/Jiraya.png"), ("Orochimaru", "Orochimaru/Orochimaru.jpg"),
          ("Kakashi", "Kakashi/Kakashi.jpg"), ("Raikage", "Raikage/Raikage.jpg"), ("Minato", "Minato/Minato.jpg"),
          ("Itachi", "Itachi/Itachi.jpg"), ("Pain", "Pain/Pain.jpg"), ("Obito", "Obito/Obito.png"),
          ("Madara", "Madara/Madara.jpg")]
naruto = [{"name": n, "image_path": N + p} for n, p in naruto]
naruto[7]["tp"] = True
naruto[8]["fake"] = True
naruto[10]["kamui"] = True
naruto.append({"name": "Naruto", "image_path": L + "_fusion/Naruto/8 SIX PATH.jpg", "gag": True, "gag_s": 1.2,
               "say": "Listen Goku... I know your pain, believe it—", "gag_label": "TALK NO JUTSU!"})
if "op" in sys.argv or "all" in sys.argv:
    print(gauntlet.generate(GOKU, one_piece, universe="One Piece", seed=4, base_hits=1, step_hits=0,
                            out=OUT / "Gauntlet - Goku vs One Piece.mp4"))
if "naruto" in sys.argv or "all" in sys.argv:
    print(gauntlet.generate(GOKU, naruto, universe="Naruto", seed=4, base_hits=1, step_hits=0,
                            out=OUT / "Gauntlet - Goku vs Naruto.mp4"))
if "sage" in sys.argv or "all" in sys.argv:          # gauntlet inversé : Naruto Sage Mode tombe contre Itachi
    SAGE = {"name": "Naruto", "image_path": L + "_fusion/Naruto/5 toad sage.webp"}
    foes = [{"name": n, "image_path": N + p} for n, p in [
        ("Ichiraku", "Teuchi/Teuchi.jpg"), ("TenTen", "TenTen/TenTen.jpg"), ("Sakura", "Sakura/Sakura.jpg"),
        ("Orochimaru", "Orochimaru/Orochimaru.jpg"), ("Kakashi", "Kakashi/Kakashi.jpg"), ("Jiraiya", "Jiraya/Jiraya.png"),
        ("Pain", "Pain/Pain.jpg"), ("Itachi", "Itachi/Itachi.jpg"), ("Minato", "Minato/Minato.jpg"),
        ("Obito", "Obito/Obito.png"), ("Madara", "Madara/Madara.jpg")]]
    foes[0].update(gag=True, gag_s=1.3, say="Free ramen if you lose! 🍜")
    print(gauntlet.generate(SAGE, foes, universe="Naruto", seed=5, base_hits=1, step_hits=0, dmg=500,
                            lose_at=7, lose_after=3.0, lose_move="TSUKUYOMI!",
                            title=("Can Sage Mode Naruto", "SURVIVE the NARUTO GAUNTLET?"),
                            out=OUT / "Gauntlet - Sage Naruto survive.mp4"))
if "gojo" in sys.argv:                                # 07/11 → 09/11 : Gojo GAGNE (l'utilisateur : « jamais il perd contre Shibuya Sukuna »), « Nah, I'd win » avant Sukuna
    J = L + "Jujutsu Kaisen/"
    GOJO = {"name": "Gojo", "image_path": L + "_gauntlet/nah id win.jpg"}          # l'icône = « Nah, I'd win »
    JJK_THEME = {"hero": (110, 200, 255), "boss": (220, 30, 70), "accent": (180, 120, 255), "title2": (120, 205, 255),
                 "bg": ((22, 8, 40), (4, 4, 14)), "grid": (60, 40, 110),
                 "glows": [(0.15, 0.2, 380, (140, 60, 255)), (0.9, 0.55, 420, (40, 120, 255)), (0.4, 0.95, 360, (200, 20, 60))],
                 "font": "tools/money_sim/fonts/anton.woff2"}
    import os
    JJK_MUSIC = os.environ.get("GAUNTLET_MUSIC") or next((str(p_) for p_ in Path("library/_music").glob("*") if any(w in p_.name.lower() for w in ("jjk", "jujutsu", "gojo", "kaisen"))), None)
    foes = [{"name": n, "image_path": J + p} for n, p in [
        ("Nobara", "Nobara Kugisaki/nobara.png"), ("Megumi", "Megumi Fushiguro/megumi.jpg"),
        ("Yuji", "Yuji Itadori/Yuji.jpg"), ("Todo", "Aoi Todo/Todo.png"), ("Choso", "Choso/choso.png"),
        ("Hanami", "Hanami/1340746.jpeg"), ("Mahito", "Mahito/mahito.png"), ("Jogo", "Jogo/1350459.jpeg"),
        ("Toji", "Toji Fushiguro/toji.jpg"), ("Mahoraga", "Mahoraga/1409410.png"), ("Shibuya Sukuna", "Sukuna/sukuna.jpg")]]
    foes[3].update(gag=True, gag_s=1.4, say="What kind of women are you into? 👏")
    foes[8].update(gag=True, gag_s=1.4, say="Long time no see, Satoru.")
    foes[9].update(gag=True, gag_s=1.4, say="⚙️ *the wheel turns*", gag_label="ADAPTING...")
    foes[10].update(gag=True, gag_s=2.2, panel=L + "_gauntlet/nah id win.jpg")
    foes[9]["hits"] = 3
    foes[10]["hits"] = 5
    print(gauntlet.generate(GOJO, foes, universe="Jujutsu Kaisen", seed=int(sys.argv[-1]) if sys.argv[-1].isdigit() else 4,
                            base_hits=1, step_hits=0, lose_at=None,
                            title=("CAN GOJO", "SURVIVE THE JJK GAUNTLET?"), theme=JJK_THEME, music=JJK_MUSIC, music_start=float(os.environ.get("GAUNTLET_MUSIC_START", "0")),
                            out=OUT / "Gauntlet - Gojo survive.mp4"))
if "sukuna" in sys.argv:                              # 07/11 : Sukuna (Shibuya, 15 doigts) tombe contre Itachi
    import os
    SUK = {"name": "Sukuna", "image_path": L + "Jujutsu Kaisen/Sukuna/sukuna.jpg"}
    SUK_THEME = {"hero": (230, 40, 60), "boss": (255, 140, 30), "accent": (255, 200, 60), "title2": (255, 150, 60),
                 "bg": ((40, 6, 10), (8, 4, 6)), "grid": (110, 40, 30),
                 "glows": [(0.15, 0.2, 380, (220, 30, 40)), (0.9, 0.55, 420, (255, 130, 20)), (0.4, 0.95, 360, (120, 10, 30))],
                 "font": "tools/money_sim/fonts/anton.woff2"}
    foes = [{"name": n, "image_path": N + p} for n, p in [
        ("TenTen", "TenTen/TenTen.jpg"), ("Sakura", "Sakura/Sakura.jpg"), ("Tsunade", "Tsunade/Tsunade.png"),
        ("Orochimaru", "Orochimaru/Orochimaru.jpg"), ("Jiraiya", "Jiraya/Jiraya.png"), ("Raikage", "Raikage/Raikage.jpg"),
        ("Itachi", "Itachi/Itachi.jpg"), ("Pain", "Pain/Pain.jpg"), ("Minato", "Minato/Minato.jpg"),
        ("Obito", "Obito/Obito.png"), ("Madara", "Madara/Madara.jpg")]]
    foes.append({"name": "Naruto", "image_path": L + "_fusion/Naruto/8 SIX PATH.jpg"})   # la liste continue : pas de spoil
    foes[1].update(gag=True, gag_s=1.3, say="SHANNAROOO! 👊")
    foes[3].update(gag=True, gag_s=1.5, say="What a fine vessel... I want that body 🐍")
    foes[6].update(gag=True, gag_s=1.5, say="You're already in my genjutsu.", gag_label="SHARINGAN")
    music = os.environ.get("GAUNTLET_MUSIC") or "library/_music/Naruto Shippuden OST 1 - Track 26 - Keisei Gyakuten ( Reverse Situation ).mp3"
    print(gauntlet.generate(SUK, foes, universe="Naruto", seed=int(sys.argv[-1]) if sys.argv[-1].isdigit() else 4,
                            base_hits=1, step_hits=0, lose_at=6, lose_after=3.0, lose_move="TSUKUYOMI!",
                            title=("CAN SHIBUYA SUKUNA", "SURVIVE THE NARUTO GAUNTLET?"), theme=SUK_THEME, music=music,
                            music_start=float(os.environ.get("GAUNTLET_MUSIC_START", "0")), music_gain=0.22,
                            out=OUT / "Gauntlet - Sukuna vs Naruto.mp4"))
if "ichigo" in sys.argv:                              # 08/11 : True Bankai Ichigo bat tout le Naruto verse (avis Reddit), Baryon compris ; boss finaux en plusieurs coups
    import os
    ICH = {"name": "Ichigo", "image_path": L + "_fusion/Ichigo/6 True Bankai.jpg"}
    ICH_THEME = {"hero": (255, 140, 40), "boss": (170, 80, 255), "accent": (255, 200, 60), "title2": (255, 150, 50),
                 "bg": ((20, 12, 24), (4, 4, 8)), "grid": (70, 50, 40),
                 "glows": [(0.15, 0.2, 380, (255, 120, 20)), (0.9, 0.55, 420, (120, 60, 255)), (0.4, 0.95, 360, (200, 40, 20))],
                 "font": "tools/money_sim/fonts/anton.woff2"}
    foes = [{"name": n, "image_path": N + p} for n, p in [
        ("Ichiraku", "Teuchi/Teuchi.jpg"), ("TenTen", "TenTen/TenTen.jpg"), ("Sakura", "Sakura/Sakura.jpg"),
        ("Tsunade", "Tsunade/Tsunade.png"), ("Jiraiya", "Jiraya/Jiraya.png"), ("Orochimaru", "Orochimaru/Orochimaru.jpg"),
        ("Kakashi", "Kakashi/Kakashi.jpg"), ("Raikage", "Raikage/Raikage.jpg"), ("Minato", "Minato/Minato.jpg"),
        ("Itachi", "Itachi/Itachi.jpg"), ("Pain", "Pain/Pain.jpg"), ("Obito", "Obito/Obito.png")]]
    foes.append({"name": "Madara", "image_path": L + "_fusion/Madara/7 six path madara.jpg"})
    foes.append({"name": "Six Paths Naruto", "image_path": L + "_fusion/Naruto/8 SIX PATH.jpg"})
    foes.append({"name": "Baryon Naruto", "image_path": L + "_fusion/Naruto/9 Baryon Mode.jpg"})
    for j, h in ((12, 2), (13, 3), (14, 4)):   # Madara, Naruto SP, Baryon : pas en 1 coup
        foes[j]["hits"] = h
    foes[14].update(gag=True, gag_s=1.6, say="Kurama... let's end this! 🔥", gag_label="BARYON MODE!")
    foes[0].update(gag=True, gag_s=1.3, say="Free ramen if you lose! 🍜")
    foes[2].update(gag=True, gag_s=1.3, say="SHANNAROOO! 👊")
    foes[8]["tp"] = True
    foes[9]["fake"] = True
    foes[11]["kamui"] = True
    foes[12].update(gag=True, gag_s=1.6, say="Wake up to reality. 🌙")
    music = os.environ.get("GAUNTLET_MUSIC") or "library/_music/Bleach OST 3 - Clavar La Espada.mp3"
    print(gauntlet.generate(ICH, foes, universe="Naruto", seed=int(sys.argv[-1]) if sys.argv[-1].isdigit() else 4,
                            base_hits=1, step_hits=0, lose_at=None,
                            title=("CAN TRUE BANKAI ICHIGO", "SURVIVE THE NARUTO GAUNTLET?"), theme=ICH_THEME, music=music,
                            music_start=float(os.environ.get("GAUNTLET_MUSIC_START", "24")), music_gain=0.26,
                            out=OUT / "Gauntlet - Ichigo vs Naruto.mp4"))
if "toji" in sys.argv:                                # 09/11 : Toji rate Jogo (pet), « Nah, I'd win », Jogo le tue (meme demandé par l'utilisateur)
    import os
    J = L + "Jujutsu Kaisen/"
    TOJI = {"name": "Toji", "image_path": J + "Toji Fushiguro/toji.jpg"}
    TOJI_THEME = {"hero": (120, 230, 140), "boss": (220, 30, 60), "accent": (190, 255, 120), "title2": (150, 235, 150),
                  "bg": ((8, 26, 18), (4, 6, 6)), "grid": (40, 90, 60),
                  "glows": [(0.15, 0.2, 380, (40, 160, 90)), (0.9, 0.55, 420, (120, 40, 160)), (0.4, 0.95, 360, (200, 20, 50))],
                  "font": "tools/money_sim/fonts/anton.woff2"}
    foes = [{"name": n, "image_path": J + p} for n, p in [
        ("Nobara", "Nobara Kugisaki/nobara.png"), ("Megumi", "Megumi Fushiguro/megumi.jpg"), ("Yuji", "Yuji Itadori/Yuji.jpg"),
        ("Maki", "Maki Zenin/makinormale.jpg"), ("Todo", "Aoi Todo/Todo.png"), ("Hanami", "Hanami/1340746.jpeg"),
        ("Dagon", "Dagon/1340750.png"), ("Mahito", "Mahito/mahito.png"), ("Jogo", "Jogo/1350459.jpeg"),
        ("Hakari", "Kinji Hakari/hakari.jpeg"), ("Geto", "Suguru Geto/geto.png"), ("Kashimo", "Hajime Kashimo/Kashimo.jpg"),
        ("Yuta", "Yuta Okkotsu/yuta.jpg"), ("Gojo", "Satoru Gojo/gojo.png"), ("Mahoraga", "Mahoraga/1409410.png"),
        ("Sukuna", "Sukuna/sukuna.jpg")]]
    foes[1].update(gag=True, gag_s=1.5, say="...Dad?")
    foes[6].update(gag=True, gag_s=1.4, say="Not this guy again 🐟")
    foes[13].update(gag=True, gag_s=1.6, say="Didn't I kill you already?")
    foes[14].update(gag=True, gag_s=1.4, say="⚙️ *the wheel turns*", gag_label="ADAPTING...")
    foes[8].update(meme=L + "_gauntlet/jogo nah id win.jpg", panel=L + "_gauntlet/jogo nah id win.jpg", gag_s=2.2, miss_after=1.0,
                   miss_sound=L + "_sounds/meme/fart with reverb.mp3", miss_gain=0.8)
    foes[13]["hits"] = 3
    foes[14]["hits"] = 3
    music = os.environ.get("GAUNTLET_MUSIC") or "library/_music/Delirious.mp3"
    print(gauntlet.generate(TOJI, foes, universe="Jujutsu Kaisen", seed=int(sys.argv[-1]) if sys.argv[-1].isdigit() else 4,
                            base_hits=1, step_hits=0, lose_at=8, lose_after=99.0, lose_move="NAH, I'D WIN.",
                            title=("CAN TOJI", "SURVIVE THE JJK GAUNTLET?"), theme=TOJI_THEME, music=music,
                            music_start=float(os.environ.get("GAUNTLET_MUSIC_START", "0")), music_gain=0.2,
                            out=OUT / "Gauntlet - Toji vs JJK.mp4"))
if "gokujjk" in sys.argv:                            # 10/11 : Base Goku bat tout le JJK verse (comme vs Naruto / One Piece, 1M vues)
    import os
    J = L + "Jujutsu Kaisen/"
    JJK_THEME = {"hero": (255, 170, 60), "boss": (220, 30, 70), "accent": (180, 120, 255), "title2": (255, 190, 80),
                 "bg": ((22, 8, 40), (4, 4, 14)), "grid": (60, 40, 110),
                 "glows": [(0.15, 0.2, 380, (140, 60, 255)), (0.9, 0.55, 420, (255, 120, 40)), (0.4, 0.95, 360, (200, 20, 60))],
                 "font": "tools/money_sim/fonts/anton.woff2"}
    foes = [{"name": n, "image_path": J + p} for n, p in [
        ("Nobara", "Nobara Kugisaki/nobara.png"), ("Megumi", "Megumi Fushiguro/megumi.jpg"), ("Yuji", "Yuji Itadori/Yuji.jpg"),
        ("Maki", "Maki Zenin/makinormale.jpg"), ("Todo", "Aoi Todo/Todo.png"), ("Hanami", "Hanami/1340746.jpeg"),
        ("Mahito", "Mahito/mahito.png"), ("Jogo", "Jogo/1350459.jpeg"), ("Toji", "Toji Fushiguro/toji.jpg"),
        ("Hakari", "Kinji Hakari/hakari.jpeg"), ("Yuta", "Yuta Okkotsu/yuta.jpg"), ("Mahoraga", "Mahoraga/1409410.png")]]
    foes.append({"name": "Gojo", "image_path": L + "_gauntlet/nah id win.jpg"})
    foes.append({"name": "Sukuna", "image_path": J + "Sukuna/sukuna.jpg"})
    foes[2].update(gag=True, gag_s=1.3, say="BLACK FLASH! ⚡")
    foes[4].update(gag=True, gag_s=1.4, say="What kind of women are you into? 👏")
    foes[11].update(gag=True, gag_s=1.4, say="*clank* ⚙️", gag_label="ADAPTING...")
    foes[12].update(gag=True, gag_s=2.2, panel=L + "_gauntlet/nah id win.jpg")
    foes[11]["hits"] = 2
    foes[12]["hits"] = 3
    foes[13]["hits"] = 4
    music = os.environ.get("GAUNTLET_MUSIC") or "library/_music/Delirious.mp3"
    print(gauntlet.generate(GOKU, foes, universe="Jujutsu Kaisen", seed=int(sys.argv[-1]) if sys.argv[-1].isdigit() else 4,
                            base_hits=1, step_hits=0, lose_at=None,
                            title=("CAN BASE GOKU", "BEAT THE JJK GAUNTLET?"), theme=JJK_THEME, music=music,
                            music_start=float(os.environ.get("GAUNTLET_MUSIC_START", "0")), music_gain=0.2,
                            out=OUT / "Gauntlet - Goku vs JJK.mp4"))
if "gojodb" in sys.argv:                              # 12/11 : Gojo vs Dragon Ball verse ; idée de l'utilisateur : il meurt DIRECT contre Frieza (la vidéo s'arrête net, c'est le gag)
    import os
    F = L + "_fusion/"
    GOJO = {"name": "Gojo", "image_path": L + "Jujutsu Kaisen/Satoru Gojo/gojo.png"}
    GDB_THEME = {"hero": (110, 200, 255), "boss": (200, 120, 255), "accent": (255, 190, 60), "title2": (120, 205, 255),
                 "bg": ((20, 8, 40), (4, 4, 14)), "grid": (70, 40, 120),
                 "glows": [(0.15, 0.2, 380, (140, 60, 255)), (0.9, 0.55, 420, (255, 150, 30)), (0.4, 0.95, 360, (90, 40, 200))],
                 "font": "tools/money_sim/fonts/anton.woff2"}
    foes = [{"name": n, "image_path": p} for n, p in [
        ("Frieza", F + "Frieza/4 FINAL FORM.jpg"), ("Perfect Cell", F + "Cell/4 PERFECT CELLL.jpg"),
        ("Kid Buu", F + "Buu/7 KID BUU.jpg"), ("Gohan", F + "Gohan/3 Gohan SSJ2.jpg"),
        ("Vegeta", F + "Vegeta/5 SSJBLUE.jpg"), ("Goku", F + "Goku/4 SSJ3.jpg"),
        ("Golden Frieza", F + "Frieza/6 GOLDEN.jpg"), ("Beast Gohan", F + "Gohan/5 Gohan Beast.jpg"),
        ("Beerus", L + "Dragon Ball Super/Beerus/Beerus.png"), ("Goku", F + "Goku/8 uimastered.jpg")]]
    foes[0].update(gag=True, gag_s=1.6, say="Ohohoho~ a human? 🤭")
    foes[1].update(gag=True, gag_s=1.3, say="PERFECT! 😈")
    foes[4].update(gag=True, gag_s=1.3, say="I am the prince of all Saiyans! 👑")
    foes[8].update(gag=True, gag_s=2.2, panel=L + "_gauntlet/nah id win.jpg")
    for i_, h_ in ((5, 2), (6, 2), (7, 3)):
        foes[i_]["hits"] = h_
    music = os.environ.get("GAUNTLET_MUSIC") or "library/_music/Delirious.mp3"
    print(gauntlet.generate(GOJO, foes, universe="Dragon Ball", seed=int(sys.argv[-1]) if sys.argv[-1].isdigit() else 4,
                            base_hits=1, step_hits=0, lose_at=0, lose_after=2.4, lose_move="DEATH BEAM.",
                            title=("CAN GOJO SURVIVE", "THE DRAGON BALL GAUNTLET?"), theme=GDB_THEME, music=music,
                            music_start=float(os.environ.get("GAUNTLET_MUSIC_START", "0")), music_gain=0.2,
                            out=OUT / "Gauntlet - Gojo vs Dragon Ball.mp4"))
