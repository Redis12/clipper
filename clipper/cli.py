"""Commande `clipper`."""
from __future__ import annotations

import typer
from pathlib import Path

from . import config, db, ingest, pipeline, quota, schedule, youtube
from .util import setup_logging, tc

app = typer.Typer(add_completion=False, no_args_is_help=True, help="Clips YouTube : sélection, revue, publication.")


@app.callback()
def main(verbose: bool = typer.Option(False, "-v", "--verbose", help="Journal détaillé")):
    setup_logging(verbose)
    config.load()


@app.command()
def add(url: str, run: bool = typer.Option(False, "--run", help="Traiter tout de suite")):
    """Ajoute une vidéo, une playlist ou une chaîne (sans retraiter l'existant)."""
    new, known = ingest.add(url)
    typer.echo(f"{len(new)} nouvelle(s) vidéo(s), {len(known)} déjà connue(s).")
    if run:
        for vid in new:
            pipeline.process_video(vid)


@app.command()
def run(video: str = typer.Option(None, "--video", help="Seulement cette vidéo (ID YouTube)")):
    """Fait avancer le pipeline sur tout ce qui est en attente."""
    pipeline.run_all(video)


@app.command()
def status():
    """État des vidéos et des clips."""
    for v in db.query("SELECT * FROM videos ORDER BY created_at"):
        n = {r["status"]: r["n"] for r in db.query(
            "SELECT status, COUNT(*) AS n FROM clips WHERE video_id=? GROUP BY status", (v["id"],))}
        detail = " ".join(f"{k}:{x}" for k, x in sorted(n.items()))
        typer.echo(f"{v['id']}  {v['status']:<11} {tc(v['duration'] or 0):>8}  {(v['title'] or '')[:50]:<50}  {detail}")
        if v["error"]:
            typer.echo(f"    ↳ {v['error'][:200]}")


@app.command()
def serve(host: str = typer.Option(None), port: int = typer.Option(None),
          lan: bool = typer.Option(False, "--lan", help="Accessible aussi depuis ton téléphone (même Wi-Fi)")):
    """Lance la page de revue locale."""
    import uvicorn

    s = config.get().get("server", {})
    lan = lan or bool(s.get("lan", False))
    h = host or ("0.0.0.0" if lan else s.get("host", "127.0.0.1"))
    p = port or int(s.get("port", 8765))
    typer.echo(f"Revue sur ce PC : http://127.0.0.1:{p}")
    if lan:
        import os
        os.environ["CLIPPER_LAN"] = "1"
        from .web import lan as lanmod
        url = lanmod.phone_url(p)
        typer.secho(f"Sur ton téléphone (même Wi-Fi) : {url}", fg="green")
        typer.echo("Garde ce lien pour toi : il donne accès à Clipper. QR code : page Téléphone sur le PC.")
        try:
            import qrcode  # facultatif : pip install qrcode
            qr = qrcode.QRCode(border=1)
            qr.add_data(url)
            qr.print_ascii(invert=True)
        except ImportError:
            pass
    uvicorn.run("clipper.web.app:app", host=h, port=p, log_level="warning")


@app.command()
def auth():
    """Connexion OAuth à YouTube (une seule fois)."""
    try:
        typer.echo(f"Jeton enregistré : {youtube.auth()}")
    except RuntimeError as e:
        typer.secho(str(e), fg="red")
        raise typer.Exit(1)


@app.command()
def playlists():
    """Liste tes playlists (ID à copier dans config.yaml)."""
    for p in youtube.list_playlists():
        typer.echo(f"{p['id']}  [{p['privacy']}]  {p['title']}")


