"""Plot what drove the risk score in each synthetic scenario.

Runs the offline pipeline (mock LLM, seed 42) on all four scenarios and
draws the score, verdict and per-signal contributions. No network, no API
calls. Needs matplotlib (optional): pip install matplotlib

    python examples/plot_scenarios.py     # writes docs/scenarios.png

All cases are synthetic, from data/generator.py.
"""

import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from agents.orchestrator import Orchestrator
from data.generator import SCENARIOS, generate_case
from llm.client import MockLLM

PALETTE = ["#2e86ab", "#e4572e", "#59a14f", "#f2a541", "#7b6d8d", "#76b7b2"]
GREY = "#555555"


def main():
    cases = []
    for name in SCENARIOS:
        alert, (tx, dev, graph) = generate_case(name, seed=42)
        case = Orchestrator(transactions=tx, devices=dev, graph=graph,
                            llm=MockLLM()).investigate(alert)
        cases.append((name, case))

    signals = []
    for _, c in cases:
        for k in c.contributions:
            if k not in signals:
                signals.append(k)
    color = {s: PALETTE[i % len(PALETTE)] for i, s in enumerate(signals)}

    plt.rcParams.update({"font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False})
    fig, ax = plt.subplots(figsize=(10, 4.6))
    for i, (name, c) in enumerate(cases):
        left = 0.0
        for s in signals:
            share = c.contributions.get(s, 0.0) * c.risk_score
            if share > 0:
                ax.barh(i, share, left=left, color=color[s], height=0.55,
                        label=s)
                left += share
        ax.text(left + 0.015, i, f"{c.risk_score:.2f}  {c.verdict.upper()}",
                va="center", fontsize=10, fontweight="bold", color=GREY)
    ax.set_yticks(range(len(cases)))
    ax.set_yticklabels([n for n, _ in cases])
    ax.invert_yaxis()
    ax.set_xlim(0, 1.15)
    ax.set_xlabel("risk score (0 to 1), split by evidence signal")
    ax.grid(axis="x", alpha=0.25)
    h, l = ax.get_legend_handles_labels()
    seen = dict(zip(l, h))
    ax.legend(seen.values(), seen.keys(), loc="lower right", frameon=False,
              ncol=2, fontsize=9)
    ax.set_title("What drove each verdict (offline run, seed 42)", loc="left")
    fig.text(0.01, 0.01, "Synthetic cases from data/generator.py. Mock LLM, "
             "no API calls. Reproduce: python examples/plot_scenarios.py",
             fontsize=8, color=GREY)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    out = os.path.join(ROOT, "docs", "scenarios.png")
    fig.savefig(out, dpi=150)
    for n, c in cases:
        print(n, round(c.risk_score, 3), c.verdict,
              {k: round(v, 2) for k, v in c.contributions.items()})


if __name__ == "__main__":
    main()
