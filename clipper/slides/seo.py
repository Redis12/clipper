"""Référencement (SEO) des vidéos générées : titre, description, tags et hashtags prêts à copier pour
YouTube Shorts, TikTok et Instagram, à partir des infos de la vidéo (.json). Gratuit (modèles, pas d'API).

Règles appliquées (2026) :
- titre YouTube ≤ 70 caractères, mot-clé principal (les noms) AU DÉBUT, question qui pousse à commenter ;
  jamais le gagnant (sinon personne ne regarde jusqu'au bout) ;
- description : 1re phrase avec les mots que les gens tapent (« Gojo vs Sukuna who would win »),
  appel au commentaire, puis 3 à 5 hashtags (les 3 premiers s'affichent au-dessus du titre ; > 15 = tous ignorés) ;
- TikTok : la légende est indexée par la recherche TikTok → phrase avec les mots-clés + 4 hashtags ;
- Instagram : 5 hashtags maximum (limite d'Instagram), mots-clés dans la légende.
"""
from __future__ import annotations

import re

from .. import db

FRANCHISES = [   # mot dans le nom de l'anime (dossier de la bibliothèque) → (nom propre, hashtags)
    ("jujutsu", "Jujutsu Kaisen", ["jjk", "jujutsukaisen"]),
    ("dragon ball", "Dragon Ball", ["dragonball", "dbz"]),
    ("naruto", "Naruto", ["naruto", "narutoshippuden"]),
    ("boruto", "Boruto", ["boruto", "naruto"]),
    ("one piece", "One Piece", ["onepiece"]),
    ("bleach", "Bleach", ["bleach"]),
    ("jojo", "JoJo's Bizarre Adventure", ["jojo", "jjba"]),
    ("demon slayer", "Demon Slayer", ["demonslayer", "kimetsunoyaiba"]),
    ("kimetsu", "Demon Slayer", ["demonslayer", "kimetsunoyaiba"]),
    ("death note", "Death Note", ["deathnote"]),
    ("hunter", "Hunter x Hunter", ["hxh", "hunterxhunter"]),
    ("attack on titan", "Attack on Titan", ["aot", "attackontitan"]),
    ("shingeki", "Attack on Titan", ["aot", "attackontitan"]),
    ("my hero", "My Hero Academia", ["mha", "myheroacademia"]),
    ("chainsaw", "Chainsaw Man", ["chainsawman"]),
    ("solo leveling", "Solo Leveling", ["sololeveling"]),
    ("cyberpunk", "Cyberpunk Edgerunners", ["edgerunners"]),
    ("tokyo ghoul", "Tokyo Ghoul", ["tokyoghoul"]),
    ("black clover", "Black Clover", ["blackclover"]),
    ("one punch", "One Punch Man", ["onepunchman"]),
    ("mob psycho", "Mob Psycho 100", ["mobpsycho"]),
    ("fullmetal", "Fullmetal Alchemist", ["fma"]),
    ("code geass", "Code Geass", ["codegeass"]),
]
KNOWN = {   # perso sans dossier dans la bibliothèque → anime
    "goku": "dragon ball", "vegeta": "dragon ball", "beerus": "dragon ball", "gohan": "dragon ball",
    "frieza": "dragon ball", "broly": "dragon ball", "gojo": "jujutsu", "sukuna": "jujutsu",
    "mahoraga": "jujutsu", "toji": "jujutsu", "yuji": "jujutsu", "megumi": "jujutsu", "naruto": "naruto",
    "sasuke": "naruto", "itachi": "naruto", "pain": "naruto", "madara": "naruto", "luffy": "one piece",
    "zoro": "one piece", "kaido": "one piece", "ichigo": "bleach", "aizen": "bleach", "dio": "jojo",
    "jotaro": "jojo", "tanjiro": "demon slayer", "muzan": "demon slayer", "light": "death note",
    "gon": "hunter", "killua": "hunter", "eren": "attack on titan", "levi": "attack on titan",
    "deku": "my hero", "denji": "chainsaw", "saitama": "one punch", "jinwoo": "solo leveling",
    "kakashi": "naruto", "minato": "naruto", "obito": "naruto", "jiraiya": "naruto", "gaara": "naruto",
    "hinata": "naruto", "shikamaru": "naruto", "kurama": "naruto", "yuta": "jujutsu", "nanami": "jujutsu",
    "choso": "jujutsu", "todo": "jujutsu", "hakari": "jujutsu", "kashimo": "jujutsu", "jogo": "jujutsu",
    "mahito": "jujutsu", "geto": "jujutsu", "kenjaku": "jujutsu", "maki": "jujutsu", "nobara": "jujutsu",
    "naoya": "jujutsu", "yuki": "jujutsu", "shanks": "one piece", "ace": "one piece", "sanji": "one piece",
    "law": "one piece", "blackbeard": "one piece", "whitebeard": "one piece", "mihawk": "one piece",
    "roger": "one piece", "byakuya": "bleach", "kenpachi": "bleach", "yhwach": "bleach", "giorno": "jojo",
    "josuke": "jojo", "joseph": "jojo", "rengoku": "demon slayer", "akaza": "demon slayer", "gojou": "jujutsu",
    "meruem": "hunter", "hisoka": "hunter", "trunks": "dragon ball", "cell": "dragon ball", "jiren": "dragon ball",
}
CORE_TAGS = ["anime", "animebattle", "whowouldwin"]           # hashtags fixes, sur toutes les vidéos et plateformes
STOP = {"son", "the", "of", "de", "no", "d", "monkey", "san", "sama", "kun", "chan"}


