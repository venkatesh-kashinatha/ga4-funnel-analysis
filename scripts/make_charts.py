"""Build the README charts in docs/.

    python scripts/make_charts.py
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from funnel.analysis import STEP_LABELS, STEPS, add_rates, load  # noqa: E402

DOCS = ROOT / "docs"
BLUE, AMBER, RED, GREEN, GREY, INK = "#1F5FA8", "#E0A100", "#C0392B", "#2E7D5B", "#9AA5B1", "#1F2933"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titleweight": "bold", "axes.titlesize": 12, "figure.dpi": 130})


def funnel_chart(df):
    row = df[df["segment_type"] == "All users"].iloc[0]
    vals = [row[s] for s in STEPS]
    fig, ax = plt.subplots(figsize=(9, 4.2))
    bars = ax.barh(STEP_LABELS[::-1], vals[::-1], color=[GREEN, AMBER, AMBER, BLUE])
    for i, v in enumerate(vals[::-1]):
        ax.text(v + 600, i, f"{v:,} ({v / vals[0]:.1%})", va="center")
    for i in range(1, 4):
        drop = 1 - vals[i] / vals[i - 1]
        ax.text(vals[0] * 0.62, 3 - i + 0.5, f"-{drop:.0%}", color=RED if i == 1 else INK,
                fontweight="bold" if i == 1 else "normal", va="center")
    ax.set_xlim(0, vals[0] * 1.25)
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{x/1000:.0f}K"))
    ax.set_title("GA4 purchase funnel, Nov 2020 - Jan 2021 (users)")
    fig.tight_layout()
    fig.savefig(DOCS / "funnel.png")
    plt.close(fig)


def segment_chart(rates):
    parts = [("User type", ["New", "Returning"]), ("Device", ["desktop", "mobile", "tablet"]),
             ("Medium", ["organic", "(none)", "referral", "cpc", "<Other>"])]
    labels, vals, cols = [], [], []
    palette = {"User type": GREEN, "Device": BLUE, "Medium": AMBER}
    for seg_type, segs in parts:
        s = rates[rates["segment_type"] == seg_type].set_index("segment")
        for seg in segs:
            labels.append(f"{seg_type}: {seg}")
            vals.append(s.loc[seg, "view_to_purchase"] * 100)
            cols.append(palette[seg_type])
    overall = rates[rates["segment_type"] == "All users"]["view_to_purchase"].iloc[0] * 100
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(labels[::-1], vals[::-1], color=cols[::-1])
    for i, v in enumerate(vals[::-1]):
        ax.text(v + 0.1, i, f"{v:.1f}%", va="center", fontsize=9)
    ax.axvline(overall, color=INK, ls="--", lw=0.9)
    ax.text(overall + 0.1, len(labels) - 0.4, f"all users {overall:.1f}%", fontsize=8.5)
    ax.xaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax.set_title("View-to-purchase conversion by segment")
    fig.tight_layout()
    fig.savefig(DOCS / "conversion_by_segment.png")
    plt.close(fig)


def step_rates_new_vs_returning(rates):
    s = rates[rates["segment_type"] == "User type"].set_index("segment")
    metrics = ["view_to_cart", "cart_to_checkout", "checkout_to_purchase"]
    names = ["View -> cart", "Cart -> checkout", "Checkout -> purchase"]
    fig, ax = plt.subplots(figsize=(8.5, 4))
    x = range(3)
    for j, (seg, col) in enumerate([("New", BLUE), ("Returning", GREEN)]):
        v = [s.loc[seg, m] * 100 for m in metrics]
        ax.bar([i + (j - 0.5) * 0.38 for i in x], v, 0.38, color=col, label=seg)
        for i, vv in enumerate(v):
            ax.text(i + (j - 0.5) * 0.38, vv + 1, f"{vv:.0f}%", ha="center", fontsize=9)
    ax.set_xticks(list(x), names)
    ax.set_ylim(0, 75)
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
    ax.set_title("Step conversion: returning users convert better at every step")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(DOCS / "new_vs_returning_steps.png")
    plt.close(fig)


def main():
    DOCS.mkdir(exist_ok=True)
    df = load(ROOT / "data" / "ga4_funnel_results.csv")
    rates = add_rates(df)
    funnel_chart(df)
    segment_chart(rates)
    step_rates_new_vs_returning(rates)
    print("Charts saved to", DOCS)


if __name__ == "__main__":
    main()
