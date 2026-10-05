"""Funnel metrics and significance tests on the BigQuery funnel output."""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
from scipy import stats

STEPS = ["viewed_item", "added_to_cart", "began_checkout", "purchased"]
STEP_LABELS = ["Product view", "Add to cart", "Checkout", "Purchase"]


def load(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = set(STEPS + ["segment_type", "segment"]) - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    return df


def check(df: pd.DataFrame) -> pd.DataFrame:
    """Each step must be <= the previous one, and segments must add up to the total."""
    total = df[df["segment_type"] == "All users"].iloc[0]
    rows = [("Steps not decreasing", int((df[STEPS].diff(axis=1).iloc[:, 1:] > 0).any(axis=1).sum()))]
    for seg_type in df["segment_type"].unique():
        if seg_type == "All users":
            continue
        sub = df[df["segment_type"] == seg_type]
        rows.append((f"{seg_type} segments do not sum to total",
                     int(sum(sub[s].sum() != total[s] for s in STEPS))))
    return pd.DataFrame(rows, columns=["check", "failing"])


def add_rates(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["view_to_cart"] = out["added_to_cart"] / out["viewed_item"]
    out["cart_to_checkout"] = out["began_checkout"] / out["added_to_cart"]
    out["checkout_to_purchase"] = out["purchased"] / out["began_checkout"]
    out["view_to_purchase"] = out["purchased"] / out["viewed_item"]
    return out


def step_dropoff(row: pd.Series) -> pd.DataFrame:
    """Users lost at each step for one segment row."""
    vals = [int(row[s]) for s in STEPS]
    recs = []
    for i in range(1, len(STEPS)):
        lost = vals[i - 1] - vals[i]
        recs.append({"step": f"{STEP_LABELS[i-1]} -> {STEP_LABELS[i]}", "entered": vals[i - 1],
                     "continued": vals[i], "lost": lost, "drop_off_rate": lost / vals[i - 1],
                     "share_of_all_lost": lost / (vals[0] - vals[-1])})
    return pd.DataFrame(recs)


def two_proportion(x1: int, n1: int, x2: int, n2: int) -> dict:
    p1, p2 = x1 / n1, x2 / n2
    pooled = (x1 + x2) / (n1 + n2)
    z = (p1 - p2) / math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    return {"p1": p1, "p2": p2, "ratio": p1 / p2, "z": z, "p_value": float(2 * stats.norm.sf(abs(z)))}


def compare(df: pd.DataFrame, seg_type: str, a: str, b: str, num: str, den: str) -> dict:
    s = df[df["segment_type"] == seg_type].set_index("segment")
    res = two_proportion(int(s.loc[a, num]), int(s.loc[a, den]), int(s.loc[b, num]), int(s.loc[b, den]))
    res.update(segment_type=seg_type, a=a, b=b, metric=f"{num}/{den}")
    return res
