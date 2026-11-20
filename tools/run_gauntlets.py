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
if "luffynaruto" in sys.argv:                         # 15/11 : Gear 5 Luffy passe tout le Naruto verse… et perd contre Naruto Baryon (choix de l'utilisateur : « Luffy ne peut pas battre Naruto »)
    import os
    LUF = {"name": "Luffy", "image_path": L + "_fusion/Luffy/6 Gear 5.jpg"}
    LUF_THEME = {"hero": (240, 240, 255), "boss": (255, 140, 40), "accent": (255, 210, 70), "title2": (255, 220, 120),
                 "bg": ((30, 14, 40), (6, 4, 10)), "grid": (90, 60, 110),
                 "glows": [(0.15, 0.2, 380, (200, 120, 255)), (0.9, 0.55, 420, (255, 140, 40)), (0.4, 0.95, 360, (255, 255, 255))],
                 "font": "tools/money_sim/fonts/anton.woff2"}
    foes = [{"name": n, "image_path": N + p} for n, p in [
        ("Ichiraku", "Teuchi/Teuchi.jpg"), ("TenTen", "TenTen/TenTen.jpg"), ("Sakura", "Sakura/Sakura.jpg"),
        ("Jiraiya", "Jiraya/Jiraya.png"), ("Orochimaru", "Orochimaru/Orochimaru.jpg"), ("Kakashi", "Kakashi/Kakashi.jpg"),
        ("Raikage", "Raikage/Raikage.jpg"), ("Minato", "Minato/Minato.jpg"), ("Itachi", "Itachi/Itachi.jpg"),
        ("Pain", "Pain/Pain.jpg"), ("Obito", "Obito/Obito.png")]]
    foes.append({"name": "Naruto", "image_path": L + "_fusion/Naruto/9 Baryon Mode.jpg"})
    foes[0].update(gag=True, gag_s=1.4, say="Free ramen if you lose! 🍜", gag_label="LUFFY IS EATING...")
    foes[2].update(gag=True, gag_s=1.3, say="SHANNAROOO! 👊")
    foes[4].update(gag=True, gag_s=1.4, say="What a fine vessel... 🐍")
    foes[7]["tp"] = True
    foes[8]["fake"] = True
    foes[10]["kamui"] = True
    foes[11].update(gag=True, gag_s=1.5, say="Not in my village. 🦊")
    music = os.environ.get("GAUNTLET_MUSIC") or "library/_music/Drums of Liberation x Overtaken (Gear 5 cover).mp3"
    print(gauntlet.generate(LUF, foes, universe="Naruto", seed=int(sys.argv[-1]) if sys.argv[-1].isdigit() else 4,
                            base_hits=1, step_hits=0, lose_at=11, lose_after=3.4, lose_move="BARYON MODE.",
                            title=("CAN GEAR 5 LUFFY", "SURVIVE THE NARUTO GAUNTLET?"), theme=LUF_THEME, music=music,
                            music_start=float(os.environ.get("GAUNTLET_MUSIC_START", "60")), music_gain=0.2,
                            out=OUT / "Gauntlet - Luffy vs Naruto.mp4"))
