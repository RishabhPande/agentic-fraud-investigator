# Agentic Fraud Investigator

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/RishabhPande/agentic-fraud-investigator/blob/main/demo.py)

A multi-agent fraud investigation system in **pure Python, zero dependencies**.
Given a transaction alert, a team of specialized agents triages it, gathers
behavioral evidence, scores the risk, and writes an analyst-style case report:
the same workflow a human fraud analyst follows, automated end to end.

## Architecture

```
                    ┌─────────────┐
                    │    Alert    │
                    └──────┬──────┘
                           ▼
              ┌────────────────────────┐
              │  1. Triage Agent       │  priority: low / medium / high
              │     (static rules)     │  + human-readable reasons
              └────────────┬───────────┘
                           ▼
              ┌────────────────────────┐
              │  2. Evidence Agent     │  velocity, amount-vs-average,
              │     (behavioral)       │  device sharing, new device,
              └────────────┬───────────┘  geo-velocity, ring expansion
                           ▼
              ┌────────────────────────┐
              │  3. Risk Scorer        │  calibrated 0..1 score
              │     (weighted+logistic)│  + per-signal contributions
              └────────────┬───────────┘
                           ▼
              ┌────────────────────────┐
              │  4. Summarizer Agent   │  analyst-style case report
              │     (LLM-backed)       │  via pluggable LLM backend
              └────────────────────────┘
```

The `Orchestrator` wires the four agents into one pipeline and returns a
fully populated `Case` object. Each agent is independently testable and
swappable: the evidence stores are simple in-memory structures, so the
whole system runs offline with no setup.

## Quickstart

```bash
# Run the end-to-end demo (4 synthetic scenarios, deterministic)
python demo.py

# Run one scenario
python demo.py mule_network

# Run the test suite (stdlib unittest only)
python -m unittest discover -s tests
```

## The agents

| Agent | File | What it does |
|---|---|---|
| Triage | `agents/triage.py` | Rule-based priority (amount, cross-border, channel, tenure, history, MCC) with reasons |
| Evidence | `agents/evidence.py` | 6 behavioral signals over in-memory transaction / device / graph stores |
| Risk scorer | `agents/risk_scorer.py` | Weighted combination + logistic calibration; reports what drove the score |
| Summarizer | `agents/summarizer.py` | LLM-backed analyst report from the investigated case |
| Orchestrator | `agents/orchestrator.py` | Runs triage → evidence → score → verdict → summary |

## LLM backends

`llm/client.py` defines a tiny `LLMClient` interface with two backends:

- **MockLLM** (default): deterministic, template-driven reports. Used by tests
  and the demo; everything runs offline.
- **AnthropicLLM**: real API calls over stdlib `urllib` (no SDK needed).
  Enabled with `AGENT_LLM_BACKEND=anthropic` and `ANTHROPIC_API_KEY` set.

## Synthetic scenarios

`data/generator.py` builds reproducible fraud cases (seeded):

| Scenario | Pattern | Expected verdict |
|---|---|---|
| `mule_network` | 5 accounts, one shared device, burst deposits → large outbound wire | block |
| `account_takeover` | Quiet history → new device, burst, impossible travel | review |
| `synthetic_identity` | Fresh account, card-testing micro-charges → big first purchase | review |
| `legit` | Steady grocery history, same device/country | approve |

## Example output

```
CASE SUMMARY
============================================================
Alert ALT-MULE-001 | Account user-mule-01
$48,500.00 at Overseas Exchange Ltd (money_transfer, wire)
Priority: HIGH | Risk score: 0.91 | Verdict: BLOCK

WHY IT WAS FLAGGED
  - Very large transaction ($48,500)
  - Cross-border: transaction in NG, account domiciled in US
  - Irreversible channel (wire transfer)

EVIDENCE
  - device_sharing: device seen on 4 other account(s) (signal 1.00)
  - ring_expansion: 4 linked account(s) within 2 hops (signal 0.75)
  ...

TOP RISK DRIVERS
  - device_sharing: 33% of score
  - ring_expansion: 27% of score
  ...
```

## Roadmap

- Streaming mode: investigate alerts as they arrive off a queue
- Graph store backed by an embedded DB for larger rings
- Precision/recall evaluation harness over labeled synthetic data
- Real-time feature store adapter (behind the same agent interface)
- Additional scenarios: triangulation fraud, refund abuse, pig-butchering

## Design notes

- **No dependencies.** Everything is stdlib, including the Anthropic API
  client (`urllib`) and the test suite (`unittest`).
- **Deterministic.** Seeded data generation and a mock LLM mean the demo and
  tests are fully reproducible.
- **Explainable.** Every priority has reasons, every score has contributions,
  every verdict traces back to evidence.

## Part of a fraud-ML series

- [GNN Fraud Ring Detection](https://github.com/RishabhPande/GNN-fraud-ring-detection) - GraphSAGE, GAT, GCN, GIN and LSTM from scratch in pure Python (zero dependencies) for fraud ring detection
- [ID-document-forgery-detection-CV-](https://github.com/RishabhPande/ID-document-forgery-detection-CV-) - Classic image forensics for ID-document forgery detection, written from scratch in pure Python, zero dependencies.
- [Time-series-anomaly-detection](https://github.com/RishabhPande/Time-series-anomaly-detection) - Time-series anomaly detection, including collective anomalies
- [fraud-eval](https://github.com/RishabhPande/fraud-eval) - Open benchmark for evaluating LLM-based fraud and abuse detectors (20-case smoke test, cost-aware metrics, counterfactual evaluation)
- [fraud-rings](https://github.com/RishabhPande/fraud-rings) - Synthetic identity-fraud ring generator plus graph-based detection, all in pure Python, no dependencies.
