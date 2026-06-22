"""Refund calculator tool.

Applies the synthetic refund rule:
  * refunds strictly under $50 are auto-eligible
  * refunds of $50 or more are over-cap and MUST escalate to a human

This tool only *evaluates* eligibility. It never moves money. The agent is
explicitly forbidden from auto-executing an over-cap refund.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache

from langchain_core.tools import tool

from ..config import REFUND_RULES_PATH


@lru_cache(maxsize=1)
def _load_rules() -> dict:
    with open(REFUND_RULES_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _parse_amount(raw: str) -> float | None:
    """Extract a dollar amount from free-form text like "$120" or "120.50"."""
    match = re.search(r"-?\d+(?:\.\d+)?", str(raw).replace(",", ""))
    return float(match.group(0)) if match else None


@tool
def refund_calculator(amount: str) -> str:
    """Check whether a refund of a given dollar amount is auto-eligible or must
    be escalated.

    Pass the refund amount (e.g. "45" or "$120"). Refunds under $50 are
    auto-eligible; refunds of $50 or more are over-cap and must be escalated to
    a human - they are never auto-executed.
    """
    rules = _load_rules()
    threshold = rules["auto_eligible_threshold"]

    value = _parse_amount(amount)
    if value is None:
        return (
            "Could not read a refund amount. Ask the customer for the exact "
            "dollar amount they want refunded."
        )

    value = abs(value)
    if value < threshold:
        return (
            f"ELIGIBLE: A ${value:.2f} refund is under the ${threshold:.0f} cap "
            f"and is auto-eligible. It can be approved and will settle in 3-5 "
            f"business days."
        )
    return (
        f"ESCALATE: A ${value:.2f} refund is at or over the ${threshold:.0f} cap. "
        f"This is over-cap and must NOT be auto-executed. Escalate to a human "
        f"specialist for manual review."
    )
