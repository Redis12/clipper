"""Fiches de persos pour Domain War : un fichier texte par perso dans library/_domain/<Perso>.txt.

Format (une ligne par clé, « # » = commentaire) :

    name: Satoru Gojo
    match: gojo, satoru                 ← mots qui reconnaissent le perso dans un nom de dossier
    color: #38bdf8                      ← couleur de son domaine
    about: Le plus fort des exorcistes…  ← résumé (affiché sur la page, pas dans la vidéo)
    zone:    Unlimited Void | domain     ← grosse attaque de zone (bomb, domain, shrine)
    front:   Hollow Purple               ← attaque devant lui (rayon)
    shots:   Red                         ← petits projectiles
    secret:  200% Hollow Purple | mega_beam
    passive: Infinity | infinity
    form:    _fusion/Goku                ← (option) image prise au moment du secret = transformation :
                                           dossier _fusion (sa dernière forme), fichier de library/, ou nom de perso

Familles d'effets (le nom affiché est libre, l'effet est commun à tous) :
- zone    : bomb (sphère qui s'abat sur le camp adverse), domain (dôme autour du perso, fige les ennemis dedans),
            shrine (dôme plus grand, entailles partout, ne fige pas)
- secret  : domain, shrine, mega_beam (rayon géant), timestop (camp adverse figé 3 s), teleport (se téléporte
            derrière un ennemi et le neutralise), summon (invoque une créature 7 s ; « summon: Mahoraga »),
            clones (4 clones 5 s), giant (balle géante qui traverse tout 3 s), meteor (énorme projectile qui s'abat)
            + option « breaks: Infinity » = ce secret annule ce passif adverse (Mahoraga s'adapte à l'Infini…)
- passive : infinity (cases autour de lui imprenables), regen (repeint autour de lui régulièrement),
            speed (×1,3), none
"""
from __future__ import annotations

import re
from pathlib import Path

from ..util import log

ZONE_FAM = {"bomb", "domain", "shrine"}
SECRET_FAM = {"domain", "shrine", "mega_beam", "timestop", "teleport", "summon", "clones", "giant", "meteor"}
PASSIVE_FAM = {"infinity", "regen", "speed", "none"}

