---
name: btse-market-analysis
title: "SKILL 3 of 5 — btse-market-analysis"
description: Read market data — prices, orderbook, funding rates, OHLCV candles, and market snapshots
---

# BTSE Market Analysis

All tools in this skill are **read-only** and safe to call freely. They do not require trading permissions on the API key.

---

## Preferred: Use the Composite Tool

For most market questions, use one call instead of three:

```
btse_market_snapshot(
  symbol="BTC-PERP",
  orderbook_depth=5,    # levels per side, default 5
  funding_count=5       # past funding periods, default 5
)
```

Returns price, orderbook, and funding history in a single response.

---

## Price Data

```
btse_get_price(symbol="BTC-PERP")
```

Returns: `lastPrice`, `markPrice`, `indexPrice` for the symbol.
Omit `symbol` to get prices for all markets.

**Use the `market_overview` prompt** for a formatted summary with 24h change, spread, and funding trend.

---

## Orderbook

```
btse_get_orderbook(symbol="BTC-PERP", depth=10)
```

Returns L2 orderbook — bids and asks at each price level.
`depth` is levels per side (default: all available).

**Spread calculation:**
- Best ask − best bid = spread in USD
- Spread / mid-price × 100 = spread in %

---

## Recent Trades

```
btse_get_trades(symbol="BTC-PERP", count=20)
```

Returns the last N public trade fills. Max `count` is typically 500.

---

## OHLCV Candles

```
btse_get_ohlcv(
  symbol="BTC-PERP",
  resolution="60",      # candle size in minutes
  start=1700000000000,  # optional, milliseconds
  end=1700086400000     # optional, milliseconds
)
```

**Valid resolutions (minutes):**
`1 | 5 | 15 | 30 | 60 | 240 | 360 | 1440 | 10080 | 43200`

---

## Funding Rates

```
btse_get_funding_history(symbol="BTC-PERP", count=10)
```

Returns historical funding rates. Omit `symbol` for all markets.

**Reading funding:**
- Positive rate → longs pay shorts (market is long-heavy)
- Negative rate → shorts pay longs (market is short-heavy)
- Rate paid every 8 hours on perpetuals

---

## Market Summary

```
btse_get_market_summary(symbol="BTC-PERP")
```

Returns full contract details: open interest, 24h volume, price change, contract size, funding rate.
Omit `symbol` to get all markets.

---

## Resources (live data, no tool call needed)

```
btse://price/BTC-PERP          # live price snapshot
btse://markets                  # all active markets
```

---

## Symbol Reference

| Symbol | Contract | Min size | Tick |
|---|---|---|---|
| BTC-PERP | Bitcoin perpetual | 0.001 | 0.5 |
| ETH-PERP | Ethereum perpetual | 0.01 | 0.05 |
| SOL-PERP | Solana perpetual | 0.1 | 0.01 |
| XRP-PERP | XRP perpetual | 1.0 | 0.0001 |
