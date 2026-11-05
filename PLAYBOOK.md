# Playbook : faire grandir une chaîne anime (Shorts / TikTok / Reels)

Toutes les manips testées sur @animelorehq, à réappliquer telles quelles sur un nouveau compte.
On ajoute une ligne à chaque nouvelle leçon, en écrivant à côté si c'est **prouvé** (chiffres) ou **en test**.
Les idées de vidéos sont dans `IDEES.md` ; le fonctionnement de Clipper est dans `CLAUDE.md`.

---

## 1. Avant de créer un compte

- **TikTok fixe la région du compte à sa création** (carte SIM et connexion du téléphone), et on ne peut plus la changer.
  Un compte créé en Belgique montre ses vidéos d'abord aux Français et aux Belges : @animelorehq3 = **88 % de France**
  alors que les vidéos sont en anglais → plafond d'environ 250 vues et 0 commentaire. **Prouvé (05/11).**
  → Pour viser le public anglophone, le compte doit être rattaché aux US ou au Royaume-Uni **dès sa création**.
- Ne pas créer plusieurs comptes en série sur le même téléphone (« animelorehq3 ») : TikTok peut freiner les comptes en série.
- YouTube : un numéro de téléphone ne vérifie que 2 chaînes. Sans vérification → programmation limitée.
  Pour un nouveau compte, prévoir un numéro libre.
- **Un seul thème dès le 1er post** (ex. combats et transformations anime). Pas d'actus, de quiz ou de wallpapers mélangés :
  l'algorithme ne sait plus à qui montrer les vidéos. **Prouvé (05/11)** : les posts hors thème ont fait 3 à 5 vues.
- **Ne pas acheter de promo** : la promo TikTok a donné 9 816 vues, mais seulement 4 likes et 2 partages. Elle amène des gens qui
  ne s'intéressent pas à l'anime et brouille le public du compte. **Prouvé (05/11).**

## 2. La vidéo elle-même (toutes plateformes)

- **La 1re seconde décide de tout** : l'image 0 doit montrer les persos et le sujet, lisibles sans contexte, jamais un écran vide.
  Il doit y avoir de l'action dans la 1re seconde. Les gens partaient après 2 s → démarrage en colonne qui fusionne tout de suite.
- **L'image 0 sert aussi de couverture** (Buffer `thumbnailOffset: 0`) : les 2 visages + « VS ».
- **Au moins 30 s.** Le meilleur Short fait environ 30 s (Luffy Transformations : 86 % regardé en moyenne).
- **Méthode vidIQ « View Jail »** :
  - 0 vue : contenu produit en masse, restrictions, ou mauvaise ouverture ;
  - 1k vues : les inconnus ne mordent pas → changer UNE chose (le format ou le sujet) ;
  - 10k vues : rendre la vidéo compréhensible sans connaître l'anime (mystère, question, choix) ;
  - 30k vues : trouver la seconde exacte où les gens partent, dans la courbe de rétention.
- **Le Short « se termine »** : écran de fin de 1,5 s, pas de « follow » ni de merci à la fin. Le « Like & Follow » va au **début**.
- **Duel « injuste mais crédible »** : le petit qui bat le dieu (Kid Goku bat Beerus) → les gens commentent pour contester.
  **Prouvé** : 18,9k vues, la vidéo accélérait encore.
- **Mais il faut aussi des défaites**, et une **logique de puissance** (pas de Kid Sasuke au-delà du Perfect Susanoo).
  Alterner victoires et défaites dans une série.
