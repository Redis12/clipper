# Clipper

Tu colles une URL YouTube (vidéo, playlist ou chaîne). Pour chaque vidéo, Clipper sort 5 à 15 clips de 2 à 5 min, chacun avec une note, 3 titres, une description, 10 tags et une miniature. Tu valides en un clic, et les clips validés partent dans une file de publication **privée et programmée** sur YouTube.

Détails techniques et conventions : voir `CLAUDE.md`.

## Installation (Windows)

1. **Python 3.11+** et **ffmpeg** :
   ```powershell
   winget install Python.Python.3.12 Gyan.FFmpeg DenoLand.Deno
   ```
   Deno sert à yt-dlp pour lire YouTube. Ferme et rouvre le terminal ensuite.
2. **Le projet** :
   ```powershell
   cd clipper
   python -m venv .venv
   .venv\Scripts\activate
   pip install -e ".[dev]"
   copy .env.example .env
   ```
3. **Clés** dans `.env` :
   - `ANTHROPIC_API_KEY` : console.anthropic.com
   - `DEEPGRAM_API_KEY` : console.deepgram.com
   - `YOUTUBE_CLIENT_SECRETS` : voir ci-dessous

### YouTube (une seule fois)
1. Dans Google Cloud Console, crée un projet et active **YouTube Data API v3**.
2. Configure l'écran de consentement OAuth : type « Externe », ajoute ton compte comme utilisateur test.
3. Crée un identifiant OAuth de type **Application de bureau**, télécharge le JSON en `client_secret.json` à la racine.
4. Lance `clipper auth`. Le navigateur s'ouvre : choisis la chaîne de destination.
5. Fais une **demande d'audit** (formulaire « YouTube API Services – Audit and Quota Extension »). Tant que le projet n'est pas audité, YouTube verrouille en privé les vidéos uploadées via l'API, même avec une date programmée : elles ne sortiront pas toutes seules.
6. Pour les miniatures personnalisées, la chaîne doit être vérifiée (youtube.com/verify).
7. `clipper playlists` liste tes playlists. Copie l'ID voulu dans `config.yaml` → `publish.playlist_id`.

## Slideshows anime (en anglais)

1. **Images** : page *Images* de `clipper serve`.
   - Colle un épisode, un trailer, un opening ou une playlist avec le nom de l'anime. L'outil garde une image nette par changement de plan.
   - Ou range tes images dans `library\<Anime>\<Personnage>\`, puis clique sur *Rescanner*. C'est le plus précis pour avoir le bon personnage.
   - Mets quelques musiques libres de droits dans `library\_music\` pour les Shorts.
2. **Tendances** : page *Tendances*. Clique *Actualiser* pour récupérer les Shorts anime les plus vus de la semaine via l'API YouTube officielle. Pour TikTok, dépose des captures d'écran des slideshows qui cartonnent dans ton fil : Claude les lit. Les idées s'en inspirent ensuite automatiquement, et le bouton *3 idées* part d'un post précis.
3. **Idées** : page *Slideshows* → *Générer 12 idées*, puis *Produire* sur celles qui te plaisent. Tu peux aussi taper ton propre sujet.
4. **Revue** : corrige le texte, clique une autre image sous une slide, vérifie les slides marquées « fait incertain », puis *Valider* (touche `v`).
5. **Publication** : un créneau est attribué, par défaut 12:30 et 19:30 heure de New York.
   - YouTube Short : automatique, en privé programmé.
   - Instagram et TikTok : bouton *Pack* (images + légende) à poster toi-même, puis *Posté*. Ça passera en automatique une fois leurs accès configurés.

## Utilisation (clips)

```powershell
clipper serve          # http://127.0.0.1:8765 : colle une URL, le traitement démarre
```
ou en ligne de commande :
```powershell
clipper add "https://www.youtube.com/@machaine" --run
clipper status
clipper queue
clipper publish --dry-run
clipper publish
```

**Publication automatique** : tant que `clipper serve` tourne, il tente une publication toutes les 30 min. Pour que ça tourne même sans la page ouverte :
```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_publish_task.ps1
```
Sur macOS ou Linux, ajoute une ligne crontab : `17 * * * * cd /chemin/clipper && .venv/bin/clipper publish`

### Raccourcis de la page de revue (pensés pour AZERTY)
| Touche | Action |
|---|---|
| `j` `k` ou `↓` `↑` | clip suivant / précédent |
| `espace` | lecture / pause (le lecteur s'arrête à la fin du clip) |
| `d` · `f` | écouter le début · les 8 dernières secondes |
| `a` `z` | début −1 s / +1 s |
| `q` `s` | fin −1 s / +1 s |
| `1` `2` `3` (ou `&` `é` `"`) | choisir le titre |
| `t` / `⇧T` | image de miniature suivante / précédente |
| `v` · `r` · `u` | valider · rejeter · annuler |

Valider attribue au clip le prochain créneau libre (`publish.slots`, `publish.days`, heure de Bruxelles). Ajuster un clip déjà validé garde son créneau. Le fichier final est re-rendu avant l'upload.

## Quota YouTube
D'après la doc officielle (mise à jour du 15/10/2026), `videos.insert` a son **propre seau de 100 appels/jour**. La miniature (50) et l'ajout en playlist (50) puisent dans les **10 000 unités/jour**. Le facteur limitant est donc ton plafond `publish.max_uploads_per_day` (6 par défaut), pas YouTube. Les coûts sont dans `config.yaml` → `quota` : si Google les change, modifie-les là.

Le compteur se remet à zéro à **minuit, heure du Pacifique** (9 h à Bruxelles). Quand le quota est atteint, la publication s'arrête proprement : la file reste intacte et reprend au passage suivant. Si une vidéo est créée mais que la miniature ou la playlist échoue, seule la partie manquante est refaite.

## Tests
```powershell
pytest -q
```
49 tests. Ils couvrent les bornes, la fusion des blocs, les créneaux, le quota, la découpe réelle avec ffmpeg (durée et −14 LUFS mesurés), les miniatures, la page de revue et la publication avec un faux client YouTube.