def tag(s: str) -> str:
    return re.sub(r"[^0-9a-z]", "", (s or "").lower())


def _franchise(text: str):
    t = (text or "").lower()
    for key, nice, tags in FRANCHISES:
        if key in t:
            return nice, tags
    return None


def anime_of(name: str):
    """(nom de l'anime, hashtags) d'un perso : bibliothèque (dossier Anime/Perso), sinon liste connue."""
    try:
        row = db.query("SELECT anime FROM images WHERE lower(character)=lower(?) AND anime IS NOT NULL LIMIT 1",
                       (name,))
        if not row:
            for w in sorted(name.split(), key=len, reverse=True):
                if len(w) >= 4:
                    row = db.query("SELECT anime FROM images WHERE lower(character) LIKE ? AND anime IS NOT NULL "
                                   "LIMIT 1", (f"%{w.lower()}%",))
                    if row:
                        break
        if row:
            f = _franchise(row[0]["anime"])
            if f:
                return f
            return row[0]["anime"], [tag(row[0]["anime"])]
    except Exception:
        pass
    for w in name.lower().split():
        if w in KNOWN:
            return _franchise(KNOWN[w])
    return None


def char_tags(name: str) -> list[str]:
    """« Satoru Gojo » → gojo, satorugojo ; « Son Goku » → goku."""
    words = [w for w in re.split(r"[\s_.-]+", name) if w]
    out = []
    main = [w for w in words if tag(w) not in STOP and len(tag(w)) >= 3]
    if main:
        out.append(tag(short(name)))                  # le nom qu'on tape (Gojo, Goku, Naruto…)
    if len(words) > 1:
        out.append(tag(name))
    return list(dict.fromkeys(t for t in out if t))


def short(name: str) -> str:
    """Nom que les gens tapent : « Satoru Gojo » → « Gojo », « Son Goku » → « Goku »,
    « Naruto Uzumaki » → « Naruto », « Itachi Uchiha » → « Itachi » (liste connue, puis 1er mot-clé de la fiche)."""
    words = [w for w in name.split() if tag(w) not in STOP]
    for w in words:
        if tag(w) in KNOWN:
            return w
    try:
        from . import movesets
        body = movesets.PRESETS.get(name) or ""
        m = re.search(r"^match:\s*([^,\n]+)", body, re.M)
        if m:
            first = m.group(1).strip()
            for w in words:
                if tag(w) == tag(first):
                    return w
    except Exception:
        pass
    return words[-1] if words else name


def _hashtags(tags: list[str], n: int) -> str:
    return " ".join("#" + t for t in list(dict.fromkeys(t for t in tags if t))[:n])


