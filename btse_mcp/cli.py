"""
CLI entry point.

Commands
--------
btse-mcp config [--account-id ID]   Configure (or reconfigure) an account
btse-mcp list                        List all configured accounts (shows testnet flag)
btse-mcp test [ACCOUNT_ID] [--check] Test API connection; --check also validates Claude Desktop config
btse-mcp delete ACCOUNT_ID          Remove a stored account
btse-mcp setup [--account-id ID]    Configure account AND auto-patch Claude Desktop config
btse-mcp start                       Start MCP server (stdio)

Also usable as:
    python -m btse_mcp config
    python -m btse_mcp test testnet
"""

import argparse
import asyncio
import getpass
import json
import os
import platform
import sys
from pathlib import Path


# ── Shared helpers ────────────────────────────────────────────────────────────

def _claude_config_path() -> Path | None:
    paths = {
        "Darwin":  Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json",
        "Windows": Path(os.environ.get("APPDATA", "")) / "Claude" / "claude_desktop_config.json",
        "Linux":   Path.home() / ".config" / "Claude" / "claude_desktop_config.json",
    }
    return paths.get(platform.system())


def _check_claude_desktop_config() -> bool:
    """Read-only check. Prints status and returns True if config looks correct."""
    cfg_path = _claude_config_path()

    print("\n  Claude Desktop config check:")

    if cfg_path is None:
        print("  ⚠  Unsupported OS — cannot locate config automatically")
        return False

    if not cfg_path.exists():
        print(f"  ✗  Config file not found at:\n     {cfg_path}")
        print("     Run: btse-mcp setup   to create it automatically")
        return False

    try:
        cfg = json.loads(cfg_path.read_text())
    except Exception as e:
        print(f"  ✗  Could not parse config JSON: {e}")
        return False

    servers = cfg.get("mcpServers", {})
    if "btse" not in servers:
        print(f"  ✗  No 'btse' entry in mcpServers")
        print("     Run: btse-mcp setup   to add it automatically")
        return False

    entry = servers["btse"]
    cmd   = entry.get("command", "")
    args_ = entry.get("args", [])

    if cmd != "btse-mcp" or args_ != ["start"]:
        print(f"  ⚠  Entry exists but looks unexpected: {entry}")
        print("     Expected: command=btse-mcp, args=[\"start\"]")
        return False

    print(f"  ✓  btse MCP entry found and looks correct")
    print(f"     {cfg_path}")
    return True


def _patch_claude_desktop_config() -> bool:
    """Write the btse entry into Claude Desktop config. Creates the file if needed."""
    cfg_path = _claude_config_path()

    if cfg_path is None:
        print("  ⚠  Unsupported OS — please add the entry manually (see README Step 4)")
        return False

    cfg_path.parent.mkdir(parents=True, exist_ok=True)

    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text())
        except Exception as e:
            print(f"  ✗  Could not parse existing config: {e}")
            print("     Fix the JSON manually then re-run setup")
            return False
    else:
        cfg = {}

    cfg.setdefault("mcpServers", {})["btse"] = {
        "command": "btse-mcp",
        "args":    ["start"],
    }

    cfg_path.write_text(json.dumps(cfg, indent=2))
    print(f"  ✓  Claude Desktop config updated")
    print(f"     {cfg_path}")
    return True


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_config(args: argparse.Namespace) -> None:
    from btse_mcp.config import save_account

    print(f"\nConfiguring account: '{args.account_id}'")
    print("(Get keys from BTSE → Account → API tab → New API)\n")

    api_key    = input("API Key    : ").strip()
    api_secret = getpass.getpass("API Secret : ").strip()
    testnet    = input("Use testnet? [y/N] : ").strip().lower() == "y"

    if not api_key or not api_secret:
        print("Error: API key and secret cannot be empty.")
        sys.exit(1)

    save_account(args.account_id, api_key, api_secret, testnet)
    print(f"\nDone. Verify with: btse-mcp test {args.account_id}")


