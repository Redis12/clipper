"""TikTok : connexion PKCE (hex), envoi en boîte de réception, hébergement GitHub Pages, planification."""
import hashlib
import json
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from clipper import db
from clipper.slides import publish, tiktok


@pytest.fixture()
def keys(cfg, monkeypatch):
    monkeypatch.setenv("TIKTOK_CLIENT_KEY", "ck")
    monkeypatch.setenv("TIKTOK_CLIENT_SECRET", "cs")
    monkeypatch.setenv("GITHUB_TOKEN", "gh")
    return cfg


def resp(url, payload, status=200, method="POST"):
    return httpx.Response(status, request=httpx.Request(method, url), json=payload)


def test_auth_url_uses_hex_pkce_and_upload_scope(keys, monkeypatch):
    u = urlparse(tiktok.auth_url(8765))
    q = {k: v[0] for k, v in parse_qs(u.query).items()}
    assert q["redirect_uri"] == "http://127.0.0.1:8765/tiktok/callback/" and q["scope"] == "user.info.basic,video.upload"
    verifier = tiktok._pending[q["state"]]
    assert q["code_challenge"] == hashlib.sha256(verifier.encode()).hexdigest()       # hexadécimal, pas base64url
    sent = {}

    def post(url, data=None, **kw):
        sent.update(data)
        return resp(url, {"access_token": "AT", "refresh_token": "RT", "expires_in": 86400,
                          "scope": "user.info.basic,video.upload", "open_id": "o"})
    monkeypatch.setattr(tiktok.httpx, "post", post)
    tiktok.finish_auth("CODE", q["state"], 8765)
    assert sent["code_verifier"] == verifier and sent["grant_type"] == "authorization_code"
    assert tiktok.connected() and tiktok.access_token() == "AT"
    with pytest.raises(RuntimeError, match="expirée"):
        tiktok.finish_auth("CODE", q["state"], 8765)                                    # state à usage unique


def test_missing_scope_is_refused(keys, monkeypatch):
    q = parse_qs(urlparse(tiktok.auth_url(8765)).query)
    monkeypatch.setattr(tiktok.httpx, "post", lambda url, **kw: resp(url, {"access_token": "AT", "scope": "user.info.basic"}))
    with pytest.raises(RuntimeError, match="video.upload"):
        tiktok.finish_auth("C", q["state"][0], 8765)
    assert not tiktok.connected()


def test_send_inbox_mode(keys, monkeypatch):
    tiktok.token_path().write_text(json.dumps({"access_token": "AT", "refresh_token": "R", "expires_at": 9e12}))
    bodies = []

    def post(url, json=None, headers=None, **kw):
        bodies.append(json)
        assert headers["Authorization"] == "Bearer AT"
        return resp(url, {"data": {"publish_id": "p_1"}, "error": {"code": "ok"}})
    monkeypatch.setattr(tiktok.httpx, "post", post)
    assert tiktok.send("T" * 120, "desc #anime", ["https://x/1.jpg", "https://x/2.jpg"]) == "p_1"
    b = bodies[0]
    assert b["post_mode"] == "MEDIA_UPLOAD" and b["media_type"] == "PHOTO" and len(b["post_info"]["title"]) == 90
    assert "privacy_level" not in b["post_info"] and b["source_info"]["photo_images"][1] == "https://x/2.jpg"
    monkeypatch.setattr(tiktok.httpx, "post", lambda url, **kw: resp(
        url, {"error": {"code": "url_ownership_unverified", "message": "m"}}, 403))
    with pytest.raises(RuntimeError, match="pas vérifiée"):
        tiktok.send("t", "d", ["https://x/1.jpg"])


def test_token_refresh(keys, monkeypatch):
    tiktok.token_path().write_text(json.dumps({"access_token": "OLD", "refresh_token": "R", "expires_at": 0}))
    monkeypatch.setattr(tiktok.httpx, "post", lambda url, data=None, **kw: resp(
        url, {"access_token": "NEW", "refresh_token": "R2", "expires_in": 86400}))
    assert tiktok.access_token() == "NEW"
    assert json.loads(tiktok.token_path().read_text())["refresh_token"] == "R2"


