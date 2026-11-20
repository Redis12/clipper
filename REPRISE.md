# REPRISE : où on en est (à lire au début de chaque nouvelle conversation)

Mis à jour le 19/11. Mémoire complète : `CLAUDE.md` (outil + règles), `PLAYBOOK.md` (leçons, stats), `IDEES.md` (idées, règles qui marchent), `DEJA_FAITES.md` (vidéos déjà faites, à vérifier avant de proposer), `ANALYSE_WHAT_IF.md` (analyse du format long).

## Façon de travailler (rappel)
- Réponses en français, heures en AM/PM. 2 vidéos par jour : **6 PM + 12 PM** recommandés (10 PM = pire créneau d'après les stats). Minutes décalées par plateforme.
- Toujours demander avant de programmer / publier / modifier un post Buffer (l'utilisateur dit oui à chaque fois).
- Buffer : org `6ae891d84df2adfbdc9aa62d` ; TikTok `6ae89213e29c69a1713848ec`, Instagram `6ae891f1e29c69a1713847e2`, YouTube `6aea2f41e29c69a1714f440b`, Money Sim `6aec9270e29c69a1716ffded`.
- Vidéos hébergées pour Buffer : dépôt `Redis12/animelore-media` (copier, commit, push → URL raw.githubusercontent.com/…/<sha>/<fichier>, vérifier en 206).
- PC : `$HOME/mnt/clipper` via device_bash quand il est relié ; ranger dans `library/_videos pretes/<Format>/` + `.txt` + ligne PLANNING.txt ; fichiers < 30 Mo.
- Pas de format « Guess » (règle du 18/11). Filigrane sur chaque vidéo. Optimiser la 1re seconde.
- **Images générées par IA (règle du 19/11)** : TOUJOURS demander un fond vert uni (#00FF00) dans les prompts, jamais « transparent » (ChatGPT/Gemini dessinent un faux damier : impossible à détourer sur les cheveux blancs de Gojo).
- **Pas de numéros de série (19/11)** : badge « IF YOU HAD... » sans « #N », titres sans numéro. Gojo Infinity = test, non publié ; Byakugan publié le 19/11 à 12 h 55.
- **DA persos (19/11)** : Shorts = style « explainer simple » (Gojo/Sukuna générés sur Gemini, tête ovale, grosses pointes, dégradés doux, pas de contour) ; vidéos longues = même style mais persos EN PIED.

## Stats (18/11, médianes TikTok)
Gauntlet 193k · Power Up 101k · Transformations 31k · Domain War 10k · Battle 4,6k · Snake/Guess ~2k. Instagram ~150 vues/post.

## Programmation
- Ven. 20/11 : 1 PM Kid Naruto vs Obito (Power Up ; YouTube bloqué par Content ID avec Obito's Theme → reposté sans musique à 13h09, https://www.youtube.com/watch?v=Ouc6MySHBEY à supprimer à la main)
- **Règle (20/11) : sur YouTube, JAMAIS de musique officielle d'anime (Content ID bloque la vidéo). Musique OST = TikTok + Instagram seulement ; YouTube = version sans musique.**, 6 PM Hokage, 10 PM LIBRE (ZA WARUDO v2/v3/v4 jugées « nulles » le 19/11, posts supprimés ; ne pas reproposer). Rien après **sam. 21/11 6 PM**.
- **Akatsuki** (« Every Akatsuki Member », `plus tard/Transformations/`) : pas programmé, proposé ven. 20/11.
- Post Instagram **Hokage** (`6afe0fd40a1fb75cd4165cd6`) : garde l'ancien son (l'utilisateur a refusé la modif). Ne pas y toucher sans demander.

## En cours
1. **Série « If you had… »** (explainers 25–30 s, DA bleu nuit + or validée le 19/11, persos Gemini style simple sur fond vert) : moteur `tools/explainer/infinity_v4.py` (texte Poppins fin + mot en gras `*…*`, compteur doré, badge « IF YOU HAD... », carte « 1 ou 2 », follow qui reboucle sur l'image 0, filigrane, voix am_adam), un fichier par épisode qui hérite de `Show` : `byakugan.py` (✅ publié 19/11 1 PM), Gojo (`infinity_v4.py` + `scripts/gojo_infinity_v4.json`, test NON publié), `zawarudo.py` (v1 refusée : « pas intéressant, gouttes moches, tête de DIO à la fin » → **v2 FAITE et programmée ven. 20/11 10 PM** (`scripts/zawarudo_v2.json`) : script « ce que TU pourrais faire » : jamais en retard, finir la pizza, pluie qui ne mouille pas, attraper une balle, road roller, 5 s à toi, puis Jotaro qui marche vers toi « yare yare daze » + ORA ORA ; assets reçus : jotaro_walk, raindrops, bullet, hand_bullet ; **attendus** : DIO choqué au style simple (1re version trop détaillée) + pizza). Détourage fond vert qui garde les éléments verts : `tools/explainer/key_green.py`. Prompts : toujours UNE image par message, fond vert.
2. **Format long « What If »** : analyse faite (`ANALYSE_WHAT_IF.md`), démo 30 s `tools/whatif/demo.py` (stop time). « On a du chemin à faire » : à reprendre plus tard.
3. **Voix de persos** Hokage / Akatsuki : si l'utilisateur les fournit (`library/_sounds/naruto_voices/`), re-rendre les 2 vidéos.
4. **Quiz « Whose theme is this? »** (Naruto : Naruto, Sasuke, Itachi, Kakashi, Jiraiya, Pain/Girei, Madara), un seul type par quiz, cohérent : en attente de validation + extraits audio (l'utilisateur télécharge, Claude donne les commandes yt-dlp).
5. **Comparaison de tailles** : il faut des images en pied.
6. **Gauntlets Base Goku vs Bleach / MHA** : il faut les images. Hashirama vs Naruto possible.
7. À ranger sur le PC quand il sera relié : brouillons de l'explainer Gojo et la démo What If (pas importants, refusés / démo).
8. Dépôt `Redis12/clipper` : conseillé de le repasser en privé ; on ne sait pas si c'est fait.
