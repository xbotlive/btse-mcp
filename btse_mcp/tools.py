"""
MCP tool definitions.

Each tool maps directly to a BTSEClient method (or a composite of several).
All tools accept an optional `account_id` parameter (default: "default").

Tool naming convention
----------------------
btse_<action>_<resource>          — 1:1 API wrapper
btse_<noun>_snapshot / summary    — composite tool (multiple API calls)
btse_safe_<action>                — composite tool with safety checks

Note on client caching
----------------------
BTSEClient instances are cached per account_id for the lifetime of the MCP
server process. If you reconfigure an account (btse-mcp config), restart the
MCP server (restart Claude Desktop / Cursor) to pick up the new credentials.
"""

import json
from typing import Any

from mcp.server import Server
from mcp.types import Tool, TextContent

from btse_mcp.client import BTSEClient
from btse_mcp.config import load_account

app = Server("btse-mcp")

# Cache clients per account_id for the lifetime of the server process.
_clients: dict[str, BTSEClient] = {}


def _get_client(account_id: str) -> BTSEClient:
    if account_id not in _clients:
        acc = load_account(account_id)
        if not acc:
            raise ValueError(
                f"Account '{account_id}' is not configured. "
                f"Run: btse-mcp config --account-id {account_id}"
            )
        _clients[account_id] = BTSEClient(
            api_key=acc["api_key"],
            api_secret=acc["api_secret"],
            testnet=acc.get("testnet", False),
        )
    return _clients[account_id]


def _ok(data: Any) -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps(data, indent=2))]


def _err(msg: str) -> list[TextContent]:
    return [TextContent(type="text", text=f"Error: {msg}")]


# ── Input validation ──────────────────────────────────────────────────────────

class ValidationError(Exception):
    pass


def _validate_create_order(args: dict) -> None:
    """Validate create_order arguments before sending to the API."""
    side       = str(args.get("side", "")).upper()
    order_type = str(args.get("order_type", "")).upper()
    size       = args.get("size")

    if side not in ("BUY", "SELL"):
        raise ValidationError(f"side must be BUY or SELL, got: {args.get('side')!r}")

    if size is None or float(size) <= 0:
        raise ValidationError(f"size must be a positive number, got: {size!r}")

    if order_type == "LIMIT" and args.get("price") is None:
        raise ValidationError("price is required for LIMIT orders")

    if order_type == "OCO":
        if args.get("take_profit_price") is None:
            raise ValidationError("take_profit_price is required for OCO orders")
        if args.get("stop_loss_price") is None:
            raise ValidationError("stop_loss_price is required for OCO orders")


def _validate_amend_order(args: dict) -> None:
    """Validate amend_order arguments before sending to the API."""
    amend_type = str(args.get("amend_type", "")).upper()
    valid_types = {"PRICE", "SIZE", "TRIGGERPRICE", "ALL"}

    if amend_type not in valid_types:
        raise ValidationError(f"amend_type must be one of {valid_types}, got: {args.get('amend_type')!r}")

    if amend_type == "ALL":
        has_any = any(
            args.get(k) is not None
            for k in ("order_price", "order_size", "trigger_price")
        )
        if not has_any:
            raise ValidationError(
                "amend_type ALL requires at least one of: order_price, order_size, trigger_price"
            )

    if amend_type == "PRICE" and args.get("value") is None and args.get("order_price") is None:
        raise ValidationError("PRICE amendment requires value or order_price")

    if amend_type == "SIZE" and args.get("value") is None and args.get("order_size") is None:
        raise ValidationError("SIZE amendment requires value or order_size")

    if amend_type == "TRIGGERPRICE" and args.get("trigger_price") is None and args.get("value") is None:
        raise ValidationError("TRIGGERPRICE amendment requires trigger_price or value")


