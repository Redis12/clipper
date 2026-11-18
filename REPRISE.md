# REPRISE : où on en est (à lire au début de chaque nouvelle conversation)

Mis à jour le 19/11. Mémoire complète : `CLAUDE.md` (outil + règles), `PLAYBOOK.md` (leçons, stats), `IDEES.md` (idées, règles qui marchent), `DEJA_FAITES.md` (vidéos déjà faites, à vérifier avant de proposer), `ANALYSE_WHAT_IF.md` (analyse du format long).

## Façon de travailler (rappel)
- Réponses en français, heures en AM/PM. 2 vidéos par jour : **6 PM + 12 PM** recommandés (10 PM = pire créneau d'après les stats). Minutes décalées par plateforme.
- Toujours demander avant de programmer / publier / modifier un post Buffer (l'utilisateur dit oui à chaque fois).
- Buffer : org `6ae891d84df2adfbdc9aa62d` ; TikTok `6ae89213e29c69a1713848ec`, Instagram `6ae891f1e29c69a1713847e2`, YouTube `6aea2f41e29c69a1714f440b`, Money Sim `6aec9270e29c69a1716ffded`.
- Vidéos hébergées pour Buffer : dépôt `Redis12/animelore-media` (copier, commit, push → URL raw.githubusercontent.com/…/<sha>/<fichier>, vérifier en 206).
- PC : `$HOME/mnt/clipper` via device_bash quand il est relié ; ranger dans `library/_videos pretes/<Format>/` + `.txt` + ligne PLANNING.txt ; fichiers < 30 Mo.
- Pas de format « Guess » (règle du 18/11). Filigrane sur chaque vidéo. Optimiser la 1re seconde.

## Stats (18/11, médianes TikTok)
Gauntlet 193k · Power Up 101k · Transformations 31k · Domain War 10k · Battle 4,6k · Snake/Guess ~2k. Instagram ~150 vues/post.

## Programmation
- Rien de programmé après **sam. 21/11 6 PM** ; le créneau du vendredi soir est vide.
- **Akatsuki** (« Every Akatsuki Member », `plus tard/Transformations/`) : pas programmé, proposé ven. 20/11.
- Post Instagram **Hokage** (`6afe0fd40a1fb75cd4165cd6`) : garde l'ancien son (l'utilisateur a refusé la modif). Ne pas y toucher sans demander.

## En cours
1. **Explainer Gojo « If you had Gojo's Infinity »** (DA vectorielle plate « un peu stickman » comme la vidéo « The math behind Gojo's Infinity ») : v1 et v2 refusées (« on reconnaît pas Gojo, DA pas ouf », pas d'images d'anime statiques). Plan : l'utilisateur génère 4 PNG détourés de Gojo (profil bandeau, face, main levée, gros plan yeux) + Sukuna dans un style vectoriel plat avec ChatGPT Images ; Claude dessine tout le reste (bonhomme « YOU » original, poing, anneaux, Zénon, atomes, horloge, pièce), anime Gojo à peine (respiration, clignement, léger balancement), caméra, compteurs jaunes, texte 3 mots, voix Kokoro am_adam, boucle. Moteur : `tools/explainer/infinity_style.py`, script `tools/explainer/scripts/gojo_infinity_v2.json`, images dans `library/_explainer/gojo_infinity/` (mettre les nouveaux PNG dans `library/_explainer/gojo_infinity/flat/`).
2. **Format long « What If »** : analyse faite (`ANALYSE_WHAT_IF.md`), démo 30 s `tools/whatif/demo.py` (stop time). « On a du chemin à faire » : à reprendre plus tard.
3. **Voix de persos** Hokage / Akatsuki : si l'utilisateur les fournit (`library/_sounds/naruto_voices/`), re-rendre les 2 vidéos.
4. **Quiz « Whose theme is this? »** (Naruto : Naruto, Sasuke, Itachi, Kakashi, Jiraiya, Pain/Girei, Madara), un seul type par quiz, cohérent : en attente de validation + extraits audio (l'utilisateur télécharge, Claude donne les commandes yt-dlp).
5. **Comparaison de tailles** : il faut des images en pied.
6. **Gauntlets Base Goku vs Bleach / MHA** : il faut les images. Hashirama vs Naruto possible.
7. À ranger sur le PC quand il sera relié : brouillons de l'explainer Gojo et la démo What If (pas importants, refusés / démo).
8. Dépôt `Redis12/clipper` : conseillé de le repasser en privé ; on ne sait pas si c'est fait.
