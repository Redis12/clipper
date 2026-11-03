"""TikTok : connexion (Login Kit Desktop + PKCE), hébergement des images, envoi du carrousel.

Mode « inbox » (par défaut) : l'API dépose le carrousel dans la boîte de réception de l'appli TikTok
(post_mode MEDIA_UPLOAD, scope video.upload). Tu reçois une notification, tu ajoutes le son, tu publies.
Pas besoin d'app auditée pour ça (l'audit ne concerne que la publication directe, sinon forcée en privé).
Limite TikTok : 5 envois en attente par 24 h.

Mode « direct » : publication immédiate (scope video.publish). Sans audit, TikTok force le post en privé.
"""
from __future__ import annotations

import hashlib
import json
import secrets
import time
from pathlib import Path

import httpx

from .. import config

AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
INIT_URL = "https://open.tiktokapis.com/v2/post/publish/content/init/"
STATUS_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"

_pending: dict[str, str] = {}          # state → code_verifier (le temps de la connexion)


def tcfg() -> dict:
    return config.get()["slides"]["publish"]["tiktok"]


def mode() -> str:
    return "direct" if tcfg().get("mode") == "direct" else "inbox"


def scopes() -> str:
    return "user.info.basic," + ("video.publish" if mode() == "direct" else "video.upload")


def token_path() -> Path:
    return config.data_dir() / "tiktok_token.json"


def connected() -> bool:
    return token_path().exists()


def redirect_uri(port: int) -> str:
    return f"http://127.0.0.1:{port}/tiktok/callback/"


def auth_url(port: int) -> str:
    """Lien de connexion. PKCE à la TikTok : le challenge est le SHA-256 du verifier en HEXADÉCIMAL."""
    verifier = secrets.token_urlsafe(48)[:64]
    state = secrets.token_urlsafe(16)
    _pending[state] = verifier
    q = httpx.QueryParams({
        "client_key": config.secret("TIKTOK_CLIENT_KEY"), "response_type": "code", "scope": scopes(),
        "redirect_uri": redirect_uri(port), "state": state,
        "code_challenge": hashlib.sha256(verifier.encode()).hexdigest(), "code_challenge_method": "S256"})
    return f"{AUTH_URL}?{q}"


def _save(tok: dict) -> dict:
    tok["expires_at"] = time.time() + int(tok.get("expires_in", 86400))
    token_path().write_text(json.dumps(tok), encoding="utf-8")
    return tok


def finish_auth(code: str, state: str, port: int) -> dict:
    verifier = _pending.pop(state, None)
    if not verifier:
        raise RuntimeError("Connexion TikTok expirée ou inconnue : recommence depuis Clipper.")
    r = httpx.post(TOKEN_URL, data={
        "client_key": config.secret("TIKTOK_CLIENT_KEY"), "client_secret": config.secret("TIKTOK_CLIENT_SECRET"),
        "code": code, "grant_type": "authorization_code", "redirect_uri": redirect_uri(port),
        "code_verifier": verifier}, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=30)
    tok = r.json()
    if "access_token" not in tok:
        raise RuntimeError(f"TikTok a refusé la connexion : {tok.get('error_description') or tok}")
    granted = set((tok.get("scope") or "").split(","))
    need = scopes().split(",")[-1]
    if need not in granted:
        raise RuntimeError(f"Autorisation « {need} » non accordée (reçu : {tok.get('scope')}). "
                           "Vérifie que le produit Content Posting API est ajouté à ton app TikTok.")
    return _save(tok)


def access_token() -> str:
    p = token_path()
    if not p.exists():
        raise RuntimeError("TikTok pas connecté : page Publication slideshows → « Connecter TikTok »")
    tok = json.loads(p.read_text(encoding="utf-8"))
    if tok.get("expires_at", 0) - time.time() < 300:
        r = httpx.post(TOKEN_URL, data={
            "client_key": config.secret("TIKTOK_CLIENT_KEY"), "client_secret": config.secret("TIKTOK_CLIENT_SECRET"),
            "grant_type": "refresh_token", "refresh_token": tok["refresh_token"]},
            headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=30)
        new = r.json()
        if "access_token" not in new:
            raise RuntimeError(f"TikTok : reconnecte-toi (jeton refusé : {new.get('error_description') or new})")
        tok = _save({**tok, **new})
    return tok["access_token"]


def send(title: str, description: str, urls: list[str]) -> str:
    """Envoie le carrousel. Rend le publish_id."""
    t = tcfg()
    info = {"title": title[:90], "description": description[:4000]}
    if mode() == "direct":
        info |= {"privacy_level": t.get("privacy_level", "PUBLIC_TO_EVERYONE"), "disable_comment": False,
                 "auto_add_music": bool(t.get("auto_add_music", True))}
    body = {"post_info": info,
            "source_info": {"source": "PULL_FROM_URL", "photo_cover_index": 0, "photo_images": urls[:35]},
            "post_mode": "DIRECT_POST" if mode() == "direct" else "MEDIA_UPLOAD", "media_type": "PHOTO"}
    r = httpx.post(INIT_URL, json=body, timeout=60,
                   headers={"Authorization": f"Bearer {access_token()}",
                            "Content-Type": "application/json; charset=UTF-8"})
    data = r.json()
    err = data.get("error") or {}
    if r.status_code >= 400 or err.get("code", "ok") != "ok":
        hint = {"url_ownership_unverified": " → l'adresse des images n'est pas vérifiée dans ton app TikTok "
                                            "(URL properties).",
                "spam_risk_too_many_pending_share": " → 5 envois en attente max : publie ou supprime ceux de "
                                                    "ta boîte TikTok.",
                "scope_not_authorized": " → reconnecte TikTok."}.get(err.get("code"), "")
        raise RuntimeError(f"TikTok {r.status_code} : {err.get('code')} {err.get('message', '')}{hint}")
    return data["data"]["publish_id"]


def status(publish_id: str) -> dict:
    r = httpx.post(STATUS_URL, json={"publish_id": publish_id}, timeout=30,
                   headers={"Authorization": f"Bearer {access_token()}",
                            "Content-Type": "application/json; charset=UTF-8"})
    return r.json().get("data") or {}
