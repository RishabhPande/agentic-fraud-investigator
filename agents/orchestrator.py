"""Orchestrator: runs the full investigation pipeline.

    alert -> triage -> evidence -> risk score -> verdict -> summary

Returns a fully populated Case object. Each stage is a separate agent,
so stages can be tested, swapped, or run independently.
"""

from __future__ import annotations

from llm.client import LLMClient
from models import Alert, Case
from .evidence import DeviceStore, EvidenceAgent, GraphStore, TransactionStore
from .risk_scorer import RiskScorer
from .summarizer import Summarizer
from .triage import TriageAgent


class Orchestrator:
    """Wires the agents into an end-to-end investigation."""

    def __init__(
        self,
        transactions: TransactionStore,
        devices: DeviceStore,
        graph: GraphStore,
        llm: LLMClient,
    ) -> None:
        self.triage = TriageAgent()
        self.evidence_agent = EvidenceAgent(transactions, devices, graph)
        self.scorer = RiskScorer()
        self.summarizer = Summarizer(llm)

    def investigate(self, alert: Alert) -> Case:
        case = Case(alert=alert)

        case.priority, case.triage_reasons = self.triage.triage(alert)
        case.evidence = self.evidence_agent.gather(alert)
        case.risk_score, case.contributions = self.scorer.score(case.evidence)
        case.verdict = self.scorer.verdict(case.risk_score)
        case.summary = self.summarizer.summarize(case)

        return case
