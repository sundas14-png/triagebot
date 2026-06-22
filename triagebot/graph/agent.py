"""TriageBot agent built on LangGraph.

Graph flow (see README for a diagram)::

        START
          |
        router  ----------------------------.
       /   |    \\                            \\
   faq   tool   escalate                      |
       \\   |    /                             |
        draft  <----------------.             |
          |                     |             |
        review --(fail & redos  |             |
          |        remaining)---'             |
          | (pass OR redo cap hit)            |
        finalize  <-------------------------- '
          |
         END

LangChain provides the model, the prompt, and the tools. LangGraph provides the
control flow: the state, the branch (router), and the self-review redo loop.
"""

from __future__ import annotations

import json
import re
from typing import Iterator

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from ..config import MAX_REDOS
from ..tools import account_lookup, faq_lookup, open_ticket, refund_calculator
from ..tools.account_tool import find_account
from .llm import make_llm
from .prompts import DRAFTER_SYSTEM, JUDGE_SYSTEM, ROUTER_SYSTEM
from .state import TriageState

# Tools available on the "tool" branch, keyed by name for execution.
_TOOLBOX = {
    "faq_lookup": faq_lookup,
    "account_lookup": account_lookup,
    "refund_calculator": refund_calculator,
    "open_ticket": open_ticket,
}


def _extract_json(text: str) -> dict:
    """Best-effort parse of a JSON object out of an LLM response."""
    text = text.strip()
    # Strip code fences if present.
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    return {}


