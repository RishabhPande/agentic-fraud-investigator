"""Tests for the data generator and the end-to-end orchestrator."""

import sys
import unittest

sys.path.insert(0, ".")

from agents.orchestrator import Orchestrator
from data.generator import SCENARIOS, generate_case
from llm.client import MockLLM
from models import Case


class TestGenerator(unittest.TestCase):
    def test_all_scenarios_generate(self):
        for scenario in SCENARIOS:
            alert, stores = generate_case(scenario, seed=7)
            self.assertTrue(alert.alert_id)
            self.assertGreater(alert.amount, 0)
            self.assertEqual(len(stores), 3)

    def test_deterministic(self):
        a1, _ = generate_case("mule_network", seed=123)
        a2, _ = generate_case("mule_network", seed=123)
        self.assertEqual(a1.alert_id, a2.alert_id)
        self.assertEqual(a1.amount, a2.amount)

    def test_unknown_scenario_raises(self):
        with self.assertRaises(ValueError):
            generate_case("not_a_scenario")

    def test_mule_network_has_shared_device(self):
        alert, (txns, devices, graph) = generate_case("mule_network", seed=1)
        self.assertGreaterEqual(len(devices.accounts_for(alert.device_id)) - 1, 4)

    def test_legit_is_low_risk_shape(self):
        alert, _ = generate_case("legit", seed=1)
        self.assertEqual(alert.country, alert.account_country)
        self.assertLess(alert.amount, 200)


def _investigate(scenario, seed=42):
    alert, stores = generate_case(scenario, seed=seed)
    orchestrator = Orchestrator(
        transactions=stores[0], devices=stores[1], graph=stores[2],
        llm=MockLLM(),
    )
    return orchestrator.investigate(alert)


class TestOrchestrator(unittest.TestCase):
    def test_returns_populated_case(self):
        case = _investigate("account_takeover")
        self.assertIsInstance(case, Case)
        self.assertIn(case.priority, ("low", "medium", "high"))
        self.assertTrue(case.triage_reasons)
        self.assertTrue(case.evidence)
        self.assertIn(case.verdict, ("approve", "review", "block"))
        self.assertTrue(case.summary)
        self.assertGreaterEqual(case.risk_score, 0.0)
        self.assertLessEqual(case.risk_score, 1.0)

    def test_mule_network_blocked(self):
        case = _investigate("mule_network")
        self.assertEqual(case.verdict, "block")
        self.assertEqual(case.priority, "high")

    def test_account_takeover_blocked_or_review(self):
        case = _investigate("account_takeover")
        self.assertIn(case.verdict, ("block", "review"))
        self.assertGreaterEqual(case.risk_score, 0.45)

    def test_synthetic_identity_reviewed(self):
        case = _investigate("synthetic_identity")
        self.assertIn(case.verdict, ("review", "block"))

    def test_legit_approved(self):
        case = _investigate("legit")
        self.assertEqual(case.verdict, "approve")
        self.assertEqual(case.priority, "low")

    def test_summary_matches_case(self):
        case = _investigate("mule_network")
        self.assertIn(case.alert.alert_id, case.summary)
        self.assertIn(case.verdict.upper(), case.summary)

    def test_pipeline_is_deterministic(self):
        c1 = _investigate("account_takeover", seed=99)
        c2 = _investigate("account_takeover", seed=99)
        self.assertEqual(c1.risk_score, c2.risk_score)
        self.assertEqual(c1.summary, c2.summary)


if __name__ == "__main__":
    unittest.main()
