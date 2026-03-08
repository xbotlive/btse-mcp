# btse-mcp

MCP server for the [BTSE](https://btse.com) Futures API. Enables AI agents (Claude Desktop, Cursor,
LangChain) to query market data, manage positions, and place orders on BTSE via natural language.

---

## Prerequisites

- **Python 3.11 or higher** — check with `python --version`
- **pip** — check with `pip --version`
- A BTSE account (testnet or live)

---

## Step 1 — Get API keys from BTSE

### Testnet (recommended first)

1. Register at https://testnet.btse.io
2. Go to **Account → API tab → New API**
3. Save the **API Key** and **Passphrase** — the passphrase is shown only once and is your `api_secret`
4. Set permissions: **Read** + **Trading** (add Transfer if needed)

### Live

Same steps at https://btse.com

---

## Step 2 — Install

```bash
pip install btse-mcp

# Verify
btse-mcp --help
```

> **Multiple Python versions (Anaconda etc):** use the full path explicitly:
> ```bash
> /usr/local/bin/python3.14 -m pip install btse-mcp
> ```

---

## Step 3 — Configure accounts

### Testnet

```bash
btse-mcp config --account-id testnet
# Prompts:
#   API Key    → paste your API key
#   API Secret → paste your passphrase (input is hidden)
#   Use testnet? [y/N] → y

# Verify the connection — should print BTC-PERP last price
btse-mcp test testnet
```

### Live (when ready)

```bash
btse-mcp config --account-id main
# Same prompts — answer 'n' to testnet

# See all configured accounts
btse-mcp list
```

Credentials are stored encrypted at `~/.config/btse-mcp/accounts.enc`.

> **Unified Futures Wallet:** If your BTSE account has been upgraded to the Unified Futures Wallet (all accounts from late 2024 onwards), account endpoints automatically use the v2.2 API. No action needed.

---

## Step 4 — Connect to Claude Desktop

```bash
btse-mcp install-claude
```

This auto-writes the correct config for your OS and creates the file if it doesn't exist. Then **restart Claude Desktop**.

> **Manual alternative:** if the command fails, add this to your config file directly:
>
> | OS      | Path |
> |---------|------|
> | macOS   | `~/Library/Application Support/Claude/claude_desktop_config.json` |
> | Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
> | Linux   | `~/.config/Claude/claude_desktop_config.json` |
>
> ```json
> {
>   "mcpServers": {
>     "btse": {
>       "command": "/full/path/to/btse-mcp",
>       "args": ["start"]
>     }
>   }
> }
> ```
>
> Find the full path with:
> ```bash
> which btse-mcp
> ```

Open a new chat in Claude Desktop — you should see a tools icon (🔧) in the input bar.

**Test it:**
> "What is the BTC-PERP mark price on BTSE using account testnet?"

---

## Step 5 — Connect to Cursor

Open Cursor → **Settings → MCP → Add Server** and enter:

```json
{
  "name": "btse",
  "command": "btse-mcp",
  "args": ["start"]
}
```

Then use natural language in Cursor chat:
> "Show my open BTSE positions"
> "Place a limit buy on BTC-PERP at 60000 size 1 using account testnet"

---

## Alternative: run from source

```bash
# Clone the repo
git clone https://github.com/xbotlive/btse-mcp.git
cd btse-mcp

# Install in editable mode
pip install -e .

# Start
python -m btse_mcp start
```

---

## Tool list

| Tool | Description |
|------|-------------|
| `btse_get_market_summary` | Market summary for one or all symbols |
| `btse_get_price` | Mark / index / last price |
| `btse_get_orderbook` | L2 orderbook snapshot |
| `btse_get_trades` | Recent public trade fills |
| `btse_get_ohlcv` | OHLCV candlestick data |
| `btse_get_funding_history` | Historical funding rates |
| `btse_get_wallet_balance` | Futures wallet balance |
| `btse_get_positions` | Open positions |
| `btse_get_account_fees` | Maker / taker fee rates |
| `btse_get_leverage` | Current leverage for a market |
| `btse_create_order` | Place LIMIT / MARKET / OCO order (supports TP/SL) |
| `btse_cancel_order` | Cancel by order ID, or cancel all for a symbol |
| `btse_get_open_orders` | List open orders |
| `btse_get_order` | Single order detail |
| `btse_get_trade_history` | User trade history |
| `btse_amend_order` | Amend price / size / trigger price |
| `btse_close_position` | Close position at market or limit |
| `btse_set_leverage` | Set leverage (isolated or cross) |
| `btse_get_risk_limit` | Get risk limit tier |

All tools accept an optional `account_id` parameter (defaults to `"default"`).
Pass `"account_id": "testnet"` to route to your testnet account.

---

## Multi-account usage

```bash
btse-mcp list           # list all configured accounts
btse-mcp test main      # test a specific account
```

In prompts, specify the account explicitly:
> "Using account testnet, show my BTC-PERP position"

---

## Symbol naming

Use new-style perpetual names: `BTC-PERP`, `ETH-PERP`, `SOL-PERP`, etc.

---

## Auth

BTSE uses **HMAC-SHA384**. The signature is:

```
HMAC-SHA384(api_secret, url_path + nonce + request_body)
```

Sent via headers: `request-api`, `request-nonce`, `request-sign`.
See `docs/integration.md` for full details and worked examples.

---

## Running tests

```bash
pip install pytest
pytest -v
```

Auth signature tests run against the worked examples in the BTSE docs — no live API connection needed.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `btse-mcp: command not found` | Run `which btse-mcp` to find the full path, or use `pip install btse-mcp` |
| `401 Unauthorized` | Check API key and secret are copied correctly |
| `Connection failed` | Confirm testnet flag matches the account you created on |
| Tools icon missing in Claude Desktop | Check JSON syntax in config file, restart Claude Desktop |
| `ModuleNotFoundError: mcp` | Run `pip install btse-mcp` again |
| `33000001: Unsupported API` | Your account uses the Unified Futures Wallet — the server auto-retries on v2.2, restart Claude Desktop |
| `btse-mcp test` works but account tools fail | Restart Claude Desktop after any config or code change |

---

## Disclaimer

Futures trading involves significant risk of loss. Always test on testnet before using live credentials.
Never commit API keys to version control — they are stored encrypted locally and excluded via `.gitignore`.
