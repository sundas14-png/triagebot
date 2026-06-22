"""Deterministic flow test using a fake LLM (no API key / network needed).

Validates the LangGraph wiring: branching, tool execution, the self-review
redo loop, the redo cap, escalation, and session memory.
Run:  python test_flow.py
"""
import os
os.environ.setdefault("OPENAI_API_KEY", "sk-test")

from triagebot.graph import agent as agent_mod
from triagebot.graph.agent import TriageBot


class FakeMsg:
    def __init__(self, content, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


class FakeLLM:
    """Scripted LLM: returns queued responses based on the system prompt."""
    def __init__(self, scripts):
        self.scripts = scripts

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        system = messages[0].content
        for key, resp in self.scripts:
            if key in system:
                if callable(resp):
                    return resp(messages)
                return resp
        return FakeMsg("(no script)")


def make_bot(router_json, judge_seq, draft_text="Here is your answer.",
             tool_calls=None):
    bot = TriageBot.__new__(TriageBot)
    bot.last_account_id = None
    judge_iter = iter(judge_seq)

    def judge(_):
        return FakeMsg(next(judge_iter))

    scripts = [
        ("router for TriageBot", FakeMsg(router_json)),
        ("compliance reviewer", judge),
        ("TriageBot, a friendly", FakeMsg(draft_text)),
        ("which tool(s) to call", FakeMsg("", tool_calls or [])),
    ]
    bot._llm = FakeLLM(scripts)
    bot._judge_llm = FakeLLM(scripts)
    bot._graph = bot._build_graph()
    return bot


def test_faq_pass():
    bot = make_bot('{"route":"faq","reason":"info"}',
                   ['{"verdict":"pass","feedback":""}'])
    r = bot.respond("What fees does NimbusPay charge?")
    assert r["route"] == "faq", r["route"]
    assert r["final_reply"] == "Here is your answer."
    assert not r.get("escalated")
    print("PASS: faq route + clean review")


def test_account_tool_and_memory():
    tcs = [{"name": "account_lookup", "args": {"account_id": "4821"}}]
    bot = make_bot('{"route":"tool","reason":"acct","account_id":"4821"}',
                   ['{"verdict":"pass","feedback":""}'], tool_calls=tcs)
    r = bot.respond("What's the balance on account 4821?")
    assert r["route"] == "tool"
    assert bot.last_account_id == "4821", bot.last_account_id
    assert "Ava Thompson" in r["tool_context"]
    print("PASS: tool route, account lookup, session memory set")


def test_redo_loop_then_escalate():
    # Judge always fails -> loop hits cap (2 redos -> 3 reviews) -> escalate.
    bot = make_bot('{"route":"tool","reason":"refund","refund_amount":"120"}',
                   ['{"verdict":"fail","feedback":"over-cap"}'] * 5,
                   draft_text="Sure, I'll refund your $120 now.",
                   tool_calls=[{"name": "refund_calculator",
                                "args": {"amount": "120"}}])
    r = bot.respond("I want a $120 refund.")
    assert r["redo_count"] == 2, r["redo_count"]          # cap respected
    assert r["escalated"] is True
    assert "human specialist" in r["final_reply"]
    print("PASS: redo cap respected + auto-escalation on repeated failure")


def test_direct_escalation():
    bot = make_bot('{"route":"escalate","reason":"over-cap money movement"}',
                   ['{"verdict":"pass","feedback":""}'],
                   draft_text="I'm escalating this to a human specialist.")
    r = bot.respond("Wire $5000 to an external account immediately.")
    assert r["route"] == "escalate"
    assert r["escalated"] is True
    assert any(c["name"] == "open_ticket" for c in r["tool_calls"])
    print("PASS: direct escalation route opens a ticket")


if __name__ == "__main__":
    test_faq_pass()
    test_account_tool_and_memory()
    test_redo_loop_then_escalate()
    test_direct_escalation()
    print("\nAll flow tests passed.")
