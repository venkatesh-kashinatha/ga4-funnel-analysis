"""Command line: python -m funnel [--data PATH] [--out DIR]"""

import argparse
import json
from pathlib import Path

from .analysis import add_rates, check, compare, load, step_dropoff

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    p = argparse.ArgumentParser(prog="funnel", description="GA4 purchase funnel analysis")
    p.add_argument("--data", type=Path, default=ROOT / "data" / "ga4_funnel_results.csv")
    p.add_argument("--out", type=Path, default=ROOT / "outputs")
    a = p.parse_args()

    df = load(a.data)
    checks = check(df)
    a.out.mkdir(parents=True, exist_ok=True)
    checks.to_csv(a.out / "quality_checks.csv", index=False)
    print(checks.to_string(index=False))
    if checks["failing"].sum():
        raise SystemExit("Checks failed")

    rates = add_rates(df)
    rates.round(4).to_csv(a.out / "funnel_rates.csv", index=False)
    drop = step_dropoff(df[df["segment_type"] == "All users"].iloc[0])
    drop.round(4).to_csv(a.out / "dropoff_all_users.csv", index=False)

    tests = [
        compare(df, "User type", "Returning", "New", "purchased", "viewed_item"),
        compare(df, "User type", "Returning", "New", "added_to_cart", "viewed_item"),
        compare(df, "Device", "mobile", "desktop", "purchased", "viewed_item"),
        compare(df, "Medium", "referral", "organic", "purchased", "viewed_item"),
    ]
    (a.out / "tests.json").write_text(json.dumps(tests, indent=2))

    print("\nDrop-off, all users:")
    print(drop.round(3).to_string(index=False))
    print("\nSegment tests (view -> purchase unless noted):")
    for t in tests:
        print(f"  {t['segment_type']}: {t['a']} {t['p1']:.2%} vs {t['b']} {t['p2']:.2%} "
              f"({t['metric']}, {t['ratio']:.2f}x, p = {t['p_value']:.2g})")


if __name__ == "__main__":
    main()
