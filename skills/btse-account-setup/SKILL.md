---
name: btse-account-setup
title: "SKILL 2 of 5 — btse-account-setup"
description: Configure API keys, switch between testnet and live, verify connection, and manage multiple accounts
---

# BTSE Account Setup

## Getting API Keys

### Testnet (start here)
1. Register at https://testnet.btse.io
2. Go to **Account → API tab → New API**
3. Save the **API Key** and **Passphrase** — the passphrase is your `api_secret` and is shown only once
4. Set permissions: **Read + Trading** (add Transfer if needed)

### Live
Same steps at https://btse.com

---

## Configuring an Account

```bash
# Configure the default account
btse-mcp config

# Configure a named account (e.g. a separate testnet account)
btse-mcp config --account-id testnet
```

You will be prompted for:
- **API Key** — paste from BTSE
- **API Secret** — paste passphrase (input is hidden)
- **Use testnet?** — y for testnet, N for live

Credentials are stored encrypted at `~/.config/btse-mcp/accounts.enc` using a Fernet key at `~/.config/btse-mcp/key` (chmod 600 on Unix).

---

## Verifying the Connection

```bash
# Test the default account
btse-mcp test

# Test a named account
btse-mcp test testnet
```

A successful test prints the current BTC-PERP last price and mark price.

**Common failures:**

| Error | Cause | Fix |
|---|---|---|
| Connection FAILED: HTTP 401 | Wrong API key or secret | Re-run `btse-mcp config` |
| Connection FAILED: HTTP 403 | Key missing Read permission | Add Read permission in BTSE API settings |
| Unexpected response | Wrong testnet setting | Check with `btse-mcp list` and reconfigure |

---

## Listing and Managing Accounts

```bash
# List all configured accounts (shows testnet/live flag)
btse-mcp list

# Delete an account
btse-mcp delete testnet
```

---

## Using Multiple Accounts

All tools accept an optional `account_id` parameter:
```
btse_get_price(symbol="BTC-PERP", account_id="testnet")
btse_account_overview(account_id="live-main")
```

Default is `"default"` when `account_id` is omitted.

**Important:** If you reconfigure an account with `btse-mcp config`, restart the MCP server (restart Claude Desktop / Cursor) for the new credentials to take effect. The server caches clients per account for the lifetime of the process.

---

## Environment Check Before Trading

Before any order tool, confirm the environment:
1. Call `btse_get_price(symbol="BTC-PERP")`
2. Testnet BTC-PERP trades around **$10,000–$30,000** (artificial)
3. Production BTC-PERP tracks the real market price (~$80,000–$100,000 range in 2025)

If the price looks wrong for the intended environment, stop and reconfigure.

---

## Transferring Funds Between Wallets

Use `btse_transfer` to move funds between spot and futures wallets, or between margin wallets.

**Always confirm these details with the user before calling the tool:**
- `from_wallet` — source wallet name
- `to_wallet` — destination wallet name
- `amount` — how much to move
- `currency` — defaults to USDT

**Common wallet names:**

| Wallet | Description |
|---|---|
| `SPOT` | Spot wallet |
| `CROSS@` | Cross-margin futures wallet |
| `ISOLATED@BTC-PERP-USDT` | Isolated margin wallet for BTC-PERP |
| `ISOLATED@ETH-PERP-USDT` | Isolated margin wallet for ETH-PERP |

**Example — move 500 USDT from spot to cross futures:**
```
btse_transfer(
  from_wallet="SPOT",
  to_wallet="CROSS@",
  amount=500,
  currency="USDT"
)
```

**Requires Transfer permission** on the API key. If the call returns HTTP 403, the key needs the Transfer permission added in BTSE → Account → API settings.

Use `btse_list_accounts()` to confirm which account you're operating on before transferring.
