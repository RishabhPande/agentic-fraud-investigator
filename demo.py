"""End-to-end demo: generate a synthetic fraud case per scenario and run the
full multi-agent investigation pipeline, printing each analyst report.

Usage:
    python demo.py [scenario] [seed]
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".")

from agents.orchestrator import Orchestrator
from data.generator import SCENARIOS, generate_case
from llm.client import get_llm


def run(scenario: str, seed: int = 42) -> None:
    alert, stores = generate_case(scenario, seed=seed)
    orchestrator = Orchestrator(
        transactions=stores[0],
        devices=stores[1],
        graph=stores[2],
        llm=get_llm(),
    )
    case = orchestrator.investigate(alert)
    print(f"\n{'#' * 70}")
    print(f"# scenario: {scenario}")
    print(f"{'#' * 70}\n")
    print(case.summary)
    print()


def main() -> None:
    args = sys.argv[1:]
    seed = int(args[1]) if len(args) > 1 else 42
    if args and args[0] != "all":
        scenarios = [args[0]]
    else:
        scenarios = list(SCENARIOS)
    for scenario in scenarios:
        run(scenario, seed=seed)


if __name__ == "__main__":
    main()
