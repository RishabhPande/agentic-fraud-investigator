"""Evidence agent: gathers behavioral evidence for a case.

Works against simple in-memory stores (transaction history, device
fingerprints, entity graph) so the whole pipeline runs with zero
dependencies. In production these stores would be backed by a feature
store / graph database; the agent interface stays the same.
"""

from __future__ import annotations

from collections import defaultdict, deque

from models import Alert, EvidenceItem

ONE_HOUR = 3600.0
IMPOSSIBLE_TRAVEL_KMH = 900.0  # faster than any commercial flight


class TransactionStore:
    """account_id -> list of past transactions (dicts)."""

    def __init__(self) -> None:
        self._txns: dict[str, list[dict]] = defaultdict(list)

    def add(self, account_id: str, txn: dict) -> None:
        self._txns[account_id].append(txn)

    def history(self, account_id: str) -> list[dict]:
        return list(self._txns[account_id])


class DeviceStore:
    """device_id -> set of account_ids ever seen on it."""

    def __init__(self) -> None:
        self._map: dict[str, set[str]] = defaultdict(set)

    def add(self, device_id: str, account_id: str) -> None:
        self._map[device_id].add(account_id)

    def accounts_for(self, device_id: str) -> set[str]:
        return set(self._map[device_id])


class GraphStore:
    """Undirected entity graph (accounts, devices, IPs)."""

    def __init__(self) -> None:
        self._adj: dict[str, set[str]] = defaultdict(set)

    def add_edge(self, a: str, b: str) -> None:
        self._adj[a].add(b)
        self._adj[b].add(a)

    def neighbors(self, entity: str, depth: int = 1) -> set[str]:
        """Breadth-first neighborhood up to `depth` hops (excluding self)."""
        seen = {entity}
        frontier = {entity}
        for _ in range(depth):
            nxt: set[str] = set()
            for node in frontier:
                for nb in self._adj[node]:
                    if nb not in seen:
                        seen.add(nb)
                        nxt.add(nb)
            frontier = nxt
        seen.discard(entity)
        return seen

    def accounts_within(self, account_id: str, depth: int = 2) -> set[str]:
        """Other accounts reachable from an account (fraud-ring expansion)."""
        return {
            n for n in self.neighbors(account_id, depth) if n.startswith("acct:")
        } - {account_id}


