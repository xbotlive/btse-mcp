# Changelog

All notable changes to this project will be documented here.

## [0.1.0] - 2025-01-01

### Added
- BTSE Futures REST client with HMAC-SHA384 authentication
- 19 MCP tools covering market data, account, orders, and risk management
- Fernet-encrypted local API key storage at `~/.config/btse-mcp/`
- CLI commands: `config`, `list`, `test`, `delete`, `start`
- Testnet support (`btse-mcp config --account-id testnet`)
- Multi-account support with per-call `account_id` routing
- Claude Desktop and Cursor integration via stdio MCP transport
- `python -m btse_mcp` module entrypoint
- Auth signature tests against BTSE docs worked examples
- GitHub Actions CI on Python 3.11 and 3.12
