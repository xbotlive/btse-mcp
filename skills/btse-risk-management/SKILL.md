---
name: btse-risk-management
title: "SKILL 5 of 5 — btse-risk-management"
description: Monitor open positions, manage leverage, set take-profit and stop-loss, and close positions safely
---

# BTSE Risk Management

---

## Viewing Positions

```
# All open positions
btse_get_positions()

# One symbol
btse_get_positions(symbol="BTC-PERP")
```

Or use the composite tool for a full account view:

```
btse_account_overview(account_id="default")
```

Returns wallet balance + positions + open orders together.

**Use the `position_review` prompt** for a formatted table with PnL and liquidation risk flags per position.

---

## Risk Flags

When reviewing positions, apply these rules:

| Flag | Condition |
|---|---|
| 🔴 DANGER | Liquidation price within 5% of mark price |
| 🟡 WARNING | Liquidation price within 10% of mark price |
| 🟢 OK | Otherwise |

Alert the user immediately if any position has a 🔴 DANGER flag.

---

## Closing a Position

**Always use `reduce_only=True` when closing** to avoid accidentally flipping direction:

```
# Close at market price (safest for urgent closes)
btse_close_position(symbol="BTC-PERP", close_type="MARKET")

# Close at a limit price
btse_close_position(symbol="BTC-PERP", close_type="LIMIT", price=85000)
```

Alternatively, place a reduce-only order:
```
btse_create_order(
  symbol="BTC-PERP",
  side="SELL",          # opposite of your position side
  order_type="MARKET",
  size=0.01,
  reduce_only=True
)
```

---

## Leverage

```
# Get current leverage
btse_get_leverage(symbol="BTC-PERP")

# Set leverage
btse_set_leverage(
  symbol="BTC-PERP",
  leverage=10,
  margin_mode="ISOLATED"  # ISOLATED | CROSS
)
```

**Rules before setting leverage:**
- Never set above 20x without the user explicitly stating the number
- Above 10x: calculate and show the liquidation price before confirming
- `leverage=0` means maximum cross leverage
- Do not change leverage if the user is just trying to close a position — it affects margin on existing positions

**Leverage safety table (approximate for isolated margin):**

| Leverage | Liquidation at loss of |
|---|---|
| 5x | ~18% |
| 10x | ~9% |
| 20x | ~4.5% |
| 50x | ~1.8% |
| 100x | ~0.9% |

---

## Risk Limits

```
# Get current risk limit tier
btse_get_risk_limit(symbol="BTC-PERP")

# Set risk limit tier
btse_set_risk_limit(symbol="BTC-PERP", risk_limit_level=1)
```

Risk limit tiers control the maximum position size allowed. Higher tiers allow larger positions but require more margin.

---

## Wallet and Fee Information

```
# Wallet balance
btse_get_wallet_balance()

# Maker/taker fee rates
btse_get_account_fees(symbol="BTC-PERP")
```

---

## Wallet History

Use `btse_get_wallet_history` to review deposits, withdrawals, and PnL settlements:

```
# Last 20 wallet transactions (default)
btse_get_wallet_history()

# Filter by market, e.g. only BTC-PERP settlements
btse_get_wallet_history(symbol="BTC-PERP", count=50)
```

Useful for:
- Confirming a deposit has cleared before placing an order
- Reviewing realised PnL over a period
- Auditing withdrawals

---

## Rate Limits (Important for Loops)

| Endpoint type | Limit |
|---|---|
| Query (prices, positions, orders) | 15 req/s per API key |
| Order submission | 75 req/s per API key |

If polling positions or prices in a loop, space calls at least **1 second apart**. On HTTP 429, wait 1 second before retrying.

---

## Emergency: Cancel All Orders

If a position is moving against the user and they want to stop out immediately:

1. `btse_cancel_order(symbol="BTC-PERP")` — cancel all open orders first
2. `btse_close_position(symbol="BTC-PERP", close_type="MARKET")` — close at market
3. Confirm with `btse_get_positions(symbol="BTC-PERP")` that position is gone