def build(meta: dict, handle: str = "@animelorehq") -> dict:
    """{youtube: {title, description, tags}, tiktok: caption, instagram: caption}."""
    kind = meta.get("kind") or str(meta.get("file") or "").split("_")[0]
    names = meta.get("names") or meta.get("fighters") or []
    animes = [a for a in (anime_of(n) for n in names) if a]
    ani_names = list(dict.fromkeys(a[0] for a in animes))
    ani_tags = [t for a in animes for t in a[1]]
    ctags = [t for n in names[:2] for t in char_tags(n)[:1]]
    if kind == "domain":
        a, b = short(names[0]), short(names[1])
        title = f"{a} vs {b}: Who Wins? 🤯 Domain War" + (f" #{meta['episode']}" if meta.get("episode") else "")
        hook = f"{a} vs {b} — who would win? Anime battle simulation"
        if ani_names:
            hook += f" ({' x '.join(ani_names)})"
        hook += ". Each fighter uses their real moves, domain and transformation."
        ask = "Comment your pick BEFORE the end 👇 Who should fight next?"
        core = ["animebattle", "whowouldwin"]
        kw = [f"{a} vs {b}", f"{b} vs {a}", f"{a} vs {b} who would win", "domain war", "anime battle",
              "who would win", "anime simulation"]
    elif kind == "powerup":
        a, b = meta.get("hero") or short(names[0]), meta.get("boss") or short(names[1])
        title = f"Can {a} beat {b} in under 60 seconds? 😳"
        hook = f"{a} vs {b}: every hit gets stronger and he transforms. Can he do it before the timer hits 0?"
        ask = "Comment if you think he makes it 👇"
        core = ["satisfying", "animebattle"]
        ctags = [t for n in names[:2] for t in char_tags(n)[:1]]
        kw = [f"{a} vs {b}", "anime simulation", "satisfying", "ball simulation", "who would win"]
    elif kind == "race":
        a, b = short(names[0]), short(names[1])
        title = f"{a} vs {b}: Who Transforms First? ⚡"
        hook = f"{a} vs {b} transformation race — every form, the first to reach the final form wins."
        ask = "Comment who you think wins 👇"
        core = ["animetransformation", "anime"]
        kw = [f"{a} vs {b}", f"{a} transformations", f"{b} transformations", "anime transformation",
              "all forms", "who would win"]
    elif kind == "fusion" or meta.get("tiers") and not names:
        base = re.sub(r"[^\w\s']", "", meta.get("title") or "").strip() or "Anime"
        base = re.sub(r"\s*\b(transformations?|every forms?|all forms?|forms?|fusion battle)\b\s*", " ", base,
                      flags=re.I).strip() or base             # « NARUTO TRANSFORMATIONS » → « Naruto »
        if base.isupper():
            base = base.title()
        tiers = meta.get("tiers") or []
        ch = anime_of(base)
        if ch:
            animes, ani_names, ani_tags = [ch], [ch[0]], list(ch[1])
        ctags = char_tags(base.split()[0]) if base.split() else []
        title = f"{base} All Transformations 😳 Every Form"[:70]
        hook = f"{base}: all {len(tiers)} forms merging, from {tiers[0] if tiers else 'base'} to " \
               f"{tiers[-1] if tiers else 'final form'}. Wait for the final form."
        ask = "Which form is your favorite? Comment 👇"
        core = ["animetransformation", "satisfying"]
        kw = [f"{base} all forms", f"{base} transformations", "anime transformation", "merge game", "suika"]
    else:                                                     # Battle « Which anime character wins? »
        title = (meta.get("title") or "Which Anime Character Wins?")[:62] + " 🏆"
        top = ", ".join(short(n) for n in names[:6])
        hook = f"Anime battle royale simulation: {top} and more — only one survives."
        ask = "Comment who you think wins BEFORE the end 👇"
        core = ["animebattle", "whowouldwin"]
        ctags = [t for n in names[:3] for t in char_tags(n)[:1]]
        kw = ["anime battle", "who would win", "anime battle royale", "anime simulation"] + \
             [short(n) for n in names[:6]]
    title = title[:70]
    # Hashtags (règle de l'utilisateur, 02/11, sur CHAQUE plateforme) : 5 max = 3 FIXES pour verrouiller le public
    # (#anime #animebattle #whowouldwin) + 2 propres à la vidéo (persos, sinon perso + anime).
    spec = list(dict.fromkeys(t for t in ctags[:2] + ani_tags[:2] if t and t not in CORE_TAGS))[:2]
    five = CORE_TAGS + spec
    credit = ""
    if meta.get("sfx_credits"):                               # packs CC BY : créditer l'auteur
        credit = "\nSFX: " + ", ".join(meta["sfx_credits"]) + " (CC BY 4.0)"
    description = f"{hook}\n{ask}\n\nNew anime battle every day → follow {handle}{credit}\n\n{_hashtags(spec + CORE_TAGS, 5)}"
    tags = ", ".join(dict.fromkeys(kw + [n for n in names] + ani_names + ["anime", "anime shorts"]))[:480]
    # TikTok / Instagram (05/11, 88 % de vues en France, ~250 vues et 0 commentaire) : hashtags de FANS
    # (persos + franchise, ex. #sasuke #naruto #narutoshippuden) + 1 seul tag de format, plus de #anime trop large ;
    # question à 1 mot (« Yes or no? ») : le moindre effort pour commenter, c'est ce qui fait sortir du 1er groupe.
    fmt = {"domain": "animebattle", "powerup": "animebattle", "race": "animetransformation",
           "fusion": "animetransformation"}.get(kind, "animebattle")
    fan = list(dict.fromkeys(t for t in ctags[:2] + ani_tags[:2] if t))[:4] + [fmt]
    # TikTok : plus de hashtags CIBLÉS (05/11, vu sur les reels anime qui marchent) : noms complets des persos
    # (#madarauchiha) et « <perso>transformation » ; Instagram reste à 5 (limite d'Instagram).
    full = [t for n in (names[:2] if names else []) for t in char_tags(n)[1:2]]
    if kind == "fusion" or meta.get("tiers") and not names:
        full += [f"{ctags[0]}transformation"] if ctags else []
    fan_tt = list(dict.fromkeys(t for t in fan[:-1] + full + [fmt] if t))[:8]
    if kind == "domain":
        easy = f"{a} or {b}? One word 👇"
    elif kind == "powerup":
        easy = f"Does {a} make it? Yes or no 👇"
    elif kind == "race":
        easy = f"{a} or {b}? 👇"
    elif kind == "fusion" or meta.get("tiers") and not names:
        easy = "Rate the final form 1-10 👇"
    else:
        easy = "Who wins? One name 👇"
    line1 = title.rstrip(' 🤯⚡😳🏆')
    tiktok = f"{line1}\n{hook}\n{easy}\n{_hashtags(fan_tt, 8)}"
    # Instagram (05/11, 5 reels anime viraux analysés : tous « crossover ») : légende courte (titre + question) et
    # 5 hashtags = 2 anime (perso + franchise) + 3 pour un 2e public (ce que nos vidéos sont vraiment).
    other = {"domain": ["simulation", "gaming", "pongwars"], "powerup": ["satisfying", "oddlysatisfying", "simulation"],
             "race": ["suikagame", "satisfying", "oddlysatisfying"], "fusion": ["suikagame", "satisfying",
             "oddlysatisfying"], "gauntlet": ["simulation", "gaming", "satisfying"]}.get(kind, ["simulation", "gaming",
                                                                                            "satisfying"])
    ig2 = list(dict.fromkeys(t for t in ctags[:1] + ani_tags[:1] if t))[:2]
    insta = f"{line1}\n{easy}\n\n{_hashtags(ig2 + other, 5)}"
    return {"youtube": {"title": title, "description": description, "tags": tags},
            "tiktok": tiktok, "instagram": insta}


