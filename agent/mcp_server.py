"""MCP server exposing the same read-only tools, so any MCP client (Claude Desktop, Claude Code, ...) can use them.

Run: python -m agent.mcp_server   (stdio transport)
"""
from mcp.server.fastmcp import FastMCP

from agent.tools import TOOLS

mcp = FastMCP("ap-inbox")
for fn in TOOLS.values():
    mcp.tool()(fn)

if __name__ == "__main__":
    mcp.run()