@app.command("queue")
def show_queue():
    """File de publication et quota restant."""
    items = schedule.queue()
    if not items:
        typer.echo("File vide.")
    for c in items:
        t = (c["titles"] or [c["topic"]])[c["title_idx"] or 0]
        flag = " (uploadé, finitions en attente)" if c["youtube_id"] else ""
        typer.echo(f"{schedule.local(c['publish_at']):<16} #{c['id']:<5} {t}{flag}")
    s = quota.summary()
    typer.echo("\nQuota (jour PT " + s["pt_day"] + ") : " + ", ".join(
        f"{b} {d['remaining']}/{d['limit']}" + (" BLOQUÉ" if d["blocked"] else "") for b, d in s["buckets"].items()))
    typer.echo(f"Uploads aujourd'hui : {s['uploads_today']}/{s['cap']} · encore possibles : {s['clips_left_today']}")


@app.command()
def publish(dry_run: bool = typer.Option(False, "--dry-run", help="Montre sans uploader")):
    """Publie ce qui est dû : clips (YouTube, privé programmé) et slideshows (Shorts, Instagram, TikTok)."""
    from .slides import publish as spublish
    for line in youtube.publish(dry_run=dry_run) + spublish.run(dry_run=dry_run):
        typer.echo(line)


@app.command("ideas")
def slides_ideas(n: int = typer.Option(None, help="Nombre d'idées")):
    """Demande des idées de slideshows à Claude."""
    from .slides import ideas as sideas
    for sid in sideas.generate_ideas(n):
        s = db.get("slideshows", sid)
        typer.echo(f"#{sid:<4} [{s['score']:>3}] {s['anime']} · {s['format']} · {s['topic']}")


@app.command("make")
def slides_make(ids: list[int] = typer.Argument(None, help="Slideshows à produire (sinon : ceux en attente)")):
    """Produit des slideshows (script, images, rendu)."""
    from .slides import produce
    for sid in ids or produce.pending():
        db.update("slideshows", sid, status="queued")
        ok = produce.produce(sid)
        typer.echo(f"#{sid} : {'prêt à valider' if ok else db.get('slideshows', sid)['error']}")


@app.command("capture")
def capture(url: str, anime: str = typer.Option(..., "--anime", help="Nom de l'anime (dossier)")):
    """Capture des images d'un épisode, trailer ou playlist dans la bibliothèque."""
    from .slides import library
    for sid in library.add_source(url, anime):
        typer.echo(f"{sid} : {library.process_source(sid)} images")


@app.command("trends")
def trends_cmd():
    """Veille : actualise les tendances (YouTube, Instagram si configuré) et les fait analyser."""
    from .slides import trends
    for line in trends.refresh():
        typer.echo(line)
    for t in trends.top(10):
        typer.echo(f"{int(t['score'] or 0):>10}  [{t['platform']}] {t['anime'] or '?'} · {t['format']} · {t['topic']}")


@app.command("trends-import")
def trends_import(files: list[str]):
    """Veille : analyse des captures d'écran de posts (TikTok, Instagram…)."""
    from pathlib import Path

    from .slides import trends
    for f in files:
        tid = trends.import_screenshot(Path(f), Path(f).name)
        t = db.get("trends", tid)
        typer.echo(f"{Path(f).name} → {t['status']} : {t['format'] or ''} · {t['topic'] or ''} · {t['views'] or '?'} vues")


@app.command("battle")
def battle_cmd(names: str = typer.Argument(..., help="Persos séparés par des virgules (noms des dossiers)"),
               title: str = typer.Option("Which anime character wins?", "--title")):
    """Vidéo « Which character wins? » : les persos-balles se volent des liens."""
    from .slides import battle
    fighters = battle.fighters_from_library([n.strip() for n in names.split(",") if n.strip()])
    typer.echo(battle.generate(fighters, title=title))


