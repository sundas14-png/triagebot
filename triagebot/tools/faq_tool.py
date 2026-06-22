"""FAQ lookup tool.

Performs a lightweight keyword-overlap search over the synthetic NimbusPay FAQ
and returns the best matching Q&A pairs. Kept dependency-free (no vector store)
so the activity stays simple and fully offline for the data layer.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import List

from langchain_core.tools import tool

from ..config import FAQ_PATH

_WORD_RE = re.compile(r"[a-z0-9]+")


@lru_cache(maxsize=1)
def _load_faq() -> List[dict]:
    with open(FAQ_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _tokenize(text: str) -> set:
    return set(_WORD_RE.findall(text.lower()))


@tool
def faq_lookup(query: str) -> str:
    """Search the NimbusPay FAQ for answers about fees, refunds, password reset,
    transfers, security, account closure, and limits.

    Use this for general informational questions that do not require looking at
    a specific customer's account. Returns the most relevant FAQ answer(s).
    """
    faq = _load_faq()
    q_tokens = _tokenize(query)

    scored = []
    for item in faq:
        text = f"{item['question']} {item['answer']}"
        overlap = len(q_tokens & _tokenize(text))
        if overlap:
            scored.append((overlap, item))

    if not scored:
        return (
            "No close FAQ match found. Consider asking the customer to rephrase, "
            "or escalate if it is account-specific."
        )

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:2]
    lines = []
    for _, item in top:
        lines.append(f"Q: {item['question']}\nA: {item['answer']}")
    return "\n\n".join(lines)
