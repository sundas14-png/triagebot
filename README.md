# 🛟 TriageBot — a self-reviewing support agent for NimbusPay

TriageBot is a small support agent for **NimbusPay** (a fintech app). Given a
customer message, it decides whether to **answer from a FAQ**, **use a tool**
(look up an account, calculate a refund, open a ticket), or **escalate to a
human**. Before replying, it **reviews its own draft** with an LLM judge and
**redoes it** if the draft breaks a rule — with a hard cap so the loop can never
run forever.

Built with **LangChain** (the model, the prompt, and the tools) and
**LangGraph** (the control flow: state, routing, and the redo loop).

---

## ✨ Features

| Requirement | Where it lives |
|---|---|
| Simple interface (CLI **and** web) | `cli.py`, `streamlit_app.py` |
| At least 3 tools | `triagebot/tools/` — FAQ, account, refund **+ ticket** |
| **Branch** — one real decision point | `router` node in `triagebot/graph/agent.py` |
| **Loop** — review own draft, redo on failure | `draft → review → bump_redo → draft` |
| **Redo cap** so it can't loop forever | `MAX_REDOS` (env `TRIAGEBOT_MAX_REDOS`, default 2) |
| **Escalate** instead of acting on over-cap money moves | `escalate` node + refund-tool guard |
| **Bonus 1** — 4th tool (open a ticket) | `triagebot/tools/ticket_tool.py` |
| **Bonus 2** — remember last account this session | `TriageBot.last_account_id` |
| **Bonus 3** — LLM judges the draft (not a hard-coded rule) | `review` node + `JUDGE_SYSTEM` prompt |
| **Bonus 4** — stream the reply token-by-token | `stream_response()` + Streamlit UI |

### Notes honored
- **API keys via environment variables only** — never hard-coded (`triagebot/config.py`).
- **Synthetic data only** — no real accounts (`triagebot/data/`).
- **Never auto-executes an over-cap refund** — refunds ≥ \$50 always escalate.
- **The redo loop is capped** — after the cap is hit, TriageBot escalates instead of looping.

---

## 🧠 How it works (graph flow)

```
                 ┌─────────┐
   customer ───▶ │ router  │  ← the one real decision point (branch)
                 └────┬────┘
        ┌────────────┼─────────────┐
        ▼            ▼             ▼
     ┌─────┐     ┌──────┐     ┌──────────┐
     │ faq │     │ tool │     │ escalate │   tool = account_lookup /
     └──┬──┘     └──┬───┘     └────┬─────┘          refund_calculator /
        └───────────┼──────────────┘                open_ticket
                    ▼
                ┌───────┐
        ┌──────▶│ draft │  ← writes a candidate reply (LangChain prompt+model)
        │       └───┬───┘
        │           ▼
        │       ┌────────┐
        │       │ review │  ← LLM judge: pass / fail  (bonus #3)
        │       └───┬────┘
   fail & redos     │ pass  OR  redo cap hit
   remaining        ▼
   (bump_redo)  ┌──────────┐
        └───────│ finalize │ ← if review never passed → escalate safely
                └────┬─────┘
                     ▼
                    END
```

- **Branch (router):** an LLM classifies each message into `faq`, `tool`, or
  `escalate`. This is the single required decision point.
- **Tools:** on the `tool` branch the model picks and calls the right tool(s).
  If the refund calculator flags an over-cap amount, the turn is escalated and a
  ticket is filed — money is **never** auto-moved.
- **Self-review loop:** the drafter writes a reply; an LLM **judge** checks it
  against the rules. On failure, the judge's feedback is fed back and the draft
  is redone — up to `MAX_REDOS` times. If it still fails, TriageBot escalates.
- **Session memory:** the last account successfully looked up is remembered, so
  follow-ups like *"and what was my last transaction?"* just work.

---

## 📁 Project structure

```
triagebot/
├── cli.py                     # command-line REPL
├── streamlit_app.py           # web chat UI (token streaming)
├── test_flow.py               # deterministic flow tests (no API key needed)
├── requirements.txt
├── .env.example               # copy to .env and add your key
├── .gitignore
└── triagebot/
    ├── config.py              # env-driven config (API key, model, redo cap)
    ├── data/
    │   ├── faq.json           # ~8 Q&A pairs
    │   ├── accounts.json      # synthetic customers + balances + last txn
    │   └── refund_rules.json  # under $50 auto / $50+ escalate
    ├── tools/
    │   ├── faq_tool.py
    │   ├── account_tool.py
    │   ├── refund_tool.py
    │   └── ticket_tool.py     # bonus 4th tool
    └── graph/
        ├── state.py           # shared LangGraph state
        ├── llm.py             # ChatOpenAI factory (env-driven)
        ├── prompts.py         # router / drafter / judge prompts
        └── agent.py           # the LangGraph + TriageBot class
```

---

## 🚀 Setup & run locally

### 1. Install
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure your key
```bash
cp .env.example .env
# edit .env and set OPENAI_API_KEY=sk-...
```

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `OPENAI_API_KEY` | ✅ | — | Your OpenAI API key |
| `TRIAGEBOT_MODEL` | ❌ | `gpt-4o-mini` | Chat model for agent + judge |
| `OPENAI_BASE_URL` | ❌ | OpenAI default | Override endpoint (Azure/proxy) |
| `TRIAGEBOT_MAX_REDOS` | ❌ | `2` | Cap on self-review redo attempts |

### 3. Run the web app (recommended for the demo)
```bash
streamlit run streamlit_app.py
```
Then open the URL Streamlit prints (default <http://localhost:8501>).

### 4. Or run the CLI
```bash
python cli.py
```

### 5. Run the flow tests (no API key needed)
```bash
python test_flow.py
```

---

## 🎬 Demo script (2 minutes)

Try these messages in order to show every required behavior:

1. **FAQ branch:** `Why was I charged a $2 fee?`
2. **Tool branch + memory:** `What's the balance on account 4821?`
3. **Memory follow-up:** `And what was my last transaction?`
4. **Auto-eligible refund:** `Can I get a $30 refund?`
5. **Escalation (over-cap):** `I want a $120 refund.` → *escalates to a human*, files a ticket, **does not** move money.

The Streamlit "🔎 How TriageBot handled this" expander shows the branch chosen,
the tools called, and how many times the self-review loop fired.

---

## ☁️ Deploy for a live URL

**Streamlit Community Cloud (free, easiest):**
1. Push this repo to GitHub.
2. Go to <https://share.streamlit.io>, sign in, and pick this repo.
3. Set the main file to `streamlit_app.py`.
4. In **Advanced settings → Secrets**, add:
   ```toml
   OPENAI_API_KEY = "sk-..."
   TRIAGEBOT_MODEL = "gpt-4o-mini"
   ```
5. Deploy — you'll get a public `https://<app>.streamlit.app` URL.

Other options: Hugging Face Spaces (Streamlit SDK), Render, or Railway —
all read the same environment variables. Never commit your real `.env`.

---

## 🛡️ Design defense (the *why*)

- **Why LangChain + LangGraph?** LangChain gives the model, prompt, and a clean
  `@tool` abstraction. LangGraph gives explicit, inspectable **control flow** —
  the branch and the redo loop are real graph edges, not buried `if` statements,
  which makes the agent easy to reason about and demo.
- **What does each do?** LangChain = the *tools and the model*. LangGraph = the
  *branching and the redo loop*.
- **Safety first:** over-cap refunds can never be auto-executed — the refund
  tool flags them, the turn escalates, and a ticket is filed. The LLM judge is a
  second line of defense, and the redo loop is capped so it can't spin forever.
