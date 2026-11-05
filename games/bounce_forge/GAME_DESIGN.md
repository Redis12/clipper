# Bounce Forge : conception (05/11/2026)

Jeu mobile (Godot 4.4, rendu Compatibility + glow HDR 2D), inspiré de « Balls Bounce - Merge & Bounce » (Moonee, 1 M+ téléchargements) mais à notre sauce.
Avis négatifs du concurrent à corriger : trop de pubs forcées, fini en ~14 h, tout repart à zéro.

## Boucle de jeu
- Des balles (bonbons) rebondissent dans un récipient en forme de tube brillant. Chaque rebond sur un **pad** rapporte des **$** (« +$60 » vert).
- 3 cartes en bas : **ADD PAD**, **ADD BALL**, **MERGE** (2 bonbons du même niveau → 1 bonbon du niveau suivant, valeur ×3).
- Objectif d'un niveau : atteindre un total de $ gagnés (la barre compte ce qu'on gagne, pas ce qu'on garde → acheter ne fait pas reculer).
- Bonbon emballé (ancien « cadeau ») qui apparaît : on le casse en N coups → gros bonus.
- Le jeu s'ouvre directement sur le niveau en cours (pas de menu). Bouton « carte » pour le chemin façon Candy Crush.

## Structure
- 5 mondes : mondes 1–4 = 10 niveaux, monde 5 = 20 niveaux → 60 niveaux avant publication.
- Un **boss tous les 5 niveaux** (12 boss). Chaque boss donne un **skin exclusif** (impossible à acheter).
- Chaque monde = sa mécanique (idées : Plinko, flippers, portails, espace zéro-G, briques). Monde 1 = découverte du merge, peu de mécaniques.

## 10 niveaux de bonbons (chaîne de fusion)
1 Dragée · 2 Bonbon rond · 3 Guimauve · 4 Chewing-gum · 5 Cookie · 6 Donut · 7 Cupcake · 8 Sucette · 9 Gâteau · 10 Bonbon doré.
Valeur par rebond ×3 à chaque niveau. Premier bonbon d'un niveau jamais vu → écran « NEW CANDY! » (suspense façon Suika / nos vidéos Fusion). Monde 1 : on atteint au mieux le cupcake.

## Monnaies
- **$ du niveau** : rebonds, dépensés dans le niveau, remis à zéro à chaque niveau.
- **Pièces** : gagnées à chaque fin de niveau (10 + 5 par étoile), permanentes, pour la **boutique de skins** (300–3 000 pièces).

## Skins = un univers complet (look + son)
Un skin remplace les 10 objets de fusion ET tous les sons. Exemples : Bonbons (base, pack Triple Treat), Fruits, Espace, Gemmes, Notes de musique, Animaux, 8-bit.

## Monde 1 (tuto) : 1 chose apprise par niveau
| Niv | Forme | Apprend / défi | Durée visée |
|---|---|---|---|
| 1 | Anneau | ajouter des balles | ~30 s |
| 2 | Anneau | la fusion (main sur MERGE) | ~45 s |
| 3 | Flacon | ajouter un pad | ~1 min |
| 4 | Flacon | le bonbon à casser | ~1 min |
| 5 | U | mini-boss | ~1 min 30 |
| 6 | U | les étoiles (finir vite) | ~1 min |
| 7 | Goutte | pads mal placés au départ | ~1 min 30 |
| 8 | Goutte | le « mur » : chrono, souvent raté de peu | ~2 min |
| 9 | Anneau | facile et généreux + balle dorée | ~45 s |
| 10 | Spéciale | boss du monde + skin | ~2 min |

## Addictivité
- Étoiles serrées (raté de peu → on rejoue), un niveau « mur » tous les 5–8 niveaux puis 2–3 faciles.
- Balle dorée rare (×10), combo affiché, sons qui montent en gamme, vibration.
- Pas de pub forcée : seulement des pubs choisies (×2 pendant X min).
- Idées gardées pour plus tard : bouton « Clip » (enregistre les 10 dernières s pour TikTok), coffre quotidien, série de jours.

## Direction artistique
Bonbon / pâte à modeler : fond rose → lilas, nuages, vermicelles ; tubes rayés façon sucre d'orge ; pads en gomme ; contours violet foncé (#4a1f52) épais façon Balls Bounce ; police Lilita One.

## Sons
Pack « Triple Treat: Sound Effects for Match-3 Games » (Reghan Cutler, itch.io) fourni par l'utilisateur. **Licence non indiquée dans le zip** : demander à l'auteur l'usage commercial / le crédit avant publication.

## Outils
- `godot --path . -- --autoplay` : un bot joue (vidéos d'aperçu avec `--write-movie`).
- `-- --sim` : simule les niveaux sans rendu pour l'équilibrage.
- `-- --level=N`, `--map`, `--demo` : captures.
