"""Tests for the triage agent."""

import sys
import unittest

sys.path.insert(0, ".")

from agents.triage import TriageAgent
from models import Alert


def _alert(**kwargs):
    base = dict(
        alert_id="ALT-TEST", account_id="user-x", amount=50.0,
        merchant="Shop", merchant_category="groceries", timestamp=1_790_000_000.0,
        channel="card_present", device_id="dev-1", ip_address="1.2.3.4",
        country="US", account_country="US", account_age_days=500,
        prior_chargebacks=0,
    )
    base.update(kwargs)
    return Alert(**base)


class TestTriageAgent(unittest.TestCase):
    def setUp(self):
        self.agent = TriageAgent()

    def test_benign_alert_is_low(self):
        priority, reasons = self.agent.triage(_alert())
        self.assertEqual(priority, "low")
        self.assertTrue(reasons)

    def test_large_wire_cross_border_is_high(self):
        alert = _alert(amount=25_000, channel="wire", country="NG")
        priority, reasons = self.agent.triage(alert)
        self.assertEqual(priority, "high")
        self.assertGreaterEqual(len(reasons), 3)

    def test_medium_band(self):
        alert = _alert(amount=2_000, channel="online")
        priority, _ = self.agent.triage(alert)
        self.assertEqual(priority, "medium")

    def test_new_account_with_chargebacks_escalates(self):
        alert = _alert(account_age_days=5, prior_chargebacks=2)
        priority, reasons = self.agent.triage(alert)
        self.assertEqual(priority, "medium")
        self.assertTrue(any("chargeback" in r for r in reasons))

    def test_high_risk_category_adds_reason(self):
        alert = _alert(merchant_category="crypto_exchange", amount=1_500)
        priority, reasons = self.agent.triage(alert)
        self.assertTrue(any("crypto_exchange" in r for r in reasons))

    def test_priority_ordering(self):
        low, _ = self.agent.triage(_alert())
        med, _ = self.agent.triage(_alert(amount=6_000))
        high, _ = self.agent.triage(_alert(amount=50_000, channel="wire"))
        order = {"low": 0, "medium": 1, "high": 2}
        self.assertLess(order[low], order[med])
        self.assertLess(order[med], order[high])


if __name__ == "__main__":
    unittest.main()
