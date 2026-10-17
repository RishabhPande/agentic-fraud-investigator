"""Risk scorer: combines evidence into a calibrated risk score.

Each evidence item carries a 0..1 suspicion signal; per-signal weights
reflect how discriminative that signal is. The weighted average is passed
through a logistic calibration so scores behave like probabilities, and
per-signal contributions are reported for explainability.
"""

from __future__ import annotations

import math

from models import EvidenceItem


class RiskScorer:
    """Weighted, calibrated combination of evidence signals."""

    # Signal weights: higher = more discriminative for fraud.
    WEIGHTS = {
        "ring_expansion": 1.5,
        "device_sharing": 1.4,
        "geo_velocity": 1.3,
        "velocity": 1.2,
        "amount_vs_average": 1.0,
        "new_device": 0.8,
    }

    # Logistic calibration: score = 1 / (1 + exp(-k * (x - x0)))
    _K = 8.0
    _X0 = 0.45

    BLOCK_THRESHOLD = 0.80
    REVIEW_THRESHOLD = 0.45

    def score(self, evidence: list[EvidenceItem]) -> tuple[float, dict[str, float]]:
        """Return (risk_score, contributions).

        contributions maps evidence name -> share of the weighted signal
        (sums to 1.0), so analysts see what drove the score.
        """
        if not evidence:
            return 0.0, {}

        weighted: dict[str, float] = {}
        total_weight = 0.0
        for item in evidence:
            w = self.WEIGHTS.get(item.name, 1.0)
            weighted[item.name] = w * item.signal
            total_weight += w

        raw = sum(weighted.values()) / total_weight if total_weight else 0.0
        risk = 1.0 / (1.0 + math.exp(-self._K * (raw - self._X0)))

        denom = sum(weighted.values())
        if denom > 0:
            contributions = {k: v / denom for k, v in weighted.items()}
        else:
            contributions = {k: 0.0 for k in weighted}

        return risk, contributions

    def verdict(self, risk_score: float) -> str:
        """Map a calibrated score to an action."""
        if risk_score >= self.BLOCK_THRESHOLD:
            return "block"
        if risk_score >= self.REVIEW_THRESHOLD:
            return "review"
        return "approve"
