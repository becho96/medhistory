"""Tool: get_health_events — patient-recorded health parameters (BP, pulse, temperature…)."""
import json
from typing import Optional
from mcp.server.fastmcp import FastMCP


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def get_health_events(
        user_id: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 50,
    ) -> str:
        """
        Return health events the patient has self-recorded (blood pressure, pulse,
        temperature, blood sugar, weight, oxygen saturation, etc.).

        Args:
            user_id: UUID of the patient.
            date_from: ISO datetime or date string to filter from.
            date_to:   ISO datetime or date string to filter up to.
            limit: Maximum number of events to return.
        """
        from mcp_server.database import get_pg_connection, get_mongo_db

        conn = await get_pg_connection()
        try:
            conditions = ["user_id = $1::uuid"]
            params: list = [user_id]

            if date_from:
                params.append(date_from)
                conditions.append(f"event_datetime >= ${len(params)}::timestamptz")
            if date_to:
                params.append(date_to)
                conditions.append(f"event_datetime <= ${len(params)}::timestamptz")

            where = " AND ".join(conditions)
            rows = await conn.fetch(
                f"SELECT mongodb_id, event_datetime, notes FROM health_events "
                f"WHERE {where} ORDER BY event_datetime DESC LIMIT ${len(params) + 1}",
                *params, limit,
            )
        finally:
            await conn.close()

        if not rows:
            return json.dumps([])

        mongo_db = get_mongo_db()
        events = []
        for row in rows:
            mongo_id = row["mongodb_id"]
            parameters = {}
            if mongo_id:
                from bson import ObjectId
                try:
                    doc = await mongo_db.health_events.find_one({"_id": ObjectId(mongo_id)})
                except Exception:
                    doc = await mongo_db.health_events.find_one({"_id": mongo_id})
                if doc:
                    parameters = doc.get("parameters", {})

            events.append({
                "datetime": row["event_datetime"].isoformat(),
                "notes": row["notes"],
                "parameters": parameters,
            })

        return json.dumps(events, ensure_ascii=False, default=str)