PRESETS = {
"Satoru Gojo": """match: gojo, satoru
color: #38bdf8
about: Le plus fort des exorcistes. Limitless (Bleu = attraction, Rouge = répulsion, Violet = les deux combinés), Six Eyes, Infini qui arrête tout ce qui l'approche. Domain : Unlimited Void (submerge l'adversaire d'informations, il ne peut plus bouger).
zone: Unlimited Void | domain
front: Lapse: Blue
shots: Reversal: Red
secret: 200% Hollow Purple | mega_beam
passive: Infinity | infinity
eyes: 200% Hollow Purple""",
"Ryomen Sukuna": """match: sukuna
color: #e11d48
about: Roi des fléaux. Shrine : Dismantle (entailles à distance) et Cleave (coupe adaptée à la cible), Fuga / Divine Flame (« Open »). Domain sans barrière : Malevolent Shrine, qui tranche tout dans un immense rayon. Utilise les Dix Ombres de Megumi : invoque Mahoraga, qui s'adapte à l'Infini de Gojo ; en tire le World Cutting Slash qui coupe l'espace. Reverse Cursed Technique (se soigne).
zone: Malevolent Shrine | shrine
front: Fuga (Divine Flame)
shots: Dismantle
secret: Summon Mahoraga | summon | breaks: Infinity
passive: Reverse Cursed Technique | regen""",
"Yuji Itadori": """match: yuji, itadori
color: #f97316
about: Corps surhumain, Divergent Fist, enchaîne les Black Flash. Finit par maîtriser Shrine (Dismantle) et sa propre Domain Expansion.
zone: Black Flash | bomb
front: Divergent Fist
shots: Dismantle
secret: Domain Expansion | domain
passive: Superhuman Body | speed""",
"Megumi Fushiguro": """match: megumi, fushiguro
color: #6366f1
about: Technique des Dix Ombres : chiens divins, Nue, Max Elephant… et Mahoraga, le shikigami le plus fort. Domain : Chimera Shadow Garden.
zone: Chimera Shadow Garden | domain
front: Divine Dogs
shots: Nue
secret: Summon Mahoraga | summon
passive: Ten Shadows | none""",
"Mahito": """match: mahito
color: #94a3b8
about: Fléau qui remodèle les âmes (Idle Transfiguration). Domain : Self-Embodiment of Perfection. Forme ultime : Instant Spirit Body of Distorted Killing.
zone: Self-Embodiment of Perfection | domain
front: Idle Transfiguration
shots: Polymorphic Soul Isomer
secret: Instant Spirit Body of Distorted Killing | giant
passive: Soul Reshaping | regen""",
"Toji Fushiguro": """match: toji
color: #64748b
about: Restriction céleste : zéro énergie occulte, corps et vitesse surhumains. Sa Lance Céleste Inversée annule les techniques (il a percé l'Infini de Gojo).
zone: Playful Cloud | bomb
front: Split Soul Katana
shots: Chain of a Thousand Miles
secret: Inverted Spear of Heaven | teleport | breaks: Infinity
passive: Heavenly Restriction | speed""",
"Yuta Okkotsu": """match: yuta, okkotsu
color: #e879f9
about: Énergie occulte immense, copie les techniques, Rika. Domain : Authentic Mutual Love.
zone: Authentic Mutual Love | domain
front: Pure Love Cannon
shots: Cursed Speech
secret: Full Manifestation: Rika | summon
passive: Reverse Cursed Technique | regen""",
"Son Goku": """match: goku, kakarot
color: #f59e0b
about: Saiyan, Kamehameha, Genkidama (Spirit Bomb), Instant Transmission. Ultra Instinct : le corps esquive et frappe tout seul.
zone: Spirit Bomb | bomb
front: Kamehameha
shots: Ki Blasts
secret: Ultra Instinct | teleport
passive: Saiyan Power | speed
form: _fusion/Goku
aura: #dbe7ff""",
"Gogeta": """match: gogeta
color: #f97316
about: Fusion Goku + Vegeta par la danse Metamoru (30 min). Big Bang Kamehameha, Ki Blast Volley, Instant Transmission. Ultime : Stardust Breaker, la sphère arc-en-ciel qui a désintégré Janemba. Gogeta Blue (Broly), SSJ4 (GT).
zone: Ultimate Impact | bomb
front: Big Bang Kamehameha
shots: Ki Blast Volley
secret: Stardust Breaker | meteor
passive: Saiyan Power | speed
form: _fusion/Gogeta
aura: #fb923c
ulti_at: finish""",
"Vegito": """match: vegito, vegetto, vegeto
color: #0ea5e9
about: Fusion Goku + Vegeta par les Potaras. Final Kamehameha, Spirit Sword (épée d'énergie), Big Bang Attack, Scatter Finger Beam, Afterimage Strike. Vegito Blue contre Zamasu. Aussi arrogant que puissant.
zone: Big Bang Attack | bomb
front: Spirit Sword | sword
shots: Scatter Finger Beam
secret: Final Kamehameha | mega_beam
passive: Afterimage Strike | speed
form: _fusion/Vegeto
aura: #60a5fa""",
"Vegeta": """match: vegeta
color: #2563eb
about: Prince des Saiyans. Final Flash, Big Bang Attack, Galick Gun. Ultra Ego : plus il prend de coups, plus il devient fort.
zone: Big Bang Attack | bomb
front: Final Flash
shots: Ki Barrage
secret: Ultra Ego | giant
passive: Saiyan Pride | regen
form: _fusion/Vegeta
aura: #a855f7""",
"Son Gohan": """match: gohan
color: #a855f7
about: Masenko, Special Beam Cannon, potentiel caché. Forme Beast.
zone: Masenko | bomb
front: Special Beam Cannon
shots: Ki Blasts
secret: Gohan Beast | giant
passive: Hidden Potential | speed""",
"Naruto Uzumaki": """match: naruto
color: #fb923c
about: Rasengan, Rasenshuriken, multiclonage, chakra de Kurama, mode Ermite des Six Chemins.
zone: Rasenshuriken | bomb
front: Rasengan
shots: Kunai
secret: Multi Shadow Clone Jutsu | clones
passive: Kurama Chakra | regen
form: _fusion/Naruto
aura: #ffb02e
voice: kage bunshin
intro: yoooo
gauge: chakra
substitute: 2""",
"Sasuke Uchiha": """match: sasuke
color: #7c3aed
about: Sharingan / Rinnegan, Chidori, Kirin, Amaterasu, Susanoo.
zone: Kirin | bomb
front: Chidori
shots: Amaterasu
secret: Perfect Susanoo | giant
passive: Sharingan | speed
form: _fusion/Sasuke
aura: #a78bfa
voice: Narutooooo
eyes: Amaterasu
combo: zone
intro: yoooo
gauge: chakra
substitute: 2""",
"Itachi Uchiha": """match: itachi
color: #dc2626
about: Mangekyô Sharingan : Tsukuyomi (illusion où le temps s'arrête), Amaterasu, Susanoo.
zone: Susanoo | bomb
front: Amaterasu
shots: Fireball Jutsu
secret: Tsukuyomi | timestop
passive: Sharingan | speed
eyes: Amaterasu, Tsukuyomi""",
"Madara Uchiha": """match: madara
color: #b91c1c
about: Rinnegan, Susanoo parfait, Tengai Shinsei (fait tomber des météores), Tsukuyomi infini.
zone: Tengai Shinsei | bomb
front: Susanoo Slash
shots: Great Fire Annihilation
secret: Infinite Tsukuyomi | timestop
passive: Rinnegan | regen""",
"Monkey D. Luffy": """match: luffy
color: #ef4444
about: Corps en caoutchouc, Gear 2/3/4, Haki des rois. Gear 5 : Nika, le corps devient un dessin animé géant.
zone: Bajrang Gun | bomb
front: Red Hawk
shots: Gatling
secret: Gear 5 | giant
passive: Rubber Body | speed""",
"Roronoa Zoro": """match: zoro
color: #22c55e
about: Style à trois sabres, Shishi Sonson, Haki des rois. Asura : apparaît avec neuf sabres.
zone: King of Hell: Three Sword Style | bomb
front: Shishi Sonson
shots: 36 Pound Cannon
secret: Asura | clones
passive: Haki | none""",
"Ichigo Kurosaki": """match: ichigo
color: #f97316
about: Shinigami, Bankai Tensa Zangetsu, Getsuga Tensho, masque de Hollow. Mugetsu : la technique finale.
zone: Getsuga Jujisho | bomb
front: Getsuga Tensho
shots: Cero
secret: Mugetsu | mega_beam
passive: Bankai Speed | speed""",
"Sosuke Aizen": """match: aizen
color: #8b5cf6
about: Kyoka Suigetsu (hypnose totale), Kido sans incantation (Hado 90 : Kurohitsugi), Hogyoku (régénération).
zone: Kurohitsugi (Black Coffin) | bomb
front: Hado 63: Raikoho
shots: Hado 31
secret: Kyoka Suigetsu | teleport
passive: Hogyoku | regen""",
"Jotaro Kujo": """match: jotaro
color: #4f46e5
about: Stand Star Platinum : force et précision énormes, ORA ORA ORA, Star Finger. Star Platinum: The World arrête le temps.
zone: ORA ORA ORA | bomb
front: Star Finger
shots: Ball Bearings
secret: Star Platinum: The World | timestop
passive: Star Platinum | none""",
"Dio Brando": """match: dio
color: #eab308
about: Vampire, Stand The World : ZA WARUDO arrête le temps, couteaux, ROAD ROLLER DA !
zone: Road Roller Da! | bomb
front: MUDA MUDA MUDA
shots: Knives
secret: ZA WARUDO | timestop
passive: Vampire | regen""",
"Tanjiro Kamado": """match: tanjiro
color: #14b8a6
about: Souffle de l'eau, Hinokami Kagura (Danse du Dieu du Feu), Marque du pourfendeur.
zone: Hinokami Kagura: Sun Halo Dragon | bomb
front: Water Wheel
shots: Water Surface Slash
secret: Demon Slayer Mark | teleport
passive: Total Concentration | speed""",
"Kyojuro Rengoku": """match: rengoku
color: #f97316
about: Pilier de la flamme, Souffle de la flamme, Neuvième forme : Rengoku.
zone: Ninth Form: Rengoku | bomb
front: Flame Tiger
shots: Rising Scorching Sun
secret: Set Your Heart Ablaze | giant
passive: Flame Breathing | none""",
"Saitama": """match: saitama
color: #facc15
about: Bat tout le monde d'un coup de poing. Série sérieuse : Serious Punch, Serious Sideways Jumps (crée des images rémanentes).
zone: Consecutive Normal Punches | bomb
front: Normal Punch
shots: Serious Sneeze
secret: Serious Punch | mega_beam
passive: Limiter Removed | regen""",
"Eren Yeager": """match: eren
color: #a16207
about: Titan Assaillant, durcissement, Titan Originel : le Grand Terrassement (Rumbling).
zone: The Rumbling | bomb
front: Attack Titan Punch
shots: Hardening Spikes
secret: Founding Titan | giant
passive: Titan Regeneration | regen""",
"Levi Ackerman": """match: levi
color: #475569
about: Le soldat le plus fort de l'humanité, équipement tridimensionnel, lances foudroyantes, réveil Ackerman.
zone: Spinning Slash | bomb
front: ODM Dash
shots: Thunder Spears
secret: Ackerman Awakening | teleport
passive: Ackerman | speed""",
}

