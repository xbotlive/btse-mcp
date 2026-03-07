# BTSE MCP Integration Guide

Detailed reference for developers integrating with btse-mcp.

---

## Authentication

BTSE uses **HMAC-SHA384** signing. Every authenticated request requires three headers:

| Header          | Value |
|-----------------|-------|
| `request-api`   | Your API key string |
| `request-nonce` | Current timestamp in milliseconds (integer as string) |
| `request-sign`  | HMAC-SHA384 signature (see below) |

### Signature algorithm

```
signature = HMAC-SHA384( api_secret, path + nonce + body )
```

- `path`  — URL path only, e.g. `/api/v2.1/order` (no host, no query string)
- `nonce` — same millisecond timestamp as the `request-nonce` header
- `body`  — raw JSON string for POST/PUT; **empty string** for GET/DELETE

### Worked example — GET (no body)

```bash
# Endpoint: GET /api/v2.1/user/wallet
# Nonce:    1624984297330
# Secret:   848db84ac252b6726e5f6e7a711d9c96d9fd77d020151b45839a5b59c37203bx

echo -n "/api/v2.1/user/wallet1624984297330" \
  | openssl dgst -sha384 -hmac "848db84ac252b6726e5f6e7a711d9c96d9fd77d020151b45839a5b59c37203bx"

# Expected signature:
# ea4f1f2b43a0f4d750ae560c5274d6214d140fcab3093da5f4a83e36828535bd
# 2ba7b12160cd12199596f422c8883333
```

### Worked example — POST (with body)

```bash
# Endpoint: POST /api/v2.1/order
# Nonce:    1624985375123

BODY='{"postOnly":false,"price":8500.0,"reduceOnly":false,"side":"BUY","size":1,"stopPrice":0.0,"symbol":"BTCPFC","time_in_force":"GTC","trailValue":0.0,"triggerPrice":0.0,"txType":"LIMIT","type":"LIMIT"}'

echo -n "/api/v2.1/order1624985375123${BODY}" \
  | openssl dgst -sha384 -hmac "848db84ac252b6726e5f6e7a711d9c96d9fd77d020151b45839a5b59c37203bx"

# Expected signature:
# 943adfce43b609a28506274976b96e08cf4bdc4ea53ca0b4cac0eb2cf0773a7d
# 0807efc0aeab779d47fadcd9a60eea13
```

---

## Environments

| Environment | REST base URL | WebSocket |
|-------------|---------------|-----------|
| Production  | `https://api.btse.com/futures` | `wss://ws.btse.com/ws/futures` |
| Testnet     | `https://testapi.btse.io/futures` | `wss://testws.btse.io/ws/futures` |

Testnet UI: https://testnet.btse.io

---

## API key permissions

| Permission | Required for |
|------------|--------------|
| Read       | Market data, positions, wallet, order history |
| Trading    | Create / cancel / amend orders, set leverage |
| Transfer   | Wallet transfers between spot and futures |

Create keys at: **BTSE → Account → API tab → New API**

The **passphrase** displayed after creation is your `api_secret`. It is shown only once.

---

## Symbol naming

Use new-style names (introduced April 2023):

| Old name  | New name  |
|-----------|-----------|
| `BTCPFC`  | `BTC-PERP` |
| `ETHPFC`  | `ETH-PERP` |
| `BTCM23`  | `BTC-230630` |

---

## Rate limits

| Category       | Per API key | Per user |
|----------------|-------------|----------|
| Query          | 15 req/s    | 30 req/s |
| Orders         | 75 req/s    | 75 req/s |

Exceeding limits returns HTTP `429` with a `Retry-After` header (unlocked timestamp).

**Tiered block durations on repeated violations:** 1 second → 5 minutes → 15 minutes.
Block timer resets if the limit is not exceeded for 1 hour.

---

## Order types

| `type`    | `txType`  | Description |
|-----------|-----------|-------------|
| `LIMIT`   | —         | Standard limit order |
| `MARKET`  | —         | Market order |
| `LIMIT`   | `TRIGGER` | Trigger limit (activates on price touch) |
| `LIMIT`   | `STOP`    | Stop-limit |
| `OCO`     | —         | One-cancels-the-other (requires `stopPrice` + `triggerPrice`) |

TP/SL can be attached to any order via `takeProfitPrice` / `stopLossPrice` params.

---

## Order status codes

| Code | Meaning |
|------|---------|
| 2    | Order inserted |
| 4    | Order fully transacted |
| 5    | Order partially transacted |
| 6    | Order cancelled |
| 9    | Trigger inserted |
| 10   | Trigger activated |
| 15   | Order rejected |

---

## Spam order policy

Orders with notional value below **5 USDT** are marked as spam automatically:

- Become hidden orders
- Always pay taker fee
- Post-only spam orders are rejected outright

Accounts placing ≥ 4 resting orders with total notional < 20 USDT may be flagged.

---

## Multi-account routing

All MCP tools accept an optional `account_id` argument (default: `"default"`).

```
"Using account testnet, what is the BTC-PERP mark price?"
"Place a limit buy on BTC-PERP at 60000 size 1 using account main"
```

Accounts are stored independently at `~/.config/btse-mcp/accounts.enc`.

---

## Key storage

Credentials are stored encrypted using [Fernet](https://cryptography.io/en/latest/fernet/)
symmetric encryption:

```
~/.config/btse-mcp/
├── key           Fernet key (chmod 600)
└── accounts.enc  Encrypted account records
```

The key file is generated on first use and never leaves your machine.
The `.gitignore` excludes `*.enc` and `*.key` files to prevent accidental commits.
