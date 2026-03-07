"""
CLI entry point.

Commands
--------
btse-mcp config [--account-id ID]   Configure (or reconfigure) an account
btse-mcp list                        List all configured accounts (shows testnet flag)
btse-mcp test [ACCOUNT_ID]          Test API connection for an account
btse-mcp delete ACCOUNT_ID          Remove a stored account
btse-mcp start                       Start MCP server (stdio)

Also usable as:
    python -m btse_mcp config
    python -m btse_mcp test testnet
"""

import argparse
import asyncio
import getpass
import sys


def cmd_config(args: argparse.Namespace) -> None:
    from btse_mcp.config import save_account

    print(f"\nConfiguring account: '{args.account_id}'")
    print("(Get keys from BTSE → Account → API tab → New API)\n")

    api_key    = input("API Key    : ").strip()
    api_secret = getpass.getpass("API Secret : ").strip()  # hidden input
    testnet    = input("Use testnet? [y/N] : ").strip().lower() == "y"

    if not api_key or not api_secret:
        print("Error: API key and secret cannot be empty.")
        sys.exit(1)

    save_account(args.account_id, api_key, api_secret, testnet)
    print(f"\nDone. Verify with: btse-mcp test {args.account_id}")


def cmd_list(args: argparse.Namespace) -> None:
    from btse_mcp.config import list_accounts

    # FIX: list_accounts now returns dicts with id + testnet flag
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

        # FIX: check result is a non-empty list before indexing
        if not result or not isinstance(result, list):
            print(f"  Unexpected response from BTSE: {result}")
            sys.exit(1)

        last_price = result[0].get("lastPrice", "N/A")
        mark_price = result[0].get("markPrice", "N/A")
        print(f"  Connection OK")
        print(f"  BTC-PERP last price : {last_price}")
        print(f"  BTC-PERP mark price : {mark_price}")

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


def cmd_start(args: argparse.Namespace) -> None:
    from btse_mcp.server import main
    asyncio.run(main())


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

    # delete
    p_delete = sub.add_parser("delete", help="Delete a stored account")
    p_delete.add_argument("account_id", help="Account ID to delete")

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
        case "start":
            cmd_start(args)
        case _:
            parser.print_help()


if __name__ == "__main__":
    main()
