"""Tests for the evidence agent and its in-memory stores."""

import sys
import unittest

sys.path.insert(0, ".")

from agents.evidence import DeviceStore, EvidenceAgent, GraphStore, TransactionStore
from models import Alert

NOW = 1_790_000_000.0


def _alert(**kwargs):
    base = dict(
        alert_id="ALT-TEST", account_id="user-x", amount=500.0,
        merchant="Shop", merchant_category="groceries", timestamp=NOW,
        channel="online", device_id="dev-x", ip_address="9.9.9.9",
        country="US", account_country="US", account_age_days=500,
        prior_chargebacks=0,
    )
    base.update(kwargs)
    return Alert(**base)


def _stores():
    return TransactionStore(), DeviceStore(), GraphStore()


class TestStores(unittest.TestCase):
    def test_transaction_store_roundtrip(self):
        txns, _, _ = _stores()
        txns.add("user-x", {"amount": 10.0})
        self.assertEqual(len(txns.history("user-x")), 1)
        self.assertEqual(txns.history("unknown"), [])

    def test_device_store_tracks_accounts(self):
        _, devices, _ = _stores()
        devices.add("dev-1", "user-a")
        devices.add("dev-1", "user-b")
        self.assertEqual(devices.accounts_for("dev-1"), {"user-a", "user-b"})

    def test_graph_two_hop_expansion(self):
        _, _, graph = _stores()
        graph.add_edge("acct:a", "dev:1")
        graph.add_edge("acct:b", "dev:1")
        graph.add_edge("acct:c", "dev:2")
        graph.add_edge("acct:b", "dev:2")
        ring = graph.accounts_within("acct:a", depth=2)
        self.assertIn("acct:b", ring)
        self.assertNotIn("acct:a", ring)
        # acct:c is 4 hops away (a -> dev:1 -> b -> dev:2 -> c)
        self.assertNotIn("acct:c", ring)
        self.assertIn("acct:c", graph.accounts_within("acct:a", depth=4))


class TestEvidenceAgent(unittest.TestCase):
    def _agent_with_burst(self):
        txns, devices, graph = _stores()
        for i in range(8):
            txns.add("user-x", {
                "timestamp": NOW - (8 - i) * 300, "amount": 100.0,
                "country": "US", "device_id": "dev-x",
            })
        devices.add("dev-x", "user-x")
        graph.add_edge("acct:user-x", "dev:dev-x")
        return EvidenceAgent(txns, devices, graph)

    def test_gather_returns_all_six_signals(self):
        agent = self._agent_with_burst()
        evidence = agent.gather(_alert())
        names = {e.name for e in evidence}
        self.assertEqual(names, {
            "velocity", "amount_vs_average", "device_sharing",
            "new_device", "geo_velocity", "ring_expansion",
        })

    def test_velocity_detects_burst(self):
        agent = self._agent_with_burst()
        (item,) = [e for e in agent.gather(_alert()) if e.name == "velocity"]
        self.assertGreaterEqual(item.signal, 0.7)
        self.assertIn("8 transactions", item.value)

    def test_quiet_account_has_low_velocity(self):
        txns, devices, graph = _stores()
        agent = EvidenceAgent(txns, devices, graph)
        (item,) = [e for e in agent.gather(_alert()) if e.name == "velocity"]
        self.assertLessEqual(item.signal, 0.1)

    def test_amount_spike_detected(self):
        txns, devices, graph = _stores()
        for _ in range(5):
            txns.add("user-x", {"timestamp": NOW - 86400, "amount": 50.0,
                                "country": "US", "device_id": "dev-x"})
        agent = EvidenceAgent(txns, devices, graph)
        (item,) = [e for e in agent.gather(_alert(amount=5_000.0))
                   if e.name == "amount_vs_average"]
        self.assertGreaterEqual(item.signal, 0.8)

    def test_device_sharing_flags_ring(self):
        txns, devices, graph = _stores()
        for i in range(5):
            devices.add("dev-shared", f"user-{i}")
            graph.add_edge(f"acct:user-{i}", "dev:dev-shared")
        devices.add("dev-shared", "user-x")
        graph.add_edge("acct:user-x", "dev:dev-shared")
        agent = EvidenceAgent(txns, devices, graph)
        (item,) = [e for e in agent.gather(_alert(device_id="dev-shared"))
                   if e.name == "device_sharing"]
        self.assertEqual(item.signal, 1.0)

    def test_impossible_travel_flagged(self):
        txns, devices, graph = _stores()
        txns.add("user-x", {"timestamp": NOW - 1800, "amount": 20.0,
                            "country": "US", "device_id": "dev-x"})
        agent = EvidenceAgent(txns, devices, graph)
        (item,) = [e for e in agent.gather(_alert(country="JP"))
                   if e.name == "geo_velocity"]
        self.assertGreaterEqual(item.signal, 0.9)

    def test_signals_bounded(self):
        agent = self._agent_with_burst()
        for item in agent.gather(_alert()):
            self.assertGreaterEqual(item.signal, 0.0)
            self.assertLessEqual(item.signal, 1.0)


if __name__ == "__main__":
    unittest.main()
