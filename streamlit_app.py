"""TriageBot Streamlit web interface.

A clean chat UI for NimbusPay support. Shows the conversation history, streams
the reply token-by-token (bonus #4), surfaces the chosen branch / tools / review
loop, and clearly flags escalations. Includes a reset button.

Run locally:
    streamlit run streamlit_app.py
"""

from __future__ import annotations

import streamlit as st

from triagebot.config import OPENAI_API_KEY
from triagebot.graph import build_triagebot

st.set_page_config(page_title="TriageBot - NimbusPay Support", page_icon="🛟",
                   layout="centered")

# --------------------------------------------------------------------------- #
# Sidebar: info, sample data, controls
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.title("🛟 TriageBot")
    st.caption("A self-reviewing support agent for **NimbusPay** "
               "(LangChain + LangGraph).")
    st.markdown(
        "**How it works**\n"
        "1. **Branch** - routes your message to *FAQ*, a *tool*, or *escalate*.\n"
        "2. **Tools** - FAQ lookup, account lookup, refund calculator, open ticket.\n"
        "3. **Self-review loop** - an LLM judge checks the draft and redoes it "
        "if it breaks a rule (capped so it can't loop forever).\n"
        "4. **Escalate** - over-cap refunds & risky requests go to a human."
    )
    st.divider()
    st.markdown(
        "**Try these**\n"
        "- *Why was I charged a \\$2 fee?*  → FAQ\n"
        "- *What's the balance on account 4821?*  → tool\n"
        "- *I want a \\$120 refund.*  → escalate\n"
        "- *...and what was my last transaction?*  → uses session memory"
    )
    st.divider()
    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.pop("history", None)
        if "bot" in st.session_state:
            st.session_state.bot.reset()
        st.rerun()

    if st.session_state.get("bot") and st.session_state.bot.last_account_id:
        st.info(f"🧠 Remembering account **{st.session_state.bot.last_account_id}** "
                f"this session.")

# --------------------------------------------------------------------------- #
# Guard: API key required
# --------------------------------------------------------------------------- #
if not OPENAI_API_KEY:
    st.error(
        "**OPENAI_API_KEY is not set.** Copy `.env.example` to `.env` and add "
        "your key (or set it in your deployment's secrets), then reload."
    )
    st.stop()

# --------------------------------------------------------------------------- #
# Init bot + history (persist across reruns)
# --------------------------------------------------------------------------- #
if "bot" not in st.session_state:
    st.session_state.bot = build_triagebot()
if "history" not in st.session_state:
    st.session_state.history = []  # list of {"role", "content", "meta"}

st.title("TriageBot")
st.caption("NimbusPay support · type a message below")

# Replay history
for turn in st.session_state.history:
    with st.chat_message(turn["role"]):
        st.markdown(turn["content"])
        meta = turn.get("meta")
        if meta:
            if meta.get("escalated"):
                st.warning("⚠️ Escalated to a human specialist")
            with st.expander("🔎 How TriageBot handled this"):
                st.markdown(f"**Branch:** `{meta.get('route', '?')}` — "
                            f"{meta.get('route_reason', '')}")
                for c in meta.get("tool_calls", []):
                    st.markdown(f"- 🛠️ `{c['name']}` → {c['args']}")
                if meta.get("redo_count"):
                    st.markdown(f"- 🔁 Self-review redone "
                                f"**{meta['redo_count']}** time(s)")

# --------------------------------------------------------------------------- #
# Chat input
# --------------------------------------------------------------------------- #
prompt = st.chat_input("Ask about fees, your balance, a refund…")
if prompt:
    st.session_state.history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        bot = st.session_state.bot
        # Run the graph once (routing + tools + reviewed reply), then stream the
        # validated text token-by-token for a live typing effect.
        result = bot.respond(prompt)
        placeholder = st.empty()
        streamed = ""
        import re as _re
        for token in _re.findall(r"\S+\s*", result.get("final_reply", "")):
            streamed += token
            placeholder.markdown(streamed + "▌")
        placeholder.markdown(streamed)

        if result.get("escalated"):
            st.warning("⚠️ Escalated to a human specialist")
        with st.expander("🔎 How TriageBot handled this"):
            st.markdown(f"**Branch:** `{result.get('route', '?')}` — "
                        f"{result.get('route_reason', '')}")
            for c in result.get("tool_calls", []):
                st.markdown(f"- 🛠️ `{c['name']}` → {c['args']}")
            if result.get("redo_count"):
                st.markdown(f"- 🔁 Self-review redone "
                            f"**{result['redo_count']}** time(s)")

    st.session_state.history.append({
        "role": "assistant",
        "content": result.get("final_reply", ""),
        "meta": {
            "route": result.get("route"),
            "route_reason": result.get("route_reason"),
            "tool_calls": result.get("tool_calls", []),
            "redo_count": result.get("redo_count", 0),
            "escalated": result.get("escalated", False),
        },
    })
