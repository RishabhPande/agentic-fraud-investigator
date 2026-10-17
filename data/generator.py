"""Synthetic fraud-case generator.

Produces realistic alerts plus the supporting history (transactions,
devices, graph edges) that the evidence agent consumes. Fully seeded,
so every scenario is reproducible.

Scenarios:
  - mule_network:       money-mule ring, shared devices, fan-in deposits
  - account_takeover:   old account, new device, impossible travel, burst
  - synthetic_identity: brand-new account, large first purchase
  - legit:              control case -- normal behavior, low risk
"""

from __future__ import annotations

import random
import time

from agents.evidence import DeviceStore, GraphStore, TransactionStore
from models import Alert

BASE_TIME = 1_790_000_000.0  # fixed anchor so timestamps are reproducible

SCENARIOS = ("mule_network", "account_takeover", "synthetic_identity", "legit")


def _txn(ts, amount, merchant, category, country, device, ip):
    return {
        "timestamp": ts,
        "amount": amount,
        "merchant": merchant,
        "merchant_category": category,
        "country": country,
        "device_id": device,
        "ip_address": ip,
    }


def _register(stores, account_id, device_id, ip, txn):
    txns, devices, graph = stores
    txns.add(account_id, txn)
    devices.add(device_id, account_id)
    graph.add_edge(f"acct:{account_id}", f"dev:{device_id}")
    graph.add_edge(f"acct:{account_id}", f"ip:{ip}")


def generate_case(scenario: str, seed: int = 42):
    """Return (alert, (transactions, devices, graph)) for a scenario."""
    if scenario not in SCENARIOS:
        raise ValueError(f"unknown scenario {scenario!r}; choose from {SCENARIOS}")
    rng = random.Random(seed)
    txns, devices, graph = TransactionStore(), DeviceStore(), GraphStore()
    stores = (txns, devices, graph)
    now = BASE_TIME

    if scenario == "mule_network":
        alert = _mule_network(rng, stores, now)
    elif scenario == "account_takeover":
        alert = _account_takeover(rng, stores, now)
    elif scenario == "synthetic_identity":
        alert = _synthetic_identity(rng, stores, now)
    else:
        alert = _legit(rng, stores, now)

    return alert, stores


def _mule_network(rng, stores, now):
    acct = "user-mule-01"
    device = "dev-shared-9"
    ip = "203.0.113.44"
    # Ring: 5 mule accounts sharing one device, fanning deposits in
    # (rapid bursts within the last hour -- classic placement behavior).
    for i in range(5):
        mule = f"user-mule-{i:02d}"
        for d in range(3):
            txn = _txn(now - (d + 1) * 900, 900 + rng.uniform(0, 90),
                       "QuickPay Transfer", "money_transfer", "US", device, ip)
            _register(stores, mule, device, ip, txn)
    # The alert: large outbound wire from the ringleader account.
    txn = _txn(now, 48_500, "Overseas Exchange Ltd", "money_transfer",
               "NG", device, ip)
    _register(stores, acct, device, ip, txn)
    return Alert(
        alert_id="ALT-MULE-001", account_id=acct, amount=48_500,
        merchant="Overseas Exchange Ltd", merchant_category="money_transfer",
        timestamp=now, channel="wire", device_id=device, ip_address=ip,
        country="NG", account_country="US", account_age_days=210,
        prior_chargebacks=0,
    )


def _account_takeover(rng, stores, now):
    acct = "user-ato-07"
    home_device, home_ip = "dev-home-3", "198.51.100.23"
    bad_device, bad_ip = "dev-unknown-77", "192.0.2.88"
    # Six months of quiet, normal history on the home device.
    for m in range(24):
        txn = _txn(now - (m + 1) * 7 * 86400, 60 + rng.uniform(0, 120),
                   "Corner Grocery", "groceries", "US", home_device, home_ip)
        _register(stores, acct, home_device, home_ip, txn)
    # Burst of 8 rapid transactions from a new device (still domestic),
    # then the alert: a big cross-border purchase minutes later.
    for i in range(8):
        txn = _txn(now - (8 - i) * 300, 400 + rng.uniform(0, 300),
                   "ElectroHub", "electronics", "US", bad_device, bad_ip)
        _register(stores, acct, bad_device, bad_ip, txn)
    txn = _txn(now, 3_899, "ElectroHub", "electronics", "RO", bad_device, bad_ip)
    _register(stores, acct, bad_device, bad_ip, txn)
    return Alert(
        alert_id="ALT-ATO-002", account_id=acct, amount=3_899,
        merchant="ElectroHub", merchant_category="electronics",
        timestamp=now, channel="online", device_id=bad_device, ip_address=bad_ip,
        country="RO", account_country="US", account_age_days=940,
        prior_chargebacks=0,
    )


def _synthetic_identity(rng, stores, now):
    acct = "user-synth-12"
    device, ip = "dev-new-12", "203.0.113.99"
    # Card-testing micro-charges in the last hour, then the big hit.
    for i in range(6):
        txn = _txn(now - (6 - i) * 420, round(rng.uniform(1.0, 5.0), 2),
                   "TestCharge LLC", "services", "US", device, ip)
        _register(stores, acct, device, ip, txn)
    # The same device already touched two other fresh synthetic accounts.
    for j in range(2):
        other = f"user-synth-{20 + j}"
        txn = _txn(now - 3600, 2.99, "TestCharge LLC", "services",
                   "US", device, ip)
        _register(stores, other, device, ip, txn)
    txn = _txn(now, 7_250, "LuxTime Watches", "jewelry", "US", device, ip)
    _register(stores, acct, device, ip, txn)
    return Alert(
        alert_id="ALT-SYN-003", account_id=acct, amount=7_250,
        merchant="LuxTime Watches", merchant_category="jewelry",
        timestamp=now, channel="online", device_id=device, ip_address=ip,
        country="US", account_country="US", account_age_days=11,
        prior_chargebacks=0,
    )


def _legit(rng, stores, now):
    acct = "user-legit-20"
    device, ip = "dev-legit-20", "198.51.100.77"
    for w in range(12):
        txn = _txn(now - (w + 1) * 7 * 86400, 45 + rng.uniform(0, 60),
                   "Weekly Mart", "groceries", "US", device, ip)
        _register(stores, acct, device, ip, txn)
    txn = _txn(now, 82.40, "Weekly Mart", "groceries", "US", device, ip)
    _register(stores, acct, device, ip, txn)
    return Alert(
        alert_id="ALT-LEG-004", account_id=acct, amount=82.40,
        merchant="Weekly Mart", merchant_category="groceries",
        timestamp=now, channel="card_present", device_id=device,
        ip_address=ip, country="US", account_country="US",
        account_age_days=1200, prior_chargebacks=0,
    )


def main() -> None:
    """Print a quick inventory of the scenarios (smoke check)."""
    for scenario in SCENARIOS:
        alert, _ = generate_case(scenario)
        print(f"{scenario:20s} {alert.alert_id}  ${alert.amount:>10,.2f}  {alert.merchant}")


if __name__ == "__main__":
    main()
