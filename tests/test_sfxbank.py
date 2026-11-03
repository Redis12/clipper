"""Banque de sons library/_sfx : rôles par nom, découpe en prises, mode « safe » sans sons d'anime."""

import numpy as np

from clipper.slides import fusion, library, sfxbank


def _wav(path, bursts):
    x = np.zeros(int(44100 * (0.6 * len(bursts) + 0.5)), dtype=np.float32)
    for i, f in enumerate(bursts):
        t = np.arange(int(0.2 * 44100)) / 44100
        x[int(i * 0.6 * 44100):int(i * 0.6 * 44100) + len(t)] = 0.8 * np.sin(2 * np.pi * f * t)
    path.parent.mkdir(parents=True, exist_ok=True)
    fusion.write_wav(path, x)


def test_classify_split_and_modes(cfg):
    assert sfxbank.classify("FGHTImpt_Anime Melee 3") == "punch"
    assert sfxbank.classify("Voicy_kamehameha charge") == "charge"
    assert sfxbank.classify("Dragon Ball Xenoverse - Kamehameha Regular Sound Effect") == "beam"
    assert sfxbank.classify("EXPLDsgn_Anime Explosion 4") == "explosion"
    root = library.root() / "_sfx"
    _wav(root / "Free Pack" / "Anime Melee 1.wav", [200, 300, 400])          # 3 coups dans un fichier
    _wav(root / "Dragon Ball SFX" / "DBZ Strong Punch.wav", [150])
    _wav(root / "Free Pack" / "Anime Explosion 1.wav", [80])
    b = sfxbank.bank()
    assert len(b["punch"]) == 4 and sum(1 for i in b["punch"] if i[1]) == 1
    assert sfxbank.pick("punch", "anime") is not None
    for s in range(10):                                                      # safe : jamais le son officiel
        x = sfxbank.pick("punch", "safe", s)
        assert x is not None and len(x) < 0.5 * 44100
    assert sfxbank.credits() == ["Free Pack"]
    assert sfxbank.sound("ko", "safe") is not None and sfxbank.sound("summon") is None
