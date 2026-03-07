"""
BTSE MCP Server — stdio transport.

Exposes:
  - 22 tools   (btse_mcp.tools)
  - 4  prompts (btse_mcp.prompts)
  - 3  resources (btse_mcp.resources)

Claude Desktop / Cursor config:

    {
      "mcpServers": {
        "btse": {
          "command": "btse-mcp",
          "args": ["start"]
        }
      }
    }

Can also be run directly:
    python -m btse_mcp start
    btse-mcp start
"""

import asyncio
from mcp.server.stdio import stdio_server
from mcp.types import GetPromptResult, ReadResourceResult

from btse_mcp.tools    import app
from btse_mcp.prompts  import PROMPTS, render_prompt
from btse_mcp.resources import list_resources, read_resource


# ── Prompts ───────────────────────────────────────────────────────────────────

@app.list_prompts()
async def _list_prompts():
    return PROMPTS


@app.get_prompt()
async def _get_prompt(name: str, arguments: dict | None) -> GetPromptResult:
    args = arguments or {}
    try:
        messages = render_prompt(name, args)
        return GetPromptResult(messages=messages)
    except ValueError as e:
        raise ValueError(str(e))


# ── Resources ─────────────────────────────────────────────────────────────────

@app.list_resources()
async def _list_resources():
    return list_resources()


@app.read_resource()
async def _read_resource(uri: str) -> ReadResourceResult:
    try:
        contents = read_resource(uri)
        return ReadResourceResult(contents=contents)
    except ValueError as e:
        raise ValueError(str(e))


# ── Entry point ───────────────────────────────────────────────────────────────

async def main() -> None:
    async with stdio_server() as (read, write):
        await app.run(read, write, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
