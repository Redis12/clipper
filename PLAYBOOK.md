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
- Ne pas créer plusieurs comptes en série sur le même téléphone : TikTok peut freiner les comptes en série (1 perso + 1 chaîne = normal).
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
- **Répondre aux commentaires dans la vidéo** (05/11) : une « part 2 » commence par un écran « YOU SAID AFTER PART 1: » avec les vrais commentaires (captures en anglais) qui arrivent un par un avec un pop, puis « LET'S SEE... » qui claque, puis la vidéo (3 s en tout). Les gens voient que la chaîne lit les commentaires, et la part 2 a une raison d'exister. Les persos restent visibles dès l'image 0. **En test (Kid Goku vs Beerus Part 2).**
- **DA qui ne fait pas « généré »** (05/11, retour de l'utilisateur : « ça fait trop Claude ») : le texte est bien, c'est le STYLE qui fait template (même police grasse partout, fond noir uni, pilules arrondies, vert/rouge/jaune de base). À faire : polices façon titres de jeux anime (gras penché, gros contour), fonds texturés (trame manga, lignes de vitesse, couleurs de la franchise), texte qui claque/arrive en biais, palette par franchise. Valider sur un avant/après avant de changer les vidéos. Le Short doit accrocher en 1 seconde, voire moins.
- **Séries numérotées** (« DOMAIN WAR #6 ») et « part 2 » quand une vidéo marche.
- **Musique** : continue et en fond, jamais rejouée à chaque événement. Volume autour de −24 LUFS (les gens trouvaient −6 LUFS beaucoup trop fort).
- **Domain War mis en pause (05/11)** : rétention < 50 % et format le plus long à produire. Garder les formats courts et lisibles en 1 seconde.
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
- **Vidéo de coaching TikTok analysée (05/11, Rob, « Fastest way to go viral on TikTok 2026 » ; c'est en partie une pub pour l'outil Content Buddy, et ses chiffres sont ceux d'un seul créateur)** :
  - **Avoir l'air humain** : TikTok soupçonne les comptes qui ne font que poster (robots) et peut les freiner sans le dire. → Passer 10 minutes à la main, 3 à 5 jours par semaine, à des heures **différentes** : liker et commenter des vidéos anime, répondre à nos commentaires. Nos posts partent aussi à des heures trop « rondes » (13:00, 18:00, 22:00 pile) → décaler de quelques minutes au hasard (13:07, 18:12…).
  - **Le compte doit dire de quoi il parle** : le niche dans le **nom affiché** (ex. « AnimeLore | Anime Battles »), une bio avec les mots qu'on tape (anime battles, who would win, transformations), des playlists par série (Domain War, Transformations, Power Up). C'est ce qui fait apparaître le compte dans la recherche TikTok. À faire à la main dans l'appli.
  - **Les mêmes mots partout** : le texte de l'accroche à l'écran = la 1re ligne de la légende = les hashtags. Si les commentaires reprennent ces mots, c'est un signal en plus.
  - **3 hashtags très précis** suffisent selon lui (nous : jusqu'à 8 ciblés ; à tester les deux).
  - **Accroche écrite en rouge** (10 de ses 12 vidéos virales) et **quelque chose qui change à l'écran toutes les 2-3 secondes**.
  - **Format et sujet en tendance** : chercher le sujet dans TikTok, regarder ce qui a percé et faire la même longueur que les vidéos qui marchent pour ce format.
- **2e vidéo TikTok analysée (05/11, « TikTok algorithm in 120 seconds »)** :
  - **Un compte neuf est d'abord « examiné »** : appareil, connexion, taille d'écran, fuseau horaire, comportement. S'il ressemble à un compte déjà banni ou suspect (même téléphone, même connexion), il est freiné avant même le 1er post. → Pas notre cas : le téléphone n'a que 2 comptes (perso + animelore), ce qui est normal ; le « 3 » vient d'un nom déjà pris. Interagir depuis le compte de la chaîne, pas le perso. Nouveau compte : **ne rien poster pendant 2-3 jours**, juste regarder et liker des vidéos de la niche (« chauffer » le compte).
  - **Groupe test de 200 à 500 personnes** qui regardent déjà ce genre de contenu ; TikTok mesure le % regardé, les revisionnages, les partages et la VITESSE de ces réactions. Si c'est bon → vague 5× plus grande, etc. (= notre plafond ~250 : on ne passe pas la 1re vague).
  - **Ne pas poster trop souvent** (lassitude du public). Après 2 semaines, regarder la meilleure vidéo et en refaire dans le même style.
  - **Heures décalées au hasard** (fait le 05/11 : 13:06, 18:11, 21:53… au lieu de 13:00 / 18:00 / 22:00 pile).
  - Monétisation TikTok (Creator Rewards) : 10k abonnés + 100k vues sur 30 jours ; les vues US paient le plus.
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
- **Vidéos de coaching Instagram analysées (05/11, Dominik, « Grow fast in 30 days » + « Growing just got easier »)** :
  - **Les abonnés ne comptent presque plus** : Instagram recommande les reels à des inconnus le jour même.
    **Chaque reel est jugé seul** : Instagram analyse ce qu'il y a dedans (texte à l'écran, son, légende) et cherche le public qui va avec.
    → Les noms des persos et le sujet doivent être **écrits dans la vidéo**, pas seulement dans la légende.
  - **Les métriques qui comptent** : la durée de visionnage, le **taux de partage** (≥ 2 % des vues = ça décolle, 3–5 % = ça explose)
    et les **commentaires « de qualité »** (une vraie phrase, un avis). « 1 » ou un emoji ne comptent presque pas.
    → Sur Instagram, question de DÉBAT + appel au partage : « Is this fair or should Madara win easily? Explain 👇
    Send this to a Sasuke fan ». Le Power Up Beerus a marché grâce au désaccord, ça va dans le même sens.
    (TikTok garde la question à un mot.)
  - **Un reel qui fait un flop ne veut rien dire** : on le **reposte en changeant UNE chose** (accroche, légende, image 0).
    Exemple de la vidéo : 1 000 vues → 6 000 → 80 000 pour le même sujet.
  - **Poster beaucoup au début** : 30 à 50 reels le plus vite possible pour apprendre au compte (et à nous) qui est le public.
    Utiliser les **Trial Reels** (montrés seulement aux non-abonnés) quand ils sont disponibles.
  - **Le profil décide en 2 secondes** : un inconnu qui arrive regarde les **9 derniers posts**. Ils doivent tous parler au même
    public. Les vieux posts hors thème (actus, quiz) le font partir → les archiver (à faire à la main dans l'appli).
  - **Session de « binge »** : un inconnu devient abonné s'il regarde environ **20 reels en 14 à 30 jours**.
    → Séries numérotées (DOMAIN WAR #N), épingler les 3 meilleurs, rythme régulier.
  - **« Gap theory »** : prendre un format qui marche dans une AUTRE niche et l'appliquer à l'anime. C'est ce qu'on fait déjà
    (Pong Wars → Domain War, Suika → Transformations, Fibonacci → Power Up). Continuer à chercher hors anime.
  - **Astuce** : un carrousel dont la 1re image est une vidéo qui bouge serait davantage poussé aux non-abonnés. **À tester.**
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

- **YouTube aussi dans Buffer** (05/11) : Buffer publie en public à l'heure (appli validée par YouTube), donc pas besoin de la programmation YouTube limitée des chaînes non vérifiées. Pas de champ « tags » : titre + description + hashtags. Plan gratuit = 3 comptes (TikTok, Instagram, YouTube).

## 7. Résultats des tests (à remplir)

| Date | Test | Résultat |
|---|---|---|
| 05/11 | TikTok 1 AM (Sasuke Transformations) vs 6 PM (Kid Sasuke vs Madara) : pays + commentaires | Sasuke Transformations (00:09) : 271 vues, plafond habituel. Kid Sasuke vs Madara parti finalement le 06/11 à 13:06 : **~2 000 vues en 2 h 30** (1re vidéo à passer le groupe test de ~250). |
| 05/11 | Hashtags ciblés + question à un mot (TikTok) | Kid Goku vs Beerus 2 avec la même formule : 288 vues → la formule seule ne suffit pas. Ce qui distingue Madara : méchant ultra connu de TikTok + duel injuste (un gamin contre un dieu) + Power Up qui finit en défaite + publié le midi. **À reproduire à l'identique** avant de conclure. |
| 05/11 | Hashtags crossover + légende courte (Instagram) | ? |

## 8. Première vidéo TikTok qui perce (06/11)
« Can Kid Sasuke beat Madara in under 60 seconds? » (Power Up, 63 s, défaite) : ~2 000 vues en 2 h 30, contre ~250 pour toutes les autres.
Légende : titre-question / phrase avec les mots-clés / « Does Kid Sasuke make it? Yes or no 👇 » / 7 hashtags ciblés
(#sasuke #madara #naruto #narutoshippuden #kidsasuke #madarauchiha #animebattle). Publiée à 13:06 Bruxelles.
Par rapport à Kid Naruto vs Sasuke (même format, 268 vues) : nouvelle légende + Madara. Par rapport à Kid Goku vs Beerus 2
(même légende, 288 vues) : Naruto/Madara + défaite. → Hypothèse : format Power Up + méchant culte + légende à un mot.
Prochaines vidéos pour vérifier : même formule, autres méchants cultes (une seule chose change à chaque fois).

## 9. Le Gauntlet fait commenter (07/11) — et c'est LE format qui marche le mieux (08/11)
**08/11, constat de l'utilisateur : « les Gauntlet c'est les vidéos qui marchent le mieux et de loin ».** → priorité de
production : au moins un Gauntlet par jour (créneau de 18h), les autres formats en complément.
Sur YouTube, le Gauntlet a fait beaucoup de commentaires : des gens frustrés par le résultat (« X aurait dû l'arrêter »).
La frustration = de l'engagement. À exploiter : répondre aux commentaires dans l'heure, épingler le plus provocant,
et faire une « Part 2 » qui répond au commentaire le plus fréquent (« You said Itachi would stop him… »).

## 10. Sponsos (09/11 : mail dans la bio TikTok)
- Mail pro dédié dans la bio (pas le perso). Beaucoup d'arnaques visent les petits créateurs : pièce jointe .zip/.exe/.scr « brief de campagne », lien qui demande de se connecter à TikTok/Google, « payez des frais pour être payé », faux noms de grandes marques depuis gmail. Règle : jamais ouvrir une pièce jointe exécutable, jamais se connecter via un lien du mail, vérifier le domaine de l'expéditeur, ne jamais payer.
- Une vraie offre donne : marque + site, format (mention, intégration de 5 s, vidéo dédiée), nombre de vidéos, plateformes, délai, prix ou demande de tarif, contrat.
- Avant de répondre, préparer un mini « media kit » : abonnés, vues moyennes par vidéo sur 30 jours, % de public par pays (88 % France au 05/11), meilleur format (Gauntlet).
- Prix de départ indicatif (petits comptes, à ajuster) : de l'ordre de 10–20 € pour 1 000 vues moyennes par vidéo ; jeux mobiles / applis anime = sponsos les plus fréquents pour ce public. Demander au moins 50 % d'avance pour une première collaboration.
- Toujours afficher le partenariat (outil « Contenu de marque » de TikTok, « Partenariat rémunéré » sur YouTube/Instagram) : obligatoire et sinon la vidéo peut être retirée.

## 11. Le compte a percé (09/11)
1,7 M de vues (dit par l'utilisateur le 09/11) ; le public n'est plus surtout français, il est devenu international → tout en anglais (titres, légendes, textes). L'utilisateur ne parle pas bien anglais : pas de voix de lui en anglais ; formats « facts » = texte à l'écran sans voix, ou voix de synthèse anglaise générée par lui (CapCut / ElevenLabs).
- Voix off (09/11) : Kokoro (kokoro-onnx, Apache 2.0, modèles sur les releases GitHub thewh1teagle/kokoro-onnx, Hugging Face bloqué dans le conteneur) ; voix choisie par l'utilisateur = **am_adam** (« on le reconnaît »).

## 12. Instagram : « Confirmez que vous êtes une personne réelle » (09/11)
Mail d'Instagram le 09/11 à 23:31 : profil animelorehq masqué tant qu'on ne confirme pas (180 jours). Un profil masqué = 0 portée → explique le plafond à ~150 vues.
- Confirmer DEPUIS L'APPLI Instagram (pas depuis le lien du mail : les faux mails copient ce modèle). C'est l'utilisateur qui le fait (selfie vidéo / téléphone), jamais Claude.
- Ensuite : Paramètres → Statut du compte → vérifier « Peut être recommandé aux non-abonnés ». Si non : c'est ça qui bloque la portée.
- Pistes pour éviter une nouvelle alerte : pas 3 posts/jour d'un coup sur un compte jeune, heures décalées (déjà fait), interagir un peu à la main (commentaires, stories), bio et photo complètes.
- Posts Buffer pendant le blocage : risquent d'échouer → les reprogrammer une fois le compte confirmé.

## 13. TikTok Shop (11/11) : débloqué mais pas prioritaire
Ouvert en Belgique depuis le 15/06/2026 (affiliés : produits d'autres marques dans la vitrine ou accrochés aux vidéos, commission par vente). Ordre de grandeur pour notre contenu : ~80–600 € pour une vidéo à 1 M de vues, presque rien en dessous, public surtout hors UE (ne peut pas acheter). Décision de l'utilisateur : pas la peine pour l'instant. À reconsidérer seulement avec un format centré produit.

## Analyse des stats (18/11, 147 posts Buffer, 29/10 → 17/11)
- Total : TikTok 7,86M vues · YouTube 3,83M · Instagram 10k (~150 vues par Reel, quel que soit le format → Instagram ne pousse pas le compte).
- TikTok, médiane par format (posts > 2 jours) : Gauntlet 193k (rétention 45 %, 3 commentaires / 1 000 vues) · Power Up 101k (max 3,3M Kid Sasuke vs Madara) · Transfo 31k (max 448k Cell) · Stickman 31k · Domain War 10k · Battle 4,6k · Snake ~2k · Carrousels ~100.
- Les gauntlets « Base Goku vs <univers> » écrasent les autres (1,5M / 390k / 253k, 1 400 à 4 100 commentaires) : crossover + perso « faible » = débat. Un perso déjà surpuissant (Gojo, Sukuna, Ichigo, Gear 5) tient beaucoup moins (6k–42k).
- Power Up : « Kid <héros> vs <grand méchant de sa série> » ; > 1 min, donc compatible Creator Rewards.
- YouTube : Transfo et Power Up très forts (Kid Goku vs Beerus 549k, JoJo transfo 404k, Kid Sasuke vs Madara 339k, Vegeta transfo 325k).
- Créneaux : 10 PM = le pire (médiane TikTok 15k contre ~30k à midi / 6 PM ; YouTube 12k contre 96k à 6 PM). En partie parce que les formats faibles étaient souvent à 10 PM.
- Chute depuis le 14/11 : 4 jours de Battles + Snakes (2,8k → 251 vues) ; à éviter, les formats faibles semblent aussi plomber les suivants.