@app.command("fusion")
def fusion_cmd(levels: str = typer.Argument(..., help="Dossier de library/_fusion, ou persos séparés par des virgules (du plus petit au plus gros)"),
               title: str = typer.Option("Fusion Battle", "--title"),
               sound: str = typer.Option("", "--sound", help="Fichier de library/_sounds"),
               fat: float = typer.Option(1.0, "--fat", help="0 = son presque normal, 2 = énorme")):
    """Vidéo « Fusion Battle » façon Suika : 2 icônes identiques fusionnent en la suivante."""
    from .slides import battle, fusion
    tiers = fusion.tiers_from_chain(levels) if "," not in levels else \
        battle.fighters_from_library([n.strip() for n in levels.split(",") if n.strip()])
    typer.echo(fusion.generate(tiers, title=title, sound=fusion.sound_path(sound), fat=fat))


@app.command("race")
def race_cmd(a: str = typer.Argument(..., help="Dossier de library/_fusion (ex. Goku)"),
             b: str = typer.Argument(..., help="Autre dossier de library/_fusion (ex. Naruto)"),
             title: str = typer.Option("", "--title"),
             sound_a: str = typer.Option("", "--sound-a"), sound_b: str = typer.Option("", "--sound-b")):
    """Vidéo « Fusion Race » : 2 bols en même temps, le premier à sa forme finale gagne."""
    from .slides import fusion, fusion_race
    typer.echo(fusion_race.generate([fusion.tiers_from_chain(a), fusion.tiers_from_chain(b)], [a, b],
                                    title=title or None,
                                    sounds=[fusion.sound_path(sound_a), fusion.sound_path(sound_b)]))


@app.command("domain")
def domain_cmd(names: str = typer.Argument(..., help="2 persos séparés par une virgule (ex. \"Gojo,Sukuna\")"),
               seconds: float = typer.Option(35, "--seconds"), title: str = typer.Option("", "--title"),
               winner: str = typer.Option("", "--winner", help="Perso qui gagne, ou draw:<perso qui perd d'abord> (égalité)"),
               comeback: bool = typer.Option(False, "--comeback", help="Il perd d'abord, sort son secret, puis gagne"),
               cine: str = typer.Option("auto", "--cine", help="Transformation : auto, clip (anime) ou card (pop-up)"),
               sounds: str = typer.Option("anime", "--sounds", help="Sons : auto, anime (officiels d'abord) ou safe")):
    """Vidéo « Domain War » : 2 domaines (grille) qui s'affrontent, attaques nommées, le plus grand gagne."""
    from .slides import battle, domain
    fighters = battle.fighters_from_library([n.strip() for n in names.split(",") if n.strip()])[:2]
    if len(fighters) != 2:
        raise typer.BadParameter("Il faut 2 persos trouvés dans la bibliothèque")
    w, under = None, None
    if winner:
        from .slides import library
        keys = [library.norm(f["name"]) for f in fighters]
        if winner.lower().startswith("draw"):               # « draw:Sasuke » = égalité, Sasuke perd d'abord
            w = -1
            who = winner.partition(":")[2]
            under = next((i for i, k in enumerate(keys) if who and library.norm(who) in k), None)
        else:
            w = next((i for i, k in enumerate(keys) if library.norm(winner) in k), None)
    typer.echo(domain.generate(fighters, seconds=seconds, title=title or None, winner=w,
                               comeback=comeback and w is not None, cine=cine, sounds=sounds, underdog=under))


@app.command("vfx-import")
def vfx_import(src: str = typer.Argument(..., help="GIF / WebP animé, vidéo (mp4, webm) ou dossier d'images"),
               name: str = typer.Option(..., "--as", help="Nom de l'attaque ou de l'effet (ex. Rasengan, impact)")):
    """VFX : importe une animation d'effet (fond sombre/blanc détouré, recadrée) dans library/_domain/fx/<nom>_frames/."""
    from pathlib import Path

    from .slides import domain, fxengine, library
    frames = [domain._prep_sprite(f, crop=False) for f in fxengine.flipbook(Path(src))]
    frames = domain._union_crop([f for f in frames if f.getchannel("A").getbbox()])
    if len(frames) < 2:
        raise typer.BadParameter("aucune animation lisible dans ce fichier")
    out = library.root() / "_domain" / "fx" / f"{name}_frames"
    out.mkdir(parents=True, exist_ok=True)
    for i, f in enumerate(frames):
        f.save(out / f"{i:03d}.png")
    typer.echo(f"{len(frames)} images → {out}")


