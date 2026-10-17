"""Shared data models for the agentic fraud investigation pipeline.

Pure stdlib dataclasses. Every agent in the pipeline reads and writes
these objects; the Orchestrator threads them together into a Case.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Alert:
    """An incoming transaction alert to investigate."""

    alert_id: str
    account_id: str
    amount: float
    merchant: str
    merchant_category: str
    timestamp: float  # epoch seconds
    channel: str  # card_present | online | wire | ach
    device_id: str
    ip_address: str
    country: str  # transaction country (ISO-2)
    account_country: str  # account domicile (ISO-2)
    account_age_days: int
    prior_chargebacks: int = 0


@dataclass
class EvidenceItem:
    """One piece of gathered evidence with a normalized suspicion signal."""

    name: str
    value: str
    signal: float  # 0.0 (benign) .. 1.0 (highly suspicious)
    detail: str


@dataclass
class Case:
    """The full investigation result for one alert."""

    alert: Alert
    priority: str = ""  # low | medium | high
    triage_reasons: list = field(default_factory=list)
    evidence: list = field(default_factory=list)  # list[EvidenceItem]
    risk_score: float = 0.0
    contributions: dict = field(default_factory=dict)  # evidence name -> share of score
    verdict: str = ""  # approve | review | block
    summary: str = ""