if "gokuall" in sys.argv:                             # 18/11 : Base Goku vs TOUS les animes (les gauntlets Base Goku = 1,5M / 390k / 253k)
    import os
    F = L + "_fusion/"
    ALL_THEME = {"hero": (255, 170, 60), "boss": (230, 40, 60), "accent": (255, 210, 70), "title2": (255, 190, 80),
                 "bg": ((26, 10, 30), (5, 4, 12)), "grid": (80, 50, 90),
                 "glows": [(0.15, 0.2, 380, (255, 120, 40)), (0.9, 0.55, 420, (140, 60, 255)), (0.4, 0.95, 360, (220, 30, 60))],
                 "font": "tools/money_sim/fonts/anton.woff2"}
    foes = [{"name": n, "image_path": p} for n, p in [
        ("Light", L + "Death Note/Light Yagami/LightYagami.jpg"),
        ("Levi", L + "Attack on Titan/Levi Ackerman/Levi.jpg"),
        ("Stain", L + "My Hero Academia/Stain/Stain.jpg"),
        ("Rengoku", L + "Demon Slayer/Kyojuro Rengoku/Rengoku.jpg"),
        ("Sanji", OP + "Sanji/Sanji.jpg"),
        ("Zoro", F + "Luffy/7 Zoro.jpeg"),
        ("Kakashi", N + "Kakashi/Kakashi.jpg"),
        ("Joseph", F + "JoJo/2 JOSEPH.jpg"),
        ("Itachi", N + "Itachi/Itachi.jpg"),
        ("Toji", L + "Jujutsu Kaisen/Toji Fushiguro/toji.jpg"),
        ("DIO", F + "JoJo Villains/05 DIO.jpg"),
        ("Ichigo", F + "Ichigo/6 True Bankai.jpg"),
        ("Gojo", L + "_gauntlet/nah id win.jpg"),
        ("Sukuna", L + "Jujutsu Kaisen/Sukuna/sukuna.jpg"),
        ("Kaido", L + "_domain/forms/Kaido/3 Hybrid.jpg"),
        ("Madara", F + "Madara/7 six path madara.jpg"),
        ("Luffy Gear 5", F + "Luffy/6 Gear 5.jpg"),
        ("Naruto", F + "Naruto/9 Baryon Mode.jpg")]]
    foes[0].update(gag=True, gag_s=1.6, say="I wrote your name 📓", gag_label="40 SECONDS...")
    foes[3].update(gag=True, gag_s=1.3, say="Set your heart ablaze! 🔥")
    foes[4].update(gag=True, gag_s=1.6, say="Wait! Let me cook for you first 🍳", gag_label="SANJI IS COOKING...")
    foes[5].update(gag=True, gag_s=1.7, fx="lost", say="Where am I? 🗺️", gag_label="ZORO GOT LOST...")
    foes[7].update(gag=True, gag_s=1.5, say="Your next line is... 😏")
    foes[8]["fake"] = True
    foes[10].update(gag=True, gag_s=1.5, say="ZA WARUDO! ⏱️", gag_label="TIME STOPPED...")
    foes[12].update(gag=True, gag_s=2.2, panel=L + "_gauntlet/nah id win.jpg")
    foes[16].update(gag=True, gag_s=1.5, fx="inflate", say="HAHAHA! 😂", gag_label="GEAR 5!")
    foes[17].update(gag=True, gag_s=1.4, say="Not in my world. 🦊")
    for i_, h_ in ((13, 2), (14, 2), (15, 3), (16, 3), (17, 4)):
        foes[i_]["hits"] = h_
    music = os.environ.get("GAUNTLET_MUSIC") or "library/_music/Delirious.mp3"
    print(gauntlet.generate(GOKU, foes, universe="Anime", seed=int(sys.argv[-1]) if sys.argv[-1].isdigit() else 4,
                            base_hits=1, step_hits=0, lose_at=None,
                            title=("CAN BASE GOKU", "BEAT EVERY ANIME?"), theme=ALL_THEME, music=music,
                            music_start=float(os.environ.get("GAUNTLET_MUSIC_START", "0")), music_gain=0.2,
                            out=OUT / "Gauntlet - Goku vs every anime.mp4"))