def _validate_set_leverage(args: dict) -> None:
    leverage = args.get("leverage")
    if leverage is None:
        raise ValidationError("leverage is required")
    leverage = float(leverage)
    if leverage < 0:
        raise ValidationError("leverage must be >= 0 (use 0 for max cross)")
    if leverage > 100:
        raise ValidationError(
            f"leverage {leverage}x seems dangerously high — max supported by BTSE is 100x. "
            "Please confirm you intended this value."
        )


# ── Tool definitions ──────────────────────────────────────────────────────────

TOOLS: list[Tool] = [

    # ── Market data ───────────────────────────────────────────────────────────

    Tool(
        name="btse_get_market_summary",
        description=(
            "Get market summary for one or all BTSE futures markets. "
            "Returns price, volume, funding rate, open interest, contract details."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "default": "default", "description": "Account to use"},
                "symbol":     {"type": "string", "description": "e.g. BTC-PERP — omit for all markets"},
            },
        },
    ),

    Tool(
        name="btse_get_price",
        description="Get mark price, index price, and last traded price for a symbol.",
        inputSchema={
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "default": "default"},
                "symbol":     {"type": "string", "description": "e.g. BTC-PERP — omit for all"},
            },
        },
    ),

    Tool(
        name="btse_get_orderbook",
        description="Get L2 orderbook snapshot (buy and sell quotes at each price level).",
        inputSchema={
            "type": "object",
            "required": ["symbol"],
            "properties": {
                "account_id": {"type": "string", "default": "default"},
                "symbol":     {"type": "string", "description": "e.g. BTC-PERP"},
                "depth":      {"type": "integer", "description": "Number of levels each side"},
            },
        },
    ),

    Tool(
        name="btse_get_trades",
        description="Get recent public trade fills for a market.",
        inputSchema={
            "type": "object",
            "required": ["symbol"],
            "properties": {
                "account_id": {"type": "string", "default": "default"},
                "symbol":     {"type": "string"},
                "count":      {"type": "integer", "default": 20, "description": "Number of trades to return"},
            },
        },
    ),

    Tool(
        name="btse_get_ohlcv",
        description="Get OHLCV (candlestick) data for a market.",
        inputSchema={
            "type": "object",
            "required": ["symbol", "resolution"],
            "properties": {
                "account_id": {"type": "string", "default": "default"},
                "symbol":     {"type": "string"},
                "resolution": {
                    "type": "string",
                    "description": "Candle size: 1 | 5 | 15 | 30 | 60 | 240 | 360 | 1440 | 10080 | 43200",
                },
                "start": {"type": "integer", "description": "Start time in milliseconds"},
                "end":   {"type": "integer", "description": "End time in milliseconds"},
            },
        },
    ),

    Tool(
        name="btse_get_funding_history",
        description="Get historical funding rates for a perpetual market.",
        inputSchema={
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "default": "default"},
                "symbol":     {"type": "string", "description": "e.g. BTC-PERP — omit for all"},
                "count":      {"type": "integer", "default": 10},
            },
        },
    ),

    # ── Account ───────────────────────────────────────────────────────────────

    Tool(
        name="btse_get_wallet_balance",
        description="Get futures wallet balance.",
        inputSchema={
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "default": "default"},
                "wallet":     {"type": "string", "description": "Specific wallet name (optional)"},
            },
        },
    ),

    Tool(
        name="btse_get_wallet_history",
        description="Get wallet transaction history (deposits, withdrawals, PnL).",
        inputSchema={
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "default": "default"},
                "symbol":     {"type": "string", "description": "Filter by market (optional)"},
                "count":      {"type": "integer", "default": 20},
            },
        },
    ),

    Tool(
        name="btse_get_positions",
        description="Get all open futures positions, or for a specific symbol.",
        inputSchema={
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "default": "default"},
                "symbol":     {"type": "string", "description": "e.g. BTC-PERP — omit for all"},
            },
        },
    ),

    Tool(
        name="btse_get_account_fees",
        description="Get maker and taker fee rates.",
        inputSchema={
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "default": "default"},
                "symbol":     {"type": "string", "description": "Specific market (optional)"},
            },
        },
    ),

    Tool(
        name="btse_get_leverage",
        description="Get current leverage and margin mode for a market.",
        inputSchema={
            "type": "object",
            "required": ["symbol"],
            "properties": {
                "account_id": {"type": "string", "default": "default"},
                "symbol":     {"type": "string"},
            },
        },
    ),

    # ── Orders ────────────────────────────────────────────────────────────────

    Tool(
        name="btse_create_order",
        description=(
            "Place a futures order. Supports LIMIT, MARKET, and OCO types. "
            "Optional take-profit and stop-loss can be attached. "
            "Size is in contract units. "
            "IMPORTANT: LIMIT requires price. OCO requires both take_profit_price and stop_loss_price."
        ),
        inputSchema={
            "type": "object",
            "required": ["symbol", "side", "order_type", "size"],
            "properties": {
                "account_id":        {"type": "string", "default": "default"},
                "symbol":            {"type": "string", "description": "e.g. BTC-PERP"},
                "side":              {"type": "string", "enum": ["BUY", "SELL"]},
                "order_type":        {"type": "string", "enum": ["LIMIT", "MARKET", "OCO"]},
                "size":              {"type": "number", "description": "Order size in contracts (must be > 0)"},
                "price":             {"type": "number", "description": "Limit price — required for LIMIT orders"},
                "time_in_force":     {"type": "string", "default": "GTC",
                                      "description": "GTC | IOC | FOK | DAY | WEEK | MONTH"},
                "post_only":         {"type": "boolean", "default": False},
                "reduce_only":       {"type": "boolean", "default": False},
                "cl_order_id":       {"type": "string", "description": "Optional custom order ID"},
                "tx_type":           {"type": "string", "description": "TRIGGER | STOP | LIMIT"},
                "trigger_price":     {"type": "number", "description": "Required for STOP and TRIGGER orders"},
                "take_profit_price": {"type": "number", "description": "OCO: TP trigger price"},
                "stop_loss_price":   {"type": "number", "description": "OCO: SL trigger price"},
            },
        },
    ),

    Tool(
        name="btse_cancel_order",
        description=(
            "Cancel a specific order by order_id or cl_order_id. "
            "If neither is provided, cancels ALL open orders for the symbol."
        ),
        inputSchema={
            "type": "object",
            "required": ["symbol"],
            "properties": {
                "account_id":  {"type": "string", "default": "default"},
                "symbol":      {"type": "string"},
                "order_id":    {"type": "string", "description": "Internal BTSE order ID"},
                "cl_order_id": {"type": "string", "description": "Your custom order ID"},
            },
        },
    ),

    Tool(
        name="btse_get_open_orders",
        description="List all open (unmatched) orders, optionally filtered by symbol.",
        inputSchema={
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "default": "default"},
                "symbol":     {"type": "string", "description": "Filter by market (optional)"},
            },
        },
    ),

    Tool(
        name="btse_get_order",
        description="Get details of a specific order. Requires order_id or cl_order_id.",
        inputSchema={
            "type": "object",
            "properties": {
                "account_id":  {"type": "string", "default": "default"},
                "order_id":    {"type": "string", "description": "Internal BTSE order ID"},
                "cl_order_id": {"type": "string", "description": "Your custom order ID"},
            },
        },
    ),

    Tool(
        name="btse_get_trade_history",
        description="Get your personal trade fill history.",
        inputSchema={
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "default": "default"},
                "symbol":     {"type": "string", "description": "Filter by market (optional)"},
                "count":      {"type": "integer", "default": 20},
            },
        },
    ),

    Tool(
        name="btse_amend_order",
        description=(
            "Amend an existing order. "
            "ALL requires at least one of order_price, order_size, trigger_price. "
            "PRICE/SIZE requires value. TRIGGERPRICE requires trigger_price."
        ),
        inputSchema={
            "type": "object",
            "required": ["symbol", "order_id", "amend_type"],
            "properties": {
                "account_id":    {"type": "string", "default": "default"},
                "symbol":        {"type": "string"},
                "order_id":      {"type": "string"},
                "amend_type":    {
                    "type": "string",
                    "enum": ["PRICE", "SIZE", "TRIGGERPRICE", "ALL"],
                },
                "value":         {"type": "number", "description": "New value for PRICE or SIZE"},
                "order_price":   {"type": "number", "description": "For amend_type ALL"},
                "order_size":    {"type": "number", "description": "For amend_type ALL"},
                "trigger_price": {"type": "number", "description": "For amend_type ALL or TRIGGERPRICE"},
            },
        },
    ),

    Tool(
        name="btse_close_position",
        description="Close an open position at market price or a specified limit price.",
        inputSchema={
            "type": "object",
            "required": ["symbol"],
            "properties": {
                "account_id": {"type": "string", "default": "default"},
                "symbol":     {"type": "string"},
                "close_type": {"type": "string", "enum": ["MARKET", "LIMIT"], "default": "MARKET"},
                "price":      {"type": "number", "description": "Required when close_type is LIMIT"},
            },
        },
    ),

    # ── Risk / leverage ───────────────────────────────────────────────────────

    Tool(
        name="btse_set_leverage",
        description=(
            "Set leverage for a market. Use leverage=0 for maximum cross leverage. "
            "Warning: values above 20x carry significant liquidation risk."
        ),
        inputSchema={
            "type": "object",
            "required": ["symbol", "leverage"],
            "properties": {
                "account_id":  {"type": "string", "default": "default"},
                "symbol":      {"type": "string"},
                "leverage":    {"type": "number", "description": "Leverage multiplier (0 = max cross, max 100)"},
                "margin_mode": {"type": "string", "enum": ["ISOLATED", "CROSS"], "default": "ISOLATED"},
            },
        },
    ),

    Tool(
        name="btse_get_risk_limit",
        description="Get the current risk limit tier for a market.",
        inputSchema={
            "type": "object",
            "required": ["symbol"],
            "properties": {
                "account_id": {"type": "string", "default": "default"},
                "symbol":     {"type": "string"},
            },
        },
    ),

    Tool(
        name="btse_set_risk_limit",
        description="Set the risk limit tier for a market.",
        inputSchema={
            "type": "object",
            "required": ["symbol", "risk_limit_level"],
            "properties": {
                "account_id":       {"type": "string", "default": "default"},
                "symbol":           {"type": "string"},
                "risk_limit_level": {"type": "integer", "description": "Risk limit tier (e.g. 1, 2, 3)"},
            },
        },
    ),

    # ── Composite tools ───────────────────────────────────────────────────────

    Tool(
        name="btse_market_snapshot",
        description=(
            "Single-call market snapshot combining price, orderbook, and recent funding rates. "
            "Use this instead of calling btse_get_price + btse_get_orderbook + btse_get_funding_history separately. "
            "Returns: current prices, best bid/ask spread, last 5 funding rates."
        ),
        inputSchema={
            "type": "object",
            "required": ["symbol"],
            "properties": {
                "account_id":    {"type": "string", "default": "default"},
                "symbol":        {"type": "string", "description": "e.g. BTC-PERP"},
                "orderbook_depth": {"type": "integer", "default": 5, "description": "Orderbook levels per side"},
                "funding_count":   {"type": "integer", "default": 5, "description": "Number of past funding periods"},
            },
        },
    ),

    Tool(
        name="btse_account_overview",
        description=(
            "Single-call account overview combining wallet balance, open positions, and open orders. "
            "Use this before placing any order to understand current exposure. "
            "Equivalent to calling btse_get_wallet_balance + btse_get_positions + btse_get_open_orders."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "default": "default"},
                "symbol":     {"type": "string", "description": "Filter positions/orders by symbol (optional)"},
            },
        },
    ),

    Tool(
        name="btse_safe_market_order",
        description=(
            "Place a MARKET order with a slippage safety check. "
            "Fetches the current mark price first, then refuses to submit if the last price "
            "has moved more than `max_slippage_pct` percent from the provided `expected_price`. "
            "Use this instead of btse_create_order for market orders to avoid bad fills."
        ),
        inputSchema={
            "type": "object",
            "required": ["symbol", "side", "size", "expected_price"],
            "properties": {
                "account_id":      {"type": "string", "default": "default"},
                "symbol":          {"type": "string", "description": "e.g. BTC-PERP"},
                "side":            {"type": "string", "enum": ["BUY", "SELL"]},
                "size":            {"type": "number", "description": "Order size in contracts (must be > 0)"},
                "expected_price":  {"type": "number",
                                    "description": "Price you expect to fill near. Order aborts if market has moved more than max_slippage_pct from this."},
                "max_slippage_pct":{"type": "number", "default": 0.5,
                                    "description": "Maximum acceptable slippage in percent (default 0.5%)"},
                "reduce_only":     {"type": "boolean", "default": False},
            },
        },
    ),
]


