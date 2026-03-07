"""
MCP Resource definitions.

Resources are read-only data sources that MCP clients can list and read.
Unlike tools (which perform actions), resources represent state — they are
safe to call repeatedly and can be subscribed to for live updates.

Available resources
-------------------
btse://markets                      — all active futures markets
btse://price/{symbol}               — live price for one symbol
btse://account/{account_id}/summary — wallet balance + position snapshot
"""

from typing import Any

from mcp.types import Resource, TextContent

from btse_mcp.client import BTSEClient
from btse_mcp.config import load_account

import json


# ── Resource registry ─────────────────────────────────────────────────────────

def list_resources() -> list[Resource]:
    """Return the static list of available resources."""
    return [
        Resource(
            uri="btse://markets",
            name="BTSE Futures Markets",
            description="All active BTSE futures markets with contract details and current prices.",
            mimeType="application/json",
        ),
        Resource(
            uri="btse://price/BTC-PERP",
            name="BTC-PERP Live Price",
            description=(
                "Live mark price, index price, and last traded price for BTC-PERP. "
                "Replace 'BTC-PERP' in the URI with any valid symbol."
            ),
            mimeType="application/json",
        ),
        Resource(
            uri="btse://account/default/summary",
            name="Account Summary",
            description=(
                "Wallet balance and open positions for the default account. "
                "Replace 'default' with any configured account_id."
            ),
            mimeType="application/json",
        ),
    ]


# ── Resource fetchers ─────────────────────────────────────────────────────────

def _get_client(account_id: str = "default") -> BTSEClient:
    acc = load_account(account_id)
    if not acc:
        raise ValueError(
            f"Account '{account_id}' is not configured. "
            f"Run: btse-mcp config --account-id {account_id}"
        )
    return BTSEClient(
        api_key=acc["api_key"],
        api_secret=acc["api_secret"],
        testnet=acc.get("testnet", False),
    )


def _fmt(data: Any) -> str:
    return json.dumps(data, indent=2)


def read_resource(uri: str) -> list[TextContent]:
    """
    Dispatch a resource URI to the correct fetcher.

    URI patterns
    ------------
    btse://markets
    btse://price/<symbol>
    btse://account/<account_id>/summary
    """
    # Strip scheme
    if not uri.startswith("btse://"):
        raise ValueError(f"Unknown resource URI scheme: {uri}")
    path = uri[len("btse://"):]   # e.g. "markets", "price/BTC-PERP", "account/default/summary"
    parts = path.split("/")

    # btse://markets
    if parts[0] == "markets":
        client = _get_client()
        data   = client.get_market_summary()
        return [TextContent(type="text", text=_fmt(data))]

    # btse://price/<symbol>
    if parts[0] == "price" and len(parts) == 2:
        symbol = parts[1]
        client = _get_client()
        data   = client.get_price(symbol)
        return [TextContent(type="text", text=_fmt(data))]

    # btse://account/<account_id>/summary
    if parts[0] == "account" and len(parts) == 3 and parts[2] == "summary":
        account_id = parts[1]
        client     = _get_client(account_id)
        summary    = {
            "wallet":     client.get_wallet_balance(),
            "positions":  client.get_positions(),
        }
        return [TextContent(type="text", text=_fmt(summary))]

    raise ValueError(f"Unknown resource URI: {uri}")