if "josephall" in sys.argv:                           # 20/11 : Joseph Joestar vs tous les animes, gags « Joseph » (Nigerundayo, Your next line…)
    import os
    F = L + "_fusion/"
    V = F + "JoJo Villains/"
    JOS_THEME = {"hero": (60, 210, 150), "boss": (230, 40, 60), "accent": (255, 210, 70), "title2": (90, 225, 170),
                 "bg": ((10, 26, 24), (4, 8, 10)), "grid": (40, 80, 70),
                 "glows": [(0.15, 0.2, 380, (40, 200, 140)), (0.9, 0.55, 420, (140, 60, 255)), (0.4, 0.95, 360, (220, 30, 60))],
                 "font": "tools/money_sim/fonts/anton.woff2"}
    JOSEPH = {"name": "Joseph", "image_path": F + "JoJo/2 JOSEPH.jpg"}
    foes = [{"name": n, "image_path": p} for n, p in [
        ("Light", L + "Death Note/Light Yagami/LightYagami.jpg"),
        ("Rengoku", L + "Demon Slayer/Kyojuro Rengoku/Rengoku.jpg"),
        ("Sanji", OP + "Sanji/Sanji.jpg"),
        ("Zoro", F + "Luffy/7 Zoro.jpeg"),
        ("Kakashi", N + "Kakashi/Kakashi.jpg"),
        ("Itachi", N + "Itachi/Itachi.jpg"),
        ("Toji", L + "Jujutsu Kaisen/Toji Fushiguro/toji.jpg"),
        ("Wamuu", V + "02 WAMUU.jpg"),
        ("Esidisi", V + "03 ESIDISI.jpg"),
        ("Kars", V + "04 KARS.jpg"),
        ("DIO", V + "05 DIO.jpg"),
        ("Ichigo", F + "Ichigo/6 True Bankai.jpg"),
        ("Gojo", L + "_gauntlet/nah id win.jpg"),
        ("Sukuna", L + "Jujutsu Kaisen/Sukuna/sukuna.jpg"),
        ("Kaido", L + "_domain/forms/Kaido/3 Hybrid.jpg"),
        ("Madara", F + "Madara/7 six path madara.jpg"),
        ("Luffy Gear 5", F + "Luffy/6 Gear 5.jpg"),
        ("Naruto", F + "Naruto/9 Baryon Mode.jpg")]]
    foes[0].update(gag=True, gag_s=1.7, say="I wrote your name 📓", gag_label="HE MISSPELLED JOESTAR")
    foes[1].update(gag=True, gag_s=1.3, say="Set your heart ablaze! 🔥")
    foes[2].update(gag=True, gag_s=1.6, say="Wait! Let me cook for you first 🍳", gag_label="SANJI IS COOKING...")
    foes[3].update(gag=True, gag_s=1.7, fx="lost", say="Where am I? 🗺️", gag_label="ZORO GOT LOST...")
    foes[4].update(gag=True, gag_s=1.5, say="I copied your best move 😑", gag_label="HE COPIED... RUNNING AWAY")
    foes[5]["fake"] = True
    foes[6].update(gag=True, gag_s=1.7, say="Your next line is: \"HOW?!\" 😏", gag_label="JOSEPH READ HIS MIND")
    foes[8].update(gag=True, gag_s=1.5, say="AAAAHHH!! 😭", gag_label="ESIDISI IS CRYING...")
    foes[9].update(gag=True, gag_s=1.7, say="I am the ultimate being! 🌋", gag_label="SENT TO SPACE")
    foes[10].update(gag=True, gag_s=1.6, say="ZA WARUDO! ⏱️", gag_label="NIGERUNDAYO!")
    foes[12].update(gag=True, gag_s=2.2, panel=L + "_gauntlet/nah id win.jpg")
    foes[16].update(gag=True, gag_s=1.5, fx="inflate", say="HAHAHA! 😂", gag_label="GEAR 5!")
    foes[17].update(gag=True, gag_s=1.6, say="Not in my world. 🦊", gag_label="OH MY GOD!")
    for i_, h_ in ((13, 2), (14, 2), (15, 3), (16, 3), (17, 4)):
        foes[i_]["hits"] = h_
    music = os.environ.get("GAUNTLET_MUSIC") or None
    print(gauntlet.generate(JOSEPH, foes, universe="Anime", seed=int(sys.argv[-1]) if sys.argv[-1].isdigit() else 4,
                            base_hits=1, step_hits=0, lose_at=None,
                            title=("CAN JOSEPH JOESTAR", "BEAT EVERY ANIME?"), theme=JOS_THEME, music=music,
                            music_start=float(os.environ.get("GAUNTLET_MUSIC_START", "0")), music_gain=0.2,
                            out=OUT / "Gauntlet - Joseph vs every anime.mp4"))