@app.command("vfx-sheet")
def vfx_sheet(out: str = typer.Option("vfx_preview.png", "--out")):
    """VFX : planche d'aperçu des effets générés (vfxgen) pour les juger / retoucher."""
    from PIL import Image

    from .slides import vfxgen
    rows = [vfxgen.sheet(n, 128) for n in vfxgen.NAMES]
    W, H = max(r.width for r in rows), sum(r.height for r in rows)
    o, y = Image.new("RGB", (W, H)), 0
    for r in rows:
        o.paste(r, (0, y))
        y += r.height
    o.save(out)
    typer.echo(out)


@app.command("upscale")
def upscale_cmd():
    """Images : agrandit par IA toutes les petites images de la bibliothèque (Real-ESRGAN anime)."""
    from .slides import upscale
    typer.echo(upscale.upscale_library())


@app.command("host-file")
def host_file(path: str):
    """Met un fichier en ligne sur l'hébergement (ex. fichier de vérification TikTok)."""
    from pathlib import Path

    from .slides import publish as spublish
    typer.echo(f"En ligne (dans ~1 min) : {spublish.host_file(Path(path))}")


@app.command("tag")
def tag(anime: str = typer.Option(..., "--anime", help="Anime dont on trie les captures")):
    """Images : Claude range les captures non triées dans les dossiers des personnages."""
    from .slides import library
    typer.echo(library.tag_frames(anime))


@app.command("scan")
def scan():
    """Rescanne la bibliothèque d'images."""
    from .slides import library
    typer.echo(library.scan())




@app.command("stats-auth")
def stats_auth():
    """Connexion LECTURE SEULE aux statistiques YouTube (une fois, choisir la chaîne animelorehq)."""
    from . import stats
    try:
        typer.echo(f"Jeton enregistré : {stats.auth()}")
    except RuntimeError as e:
        typer.secho(str(e), fg="red")
        raise typer.Exit(1)


@app.command("stats")
def stats_cmd(min_hours: float = typer.Option(24, "--min-hours", help="Seulement les Shorts publiés depuis N heures")):
    """Bilan des Shorts (méthode vidIQ « View Jail ») → library/_stats/rapport_<date>.txt."""
    from . import stats
    try:
        p = stats.run(min_hours)
    except RuntimeError as e:
        typer.secho(str(e), fg="red")
        raise typer.Exit(1)
    typer.echo(p.read_text(encoding="utf-8"))
    typer.secho(f"\nRapport : {p}", fg="green")


@app.command("ulti")
def ulti_cmd(name: str = typer.Argument(..., help="Perso (ex. \"Satoru Gojo\")"),
             image: str = typer.Option(..., "--image", help="Image du perso (mains visibles de préférence)"),
             move: str = typer.Option(..., "--move", help="Nom de l'attaque (ex. \"Hollow Purple\")"),
             color: str = typer.Option("#af46ff", "--color", help="Couleur de l'énergie"),
             clip: str = typer.Option(None, "--clip", help="Vidéo du perso animé par une IA (sinon : animation sans IA)"),
             out: str = typer.Option("ulti_test.mp4", "--out")):
    """Cinématique d'ulti seule (test du rendu, sans lancer de combat)."""
    from .slides import domain, ulti
    st = domain.style_of(move)
    p = ulti.generate(name, image, move, Path(out), color=domain.hex_rgb(color, (175, 70, 255)), style=st, clip=clip)
    typer.echo(f"Ulti : {p}")


if __name__ == "__main__":
    app()
