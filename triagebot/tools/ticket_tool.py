"""Open ticket tool (bonus 4th tool).

Files a lightweight support ticket by appending it to a local JSONL file. In a
real system this would call a ticketing API (Zendesk, Jira Service Management,
etc.); here it is a safe, inspectable stand-in for the activity.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from langchain_core.tools import tool

# Tickets are written next to the project root so they are easy to inspect and
# are git-ignored (see .gitignore).
TICKETS_PATH = Path(__file__).resolve().parents[2] / "tickets.jsonl"


@tool
def open_ticket(summary: str, account_id: str = "unknown") -> str:
    """Open a support ticket for a human specialist to follow up on.

    Use this when a request must be escalated (for example an over-cap refund,
    a frozen account, or anything the bot cannot safely resolve). Provide a
    short summary of the issue and the customer's account id if known. Returns
    the new ticket id.
    """
    ticket_id = f"TKT-{uuid.uuid4().hex[:8].upper()}"
    record = {
        "ticket_id": ticket_id,
        "account_id": str(account_id),
        "summary": summary,
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(TICKETS_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")

    return (
        f"Ticket {ticket_id} opened for account {account_id}. A human specialist "
        f"will review: {summary}"
    )
