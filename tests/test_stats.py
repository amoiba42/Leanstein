import numpy as np
import pytest
from scipy import stats as st

from prl.analysis import stats as S


def test_signflip_exact_small():
    x = np.array([1, 1, 1, 0, 0])
    y = np.array([0, 0, 0, 0, 0])
    obs, p = S.signflip_test(x, y)
    assert obs == pytest.approx(0.6)
    assert p == pytest.approx(1 / 8)  # 3 non-zero diffs, only all-positive reaches obs


def test_signflip_null_and_symmetry():
    x = np.zeros(10)
    assert S.signflip_test(x, x)[1] == 1.0
    rng = np.random.default_rng(0)
    a = rng.random(40)
    b = a + 0.3
    assert S.signflip_test(b, a)[1] < 0.001
    assert S.signflip_test(a, b)[1] > 0.99


def test_holm():
    assert S.holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])


def test_mcnemar_matches_scipy():
    r = S.mcnemar_exact(9, 2)
    assert r["p_two_sided"] == pytest.approx(st.binomtest(9, 11, 0.5).pvalue)
    assert S.mcnemar_exact(0, 0)["p_two_sided"] == 1.0


def test_bootstrap_deterministic_and_covers():
    x = np.array([1, 1, 0, 1, 0, 1, 1, 0] * 5, float)
    y = np.array([0, 1, 0, 0, 0, 1, 0, 0] * 5, float)
    a = S.cluster_bootstrap_diff(x, y, B=2000, seed=1)
    b = S.cluster_bootstrap_diff(x, y, B=2000, seed=1)
    assert a == b and a[1] <= a[0] <= a[2]


def test_cohens_h_and_min_detectable():
    assert S.cohens_h(0.5, 0.5) == 0
    assert S.cohens_h(0.6, 0.4) > 0
    assert S.min_detectable(5) == 5  # 5/5 gives p=1/32 < .05, 4/5 gives .1875
    assert S.min_detectable(2) is None


def test_paired_compare_counts():
    x = np.array([1, 1, 0, 2 / 3, 0])
    y = np.array([0, 1, 0, 1 / 3, 1])
    r = S.paired_compare(x, y, B=500, n_perm=1000, seed=3, alpha=0.05)
    assert (r.only_x, r.only_y, r.both, r.neither) == (2, 1, 1, 1)