EXTRA = {
"Aoi Todo": """match: todo
color: #a16207
about: Boogie Woogie : un clap et il échange sa place avec quelqu'un. Corps de brute, enchaîne les Black Flash. « Brother ! »
zone: Black Flash | bomb
front: Brotherly Punch
shots: Boogie Woogie Claps
secret: Boogie Woogie | teleport
passive: Best Friend Power | speed""",
"Choso": """match: choso
color: #be123c
about: Manipulation du sang : Piercing Blood (rayon de sang ultra rapide), Supernova (explosion de sang), Flowing Red Scale (boost).
zone: Supernova | bomb
front: Piercing Blood
shots: Slicing Exorcism
secret: Flowing Red Scale | giant
passive: Cursed Womb Body | regen""",
"Dagon": """match: dagon
color: #0ea5e9
about: Fléau de l'eau. Domain : Horizon of the Captivating Skandha, des bancs infinis de poissons-shikigamis (Death Swarm).
zone: Horizon of the Captivating Skandha | domain
front: Water Torrent
shots: Shikigami Fish
secret: Death Swarm | clones
passive: Cursed Water | none""",
"Hajime Kashimo": """match: kashimo
color: #22d3ee
about: Énergie occulte électrique. Technique ultime à usage unique : Mythical Beast Amber, son corps devient éclair.
zone: Electric Discharge | bomb
front: Lightning Strike
shots: Bo Staff Sparks
secret: Mythical Beast Amber | giant
passive: Electric Charge | speed""",
"Hanami": """match: hanami
color: #65a30d
about: Fléau de la nature. Graines maudites, racines, Ceremonial Sea of Light. Flower Field apaise ses ennemis et les empêche de bouger.
zone: Cursed Buds | bomb
front: Ceremonial Sea of Light
shots: Wooden Balls
secret: Flower Field | timestop
passive: Plant Body | regen""",
"Jogo": """match: jogo
color: #ea580c
about: Fléau du volcan. Domain : Coffin of the Iron Mountain. Technique ultime : Maximum: Meteor.
zone: Coffin of the Iron Mountain | domain
front: Flame Burst
shots: Ember Insects
secret: Maximum: Meteor | meteor
passive: Volcano Body | none""",
"Kenjaku": """match: kenjaku
color: #78716c
about: Change de corps depuis 1000 ans. Manipulation des fléaux de Geto (Maximum: Uzumaki), antigravité. Domain : Womb Profusion.
zone: Womb Profusion | domain
front: Maximum: Uzumaki
shots: Anti-Gravity System
secret: Summon Cursed Spirits | clones
passive: Body Swap | regen""",
"Kento Nanami": """match: nanami
color: #ca8a04
about: Ratio 7:3 : coupe le point faible de n'importe quoi. Collapse détruit tout autour. Overtime : plus fort après ses heures de travail.
zone: Collapse | bomb
front: Ratio Technique 7:3
shots: Blunt Sword Strikes
secret: Overtime | giant
passive: Ratio Technique | none""",
"Kinji Hakari": """match: hakari
color: #16a34a
about: Domain : Idle Death Gamble, une machine à sous. Au JACKPOT : énergie infinie, il devient quasi immortel 4 min 11 s.
zone: Idle Death Gamble | domain
front: Rough Energy
shots: Shutter Doors
secret: JACKPOT | giant
passive: Rough Energy | regen""",
"Maki Zenin": """match: maki
color: #15803d
about: Restriction céleste totale : zéro énergie occulte, force et vitesse surhumaines. Massacre du clan Zenin avec le Split Soul Katana.
zone: Zenin Clan Massacre | bomb
front: Split Soul Katana
shots: Cursed Tools
secret: Full Heavenly Restriction | teleport
passive: Heavenly Restriction | speed""",
"Naoya Zenin": """match: naoya
color: #a3a3a3
about: Projection Sorcery : découpe ses mouvements en 24 images par seconde ; celui qui ne suit pas la règle est figé dans une image.
zone: Time Cell Moon Palace | domain
front: Projection Strike
shots: Supersonic Jabs
secret: Projection Sorcery | timestop
passive: 24 FPS | speed""",
"Nobara Kugisaki": """match: nobara
color: #f43f5e
about: Technique de la poupée de paille : marteau, clous, Hairpin (les clous explosent), Resonance (frappe l'âme à distance).
zone: Hairpin | bomb
front: Nail Barrage
shots: Nails
secret: Resonance | teleport
passive: Straw Doll | none""",
"Suguru Geto": """match: geto
color: #4b5563
about: Manipulation des fléaux : absorbe et invoque des milliers de fléaux. Maximum: Uzumaki les concentre en une seule attaque.
zone: Maximum: Uzumaki | bomb
front: Rainbow Dragon
shots: Cursed Spirits
secret: Summon Cursed Spirits | clones
passive: Cursed Spirit Shield | none""",
"Toge Inumaki": """match: inumaki, toge
color: #e5e7eb
about: Parole maudite : ce qu'il dit arrive. « Don't move » fige l'ennemi, « Blast away » le projette.
zone: Blast Away | bomb
front: Get Crushed
shots: Twist
secret: Don't Move | timestop
passive: Cursed Speech | none""",
"Uraume": """match: uraume
color: #93c5fd
about: Serviteur de Sukuna. Technique de glace : Frost Calm gèle tout, Ice Fall écrase.
zone: Ice Fall | bomb
front: Icicle Spear
shots: Icicles
secret: Frost Calm | timestop
passive: Ice Body | none""",
"Yuki Tsukumo": """match: yuki, tsukumo
color: #facc15
about: Star Rage : donne une masse virtuelle à elle et à son shikigami Garuda. Peut créer un trou noir.
zone: Star Rage: Garuda | bomb
front: Bom Ba Ye
shots: Garuda
secret: Black Hole | meteor
passive: Virtual Mass | none""",
"Mahoraga": """match: mahoraga
color: #d4d4d8
about: Le shikigami le plus fort des Dix Ombres. La roue tourne et il s'adapte à toute attaque, même l'Infini. Épée d'extermination.
zone: Wheel Turn | bomb
front: Sword of Extermination
shots: Extermination Strikes
secret: Adaptation | teleport | breaks: Infinity
passive: Adaptation | regen""",
"Beerus": """match: beerus
color: #a855f7
about: Dieu de la destruction. Hakai efface ce qu'il touche, Sphere of Destruction.
zone: Sphere of Destruction | bomb
front: Destruction Beam
shots: Ki Blasts
secret: Hakai | teleport
passive: God of Destruction | speed""",
"Pain": """match: pain, nagato
color: #f97316
about: Rinnegan, six chemins de Pain. Shinra Tensei repousse tout, Chibaku Tensei crée une sphère géante qui aspire tout.
zone: Shinra Tensei | bomb
front: Bansho Ten'in
shots: Chakra Rods
secret: Chibaku Tensei | meteor
passive: Six Paths | none""",
"Light Yagami": """match: light, yagami, kira
color: #b91c1c
about: Kira. Le Death Note tue toute personne dont il écrit le nom. Tout se passe comme prévu.
zone: Kira's Judgment | bomb
front: Death Note
shots: Ryuk's Apples
secret: Just As Planned | timestop
passive: Genius Plan | none""",
"L Lawliet": """match: lawliet
color: #e5e7eb
about: Le plus grand détective du monde. Déductions, équipe d'enquête, beaucoup de sucre.
zone: Investigation Team | bomb
front: Deduction
shots: Sugar Cubes
secret: I'm L | teleport
passive: Genius Detective | speed""",
"David Martinez": """match: david
color: #facc15
about: Edgerunner bourré d'implants. Sandevistan : ralentit le temps autour de lui. Finit dans un cyber-squelette militaire.
zone: Cyberskeleton Slam | bomb
front: Gorilla Arms
shots: Smart Pistol
secret: Sandevistan | timestop
passive: Chrome | speed""",
"Funny Valentine": """match: valentine
color: #60a5fa
about: Président. Stand D4C : voyage entre les mondes parallèles. Love Train : le malheur est renvoyé ailleurs, rien ne peut le toucher.
zone: Dirty Deeds Done Dirt Cheap | bomb
front: Revolver
shots: Flag Pole
secret: D4C: Parallel Worlds | clones
passive: Love Train | infinity""",
"Gyro Zeppeli": """match: gyro
color: #84cc16
about: Technique de la rotation (Spin) avec ses Steel Balls. Ball Breaker : la rotation parfaite du cheval.
zone: Steel Ball Barrage | bomb
front: Golden Spin
shots: Steel Balls
secret: Ball Breaker | mega_beam
passive: Spin | speed""",
"Joseph Joestar": """match: joseph
color: #059669
about: Hamon, clackers, Hermit Purple. « Your next line is… ! » : il prévoit tout ce que fait l'adversaire.
zone: Clacker Volley | bomb
front: Hamon Overdrive
shots: Hermit Purple
secret: Your Next Line Is…! | teleport
passive: Hamon Breathing | regen""",
"Stain": """match: stain
color: #991b1b
about: Le tueur de héros. Bloodcurdle : en léchant le sang de sa cible, il la paralyse.
zone: Hero Killer | bomb
front: Blade Rush
shots: Throwing Knives
secret: Bloodcurdle | timestop
passive: Hero Killer's Will | none""",
"Rocks D. Xebec": """match: xebec, rocks
color: #374151
about: Capitaine des Rocks Pirates, le pirate le plus craint avant Roger. Haki des rois.
zone: Rocks Pirates Raid | bomb
front: Haki Strike
shots: Cannon Fire
secret: Conqueror's Haki | timestop
passive: Captain of the Rocks | none""",
}
PRESETS.update(EXTRA)


