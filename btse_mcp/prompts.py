"""
MCP Prompt definitions.

Prompts are pre-built message templates the user (or Claude) can invoke
by name. They guide the agent through multi-step workflows and produce
consistent, well-structured outputs.

Available prompts
-----------------
market_overview     — price + funding + spread summary for a symbol
position_review     — all open positions with PnL and risk flags
account_summary     — balance + positions + open orders in one view
place_order_guide   — step-by-step guided order placement with sanity checks
"""

from mcp.types import Prompt, PromptArgument, PromptMessage, TextContent


PROMPTS: list[Prompt] = [

    Prompt(
        name="market_overview",
        description=(
            "Summarise current market conditions for a BTSE futures symbol. "
            "Covers live price, 24h change, funding rate, and orderbook spread."
        ),
        arguments=[
            PromptArgument(
                name="symbol",
                description="Market symbol, e.g. BTC-PERP",
                required=False,
            ),
            PromptArgument(
                name="account_id",
                description="Account to use (default: 'default')",
                required=False,
            ),
        ],
    ),

    Prompt(
        name="position_review",
        description=(
            "Review all open futures positions. "
            "Shows entry price, mark price, unrealised PnL, leverage, and flags "
            "any positions where liquidation price is within 10% of mark price."
        ),
        arguments=[
            PromptArgument(
                name="account_id",
                description="Account to review (default: 'default')",
                required=False,
            ),
        ],
    ),

    Prompt(
        name="account_summary",
        description=(
            "Full account snapshot: wallet balance, open positions, and open orders. "
            "Use this before placing any order to understand current exposure."
        ),
        arguments=[
            PromptArgument(
                name="account_id",
                description="Account to summarise (default: 'default')",
                required=False,
            ),
        ],
    ),

    Prompt(
        name="place_order_guide",
        description=(
            "Interactive guide for placing a futures order safely. "
            "Checks balance, current price, and confirms details before submitting."
        ),
        arguments=[
            PromptArgument(
                name="symbol",
                description="Market symbol, e.g. BTC-PERP",
                required=True,
            ),
            PromptArgument(
                name="side",
                description="BUY or SELL",
                required=True,
            ),
            PromptArgument(
                name="size",
                description="Order size in contracts",
                required=True,
            ),
            PromptArgument(
                name="account_id",
                description="Account to use (default: 'default')",
                required=False,
            ),
        ],
    ),
]


# ── Prompt renderers ──────────────────────────────────────────────────────────
# Each renderer returns the list[PromptMessage] that the MCP server sends back.
# The messages tell Claude exactly what to do — which tools to call, in what
# order, and how to present the results.

def render_market_overview(symbol: str = "BTC-PERP", account_id: str = "default") -> list[PromptMessage]:
    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=f"""Please give me a market overview for {symbol}.

Use these tools in order:
1. btse_get_price         — symbol="{symbol}", account_id="{account_id}"
2. btse_get_market_summary — symbol="{symbol}", account_id="{account_id}"
3. btse_get_funding_history — symbol="{symbol}", count=5, account_id="{account_id}"
4. btse_get_orderbook      — symbol="{symbol}", depth=5, account_id="{account_id}"

Then present a concise summary covering:
- Current last price, mark price, index price
- 24h price change (%) and volume
- Current funding rate and recent trend (last 5 periods)
- Best bid / best ask and the spread (in USD and %)
- Any notable observations (e.g. funding rate unusually high, wide spread)
""",
            ),
        )
    ]


def render_position_review(account_id: str = "default") -> list[PromptMessage]:
    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=f"""Please review all my open futures positions.

Steps:
1. Call btse_get_positions with account_id="{account_id}" to get all positions
2. For each position, call btse_get_price with the position's symbol to get current mark price
3. Call btse_get_leverage for each symbol to confirm leverage in use

Then present a table with these columns:
| Symbol | Side | Size | Entry Price | Mark Price | Unrealised PnL | PnL % | Leverage | Liq. Price | Risk Flag |

Risk Flag rules:
- 🔴 DANGER  — liquidation price within 5% of mark price
- 🟡 WARNING — liquidation price within 10% of mark price
- 🟢 OK      — otherwise

Finish with a one-paragraph summary of total exposure and any recommended actions.
""",
            ),
        )
    ]


def render_account_summary(account_id: str = "default") -> list[PromptMessage]:
    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=f"""Please give me a full account snapshot for account '{account_id}'.

Call these tools in parallel if possible, otherwise in order:
1. btse_get_wallet_balance — account_id="{account_id}"
2. btse_get_positions      — account_id="{account_id}"
3. btse_get_open_orders    — account_id="{account_id}"

Present results in three sections:

**Wallet**
- Available balance, total balance, unrealised PnL

**Open Positions**
- Symbol, side, size, entry price, mark price, unrealised PnL, leverage

**Open Orders**
- Symbol, side, type, size, price, status

End with a one-line summary: total capital at risk as a % of wallet balance.
""",
            ),
        )
    ]


def render_place_order_guide(
    symbol: str,
    side: str,
    size: str,
    account_id: str = "default",
) -> list[PromptMessage]:
    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=f"""I want to place a {side} order for {size} contracts of {symbol}.
Account: {account_id}

Please guide me through this safely:

**Step 1 — Pre-flight checks**
Call btse_account_summary prompt (or manually call btse_get_wallet_balance and btse_get_positions)
to confirm I have sufficient balance and this order won't push me over safe exposure limits.

**Step 2 — Market check**
Call btse_get_price for symbol="{symbol}", account_id="{account_id}"
Show me the current last price, mark price, and spread.

**Step 3 — Confirm order details**
Present the order I'm about to place:
- Symbol  : {symbol}
- Side    : {side}
- Size    : {size} contracts
- Type    : (ask me: LIMIT or MARKET?)
- Price   : (ask me if LIMIT)
- Est. value at current price

Ask me to confirm before proceeding.

**Step 4 — Place the order**
Only after my explicit confirmation, call btse_create_order with the agreed parameters.
Show the full response from BTSE including the order ID.

**Step 5 — Verify**
Call btse_get_order with the returned order ID to confirm it is live.
""",
            ),
        )
    ]


# ── Dispatch ──────────────────────────────────────────────────────────────────

def render_prompt(name: str, arguments: dict) -> list[PromptMessage]:
    """Route a prompt name + arguments to the correct renderer."""
    match name:
        case "market_overview":
            return render_market_overview(
                symbol=arguments.get("symbol", "BTC-PERP"),
                account_id=arguments.get("account_id", "default"),
            )
        case "position_review":
            return render_position_review(
                account_id=arguments.get("account_id", "default"),
            )
        case "account_summary":
            return render_account_summary(
                account_id=arguments.get("account_id", "default"),
            )
        case "place_order_guide":
            return render_place_order_guide(
                symbol=arguments["symbol"],
                side=arguments["side"],
                size=arguments["size"],
                account_id=arguments.get("account_id", "default"),
            )
        case _:
            raise ValueError(f"Unknown prompt: {name}")