class TriageBot:
    """Wraps the compiled LangGraph and holds session memory."""

    def __init__(self) -> None:
        # One shared model for routing/drafting, one stricter one for judging.
        self._llm = make_llm(temperature=0.2)
        self._judge_llm = make_llm(temperature=0.0)
        # Session memory (bonus #2): last account looked up this session.
        self.last_account_id: str | None = None
        self._graph = self._build_graph()

    # ------------------------------------------------------------------ #
    # Nodes
    # ------------------------------------------------------------------ #
    def _router_node(self, state: TriageState) -> dict:
        """Branch: decide FAQ vs tool vs escalate (the real decision point)."""
        msg = state["message"]
        resp = self._llm.invoke(
            [SystemMessage(ROUTER_SYSTEM), HumanMessage(msg)]
        )
        parsed = _extract_json(resp.content)
        route = parsed.get("route", "faq")
        if route not in {"faq", "tool", "escalate"}:
            route = "faq"

        # Capture an account id only when it is clearly an account reference:
        # the router's parsed id (validated against the table) or an explicit
        # "account <number>" phrase. We deliberately do NOT grab bare numbers
        # like a refund amount ("$120"). Fall back to session memory otherwise.
        account_id = (parsed.get("account_id") or "").strip()
        if account_id and not find_account(account_id):
            account_id = ""  # router hallucinated / it was an amount, ignore
        if not account_id:
            m = re.search(r"account\s*#?\s*(\d{3,})", msg, flags=re.IGNORECASE)
            account_id = m.group(1) if m else ""
        if not account_id and self.last_account_id:
            account_id = self.last_account_id

        return {
            "route": route,
            "route_reason": parsed.get("reason", ""),
            "last_account_id": account_id or state.get("last_account_id"),
            "tool_calls": [],
            "redo_count": 0,
            "max_redos": state.get("max_redos", MAX_REDOS),
        }

    def _faq_node(self, state: TriageState) -> dict:
        """FAQ branch: answer from the knowledge base."""
        result = faq_lookup.invoke({"query": state["message"]})
        return {
            "tool_calls": [
                {"name": "faq_lookup", "args": {"query": state["message"]},
                 "result": result}
            ],
            "tool_context": f"FAQ results:\n{result}",
        }

    def _tool_node(self, state: TriageState) -> dict:
        """Tool branch: let the model pick and call the right tool(s)."""
        msg = state["message"]
        account_hint = state.get("last_account_id") or ""
        llm_with_tools = self._llm.bind_tools(
            [account_lookup, refund_calculator, faq_lookup, open_ticket]
        )
        guidance = (
            "Decide which tool(s) to call to help this customer. "
            "If they ask about a specific account/balance/transaction, call "
            "account_lookup. If they ask about a refund amount, call "
            "refund_calculator. "
        )
        if account_hint:
            guidance += f"If no account number is given, assume account {account_hint}. "

        ai = llm_with_tools.invoke(
            [SystemMessage(guidance), HumanMessage(msg)]
        )

        calls = []
        context_parts = []
        last_account = state.get("last_account_id")
        for tc in getattr(ai, "tool_calls", []) or []:
            name = tc["name"]
            args = tc.get("args", {})
            tool = _TOOLBOX.get(name)
            if not tool:
                continue
            result = tool.invoke(args)
            calls.append({"name": name, "args": args, "result": result})
            context_parts.append(f"{name}({args}) ->\n{result}")
            # Update session memory whenever an account is successfully read.
            if name == "account_lookup":
                m = re.search(r"\d{3,}", str(args.get("account_id", "")))
                if m and find_account(m.group(0)):
                    last_account = m.group(0)

        if not calls:
            # Model chose no tool; fall back to FAQ so we still help.
            result = faq_lookup.invoke({"query": msg})
            calls.append({"name": "faq_lookup", "args": {"query": msg},
                          "result": result})
            context_parts.append(f"FAQ results:\n{result}")

        # If the refund calculator flagged an over-cap amount, this turn is an
        # escalation: file a ticket and mark it so the UI / caller knows. The
        # bot must never auto-execute an over-cap refund.
        escalated = any("ESCALATE" in c["result"] for c in calls)
        if escalated:
            summary = f"Over-cap refund request escalated by TriageBot: {msg}"
            ticket = open_ticket.invoke(
                {"summary": summary, "account_id": last_account or "unknown"}
            )
            calls.append({"name": "open_ticket",
                          "args": {"summary": summary,
                                   "account_id": last_account or "unknown"},
                          "result": ticket})
            context_parts.append(
                f"This is an over-cap request that MUST be escalated. {ticket}"
            )

        return {
            "tool_calls": calls,
            "tool_context": "\n\n".join(context_parts),
            "last_account_id": last_account,
            "escalated": escalated,
        }

    def _escalate_node(self, state: TriageState) -> dict:
        """Escalate branch: open a ticket and hand off to a human."""
        account_id = state.get("last_account_id") or "unknown"
        summary = f"Escalated from TriageBot: {state['message']}"
        ticket = open_ticket.invoke(
            {"summary": summary, "account_id": account_id}
        )
        context = (
            f"This request must be escalated to a human (reason: "
            f"{state.get('route_reason', 'policy')}). A ticket was filed:\n{ticket}"
        )
        return {
            "escalated": True,
            "tool_calls": [
                {"name": "open_ticket",
                 "args": {"summary": summary, "account_id": account_id},
                 "result": ticket}
            ],
            "tool_context": context,
        }

    def _draft_node(self, state: TriageState) -> dict:
        """Write a candidate reply from the gathered context."""
        redo_note = ""
        if state.get("redo_count", 0) > 0 and state.get("review_feedback"):
            redo_note = (
                "Your previous draft was rejected by the reviewer. "
                f"Fix this issue: {state['review_feedback']}"
            )
        system = DRAFTER_SYSTEM.format(redo_note=redo_note)
        human = (
            f"Customer message:\n{state['message']}\n\n"
            f"Context to use:\n{state.get('tool_context', '(none)')}"
        )
        resp = self._llm.invoke([SystemMessage(system), HumanMessage(human)])
        return {"draft": resp.content.strip()}

    def _review_node(self, state: TriageState) -> dict:
        """LLM judge reviews the draft against the rules (bonus #3)."""
        human = (
            f"Customer message:\n{state['message']}\n\n"
            f"Context:\n{state.get('tool_context', '(none)')}\n\n"
            f"Draft reply:\n{state['draft']}"
        )
        resp = self._judge_llm.invoke(
            [SystemMessage(JUDGE_SYSTEM), HumanMessage(human)]
        )
        parsed = _extract_json(resp.content)
        passed = parsed.get("verdict", "pass").lower() == "pass"
        return {
            "review_passed": passed,
            "review_feedback": parsed.get("feedback", ""),
        }

    def _finalize_node(self, state: TriageState) -> dict:
        """Produce the final reply shown to the customer."""
        reply = state.get("draft", "")
        # Safety net: if the review never passed (redo cap hit), escalate rather
        # than send a reply the judge rejected.
        if not state.get("review_passed", True):
            account_id = state.get("last_account_id") or "unknown"
            ticket = open_ticket.invoke({
                "summary": f"Auto-escalated after {state.get('redo_count', 0)} "
                           f"failed self-reviews: {state['message']}",
                "account_id": account_id,
            })
            reply = (
                "I want to make sure this is handled correctly, so I'm escalating "
                f"this to a human specialist. {ticket}"
            )
            return {"final_reply": reply, "escalated": True}
        return {"final_reply": reply}

    # ------------------------------------------------------------------ #
    # Edges
    # ------------------------------------------------------------------ #
    @staticmethod
    def _route_edge(state: TriageState) -> str:
        return state["route"]

    @staticmethod
    def _review_edge(state: TriageState) -> str:
        """Loop back to draft on failure (until the redo cap), else finalize."""
        if state.get("review_passed"):
            return "finalize"
        if state.get("redo_count", 0) >= state.get("max_redos", MAX_REDOS):
            return "finalize"  # cap hit -> finalize will escalate safely
        return "redo"

    def _bump_redo(self, state: TriageState) -> dict:
        return {"redo_count": state.get("redo_count", 0) + 1}

    # ------------------------------------------------------------------ #
    # Build
    # ------------------------------------------------------------------ #
    def _build_graph(self):
        g = StateGraph(TriageState)
        g.add_node("router", self._router_node)
        g.add_node("faq", self._faq_node)
        g.add_node("tool", self._tool_node)
        g.add_node("escalate", self._escalate_node)
        g.add_node("draft", self._draft_node)
        g.add_node("review", self._review_node)
        g.add_node("bump_redo", self._bump_redo)
        g.add_node("finalize", self._finalize_node)

        g.add_edge(START, "router")
        g.add_conditional_edges(
            "router",
            self._route_edge,
            {"faq": "faq", "tool": "tool", "escalate": "escalate"},
        )
        # All three branches feed the drafter.
        g.add_edge("faq", "draft")
        g.add_edge("tool", "draft")
        g.add_edge("escalate", "draft")
        g.add_edge("draft", "review")
        # Self-review redo loop with a hard cap.
        g.add_conditional_edges(
            "review",
            self._review_edge,
            {"redo": "bump_redo", "finalize": "finalize"},
        )
        g.add_edge("bump_redo", "draft")
        g.add_edge("finalize", END)
        return g.compile()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def respond(self, message: str) -> dict:
        """Run the full graph for one customer message and return final state."""
        result = self._graph.invoke({
            "message": message,
            "last_account_id": self.last_account_id,
            "max_redos": MAX_REDOS,
        })
        # Persist session memory across turns.
        if result.get("last_account_id"):
            self.last_account_id = result["last_account_id"]
        return result

    def stream_response(self, message: str) -> Iterator[str]:
        """Yield the validated reply token-by-token (bonus #4).

        The full graph (routing, tools, and the self-review loop) runs first so
        that only an approved, compliant reply is ever streamed. The approved
        text is then emitted in small chunks for a live typing effect.
        """
        result = self.respond(message)
        reply = result.get("final_reply", "")
        for token in re.findall(r"\S+\s*", reply):
            yield token

    def reset(self) -> None:
        """Clear session memory (used by the UI's reset button)."""
        self.last_account_id = None


def build_triagebot() -> TriageBot:
    """Convenience factory."""
    return TriageBot()
