# Analyse des 3 vidéos de référence (07/11, `library/ENTRAINEENT STICKMAN/`)

Vidéos : « fan animation » (20 s, stickmen rouge/bleu, fond blanc), « STRENGTH VS SPEED ROUND 2 » (Stick Nodes,
4 min 42, très stylisé), « gaara vs rock lee » (Fabiano Cruz, 4 min 37, style plat avec décor). Images extraites aux
changements de plan + passages d'action à 8 i/s.

## 1. Mouvements rapides (dash, course, vol)
| Ce qu'on voit | Où | Effet à reproduire |
|---|---|---|
| Le perso laisse 4–8 copies de lui-même, de plus en plus transparentes, LE LONG DU MOUVEMENT (pas les images précédentes : des positions intermédiaires) | fan 5.8 s, 14.8 s ; SvS 3:44, 4:18 | **écho de mouvement** : on rend la pose à t − k·dt (sous-images) |
| Traînée de traits horizontaux À LA COULEUR DU PERSO qui traverse tout l'écran | fan 15.6 s, 16.6 s ; SvS 1:30, 1:33 | **traits de vitesse colorés** (pas blancs), flous, devant et derrière |
| Fond qui file en traits gris clairs, horizon penché | SvS 0:54–0:56, 4:18 | **lignes de vitesse du décor** + caméra penchée (dutch) |
| Éclairs bleus autour du perso le plus rapide | SvS 0:52–0:54 | **crépitement** (vfxgen lightning) sur les persos « vitesse » |
| Le perso arrive d'un coup : 1 image floue puis net | SvS 3:40 (2 persos flous puis nets) | arrivée = 1–2 images d'écho fort puis net |

## 2. Coups (poing, pied, coude)
| Ce qu'on voit | Où | Effet |
|---|---|---|
| Arc plein en forme de croissant derrière le pied / le poing, à la couleur du perso, qui s'efface en 2–3 images | fan 8.4 s, 9.6 s, 11.0 s | **arc de traînée du membre** (trajet du poing / du pied) |
| Le bras qui frappe est flou à l'image de l'impact, net juste après | SvS 3:42.375 | écho uniquement sur le membre qui frappe (via écho global court) |
| Pose d'anticipation tenue longtemps (0,5–1 s figée), puis frappe en 1–2 images | SvS 3:41–3:42 (gros plan figé 1 s), gaara 3:00–3:04 | **tenue avant le coup** (hold) puis snap |
| Impact : étoile rouge/orange à pointes + petits traits qui partent en étoile | fan 17.8 s ; SvS 1:03, 1:37, 1:47, 3:42.25 | **étoile d'impact** (polygone à pointes, 2 couleurs) + traits radiaux |
| Écran entier teinté rose/rouge 1–2 images | SvS 3:42.1, 3:44.5 | **flash teinté** à la couleur de l'attaquant |
| Gros plan sur le poing ou le visage au moment de l'impact | SvS 0:50, 1:04, 4:00 | **zoom caméra** vers l'impact (×1,3–1,6) |

## 3. Se prendre un coup / être projeté
| Ce qu'on voit | Où | Effet |
|---|---|---|
| Projeté en arc, corps qui tourne, écho derrière | fan 7.6–8.2 s ; gaara 1:40 | tumble + rotation + **écho** |
| Glisse au sol en laissant une traînée de poussière grise floue | SvS 2:26, 1:25 | **traînée de poussière** au ras du sol |
| Rebondit / se réceptionne accroupi | fan 10.4 s, 12.8 s | atterrissage en crouch (déjà là) |
| Choc contre le sol : cratère, cailloux noirs qui sautent, onde grise | SvS 1:52, 2:18 ; gaara 4:06 | **débris noirs** + **anneaux de choc** gris en perspective |

## 4. Gros impacts / moments clés
| Ce qu'on voit | Où | Effet |
|---|---|---|
| Image en négatif : fond noir, persos blancs (silhouettes) | SvS 1:40.7, 1:46.6, 1:49 | **impact frame silhouette** (2 images) |
| Lignes de vitesse radiales façon manga, noires sur blanc ou blanches sur noir, centrées sur l'impact | SvS 0:55.75, 1:25.6, 1:47.9 | **lignes radiales manga** |
| Fond uni de couleur vive (rouge) + silhouette noire + lignes radiales | SvS 1:25.58 | variante « COUNTER » colorée |
| Anneaux concentriques gris qui s'étalent (perspective) | SvS 0:54.3, 1:25.7, 3:44.5 | **anneaux de choc** |
| Texte qui claque (« COUNTER! ») | SvS 1:25.6 | bannière texte style A |
| Énorme croissant à la couleur du perso (coup de sabre / onde) | fan 18.4 s | croissant géant |

## 5. Charge / transformation (gaara : ouverture des portes)
| Ce qu'on voit | Où | Effet |
|---|---|---|
| Colonne de lumière verticale + traits blancs qui montent | gaara 3:24–3:30 | **colonne d'énergie** |
| Arcs d'énergie bleus qui tournent autour du perso | gaara 3:24 | **arcs qui tournent** |
| Contour lumineux (liseré vert) autour du perso | gaara 3:25 | **liseré lumineux** (rim glow) |
| Sol fissuré autour | gaara 2:43+ | fissures au sol |
| Plans serrés pendant la charge (pieds, visage), puis plan large | gaara 3:25–3:30 | caméra : gros plans |

## 6. Mise en scène
- Rythme : longues tenues immobiles (tension) puis action en 2–4 images → le contraste fait l'effet.
- Fond simple (blanc + ligne de sol) : toute l'attention sur les persos et les effets.
- Caméra : horizon penché, zooms, gros plans, plans larges pour l'espace.
- Persos : traits épais, ombrage par 2–3 traits sombres sur les membres (SvS 2:14+).

## Ce qui a été ajouté au moteur (`stickfx.py`, `stickanim.py`)
écho de mouvement (sous-images), arcs de traînée des membres, traits de vitesse colorés, étoile d'impact, lignes
radiales manga, flash teinté, impact frame silhouette, anneaux de choc en perspective, débris noirs, traînée de
poussière, colonne d'énergie + arcs + liseré lumineux, caméra (zoom, horizon penché, tremblement), tenue avant les coups.