DEFAULT_SLOTS = {"zone": "bomb", "front": "beam", "shots": "shots", "secret": "giant", "passive": "none"}


def folder() -> Path:
    from . import library
    d = library.root() / "_domain"
    d.mkdir(parents=True, exist_ok=True)
    return d


def ensure_presets() -> None:
    """Écrit les fiches prêtes dans library/_domain/ (jamais d'écrasement : tes corrections restent)."""
    d = folder()
    for name, body in PRESETS.items():
        p = d / f"{name}.txt"
        if not p.exists():
            p.write_text(f"name: {name}\n{body}\n", encoding="utf-8")
            continue
        txt = p.read_text(encoding="utf-8-sig")
        new = txt
        for key in ("form:", "aura:", "voice:", "intro:", "gauge:", "substitute:", "eyes:", "combo:"):   # clés ajoutées aux anciennes fiches
            line = [x for x in body.splitlines() if x.startswith(key)]
            if line and not any(x.strip().startswith(key) for x in new.splitlines()):
                new = new.rstrip("\n") + "\n" + line[0] + "\n"
        new = new.replace("intro: export_ofoct", "intro: yoooo")              # ancien son d'intro → le vrai « yoooo »
        if name == "Satoru Gojo":                                             # 03/11 : Bleu en rayon (le Violet = ulti)
            new = new.replace("front: Hollow Purple\n", "front: Lapse: Blue\n")
        if new != txt:
            p.write_text(new, encoding="utf-8")


