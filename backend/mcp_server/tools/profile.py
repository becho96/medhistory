"""Tool: get_patient_profile — basic demographic info about the patient."""
import json
from datetime import date
from mcp.server.fastmcp import FastMCP

from mcp_server.database import get_pg_pool
from mcp_server.tools._user import resolve_user_id


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def get_patient_profile() -> str:
        """
        Return the patient's basic profile: full name, gender, and age.
        Always call this first to get demographic context for medical analysis
        (e.g. gender-specific reference ranges for lab results).
        """
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT full_name, gender, birth_date FROM users WHERE id = $1::uuid",
                resolve_user_id(),
            )

        if not row:
            return json.dumps({"error": "Patient not found"})

        age = None
        if row["birth_date"]:
            today = date.today()
            bd = row["birth_date"]
            age = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))

        return json.dumps({
            "full_name": row["full_name"],
            "gender": row["gender"],
            "age": age,
            "birth_date": str(row["birth_date"]) if row["birth_date"] else None,
        }, ensure_ascii=False)
