"""Central configuration for TriageBot.

All secrets (the OpenAI API key) are read from environment variables and are
*never* hard-coded. Copy ``.env.example`` to ``.env`` and fill it in, or export
the variables in your shell / deployment platform.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load variables from a local .env file if present (no-op in production where
# the platform injects real environment variables).
load_dotenv()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PACKAGE_DIR = Path(__file__).resolve().parent
DATA_DIR = PACKAGE_DIR / "data"

FAQ_PATH = DATA_DIR / "faq.json"
ACCOUNTS_PATH = DATA_DIR / "accounts.json"
REFUND_RULES_PATH = DATA_DIR / "refund_rules.json"

# ---------------------------------------------------------------------------
# Model / runtime settings (all from env, with safe defaults)
# ---------------------------------------------------------------------------
MODEL_NAME = os.getenv("TRIAGEBOT_MODEL", "gpt-4o-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")  # optional override

# Cap on self-review redo attempts so the loop can never run forever.
MAX_REDOS = int(os.getenv("TRIAGEBOT_MAX_REDOS", "2"))


def require_api_key() -> str:
    """Return the OpenAI API key or raise a clear, actionable error.

    Kept as a function (instead of failing at import time) so the data tools
    and unit tests can run without a key.
    """
    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Copy .env.example to .env and add your "
            "key, or export OPENAI_API_KEY in your environment."
        )
    return OPENAI_API_KEY