- **Séries numérotées** (« DOMAIN WAR #6 ») et « part 2 » quand une vidéo marche.
- **Musique** : continue et en fond, jamais rejouée à chaque événement. Volume autour de −24 LUFS (les gens trouvaient −6 LUFS beaucoup trop fort).
- **Les formats qui marchent sur YouTube** : Transformations (fusion façon Suika, environ 30 s, avec un easter egg), Power Up.

## 3. YouTube Shorts (ce qui marche le mieux)

- **Titre** (70 car. max) : les noms des persos au début, une question, **jamais le gagnant**.
- **Description** : une phrase avec les mots que les gens tapent (« A vs B who would win »), un appel au commentaire,
  5 hashtags max (perso A, perso B, anime + 2 de format).
- **Tags** : 500 caractères, avec les variantes de recherche.
- **Publication** : à la main (un compte non vérifié a une programmation limitée ; l'API d'un projet non audité force la vidéo en privé).
- **Monétisation** : jamais d'extraits d'anime (la chaîne AMV a été refusée pour « réutilisation de contenus »).
  Plusieurs formats, une identité forte, pas l'air « produit à la chaîne ». Sons officiels d'anime = risque Content ID.
- **Paliers YPP** : 500 abonnés + 3 vidéos + 3M vues Shorts en 90 j (dons des fans) ; 10M en 90 j (palier complet) ;
  20M en 90 j à partir du 1er février 2027.

## 4. TikTok

- **Le groupe test** : chaque vidéo est montrée à environ 250 personnes. Pour passer à l'étape suivante, il faut des **commentaires
  et des partages** (pas seulement des likes).
- **Question à un mot** dans la légende : « Luffy or Kaido? One word 👇 », « Yes or no 👇 », « Rate the final form 1-10 👇 ».
  Commenter doit demander zéro effort. **En test (05/11).**
- **Légende** : titre / une phrase avec les mots-clés (TikTok indexe la légende dans sa recherche) / la question / les hashtags.
- **Hashtags** : jusqu'à 8, tous **ciblés** : persos (#sasuke), noms complets (#madarauchiha), franchise (#naruto #narutoshippuden),
  1 seul tag de format (#animebattle ou #animetransformation). Pas de #fyp ni #anime. **En test (05/11).**
- **Créneau** : test d'un post à 1:00 AM Bruxelles (7 PM New York) face à un post à 6:00 PM. Rappel : l'heure ne change pas le PAYS,
  seulement combien de gens sont réveillés. **En test (05/11).**
- **Pas de son tendance ni de post à la main** : tout passe par Buffer (indispensable avec plusieurs comptes).
- **Idée pas encore faite** : « 1 or 2? Comment 👇 » écrit DANS la vidéo, avec un numéro sur chaque perso.

## 5. Instagram Reels

- **Les reels anime viraux sont des « crossovers »** : l'anime plus un 2e public, souvent plus grand
  (#onepiece + #gym, #rocklee + #setups, #attackontitan + #guitar, #naruto + #cars, #anime + #ps5). 5 sur 5 analysés le 05/11.
- **Légende très courte** : 1 à 4 mots (« RUMBLING », « One Piece Workout Arc », « Rock Lee🔥 »), souvent une référence
  que seuls les fans comprennent. Chez nous : titre + question courte, sans « Follow ».
- **5 hashtags max** (limite d'Instagram) = 2 anime (perso + franchise) + 3 du 2e public selon le format :
  - Domain War : #simulation #gaming #pongwars
  - Power Up : #satisfying #oddlysatisfying #simulation
  - Transformations : #suikagame #satisfying #oddlysatisfying
  **En test (05/11).**
- **Ce qui fait tourner un reel, c'est le partage en DM** (quelqu'un l'envoie à un pote), puis le temps de visionnage.
  Les hashtags indiquent seulement le sujet. Idée : « Tag a friend who'd pick Sasuke 👇 ».
- **À ne pas faire** : la légende copiée-collée « astuce algorithme » (#🇯🇵, résumés de films…) vue sur les comptes robots.
  C'est du spam, sans rapport avec la vidéo, et ça brouille le public.

## 6. Organisation (Buffer)

- Buffer gratuit : 3 comptes, 10 posts programmés max par compte. TikTok et Instagram 100 % automatiques.
- La vidéo doit être à une URL publique stable (dépôt GitHub `animelore-media`, URL raw **figée sur un commit** :
  l'URL `main` peut renvoyer 404 juste après un envoi).
- Chaque vidéo prête = `.mp4` + `.txt` (heure, légendes TikTok et Instagram, titre, description et tags YouTube) dans `_videos pretes/`.
  Les vidéos sans date vont dans `_videos pretes/plus tard/`.
- 1 vidéo de transformations par jour ; au moins 2 h entre deux posts ; formats variés dans la journée.
- Ne pas juger un format avant une vingtaine de posts. Ne pas toucher (accélérer, recouper) une vidéo déjà programmée.
- Répondre aux premiers commentaires dans l'heure et épingler son propre commentaire.

## 7. Résultats des tests (à remplir)

| Date | Test | Résultat |
|---|---|---|
| 05/11 | TikTok 1 AM (Sasuke Transformations) vs 6 PM (Kid Sasuke vs Madara) : pays + commentaires | ? |
| 05/11 | Hashtags ciblés + question à un mot (TikTok) | ? |
| 05/11 | Hashtags crossover + légende courte (Instagram) | ? |