# ── MCP handler registration ──────────────────────────────────────────────────

@app.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    account_id = arguments.get("account_id", "default")

    try:
        client = _get_client(account_id)
    except ValueError as e:
        return _err(str(e))

    try:
        match name:

            # ── Market data ───────────────────────────────────────────────────

            case "btse_get_market_summary":
                return _ok(client.get_market_summary(arguments.get("symbol")))

            case "btse_get_price":
                return _ok(client.get_price(arguments.get("symbol")))

            case "btse_get_orderbook":
                return _ok(client.get_orderbook(
                    arguments["symbol"],
                    arguments.get("depth"),
                ))

            case "btse_get_trades":
                return _ok(client.get_trades(
                    arguments["symbol"],
                    arguments.get("count", 20),
                ))

            case "btse_get_ohlcv":
                return _ok(client.get_ohlcv(
                    arguments["symbol"],
                    arguments["resolution"],
                    arguments.get("start"),
                    arguments.get("end"),
                ))

            case "btse_get_funding_history":
                return _ok(client.get_funding_history(
                    arguments.get("symbol"),
                    arguments.get("count", 10),
                ))

            # ── Account ───────────────────────────────────────────────────────

            case "btse_get_wallet_balance":
                return _ok(client.get_wallet_balance(arguments.get("wallet")))

            case "btse_get_wallet_history":
                return _ok(client.get_wallet_history(
                    arguments.get("symbol"),
                    arguments.get("count", 20),
                ))

            case "btse_get_positions":
                return _ok(client.get_positions(arguments.get("symbol")))

            case "btse_get_account_fees":
                return _ok(client.get_account_fees(arguments.get("symbol")))

            case "btse_get_leverage":
                return _ok(client.get_leverage(arguments["symbol"]))

            # ── Orders ────────────────────────────────────────────────────────

            case "btse_create_order":
                _validate_create_order(arguments)
                return _ok(client.create_order(
                    symbol=arguments["symbol"],
                    side=arguments["side"],
                    order_type=arguments["order_type"],
                    size=arguments["size"],
                    price=arguments.get("price"),
                    time_in_force=arguments.get("time_in_force", "GTC"),
                    post_only=arguments.get("post_only", False),
                    reduce_only=arguments.get("reduce_only", False),
                    cl_order_id=arguments.get("cl_order_id"),
                    tx_type=arguments.get("tx_type"),
                    trigger_price=arguments.get("trigger_price"),
                    take_profit_price=arguments.get("take_profit_price"),
                    stop_loss_price=arguments.get("stop_loss_price"),
                ))

            case "btse_cancel_order":
                return _ok(client.cancel_order(
                    arguments["symbol"],
                    arguments.get("order_id"),
                    arguments.get("cl_order_id"),
                ))

            case "btse_get_open_orders":
                return _ok(client.get_open_orders(arguments.get("symbol")))

            case "btse_get_order":
                return _ok(client.get_order(
                    arguments.get("order_id"),
                    arguments.get("cl_order_id"),
                ))

            case "btse_get_trade_history":
                return _ok(client.get_trade_history(
                    arguments.get("symbol"),
                    arguments.get("count", 20),
                ))

            case "btse_amend_order":
                _validate_amend_order(arguments)
                return _ok(client.amend_order(
                    arguments["symbol"],
                    arguments["order_id"],
                    arguments["amend_type"],
                    arguments.get("value"),
                    arguments.get("order_price"),
                    arguments.get("order_size"),
                    arguments.get("trigger_price"),
                ))

            case "btse_close_position":
                return _ok(client.close_position(
                    arguments["symbol"],
                    arguments.get("close_type", "MARKET"),
                    arguments.get("price"),
                ))

            # ── Risk / leverage ───────────────────────────────────────────────

            case "btse_set_leverage":
                _validate_set_leverage(arguments)
                return _ok(client.set_leverage(
                    arguments["symbol"],
                    arguments["leverage"],
                    arguments.get("margin_mode", "ISOLATED"),
                ))

            case "btse_get_risk_limit":
                return _ok(client.get_risk_limit(arguments["symbol"]))

            case "btse_set_risk_limit":
                return _ok(client.set_risk_limit(
                    arguments["symbol"],
                    arguments["risk_limit_level"],
                ))

            # ── Composite tools ───────────────────────────────────────────────

            case "btse_market_snapshot":
                symbol         = arguments["symbol"]
                orderbook_depth = arguments.get("orderbook_depth", 5)
                funding_count   = arguments.get("funding_count", 5)
                snapshot = {
                    "price":          client.get_price(symbol),
                    "orderbook":      client.get_orderbook(symbol, depth=orderbook_depth),
                    "funding_history": client.get_funding_history(symbol, count=funding_count),
                }
                return _ok(snapshot)

            case "btse_account_overview":
                symbol   = arguments.get("symbol")
                overview = {
                    "wallet":      client.get_wallet_balance(),
                    "positions":   client.get_positions(symbol),
                    "open_orders": client.get_open_orders(symbol),
                }
                return _ok(overview)

            case "btse_safe_market_order":
                symbol          = arguments["symbol"]
                side            = str(arguments["side"]).upper()
                size            = arguments["size"]
                expected_price  = float(arguments["expected_price"])
                max_slippage    = float(arguments.get("max_slippage_pct", 0.5))
                reduce_only     = arguments.get("reduce_only", False)

                # Basic validation first
                if side not in ("BUY", "SELL"):
                    return _err(f"side must be BUY or SELL, got: {side!r}")
                if float(size) <= 0:
                    return _err(f"size must be > 0, got: {size}")

                # Fetch current price
                price_data  = client.get_price(symbol)
                if not price_data or not isinstance(price_data, list):
                    return _err(f"Could not fetch current price for {symbol}")
                last_price = float(price_data[0].get("lastPrice", 0))
                if last_price == 0:
                    return _err(f"Received invalid last price 0 for {symbol} — aborting")

                # Slippage check
                slippage_pct = abs(last_price - expected_price) / expected_price * 100
                if slippage_pct > max_slippage:
                    return _err(
                        f"Slippage check failed: current price {last_price} is {slippage_pct:.2f}% "
                        f"away from your expected price {expected_price} "
                        f"(max allowed: {max_slippage}%). Order NOT submitted."
                    )

                # Place the order
                result = client.create_order(
                    symbol=symbol,
                    side=side,
                    order_type="MARKET",
                    size=size,
                    reduce_only=reduce_only,
                )
                return _ok({
                    "slippage_check": {
                        "expected_price":  expected_price,
                        "last_price":      last_price,
                        "slippage_pct":    round(slippage_pct, 4),
                        "max_slippage_pct": max_slippage,
                        "passed":          True,
                    },
                    "order": result,
                })

            case _:
                return _err(f"Unknown tool: {name}")

    except ValidationError as e:
        return _err(f"Validation error: {e}")
    except Exception as e:
        return _err(str(e))
