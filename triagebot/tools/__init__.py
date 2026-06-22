"""TriageBot tools (LangChain ``@tool`` callables).

Four tools are exposed:
  1. faq_lookup        - search the NimbusPay FAQ
  2. account_lookup    - look up a customer account by id
  3. refund_calculator - apply the refund rule (auto vs escalate)
  4. open_ticket       - file a support ticket (bonus 4th tool)
"""

from .faq_tool import faq_lookup
from .account_tool import account_lookup
from .refund_tool import refund_calculator
from .ticket_tool import open_ticket

ALL_TOOLS = [faq_lookup, account_lookup, refund_calculator, open_ticket]

__all__ = [
    "faq_lookup",
    "account_lookup",
    "refund_calculator",
    "open_ticket",
    "ALL_TOOLS",
]
