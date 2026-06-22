"""Account lookup tool.

Looks up a customer account in the synthetic accounts table by account id.
Only the provided synthetic data is used - there are no real accounts.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import List, Optional

from langchain_core.tools import tool

from ..config import ACCOUNTS_PATH


@lru_cache(maxsize=1)
def _load_accounts() -> List[dict]:
    with open(ACCOUNTS_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def find_account(account_id: str) -> Optional[dict]:
    """Return the raw account dict for ``account_id`` or ``None``."""
    account_id = str(account_id).strip()
    for acct in _load_accounts():
        if acct["account_id"] == account_id:
            return acct
    return None


@tool
def account_lookup(account_id: str) -> str:
    """Look up a NimbusPay customer account by its numeric account id
    (for example "4821").

    Use this when a customer asks about their balance, status, or last
    transaction. Returns the account holder's name, balance, status, and most
    recent transaction. If the id is not found, says so.
    """
    # Be forgiving: pull the first run of digits out of whatever was passed.
    match = re.search(r"\d{3,}", str(account_id))
    cleaned = match.group(0) if match else str(account_id).strip()

    acct = find_account(cleaned)
    if acct is None:
        return (
            f"No account found with id '{cleaned}'. Ask the customer to confirm "
            f"their account number."
        )

    txn = acct["last_transaction"]
    return (
        f"Account {acct['account_id']} - {acct['name']} ({acct['email']})\n"
        f"Status: {acct['status']}\n"
        f"Balance: {acct['balance']:.2f} {acct['currency']}\n"
        f"Last transaction: {txn['date']} | {txn['description']} | "
        f"{txn['amount']:.2f} {acct['currency']}"
    )
