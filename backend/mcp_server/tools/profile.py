"""Tool: get_patient_profile — basic demographic info about the patient."""
import json
from datetime import date
from mcp.server.fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def get_patient_profile(user_id: str) -> str:
        """
        Return the patient's basic profile: full name, gender, and age.
        Always call this first to get demographic context for medical analysis.

        Args:
            user_id: UUID of the patient (from the authenticated session).
        """
        from mcp_server.database import get_pg_connection

        conn = await get_pg_connection()
        try:
            row = await conn.fetchrow(
                "SELECT full_name, gender, birth_date FROM users WHERE id = $1::uuid",
                user_id,
            )
        finally:
            await conn.close()

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
        })
