"""Tests for the summarizer agent."""

import sys
import unittest

sys.path.insert(0, ".")

from agents.summarizer import SYSTEM_PROMPT, Summarizer
from llm.client import MockLLM
from models import Alert, Case, EvidenceItem


def _case():
    alert = Alert(
        alert_id="ALT-9", account_id="user-9", amount=9_999.0,
        merchant="ElectroHub", merchant_category="electronics",
        timestamp=1_790_000_000.0, channel="online",
        device_id="dev-9", ip_address="5.6.7.8",
        country="RO", account_country="US", account_age_days=940,
    )
    return Case(
        alert=alert,
        priority="high",
        triage_reasons=["Cross-border: transaction in RO, account domiciled in US"],
        evidence=[EvidenceItem(name="velocity", value="8 in last hour",
                               signal=0.9, detail="burst")],
        risk_score=0.93,
        contributions={"velocity": 1.0},
        verdict="block",
    )


class TestSummarizer(unittest.TestCase):
    def test_summary_mentions_key_facts(self):
        summary = Summarizer(MockLLM()).summarize(_case())
        self.assertIn("ALT-9", summary)
        self.assertIn("BLOCK", summary)
        self.assertIn("velocity", summary)

    def test_prompt_embeds_case_json(self):
        summarizer = Summarizer(MockLLM())
        prompt = summarizer._build_prompt(_case())
        self.assertIn("CASE_JSON:", prompt)
        self.assertIn("ALT-9", prompt)

    def test_deterministic_with_mock(self):
        summarizer = Summarizer(MockLLM())
        case = _case()
        self.assertEqual(summarizer.summarize(case), summarizer.summarize(case))

    def test_system_prompt_is_analyst_framed(self):
        self.assertIn("fraud analyst", SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
