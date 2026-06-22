"""Shared state for the TriageBot LangGraph.

The state is the single object that flows through every node. LangGraph merges
each node's returned dict into this state, which is how the branch and the
redo loop pass information around.
"""

from __future__ import annotations

from typing import List, Optional, TypedDict


class TriageState(TypedDict, total=False):
    # --- input ---
    message: str                      # the customer's message for this turn

    # --- routing / branching ---
    route: str                        # "faq" | "tool" | "escalate"
    route_reason: str                 # why the router chose this path

    # --- tool work ---
    tool_calls: List[dict]            # [{"name": ..., "args": ..., "result": ...}]
    tool_context: str                 # flattened tool results for the drafter

    # --- self-review redo loop ---
    draft: str                        # current candidate reply
    review_passed: bool               # did the LLM judge approve the draft?
    review_feedback: str              # judge's critique used to redo
    redo_count: int                   # how many redos have happened
    max_redos: int                    # cap so the loop can never run forever

    # --- output ---
    final_reply: str                  # the reply shown to the customer
    escalated: bool                   # True if this turn escalated to a human

    # --- session memory (bonus #2) ---
    last_account_id: Optional[str]    # last account looked up this session
