import math
from pathlib import Path

import pandas as pd
import pytest

from funnel.analysis import add_rates, check, compare, load, step_dropoff, two_proportion

DATA = Path(__file__).resolve().parent.parent / "data" / "ga4_funnel_results.csv"


def _toy():
    return pd.DataFrame([
        ("All users", "All", 1000, 200, 80, 40),
        ("Device", "desktop", 600, 120, 50, 25),
        ("Device", "mobile", 400, 80, 30, 15),
    ], columns=["segment_type", "segment", "viewed_item", "added_to_cart", "began_checkout", "purchased"])


def test_checks_pass_on_consistent_data():
    assert check(_toy())["failing"].sum() == 0


def test_checks_catch_segments_not_summing():
    bad = _toy()
    bad.loc[1, "purchased"] = 30
    assert check(bad)["failing"].sum() > 0


def test_checks_catch_increasing_step():
    bad = _toy()
    bad.loc[2, "began_checkout"] = 90
    assert check(bad)["failing"].sum() > 0


def test_rates():
    r = add_rates(_toy()).iloc[0]
    assert r["view_to_cart"] == pytest.approx(0.2)
    assert r["cart_to_checkout"] == pytest.approx(0.4)
    assert r["checkout_to_purchase"] == pytest.approx(0.5)
    assert r["view_to_purchase"] == pytest.approx(0.04)


def test_dropoff_shares_sum_to_one():
    d = step_dropoff(_toy().iloc[0])
    assert d["lost"].sum() == 960
    assert d["share_of_all_lost"].sum() == pytest.approx(1.0)


def test_two_proportion_hand_calc():
    r = two_proportion(812, 9118, 2044, 52134)
    p = (812 + 2044) / (9118 + 52134)
    z = (812 / 9118 - 2044 / 52134) / math.sqrt(p * (1 - p) * (1 / 9118 + 1 / 52134))
    assert r["z"] == pytest.approx(z)
    assert r["p_value"] < 1e-10


def test_compare_on_real_output():
    df = load(DATA)
    assert check(df)["failing"].sum() == 0
    res = compare(df, "User type", "Returning", "New", "purchased", "viewed_item")
    assert res["ratio"] > 2


def test_missing_columns(tmp_path):
    p = tmp_path / "x.csv"
    pd.DataFrame({"segment": ["a"]}).to_csv(p, index=False)
    with pytest.raises(ValueError):
        load(p)
