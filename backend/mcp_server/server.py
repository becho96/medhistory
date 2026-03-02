"""
Standalone FastMCP server exposing patient medical data as tools.

Run:
    python -m mcp_server.server

This server can be used by:
  - Claude Desktop (via MCP config)
  - Any other MCP-compatible client
  - External integrations

Environment variables required (same as the main FastAPI app):
  DATABASE_URL, MONGODB_URL
"""
from mcp.server.fastmcp import FastMCP

from mcp_server.tools import (
    profile,
    lab_results,
    documents,
    health_events,
    interpretations,
)

mcp = FastMCP(
    "medhistory-patient-data",
    instructions=(
        "You have access to a patient's medical history stored in the MedHistory service. "
        "Always retrieve the patient profile first to get gender and age for proper "
        "medical context and reference range selection."
    ),
)

# Register all tool groups
profile.register(mcp)
lab_results.register(mcp)
documents.register(mcp)
health_events.register(mcp)
interpretations.register(mcp)

# ─── Future tool groups (uncomment when ready) ────────────────────────────────
# from mcp_server.tools import notes
# notes.register(mcp)
#
# from mcp_server.tools import illness_periods
# illness_periods.register(mcp)
#
# from mcp_server.tools import fitness
# fitness.register(mcp)


if __name__ == "__main__":
    mcp.run()