def pack_text(meta: dict, when: str | None = None, handle: str = "@animelorehq") -> str:
    """Texte du .txt livré avec chaque vidéo prête (library/_videos pretes/) : bloc BUFFER en haut (TikTok +
    Instagram programmés via Buffer, demandé le 02/11 : « automatisons insta et tiktok avec buffer »), puis
    YouTube Shorts (publié à la main par l'utilisateur à cause des limites de vérification du compte)."""
    s = build(meta, handle)
    y = s["youtube"]
    head = f"PUBLICATION : {when}\n\n" if when else ""
    return (f"{head}"
            "=== BUFFER (TikTok + Instagram, programmés automatiquement) ===\n"
            "1) Buffer → Create post → glisser la vidéo → cocher TikTok + Instagram\n"
            "2) Légende TikTok (onglet TikTok) :\n"
            f"{s['tiktok']}\n\n"
            "3) Légende Instagram (onglet Instagram, type « Reel ») :\n"
            f"{s['instagram']}\n\n"
            f"4) Schedule Post → {when or 'date et heure du planning'}\n\n"
            "=== YOUTUBE SHORTS (à publier toi-même) ===\n"
            f"Titre :\n{y['title']}\n\nDescription :\n{y['description']}\n\nTags :\n{y['tags']}\n")
