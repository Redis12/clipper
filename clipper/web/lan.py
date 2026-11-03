"""Accès depuis le téléphone (même Wi-Fi) : protégé par une clé secrète dans l'URL, puis un cookie.

Les requêtes venant du PC lui-même (127.0.0.1) passent toujours ; les autres doivent présenter la clé.
"""
from __future__ import annotations

import secrets
import socket

from fastapi import Request
from fastapi.responses import HTMLResponse

from .. import config

COOKIE = "clipper_key"
LOCAL = {"127.0.0.1", "::1", "localhost", "testclient"}


def token() -> str:
    p = config.data_dir() / "lan_key.txt"
    if not p.exists():
        p.write_text(secrets.token_urlsafe(12), encoding="utf-8")
    return p.read_text(encoding="utf-8").strip()


def phone_url(port: int) -> str:
    return f"http://{lan_ip()}:{port}/m?k={token()}"


def qr_svg(text: str) -> str:
    """QR code en SVG (vide si le paquet `qrcode` n'est pas installé)."""
    try:
        import qrcode
        import qrcode.image.svg
    except ImportError:
        return ""
    img = qrcode.make(text, image_factory=qrcode.image.svg.SvgPathImage, box_size=8, border=2)
    return img.to_string(encoding="unicode")


REFUSED = """<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Clipper · accès</title>
<style>body{font:16px system-ui,sans-serif;margin:0;padding:24px;background:#111;color:#eee}
input,button{font-size:16px;padding:12px;width:100%;box-sizing:border-box;margin-top:8px;border-radius:8px;border:1px solid #444}
button{background:#FFD400;color:#111;font-weight:700;border:0}p{color:#aaa;line-height:1.4}</style></head><body>
<h2>Clipper : clé demandée</h2>
<p>Ce téléphone n'a pas (ou plus) la bonne clé. Le plus simple : sur le PC, ouvre la page
<b>Téléphone</b> de Clipper et scanne le QR code. Sinon, colle ici la clé (la fin du lien, après <code>k=</code>) :</p>
<form method="get" action="/m"><input name="k" placeholder="clé" autocomplete="off" autocapitalize="off">
<button>Entrer</button></form></body></html>"""


def lan_ip() -> str:
    """Adresse du PC sur le réseau local (aucun paquet n'est envoyé)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


async def guard(request: Request, call_next):
    host = request.client.host if request.client else ""
    if host in LOCAL:
        return await call_next(request)
    key = token()
    given = request.query_params.get("k") or request.cookies.get(COOKIE)
    if not given or not secrets.compare_digest(given, key):
        return HTMLResponse(REFUSED, status_code=403)
    response = await call_next(request)
    if request.query_params.get("k"):
        response.set_cookie(COOKIE, key, max_age=60 * 60 * 24 * 365, httponly=True, samesite="lax")
    return response