def test_github_hosting(keys, monkeypatch, tmp_path):
    keys["slides"]["publish"]["hosting"].update(kind="github", repo="me/media", branch="main",
                                                 public_base_url="https://me.github.io/media/")
    calls = []

    def handler(req: httpx.Request):
        calls.append((req.method, req.url.path, req.headers.get("authorization")))
        if req.method == "GET":
            return httpx.Response(404, json={})
        body = json.loads(req.content)
        assert body["branch"] == "main" and body["content"] and "sha" not in body
        return httpx.Response(201, json={"content": {}})
    real = httpx.Client
    monkeypatch.setattr(publish.httpx, "Client", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
    f = tmp_path / "tiktokABC.txt"
    f.write_text("tiktok-developers-site-verification=XYZ")
    assert publish.host_file(f) == "https://me.github.io/media/tiktokABC.txt"
    assert calls[-1] == ("PUT", "/repos/me/media/contents/tiktokABC.txt", "Bearer gh")

    shots = [tmp_path / "01.jpg", tmp_path / "02.jpg"]
    for p in shots:
        p.write_bytes(b"jpg")
    monkeypatch.setattr(publish.render, "slide_paths", lambda sid, fmt: shots)
    waited = []
    monkeypatch.setattr(publish, "wait_public", lambda urls: waited.extend(urls))
    urls = publish.host_images(7, "vertical")
    assert len(urls) == 2 and urls[0].startswith("https://me.github.io/media/s/7-") and urls[0].endswith("/01.jpg")
    assert waited == urls


def test_wait_public(cfg, monkeypatch):
    seen = {"n": 0}

    def handler(req):
        seen["n"] += 1
        return httpx.Response(200 if seen["n"] > 2 else 404)
    real = httpx.Client
    monkeypatch.setattr(publish.httpx, "Client", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
    publish.wait_public(["https://a/1.jpg"], timeout_s=5, every=0)
    assert seen["n"] == 3
    seen["n"] = -10**6
    with pytest.raises(RuntimeError, match="pas encore en ligne"):
        publish.wait_public(["https://a/1.jpg"], timeout_s=0, every=0)


def test_tiktok_auto_needs_connection_and_goes_early(keys):
    keys["slides"]["publish"]["tiktok"]["enabled"] = True
    keys["slides"]["publish"]["hosting"]["kind"] = "github"
    assert not publish.is_auto("tiktok")
    tiktok.token_path().write_text("{}")
    assert publish.is_auto("tiktok")
    at = datetime.now(timezone.utc) + timedelta(minutes=20)
    sid = db.insert("slideshows", anime="A", format="facts", topic="t", status="approved", publish_at=at.isoformat())
    db.insert("posts", slideshow_id=sid, platform="tiktok", mode="auto", publish_at=at.isoformat(), status="scheduled")
    db.insert("posts", slideshow_id=sid, platform="instagram", mode="auto", publish_at=at.isoformat(), status="scheduled")
    assert [p["platform"] for p in publish.due()] == ["tiktok"]           # inbox : 30 min d'avance, Instagram à l'heure


def test_tiktok_routes(keys, monkeypatch):
    from fastapi.testclient import TestClient
    from clipper.web import app as appmod
    with TestClient(appmod.app) as c:
        r = c.get("/slides-queue")
        assert r.status_code == 200 and "Connecter TikTok" in r.text
        r = c.get("/tiktok/connect", follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"].startswith("https://www.tiktok.com/v2/auth/authorize/")
        state = parse_qs(urlparse(r.headers["location"]).query)["state"][0]
        monkeypatch.setattr(tiktok.httpx, "post", lambda url, **kw: resp(url, {
            "access_token": "AT", "refresh_token": "R", "expires_in": 1, "scope": "user.info.basic,video.upload"}))
        r = c.get(f"/tiktok/callback/?code=X&state={state}", follow_redirects=False)
        assert r.status_code == 303 and tiktok.connected()
        assert c.get("/tiktok/callback/?error=access_denied").status_code == 400
