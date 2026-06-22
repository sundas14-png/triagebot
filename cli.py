"""TriageBot command-line interface.

A tiny REPL: type a customer message, get TriageBot's reply. It also prints the
branch that was chosen, any tool calls, and the self-review loop status so you
can see the agent's reasoning during a demo.

Usage:
    python cli.py
"""

from __future__ import annotations

import sys

from triagebot.graph import build_triagebot

BANNER = r"""
==============================================
  TriageBot - NimbusPay self-reviewing agent
  (LangChain + LangGraph)
==============================================
Type a customer message and press Enter.
Commands:  :reset  (clear session memory)   :quit  (exit)

Try:
  - Why was I charged a $2 fee?
  - What's the balance on account 4821?
  - I want a $120 refund.
"""


def _print_trace(result: dict) -> None:
    """Show the branch, tools, and review status for transparency."""
    route = result.get("route", "?")
    print(f"   [branch] {route}  ({result.get('route_reason', '')})")
    for call in result.get("tool_calls", []):
        print(f"   [tool]   {call['name']}({call['args']})")
    redos = result.get("redo_count", 0)
    if redos:
        print(f"   [review] redone {redos} time(s)")
    if result.get("escalated"):
        print("   [escalated to human]")


def main() -> int:
    try:
        bot = build_triagebot()
    except RuntimeError as exc:  # missing API key, etc.
        print(f"Startup error: {exc}")
        return 1

    print(BANNER)
    while True:
        try:
            msg = input("you > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye!")
            return 0

        if not msg:
            continue
        if msg in {":quit", ":q", "exit"}:
            print("bye!")
            return 0
        if msg == ":reset":
            bot.reset()
            print("(session memory cleared)")
            continue

        result = bot.respond(msg)
        _print_trace(result)
        print(f"bot > {result.get('final_reply', '')}\n")


if __name__ == "__main__":
    sys.exit(main())
