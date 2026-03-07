---
name: btse-onboarding
title: "SKILL 1 of 5 — btse-onboarding"
description: START HERE - Overview of btse-mcp, what it does, setup steps, and which skills to load for your task
---

# BTSE MCP — Onboarding

## What is btse-mcp?

`btse-mcp` is a Model Context Protocol server that connects AI agents (Claude Desktop, Cursor, Claude Code) to the **BTSE Futures API**. It lets you query market data, manage positions, and place orders using natural language.

## What's available

| Layer | Count | What it gives you |
|---|---|---|
| Tools | 24 | Direct API wrappers + 3 composite tools |
| Prompts | 4 | Guided multi-step workflows |
| Resources | 3 | Live read-only data feeds |

## Is it set up?

Run this to check:
```bash
btse-mcp list
```

If you see no accounts, run setup first — load the **btse-account-setup** skill.

If accounts are listed, you're ready to go.

## Load the right skill for your task

| What you want to do | Load this skill |
|---|---|
| Set up API keys or switch testnet/live | `btse-account-setup` |
| Check prices, funding rates, orderbook | `btse-market-analysis` |
| Place, amend, or cancel an order | `btse-placing-orders` |
| Check positions, set leverage, manage risk | `btse-risk-management` |

## Quick capability reference

**Composite tools** (prefer these over chaining individual calls):
- `btse_market_snapshot` — price + orderbook + funding in one call
- `btse_account_overview` — balance + positions + open orders in one call
- `btse_safe_market_order` — market order with slippage protection

**Prompts** (invoke by name for structured workflows):
- `market_overview` — full market conditions summary
- `position_review` — positions with PnL and risk flags
- `account_summary` — full account snapshot before trading
- `place_order_guide` — step-by-step guided order placement

**Resources** (live read-only data):
- `btse://price/BTC-PERP` — live price (replace symbol as needed)
- `btse://account/default/summary` — wallet + positions snapshot
- `btse://markets` — all active futures markets

## Key facts
- Symbol format: `BTC-PERP`, `ETH-PERP`, `SOL-PERP` (new-style with hyphen)
- All tools accept optional `account_id` — defaults to `"default"`
- Testnet base: `https://testapi.btse.io/futures`
- Production base: `https://api.btse.com/futures`
