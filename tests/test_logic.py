from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from clipper import bounds, db, quota, schedule, selection, titles
from clipper.transcript import render, sentences
from conftest import fake_words

BXL = ZoneInfo("Europe/Brussels")


# --- transcript ---------------------------------------------------------------

def test_sentences_split_on_punctuation_and_speaker():
    s = sentences(fake_words(n_sentences=50, spk_every=10))
    assert len(s) == 50
    assert all(x.text.endswith(".") for x in s)
    assert s[9].spk != s[10].spk
    assert "[s0 0:00.0 S0]" in render(s)


def test_sentences_without_punctuation_split_on_gap():
    words = [{"w": "a", "s": i * 0.3, "e": i * 0.3 + 0.2, "spk": 0} for i in range(10)]
    words += [{"w": "b", "s": 10 + i * 0.3, "e": 10 + i * 0.3 + 0.2, "spk": 0} for i in range(10)]
    assert len(sentences(words)) == 2


# --- bornes -------------------------------------------------------------------

def test_bounds_margin_does_not_bite_neighbour_words():
    words = fake_words()
    s = sentences(words)
    b = bounds.compute(s, words, 10, 40, 1000)
    assert b.reject is None
    # silence de 0,4 s entre phrases : la marge est plafonnée au milieu (0,2 s), pas 0,3 s
    prev_end = words[s[10].w0 - 1]["e"]
    assert prev_end < b.start <= s[10].start
    assert abs((s[10].start - b.start) - (s[10].start - prev_end) / 2) < 1e-6
    assert s[40].end <= b.end < words[s[40].w1 + 1]["s"]


def test_bounds_reject_explains():
    words = fake_words()
    s = sentences(words)
    assert "Trop court" in bounds.compute(s, words, 0, 3, 1000).reject
    assert "Trop long" in bounds.compute(s, words, 0, 110, 1000).reject


def test_overlap_ratio():
    assert bounds.overlap_ratio((0, 100), (100, 200)) == 0
    assert bounds.overlap_ratio((0, 100), (80, 300)) == pytest.approx(0.2)
    assert bounds.overlap_ratio((0, 300), (100, 200)) == 1


# --- sélection ----------------------------------------------------------------

def test_merge_keeps_best_and_limits_overlap():
    C = selection.Candidate
    cands = [C(0, 0, "a", 90, "", 0, 200), C(0, 0, "b", 80, "", 170, 400),   # 30 s / 200 s = 15 % → gardé
             C(0, 0, "c", 85, "", 50, 250), C(0, 0, "d", 70, "", 500, 700)]   # recouvre a à 75 % → écarté
    kept = selection.merge(cands, 0.2, 10)
    assert [k.topic for k in kept] == ["a", "b", "d"]
    assert len(selection.merge(cands, 0.2, 2)) == 2


def test_plan_chunks_overlap_covers_max_clip():
    s = sentences(fake_words(n_sentences=1500))   # ~1 h 50
    chunks = selection.plan_chunks(s, 1000, 25 * 60, 6 * 60)
    assert len(chunks) > 3
    assert chunks[0][0] == 0 and chunks[-1][1] == len(s) - 1
    for (a0, a1), (b0, b1) in zip(chunks, chunks[1:]):
        assert s[a1].end - s[b0].start >= 5 * 60 - 10   # recouvrement ≥ durée max d'un clip
    assert selection.plan_chunks(s, 10**9, 1500, 360) == [(0, len(s) - 1)]


def test_select_end_to_end_with_mocked_claude(video_in_db, monkeypatch):
    calls = []

    def fake(**kw):
        calls.append(kw)
        return {"clips": [
            {"first_sentence": 0, "last_sentence": 40, "topic": "Intro", "score": 70, "reason": "r"},       # ok ~3 min
            {"first_sentence": 20, "last_sentence": 60, "topic": "Doublon", "score": 60, "reason": "r"},    # chevauche trop
            {"first_sentence": 80, "last_sentence": 85, "topic": "Court", "score": 90, "reason": "r"},      # trop court
            {"first_sentence": 70, "last_sentence": 110, "topic": "Deux", "score": 88, "reason": "r"},      # ok
            {"first_sentence": 500, "last_sentence": 510, "topic": "Hors", "score": 99, "reason": "r"},     # index inventé
        ]}

    monkeypatch.setattr("clipper.llm.structured", fake)
    n = selection.select(video_in_db)
    assert n == 2 and len(calls) == 1
    assert "[s0 " in calls[0]["user"]
    rows = db.clips_for(video_in_db)
    assert {r["topic"]: r["status"] for r in rows} == {"Intro": "pending", "Deux": "pending", "Court": "rejected_auto"}
    assert db.get_clip([r for r in rows if r["topic"] == "Deux"][0]["id"])["rank"] == 1
    # Idempotent : pas de second appel
    selection.select(video_in_db)
    assert len(calls) == 1


# --- titres -------------------------------------------------------------------

