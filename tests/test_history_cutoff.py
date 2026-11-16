"""Future transactions must not change an earlier alert's evidence."""
import unittest
from dataclasses import asdict

from agents.evidence import EvidenceAgent
from data.generator import generate_case


class TestHistoryCutoff(unittest.TestCase):
    def test_future_burst_does_not_change_evidence(self):
        alert, stores = generate_case("legit")
        agent = EvidenceAgent(*stores)
        before = [asdict(e) for e in agent.gather(alert)]
        for i in range(12):
            stores[0].add(alert.account_id, {
                "timestamp": alert.timestamp + 3600 + i,
                "amount": 1_000_000, "device_id": alert.device_id,
                "country": "NG",
            })
        self.assertEqual([asdict(e) for e in agent.gather(alert)], before)

    def test_only_future_history_uses_no_prior_baseline(self):
        alert, stores = generate_case("legit")
        from agents.evidence import TransactionStore
        txns = TransactionStore()
        txns.add(alert.account_id, {"timestamp": alert.timestamp + 1,
                                   "amount": 99, "device_id": alert.device_id})
        evidence = {e.name: e for e in EvidenceAgent(txns, *stores[1:]).gather(alert)}
        self.assertEqual(evidence["velocity"].value, "0 transactions in the last hour")
        self.assertEqual(evidence["amount_vs_average"].value, "no prior history")
        self.assertEqual(len(txns.history(alert.account_id)), 1)

    def test_future_device_sighting_does_not_establish_device_age(self):
        alert, stores = generate_case("legit")
        alert.device_id = "new-device"
        agent = EvidenceAgent(*stores)
        before = next(e for e in agent.gather(alert) if e.name == "new_device")
        stores[0].add(alert.account_id, {
            "timestamp": alert.timestamp + 60, "amount": 100,
            "device_id": alert.device_id, "country": alert.country,
        })
        after = next(e for e in agent.gather(alert) if e.name == "new_device")
        self.assertEqual(asdict(before), asdict(after))
        self.assertIn("first transaction", after.value)

    def test_velocity_includes_hour_boundary_but_not_future(self):
        alert, stores = generate_case("legit")
        agent = EvidenceAgent(*stores)
        rows = [{"timestamp": alert.timestamp - 3600},
                {"timestamp": alert.timestamp - 3600.001},
                {"timestamp": alert.timestamp},
                {"timestamp": alert.timestamp + .001}]
        self.assertEqual(agent._velocity(alert, rows).value,
                         "2 transactions in the last hour")

    def test_gather_does_not_remove_future_transactions_from_store(self):
        alert, stores = generate_case("legit")
        stores[0].add(alert.account_id, {"timestamp": alert.timestamp + 1,
                                       "amount": 100})
        before = stores[0].history(alert.account_id)
        EvidenceAgent(*stores).gather(alert)
        self.assertEqual(stores[0].history(alert.account_id), before)