if "josephskits" in sys.argv:                         # 21/11 : Joseph vs every anime v2 — 12 adversaires, UN sketch chacun, twist Jotaro
    import os
    F = L + "_fusion/"
    V = F + "JoJo Villains/"
    SJ = L + "_sounds/jojo_villains/"
    JOS_THEME = {"hero": (60, 210, 150), "boss": (230, 40, 60), "accent": (255, 210, 70), "title2": (90, 225, 170),
                 "bg": ((10, 26, 24), (4, 8, 10)), "grid": (40, 80, 70),
                 "glows": [(0.15, 0.2, 380, (40, 200, 140)), (0.9, 0.55, 420, (140, 60, 255)), (0.4, 0.95, 360, (220, 30, 60))],
                 "font": "tools/money_sim/fonts/anton.woff2"}
    JOSEPH = {"name": "Joseph", "image_path": F + "JoJo/2 JOSEPH.jpg"}
    W_ = (255, 255, 255)
    foes = [
        dict(name="Light", image_path=L + "Death Note/Light Yagami/LightYagami.jpg", skit="deathnote", gag_s=2.6,
             auto_ko="leave", ko_boom=False, ko_sub="HEART ATTACK",
             lines=[(0.0, 1.0, "foe", "I'll write your name... 📓"), (1.45, 2.6, "hero", "Nah. YOURS 😏")],
             label=(0.95, "JOSEPH STOLE THE NOTE")),
        dict(name="Zoro", image_path=F + "Luffy/7 Zoro.jpeg", skit="lost", gag_s=2.5, auto_ko="leave", ko_boom=False,
             ko_text="LOST!", ko_sub="HE'S STILL WALKING", whoosh=[1.5],
             lines=[(0.0, 1.1, "hero", "The fight is that way! 👈"), (1.0, 1.6, "foe", "Thanks! 😁")],
             label=(1.7, "ZORO GOT LOST...")),
        dict(name="Sanji", image_path=L + "One Piece/Sanji/Sanji.jpg", skit="letter", gag_s=2.7, auto_ko="leave",
             ko_boom=False, ko_sub="NOSEBLEED",
             lines=[(0.0, 1.0, "hero", "A girl wrote you this 💌"), (1.0, 1.9, "foe", "MELLORINE~ ❤️")]),
        dict(name="Kakashi", image_path=L + "Naruto/Kakashi/Kakashi.jpg", skit="copy", gag_s=2.5, auto_ko="leave",
             hero_exit=True, ko_boom=False, ko_text="BOTH RAN AWAY", ko_sub="KAKASHI", whoosh=[1.45],
             lines=[(0.0, 1.35, "foe", "I copied your best technique. 😑")], label=(1.3, "...RUNNING AWAY")),
        dict(name="Itachi", image_path=L + "Naruto/Itachi/Itachi.jpg", skit="goggles", gag_s=2.3, hits=1,
             lines=[(0.0, 1.0, "foe", "Tsukuyomi."), (1.25, 2.3, "hero", "Nice try 😎")],
             label=(1.05, "GENJUTSU BLOCKED", (255, 90, 90))),
        dict(name="Esidisi", image_path=V + "03 ESIDISI.jpg", skit="crying", gag_s=2.4, hits=1,
             lines=[(0.0, 1.5, "foe", "AAAAHHH!! 😭"), (1.55, 2.4, "hero", "Are you done? 🙄")],
             label=(0.7, "ESIDISI IS CRYING...", (120, 200, 255))),
        dict(name="Goku", image_path=F + "Goku/1 Base.png", skit="eat", gag_s=2.8, auto_ko="leave", ko_boom=False,
             ko_text="FORFEIT!", ko_sub="TOO HUNGRY", ko_y=0.66,
             lines=[(0.0, 0.9, "foe", "Let's fight! 💪"), (0.8, 1.8, "hero", "Let's eat first 🍜"),
                    (1.95, 2.8, "foe", "Itadakimasu! 😋")],
             label=(1.9, "GOKU FORGOT THE FIGHT")),
        dict(name="Sukuna", image_path=L + "Jujutsu Kaisen/Sukuna/sukuna.jpg", skit="lookbehind", gag_s=2.0,
             auto_ko="hit", whoosh=[1.45],
             lines=[(0.0, 0.95, "hero", "Look, Gojo! 👉"), (0.7, 1.45, "foe", "?!")],
             label=(1.5, "CHEAP SHOT!", (255, 214, 10))),
        dict(name="Gojo", image_path=L + "Jujutsu Kaisen/Satoru Gojo/Gojo.jpg", skit="nextline", gag_s=3.0, hits=2,
             sounds=[(1.5, SJ + "dojyaan.mp3", 0.9, 2.0)],
             lines=[(0.0, 1.5, "hero", "Your next line is: \"Nah, I'd win.\" 😏"), (1.5, 2.45, "foe", "Nah, I'd win."),
                    (2.45, 3.0, "foe", "...wait, HOW?! 😳")],
             label=(1.6, "JOSEPH READ HIS MIND", (255, 214, 10))),
        dict(name="Kars", image_path=V + "04 KARS.jpg", skit="kars", gag_s=1.3, hits=2, ko_fx="volcano", ko_pause=2.7,
             ko_text="SENT TO SPACE", ko_sub="HE STOPPED THINKING", ko_text_at=0.75, ko_y=0.62,
             sounds=[(0.0, SJ + "pillar men.mp3", 0.6, 1.8)],
             lines=[(0.0, 1.3, "foe", "I am the ultimate being! 😈")]),
        dict(name="DIO", image_path=V + "05 DIO.jpg", skit="zawarudo", gag_s=3.2, auto_ko="hit", whoosh=[0.3, 2.7],
             sounds=[(0.0, SJ + "za warudo.mp3", 1.0, 2.6)],
             lines=[(0.0, 0.95, "foe", "ZA WARUDO! ⏱️"), (1.15, 2.55, "foe", "Where did he go?! 😡")],
             label=(2.75, "BEHIND YOU!", (255, 214, 10))),
        dict(name="Jotaro", image_path=F + "JoJo/3 JOTARO.jpg", skit="grandson", gag_s=2.7, ora=True,
             lines=[(0.0, 1.5, "hero", "I can't hit my own grandson... 🥺"), (1.5, 2.7, "foe", "Yare yare daze.")]),
    ]
    for f_ in foes:
        f_.update(gag=True, stage=True)
    music = os.environ.get("GAUNTLET_MUSIC") or None
    print(gauntlet.generate(JOSEPH, foes, universe="Anime", seed=int(sys.argv[-1]) if sys.argv[-1].isdigit() else 4,
                            base_hits=1, step_hits=0, lose_at=11, lose_after=2.8, lose_move=" ",
                            lose_cta="Did Joseph deserve this? Comment 👇",
                            title=("CAN JOSEPH JOESTAR", "BEAT EVERY ANIME?"), theme=JOS_THEME, music=music,
                            music_start=float(os.environ.get("GAUNTLET_MUSIC_START", "0")), music_gain=0.2,
                            out=OUT / "Gauntlet - Joseph vs every anime v2.mp4"))