def parse(text: str) -> dict:
    out = {"match": []}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, val = line.partition(":")
        key, val = key.strip().lower(), val.strip()
        if key == "match":
            out["match"] = [m.strip().lower() for m in val.split(",") if m.strip()]
        elif key in ("zone", "front", "shots", "secret", "passive"):
            parts = [p.strip() for p in val.split("|")]
            mv = {"name": parts[0], "fam": DEFAULT_SLOTS[key]}
            for extra in parts[1:]:
                if extra.lower().startswith("breaks"):
                    mv["breaks"] = extra.partition(":")[2].strip().lower()
                elif extra:
                    mv["fam"] = extra.lower().replace(" ", "_")
            allowed = {"zone": ZONE_FAM, "secret": SECRET_FAM, "passive": PASSIVE_FAM}.get(key)
            if allowed and mv["fam"] not in allowed:
                mv["fam"] = DEFAULT_SLOTS[key]
            if key == "secret" and mv["fam"] == "summon":
                mv["summon"] = re.sub(r"^(summon|invoque)\s+", "", mv["name"], flags=re.I).strip()
            out[key] = mv
        else:
            out[key] = val
    return out


def all_sheets() -> list[dict]:
    ensure_presets()
    out = []
    for p in sorted(folder().glob("*.txt")):
        try:
            s = parse(p.read_text(encoding="utf-8-sig"))
        except OSError:
            continue
        s.setdefault("name", p.stem)
        s["file"] = p.name
        out.append(s)
    return out


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", s.lower())