def test_titles_helpers():
    assert titles.shorten("Pourquoi les impôts augmentent chaque année en Belgique et ailleurs", 60) == \
        "Pourquoi les impôts augmentent chaque année en Belgique et"
    assert titles.clean(' « Titre <b> » ') == "Titre b"
    tags = titles.fit_tags(["#Économie", "économie", "impôts", ""] + [f"t{i}" for i in range(20)], 10)
    assert tags[:2] == ["économie", "impôts"] and len(tags) == 10
    d = titles.build_description("Corps.", {"id": "abcdefghijk", "title": "Source"}, 754.2)
    assert "https://youtu.be/abcdefghijk?t=754" in d and "12:34" in d
    d2 = titles.refresh_link(d, {"id": "abcdefghijk"}, 3725)
    assert "?t=3725" in d2 and "1:02:05" in d2
    errs = titles.problems({"titles": ["x" * 61, "a", "b"], "tags": ["t"] * 9, "thumbnail_text": "deux mots"}, 3, 60, 10)
    assert len(errs) == 3


def test_titles_generate_retries_then_enforces(video_in_db, monkeypatch):
    cid = db.insert_clip(video_in_db, start=10.0, end=190.0, topic="Sujet", score=80, reason="r", status="pending")
    answers = [
        {"titles": ["T" * 70, "Deux", "Trois"], "description": "D", "tags": ["a"] * 3, "thumbnail_text": "un"},
        {"titles": ["Un titre correct", "Un autre angle", "Long " * 20], "description": "Ce qu'on apprend.",
         "tags": [f"tag{i}" for i in range(10)], "thumbnail_text": "Trois mots ici"},
    ]
    seen = []
    monkeypatch.setattr("clipper.llm.structured", lambda **kw: (seen.append(kw), answers[len(seen) - 1])[1])
    titles.generate(cid)
    c = db.get_clip(cid)
    assert len(seen) == 2 and "corrige" in seen[1]["user"]
    assert all(len(t) <= 60 for t in c["titles"]) and len(c["titles"]) == 3
    assert len(c["tags"]) == 10 and c["thumb_text"] == "Trois mots ici"
    assert "youtu.be/abcdefghijk?t=10" in c["description"]


# --- planification ------------------------------------------------------------

def test_slots_and_approve(video_in_db, cfg):
    cfg["publish"]["slots"] = ["18:00", "09:30"]
    cfg["publish"]["days"] = ["mon", "wed"]
    now = datetime(2026, 10, 27, 12, 0, tzinfo=BXL)   # mardi
    got = [s for _, s in zip(range(4), schedule.slots(now))]
    assert [(g.strftime("%a %H:%M")) for g in got] == ["Wed 09:30", "Wed 18:00", "Mon 09:30", "Mon 18:00"]
    # Changement d'heure (25/10/2026) : 18:00 Bruxelles reste 18:00 locale
    assert got[2].utcoffset() == timedelta(hours=1)

    a = db.insert_clip(video_in_db, start=0.0, end=150.0, topic="a", score=1, reason="", status="review")
    b = db.insert_clip(video_in_db, start=200.0, end=350.0, topic="b", score=1, reason="", status="review")
    pa, pb = schedule.approve(a), schedule.approve(b)
    assert pa != pb and pa < pb
    assert schedule.approve(a) == pa            # idempotent
    schedule.unapprove(a)
    assert db.get_clip(a)["publish_at"] is None
    assert schedule.approve(a) == pa            # le créneau libéré est repris


def test_reschedule_overdue(video_in_db):
    a = db.insert_clip(video_in_db, start=0.0, end=150.0, topic="a", score=1, reason="", status="approved",
                       publish_at=(datetime.now(timezone.utc) - timedelta(hours=5)).replace(microsecond=0).isoformat())
    assert schedule.reschedule_overdue() == [a]
    assert schedule.parse(db.get_clip(a)["publish_at"]) > datetime.now(timezone.utc)


# --- quota --------------------------------------------------------------------

def test_quota_current_costs(cfg):
    # 100 uploads/jour dans leur seau ; miniature + playlist = 100 unités sur 10 000 → plafond perso (6) décisif
    assert quota.clips_left_today() == 6
    cfg["publish"]["max_uploads_per_day"] = 1000
    assert quota.clips_left_today() == 100
    for _ in range(99):
        quota.record("thumbnails.set")
    assert quota.remaining("default") == 10000 - 99 * 50
    assert quota.clips_left_today() == 50   # 5050 // 100


def test_quota_legacy_costs_give_five(cfg):
    # Si YouTube revenait à 1 600 unités par upload dans le seau commun : 5 clips complets, pas 6.
    cfg["quota"]["costs"]["videos.insert"] = ["default", 1600]
    cfg["publish"]["max_uploads_per_day"] = 1000
    assert quota.clips_left_today() == 5


def test_quota_block(cfg):
    quota.block("uploads")
    assert quota.remaining("uploads") == 0
    assert "épuisé" in quota.affordable(["videos.insert"])
    assert quota.clips_left_today() == 0


def test_stale_lock_from_dead_process_is_cleared(tmp_path):
    from clipper.util import file_lock
    lock = tmp_path / ".lock"
    lock.write_text("999999")                       # processus inexistant (serveur coupé par Ctrl+C)
    with file_lock(lock) as got:
        assert got
    import os
    lock.write_text(str(os.getppid()))              # processus vivant : on respecte le verrou
    with file_lock(lock) as got:
        assert not got
    lock.unlink()
