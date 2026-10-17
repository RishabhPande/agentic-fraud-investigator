"""Tests for the LLM backends."""

import os
import sys
import unittest

sys.path.insert(0, ".")

from llm.client import AnthropicLLM, LLMClient, MockLLM, get_llm

PROMPT = "Write a fraud case summary.\n\nCASE_JSON:\n" + (
    '{"alert": {"alert_id": "ALT-1", "account_id": "user-1", "amount": 100.0,'
    ' "merchant": "Shop", "merchant_category": "groceries", "channel": "online",'
    ' "country": "US", "account_country": "US", "device_id": "dev-1"},'
    ' "priority": "high", "triage_reasons": ["Large transaction"],'
    ' "evidence": [{"name": "velocity", "value": "8 in last hour", "signal": 0.9}],'
    ' "risk_score": 0.93, "contributions": {"velocity": 1.0},'
    ' "verdict": "block"}'
)


class TestMockLLM(unittest.TestCase):
    def test_is_llm_client(self):
        self.assertIsInstance(MockLLM(), LLMClient)

    def test_renders_report_sections(self):
        report = MockLLM().complete(PROMPT)
        for section in ("CASE SUMMARY", "WHY IT WAS FLAGGED",
                        "EVIDENCE", "TOP RISK DRIVERS", "ANALYST NOTE"):
            self.assertIn(section, report)

    def test_report_contains_case_facts(self):
        report = MockLLM().complete(PROMPT)
        self.assertIn("ALT-1", report)
        self.assertIn("BLOCK", report)
        self.assertIn("velocity", report)

    def test_deterministic(self):
        llm = MockLLM()
        self.assertEqual(llm.complete(PROMPT), llm.complete(PROMPT))

    def test_block_verdict_note(self):
        report = MockLLM().complete(PROMPT)
        self.assertIn("immediate block", report)

    def test_graceful_without_case_json(self):
        report = MockLLM().complete("hello, no json here")
        self.assertIn("no case data", report)


class TestAnthropicLLM(unittest.TestCase):
    def test_missing_key_fails_fast(self):
        saved = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            with self.assertRaises(RuntimeError):
                AnthropicLLM()
        finally:
            if saved is not None:
                os.environ["ANTHROPIC_API_KEY"] = saved


class TestGetLLM(unittest.TestCase):
    def test_default_is_mock(self):
        saved = os.environ.pop("AGENT_LLM_BACKEND", None)
        try:
            self.assertIsInstance(get_llm(), MockLLM)
        finally:
            if saved is not None:
                os.environ["AGENT_LLM_BACKEND"] = saved

    def test_explicit_mock(self):
        os.environ["AGENT_LLM_BACKEND"] = "mock"
        try:
            self.assertIsInstance(get_llm(), MockLLM)
        finally:
            del os.environ["AGENT_LLM_BACKEND"]


if __name__ == "__main__":
    unittest.main()