def find(name: str) -> dict | None:
    words = set(_norm(name).split())
    for s in all_sheets():
        keys = s.get("match") or [_norm(s["name"]).split()[0]]
        if any(set(k.split()) <= words for k in keys) or _norm(s["name"]).strip() == _norm(name).strip():
            return s
    return None


SHEET_SCHEMA = {"type": "object", "properties": {
    "about": {"type": "string"},
    "zone": {"type": "string"}, "zone_family": {"type": "string", "enum": sorted(ZONE_FAM)},
    "front": {"type": "string"}, "shots": {"type": "string"},
    "secret": {"type": "string"}, "secret_family": {"type": "string", "enum": sorted(SECRET_FAM)},
    "passive": {"type": "string"}, "passive_family": {"type": "string", "enum": sorted(PASSIVE_FAM)},
    "color": {"type": "string"}},
    "required": ["about", "zone", "zone_family", "front", "shots", "secret", "secret_family", "passive",
                 "passive_family", "color"], "additionalProperties": False}

SHEET_SYSTEM = (
    "You build a moveset sheet for an anime/manga character, for a short fan video game. Use the character's REAL, "
    "canon, iconic techniques (English names fans use). zone = their biggest area attack (or Domain Expansion); "
    "front = a beam/straight attack; shots = small projectiles or quick hits; secret = their most iconic trump card; "
    "passive = an always-on trait. Pick the closest effect family for each. about = 2 short sentences in French "
    "summarising what they can do. color = hex color associated with the character.")


