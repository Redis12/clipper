from clipper import stats


def test_jail_buckets():
    assert stats.jail(5)[0] == "0 vue"
    assert stats.jail(1200)[0] == "1k"
    assert stats.jail(9000)[0] == "10k"
    assert stats.jail(40000)[0] == "30k"


def test_leak_zones():
    curve = [(i / 20, 1.0 - (0.5 if i >= 11 else 0) - i * 0.01) for i in range(21)]
    lk = stats.leak(curve, 40)
    assert lk["zone"] == "MILIEU" and 20 <= lk["second"] <= 22
    curve = [(0.0, 1.0), (0.05, 0.4), (0.5, 0.35), (1.0, 0.3)]
    assert stats.leak(curve, 60)["zone"] == "OUVERTURE"
    assert stats.leak([], 60) is None


def test_dur():
    assert stats._dur("PT1M5S") == 65 and stats._dur("PT45S") == 45
