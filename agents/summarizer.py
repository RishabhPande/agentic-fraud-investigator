"""Summarizer agent: writes the human-readable case report.

Builds a structured prompt from the investigated case (triage, evidence,
score, verdict) and hands it to the configured LLM backend. The report is
what a fraud analyst actually reads.
"""

from __future__ import annotations

import json

from llm.client import LLMClient
from models import Case

SYSTEM_PROMPT = (
    "You are a senior fraud analyst. Write a concise, professional case "
    "summary for a fraud operations queue. Cover: what happened, why it "
    "was flagged, the key evidence, the top risk drivers, and your "
    "recommended action. Be specific and avoid speculation beyond the "
    "evidence provided."
)


class Summarizer:
    """Turns an investigated Case into an analyst-style report."""

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def summarize(self, case: Case) -> str:
        prompt = self._build_prompt(case)
        return self.llm.complete(prompt, system=SYSTEM_PROMPT)

    def _build_prompt(self, case: Case) -> str:
        payload = {
            "alert": {
                "alert_id": case.alert.alert_id,
                "account_id": case.alert.account_id,
                "amount": case.alert.amount,
                "merchant": case.alert.merchant,
                "merchant_category": case.alert.merchant_category,
                "channel": case.alert.channel,
                "country": case.alert.country,
                "account_country": case.alert.account_country,
                "device_id": case.alert.device_id,
            },
            "priority": case.priority,
            "triage_reasons": case.triage_reasons,
            "evidence": [
                {
                    "name": e.name,
                    "value": e.value,
                    "signal": round(e.signal, 2),
                    "detail": e.detail,
                }
                for e in case.evidence
            ],
            "risk_score": round(case.risk_score, 4),
            "contributions": {
                k: round(v, 4) for k, v in case.contributions.items()
            },
            "verdict": case.verdict,
        }
        return (
            "Write a fraud case summary for the operations queue.\n\n"
            "CASE_JSON:\n" + json.dumps(payload, indent=2)
        )