def sheet_for(name: str) -> dict:
    """Fiche du perso : fichier existant, sinon Claude l'écrit (une fois, enregistrée), sinon générique."""
    s = find(name)
    if s:
        return s
    try:
        from .. import llm
        from .library import cfg as lcfg
        out = llm.structured(model=lcfg()["model"], system=SHEET_SYSTEM, user=f"Character: {name}",
                             tool_name="moveset", tool_desc="Store the moveset.", schema=SHEET_SCHEMA, max_tokens=800)
        text = (f"name: {name}\nmatch: {_norm(name).split()[-1] if _norm(name).split() else name.lower()}\n"
                f"color: {out['color']}\nabout: {out['about']}\n"
                f"zone: {out['zone']} | {out['zone_family']}\nfront: {out['front']}\nshots: {out['shots']}\n"
                f"secret: {out['secret']} | {out['secret_family']}\npassive: {out['passive']} | {out['passive_family']}\n")
        safe = re.sub(r'[\\/:*?"<>|]', "", name)
        p = folder() / f"{safe}.txt"
        p.write_text("# Écrit par Claude : corrige si besoin\n" + text, encoding="utf-8")
        log.info("fiche Domain War créée pour %s → %s", name, p.name)
        s = parse(text)
        s["file"] = p.name
        return s
    except Exception as e:                          # pas de clé… → fiche générique
        log.info("fiche Domain War générique pour %s (%s)", name, e)
        return parse(f"name: {name}\nzone: Big Attack | bomb\nfront: Beam\nshots: Blasts\n"
                     f"secret: Power Up | giant\npassive: Fighting Spirit | none")
