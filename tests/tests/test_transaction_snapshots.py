"""Transaction evidence must not change through caller-owned dictionaries."""
import unittest

from agents.evidence import TransactionStore, EvidenceAgent, DeviceStore, GraphStore
from tests.test_evidence import _alert, NOW


class TransactionSnapshotTests(unittest.TestCase):
    def transaction(self):
        return {"timestamp": NOW - 100, "amount": 50.0, "country": "US",
                "device_id": "dev-x", "metadata": {"tags": ["synthetic"]}}

    def test_add_snapshots_original_record(self):
        store = TransactionStore()
        record = self.transaction()
        store.add("user-x", record)
        record["amount"] = 9000
        self.assertEqual(store.history("user-x")[0]["amount"], 50)

    def test_add_snapshots_nested_metadata(self):
        store = TransactionStore()
        record = self.transaction()
        store.add("user-x", record)
        record["metadata"]["tags"].append("changed")
        self.assertEqual(store.history("user-x")[0]["metadata"]["tags"], ["synthetic"])

    def test_history_returns_independent_records(self):
        store = TransactionStore()
        store.add("user-x", self.transaction())
        first = store.history("user-x")
        first[0]["country"] = "JP"
        first.clear()
        self.assertEqual(store.history("user-x")[0]["country"], "US")

    def test_history_nested_values_are_independent(self):
        store = TransactionStore()
        store.add("user-x", self.transaction())
        store.history("user-x")[0]["metadata"]["tags"].clear()
        self.assertEqual(store.history("user-x")[0]["metadata"]["tags"], ["synthetic"])

    def test_reused_input_records_retain_each_insertion(self):
        store = TransactionStore()
        record = self.transaction()
        store.add("user-x", record)
        record["amount"] = 100
        store.add("user-x", record)
        self.assertEqual([t["amount"] for t in store.history("user-x")], [50, 100])

    def test_mutating_input_or_history_cannot_change_gathered_evidence(self):
        store = TransactionStore()
        record = self.transaction()
        store.add("user-x", record)
        agent = EvidenceAgent(store, DeviceStore(), GraphStore())
        baseline = agent.gather(_alert())
        record.update(amount=9000, timestamp=NOW + 100, country="JP", device_id="other")
        self.assertEqual(agent.gather(_alert()), baseline)
        store.history("user-x")[0].update(amount=9000, country="JP")
        self.assertEqual(agent.gather(_alert()), baseline)

    def test_empty_unknown_and_repeated_reads_keep_values(self):
        store = TransactionStore()
        self.assertEqual(store.history("missing"), [])
        record = self.transaction()
        store.add("user-x", record)
        self.assertEqual(store.history("user-x"), [record])
        self.assertEqual(store.history("user-x"), store.history("user-x"))