class EvidenceAgent:
    """Collects behavioral evidence items for an alert."""

    def __init__(
        self,
        transactions: TransactionStore,
        devices: DeviceStore,
        graph: GraphStore,
    ) -> None:
        self.transactions = transactions
        self.devices = devices
        self.graph = graph

    def gather(self, alert: Alert) -> list[EvidenceItem]:
        evidence: list[EvidenceItem] = []
        history = self.transactions.history(alert.account_id)

        evidence.append(self._velocity(alert, history))
        evidence.append(self._amount_vs_average(alert, history))
        evidence.append(self._device_sharing(alert))
        evidence.append(self._new_device(alert, history))
        evidence.append(self._geo_velocity(alert, history))
        evidence.append(self._ring_expansion(alert))

        return evidence

    # -- individual evidence collectors -----------------------------------

    def _velocity(self, alert: Alert, history: list[dict]) -> EvidenceItem:
        recent = [t for t in history if alert.timestamp - t["timestamp"] <= ONE_HOUR]
        n = len(recent)
        if n >= 10:
            signal, value = 1.0, f"{n} transactions in the last hour"
        elif n >= 5:
            signal, value = 0.7, f"{n} transactions in the last hour"
        elif n >= 3:
            signal, value = 0.4, f"{n} transactions in the last hour"
        else:
            signal, value = 0.1, f"{n} transactions in the last hour"
        return EvidenceItem(
            name="velocity",
            value=value,
            signal=signal,
            detail="Burst activity is a classic account-takeover / testing pattern.",
        )

    def _amount_vs_average(self, alert: Alert, history: list[dict]) -> EvidenceItem:
        amounts = [t["amount"] for t in history]
        if not amounts:
            return EvidenceItem(
                name="amount_vs_average",
                value="no prior history",
                signal=0.5,
                detail="No baseline to compare against; treated as moderately unusual.",
            )
        avg = sum(amounts) / len(amounts)
        ratio = alert.amount / avg if avg > 0 else 0.0
        if ratio >= 10:
            signal = 1.0
        elif ratio >= 5:
            signal = 0.8
        elif ratio >= 2:
            signal = 0.5
        else:
            signal = 0.1
        return EvidenceItem(
            name="amount_vs_average",
            value=f"${alert.amount:,.0f} vs ${avg:,.0f} avg ({ratio:.1f}x)",
            signal=signal,
            detail="Large deviation from the account's typical ticket size.",
        )

    def _device_sharing(self, alert: Alert) -> EvidenceItem:
        accounts = self.devices.accounts_for(alert.device_id)
        others = len(accounts - {alert.account_id})
        if others >= 4:
            signal = 1.0
        elif others >= 2:
            signal = 0.7
        elif others >= 1:
            signal = 0.4
        else:
            signal = 0.05
        return EvidenceItem(
            name="device_sharing",
            value=f"device seen on {others} other account(s)",
            signal=signal,
            detail="Shared devices link accounts into fraud rings or mule networks.",
        )

    def _new_device(self, alert: Alert, history: list[dict]) -> EvidenceItem:
        device_txns = [t for t in history if t.get("device_id") == alert.device_id]
        if not device_txns and history:
            return EvidenceItem(
                name="new_device",
                value="yes -- first transaction on this device",
                signal=0.6,
                detail="First transaction from this device on the account.",
            )
        if device_txns:
            first_seen = min(t["timestamp"] for t in device_txns)
            age_hours = (alert.timestamp - first_seen) / 3600.0
            if age_hours < 24:
                return EvidenceItem(
                    name="new_device",
                    value=f"device first seen {age_hours:.1f}h ago",
                    signal=0.5,
                    detail="Device appeared on this account very recently.",
                )
        return EvidenceItem(
            name="new_device",
            value="no",
            signal=0.05,
            detail="Device is established on this account.",
        )

    def _geo_velocity(self, alert: Alert, history: list[dict]) -> EvidenceItem:
        # Find the most recent prior transaction from a different country.
        prior = [t for t in history if t["timestamp"] < alert.timestamp]
        if not prior:
            return EvidenceItem(
                name="geo_velocity", value="no prior location",
                signal=0.2,
                detail="No prior location baseline.",
            )
        last = max(prior, key=lambda t: t["timestamp"])
        if last.get("country") == alert.country:
            return EvidenceItem(
                name="geo_velocity", value="same country as last transaction",
                signal=0.05,
                detail="Location consistent with recent activity.",
            )
        dt_hours = (alert.timestamp - last["timestamp"]) / 3600.0
        # Crude impossible-travel heuristic: different country within 2h.
        if dt_hours < 2:
            signal = 0.95
            value = f"{last.get('country')} -> {alert.country} in {dt_hours:.1f}h"
        elif dt_hours < 12:
            signal = 0.5
            value = f"{last.get('country')} -> {alert.country} in {dt_hours:.1f}h"
        else:
            signal = 0.15
            value = f"{last.get('country')} -> {alert.country} in {dt_hours:.1f}h"
        return EvidenceItem(
            name="geo_velocity",
            value=value,
            signal=signal,
            detail="Impossible-travel heuristic: country changed faster than feasible.",
        )

    def _ring_expansion(self, alert: Alert) -> EvidenceItem:
        ring = self.graph.accounts_within(f"acct:{alert.account_id}", depth=2)
        n = len(ring)
        if n >= 5:
            signal = 1.0
        elif n >= 3:
            signal = 0.75
        elif n >= 1:
            signal = 0.45
        else:
            signal = 0.05
        return EvidenceItem(
            name="ring_expansion",
            value=f"{n} linked account(s) within 2 hops",
            signal=signal,
            detail="Graph expansion over shared devices/IPs; dense clusters suggest rings.",
        )
