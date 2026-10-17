"""Triage agent: classifies an incoming alert as low / medium / high priority.

Rule-based and fully explainable: every priority comes with the list of
reasons that produced it, so an analyst can see exactly why a case was
escalated.
"""

from __future__ import annotations

from models import Alert


HIGH_RISK_CATEGORIES = {
    "gambling",
    "crypto_exchange",
    "money_transfer",
    "prepaid_cards",
}


class TriageAgent:
    """Scores alerts on static risk factors and assigns a priority."""

    def triage(self, alert: Alert) -> tuple[str, list[str]]:
        """Return (priority, reasons). Priority is 'low', 'medium' or 'high'."""
        points = 0
        reasons: list[str] = []

        # Transaction size
        if alert.amount >= 10_000:
            points += 3
            reasons.append(f"Very large transaction (${alert.amount:,.0f})")
        elif alert.amount >= 5_000:
            points += 2
            reasons.append(f"Large transaction (${alert.amount:,.0f})")
        elif alert.amount >= 1_000:
            points += 1
            reasons.append(f"Elevated transaction amount (${alert.amount:,.0f})")

        # Cross-border
        if alert.country != alert.account_country:
            points += 2
            reasons.append(
                f"Cross-border: transaction in {alert.country}, "
                f"account domiciled in {alert.account_country}"
            )

        # Channel risk
        if alert.channel == "wire":
            points += 2
            reasons.append("Irreversible channel (wire transfer)")
        elif alert.channel == "online":
            points += 1
            reasons.append("Card-not-present (online) transaction")

        # Account tenure
        if alert.account_age_days < 30:
            points += 1
            reasons.append(f"New account ({alert.account_age_days} days old)")

        # History
        if alert.prior_chargebacks > 0:
            points += 2
            reasons.append(f"{alert.prior_chargebacks} prior chargeback(s) on account")

        # Merchant category
        if alert.merchant_category in HIGH_RISK_CATEGORIES:
            points += 1
            reasons.append(f"High-risk merchant category ({alert.merchant_category})")

        if points >= 5:
            priority = "high"
        elif points >= 2:
            priority = "medium"
        else:
            priority = "low"

        if not reasons:
            reasons.append("No static risk factors triggered")

        return priority, reasons