def cmd_list(args: argparse.Namespace) -> None:
    from btse_mcp.config import list_accounts

    accounts = list_accounts()
    if not accounts:
        print("No accounts configured. Run: btse-mcp config")
    else:
        print("Configured accounts:")
        for acc in accounts:
            env = "testnet" if acc["testnet"] else "live"
            print(f"  - {acc['id']}  ({env})")


def cmd_test(args: argparse.Namespace) -> None:
    from btse_mcp.client import BTSEClient
    from btse_mcp.config import load_account

    account_id = args.account_id
    acc        = load_account(account_id)

    if not acc:
        print(f"Account '{account_id}' not found. Run: btse-mcp config --account-id {account_id}")
        sys.exit(1)

    testnet = acc.get("testnet", False)
    env     = "testnet" if testnet else "production"
    print(f"Testing account '{account_id}' ({env})...")

    client = BTSEClient(acc["api_key"], acc["api_secret"], testnet=testnet)

    try:
        result = client.get_price("BTC-PERP")

        if not result or not isinstance(result, list):
            print(f"  Unexpected response from BTSE: {result}")
            sys.exit(1)

        last_price = result[0].get("lastPrice", "N/A")
        mark_price = result[0].get("markPrice", "N/A")
        print(f"  Connection OK")
        print(f"  BTC-PERP last price : {last_price}")
        print(f"  BTC-PERP mark price : {mark_price}")

        if getattr(args, "check", False):
            ok = _check_claude_desktop_config()
            if not ok:
                sys.exit(1)

    except Exception as e:
        print(f"  Connection FAILED: {e}")
        print("\nCommon causes:")
        print("  - API key or secret is incorrect")
        print("  - Wrong testnet setting (run btse-mcp list to check)")
        print("  - API key does not have Read permission")
        sys.exit(1)


def cmd_delete(args: argparse.Namespace) -> None:
    from btse_mcp.config import delete_account
    delete_account(args.account_id)


def cmd_setup(args: argparse.Namespace) -> None:
    """One-shot: configure account + patch Claude Desktop config."""
    print("=== btse-mcp setup ===\n")

    # Step 1 — API credentials
    cmd_config(args)

    # Step 2 — Claude Desktop config
    print("\nPatching Claude Desktop config...")
    ok = _patch_claude_desktop_config()

    if ok:
        print("\nAll done. Restart Claude Desktop, then test with:")
        print(f"  btse-mcp test {args.account_id} --check")
    else:
        print("\nCredentials saved. Add the Claude Desktop entry manually (see README Step 4).")


def cmd_start(args: argparse.Namespace) -> None:
    from btse_mcp.server import main
    asyncio.run(main())


# ── Argument parser ───────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="btse-mcp",
        description="BTSE MCP Server — connect Claude Desktop / Cursor to BTSE Futures",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    # config
    p_config = sub.add_parser("config", help="Configure an account")
    p_config.add_argument(
        "--account-id",
        default="default",
        help="Account name (default: 'default')",
    )

    # list
    sub.add_parser("list", help="List all configured accounts")

    # test
    p_test = sub.add_parser("test", help="Test API connection")
    p_test.add_argument(
        "account_id",
        nargs="?",
        default="default",
        help="Account to test (default: 'default')",
    )
    p_test.add_argument(
        "--check",
        action="store_true",
        help="Also verify Claude Desktop config contains the btse MCP entry",
    )

    # delete
    p_delete = sub.add_parser("delete", help="Delete a stored account")
    p_delete.add_argument("account_id", help="Account ID to delete")

    # setup
    p_setup = sub.add_parser(
        "setup",
        help="Configure account AND auto-patch Claude Desktop config (one-shot onboarding)",
    )
    p_setup.add_argument(
        "--account-id",
        default="default",
        help="Account name (default: 'default')",
    )

    # start
    sub.add_parser("start", help="Start MCP server (stdio transport)")

    args = parser.parse_args()

    match args.command:
        case "config":
            cmd_config(args)
        case "list":
            cmd_list(args)
        case "test":
            cmd_test(args)
        case "delete":
            cmd_delete(args)
        case "setup":
            cmd_setup(args)
        case "start":
            cmd_start(args)
        case _:
            parser.print_help()


if __name__ == "__main__":
    main()
