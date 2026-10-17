"""Tests for the risk scorer."""

import sys
import unittest

sys.path.insert(0, ".")

from agents.risk_scorer import RiskScorer
from models import EvidenceItem


def _ev(name, signal):
    return EvidenceItem(name=name, value="test", signal=signal, detail="test")


class TestRiskScorer(unittest.TestCase):
    def setUp(self):
        self.scorer = RiskScorer()

    def test_all_benign_scores_low(self):
        evidence = [_ev(n, 0.05) for n in
                    ("velocity", "device_sharing", "geo_velocity")]
        score, _ = self.scorer.score(evidence)
        self.assertLess(score, 0.2)
        self.assertEqual(self.scorer.verdict(score), "approve")

    def test_all_suspicious_scores_high(self):
        evidence = [_ev(n, 1.0) for n in
                    ("velocity", "device_sharing", "geo_velocity",
                     "ring_expansion", "amount_vs_average", "new_device")]
        score, _ = self.scorer.score(evidence)
        self.assertGreater(score, 0.9)
        self.assertEqual(self.scorer.verdict(score), "block")

    def test_mixed_signals_land_in_review(self):
        evidence = [
            _ev("velocity", 0.7),
            _ev("device_sharing", 0.4),
            _ev("geo_velocity", 0.5),
            _ev("ring_expansion", 0.45),
            _ev("amount_vs_average", 0.5),
            _ev("new_device", 0.6),
        ]
        score, _ = self.scorer.score(evidence)
        self.assertGreaterEqual(score, RiskScorer.REVIEW_THRESHOLD)
        self.assertLess(score, RiskScorer.BLOCK_THRESHOLD)
        self.assertEqual(self.scorer.verdict(score), "review")

    def test_contributions_sum_to_one(self):
        evidence = [_ev("velocity", 0.7), _ev("new_device", 0.3)]
        _, contributions = self.scorer.score(evidence)
        self.assertAlmostEqual(sum(contributions.values()), 1.0, places=6)

    def test_stronger_signal_dominates_contribution(self):
        evidence = [_ev("velocity", 1.0), _ev("new_device", 0.1)]
        _, contributions = self.scorer.score(evidence)
        self.assertGreater(contributions["velocity"], contributions["new_device"])

    def test_score_bounded(self):
        evidence = [_ev("velocity", 0.62)]
        score, _ = self.scorer.score(evidence)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_empty_evidence_scores_zero(self):
        score, contributions = self.scorer.score([])
        self.assertEqual(score, 0.0)
        self.assertEqual(contributions, {})

    def test_verdict_thresholds(self):
        self.assertEqual(self.scorer.verdict(0.95), "block")
        self.assertEqual(self.scorer.verdict(0.80), "block")
        self.assertEqual(self.scorer.verdict(0.60), "review")
        self.assertEqual(self.scorer.verdict(0.45), "review")
        self.assertEqual(self.scorer.verdict(0.10), "approve")


if __name__ == "__main__":
    unittest.main()
