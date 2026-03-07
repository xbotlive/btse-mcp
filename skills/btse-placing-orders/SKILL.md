---
name: btse-placing-orders
title: "SKILL 4 of 5 — btse-placing-orders"
description: Place, amend, and cancel futures orders on BTSE — including order types, pre-flight checklist, and safe market orders
---

# BTSE Placing Orders

Orders are **irreversible once filled**. Always follow the pre-flight checklist.

---

## Pre-Flight Checklist (Every Order)

1. **Confirm environment** — call `btse_get_price("BTC-PERP")` and check the price is realistic for testnet vs live
2. **Check account** — call `btse_account_overview()` to see balance and existing exposure
3. **State the order to the user** — symbol, side, size, type, price (if limit)
4. **Get explicit confirmation** before calling any order tool
5. **Use the `place_order_guide` prompt** for a fully guided flow

---

## Order Types

| Type | When to use | Required fields |
|---|---|---|
| `MARKET` | Fill immediately at best available price | symbol, side, size |
| `LIMIT` | Fill at a specific price or better | symbol, side, size, price |
| `OCO` | One-Cancels-Other: TP + SL in one order | symbol, side, size, take_profit_price, stop_loss_price |

---

## Placing a Market Order (Safe Method)

**Always prefer this over `btse_create_order` for market orders:**

```
btse_safe_market_order(
  symbol="BTC-PERP",
  side="BUY",
  size=0.01,
  expected_price=85000,   # price you're expecting to fill near
  max_slippage_pct=0.5,   # abort if market has moved more than 0.5%
  reduce_only=False
)
```

If the current price is more than `max_slippage_pct` away from `expected_price`, the order is **not submitted** and an error is returned. Ask the user to confirm the new price before retrying.

---

## Placing a Limit Order

```
btse_create_order(
  symbol="BTC-PERP",
  side="BUY",
  order_type="LIMIT",
  size=0.01,
  price=84000,
  time_in_force="GTC",   # GTC | IOC | FOK | DAY | WEEK | MONTH
  post_only=False,
  reduce_only=False
)
```

---

## Placing an OCO Order

```
btse_create_order(
  symbol="BTC-PERP",
  side="SELL",
  order_type="OCO",
  size=0.01,
  take_profit_price=90000,
  stop_loss_price=80000
)
```

---

## Viewing Orders

```
# All open orders (optionally filter by symbol)
btse_get_open_orders(symbol="BTC-PERP")

# Single order by ID
btse_get_order(order_id="abc123")
btse_get_order(cl_order_id="my-custom-id")

# Trade fill history
btse_get_trade_history(symbol="BTC-PERP", count=20)
```

---

## Amending an Order

```
# Change price only
btse_amend_order(symbol="BTC-PERP", order_id="abc123", amend_type="PRICE", value=83000)

# Change size only
btse_amend_order(symbol="BTC-PERP", order_id="abc123", amend_type="SIZE", value=0.02)

# Change everything at once
btse_amend_order(
  symbol="BTC-PERP",
  order_id="abc123",
  amend_type="ALL",
  order_price=83000,
  order_size=0.02
)
```

`amend_type` options: `PRICE | SIZE | TRIGGERPRICE | ALL`

---

## Cancelling Orders

```
# Cancel one order by ID
btse_cancel_order(symbol="BTC-PERP", order_id="abc123")

# Cancel by custom order ID
btse_cancel_order(symbol="BTC-PERP", cl_order_id="my-custom-id")

# Cancel ALL open orders for a symbol
btse_cancel_order(symbol="BTC-PERP")
```

⚠️ Cancelling without an order ID cancels **all** open orders for the symbol. Confirm with the user first.

---

## Minimum Contract Sizes

| Symbol | Min size | Tick size |
|---|---|---|
| BTC-PERP | 0.001 | 0.5 |
| ETH-PERP | 0.01 | 0.05 |
| SOL-PERP | 0.1 | 0.01 |
| XRP-PERP | 1.0 | 0.0001 |

Submitting below minimum size returns HTTP 400. Warn the user before attempting.

---

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `price is required for LIMIT orders` | Missing price field | Add `price=...` |
| `take_profit_price is required for OCO` | OCO missing TP | Add `take_profit_price=...` |
| `Slippage check failed` | Market moved before order | Confirm new price with user |
| `HTTP 400: insufficient balance` | Not enough wallet balance | Check with `btse_account_overview()` |
| `HTTP 400: order size too small` | Below minimum | Check min sizes table above |
