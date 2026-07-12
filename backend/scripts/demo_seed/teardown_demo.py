"""Remove the demo account and all of its data (clean rollback).

Scoped strictly to the demo owner (by email) and its family members — existing
real users are never touched. Postgres children cascade from `users`
(documents → reminders, family_relations, consents all ON DELETE CASCADE);
MongoDB metadata and MinIO objects are cleaned explicitly.

Usage (inside the backend container, cwd /app):
    python -m scripts.demo_seed.teardown_demo          # asks for confirmation
    python -m scripts.demo_seed.teardown_demo --yes    # non-interactive
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))  # /app

from sqlalchemy import select, delete

from app.db.postgres import AsyncSessionLocal
from app.db.mongodb import document_metadata_collection
from app.db.minio_client import minio_client
from app.core.config import settings
from app.models.user import User
from app.models.family import FamilyRelation

from . import config as C


async def _collect_user_ids(db) -> list:
    res = await db.execute(select(User.id).where(User.email == C.OWNER_EMAIL))
    owner_id = res.scalar_one_or_none()
    if owner_id is None:
        return []
    res = await db.execute(
        select(FamilyRelation.member_id).where(FamilyRelation.owner_id == owner_id)
    )
    members = list(res.scalars().all())
    return [owner_id, *members]


def _purge_minio(user_ids: list) -> int:
    removed = 0
    for uid in user_ids:
        prefix = f"{uid}/"
        try:
            objects = minio_client.list_objects(settings.MINIO_BUCKET, prefix=prefix, recursive=True)
            for obj in objects:
                minio_client.remove_object(settings.MINIO_BUCKET, obj.object_name)
                removed += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  MinIO cleanup warning for {prefix}: {exc}")
    return removed


async def main(confirm: bool) -> None:
    async with AsyncSessionLocal() as db:
        user_ids = await _collect_user_ids(db)
        if not user_ids:
            print(f"No demo account found for {C.OWNER_EMAIL}. Nothing to do.")
            return
        str_ids = [str(u) for u in user_ids]
        print(f"Demo users to delete ({len(user_ids)}): {str_ids}")

        if not confirm:
            answer = input("Type 'delete' to remove the demo account and all its data: ")
            if answer.strip().lower() != "delete":
                print("Aborted.")
                return

        # MinIO first (needs the ids), then Mongo, then Postgres (cascade).
        n_minio = _purge_minio(user_ids)
        mongo_res = await document_metadata_collection.delete_many({"user_id": {"$in": str_ids}})
        await db.execute(delete(User).where(User.id.in_(user_ids)))
        await db.commit()

        print(f"Deleted: {len(user_ids)} users (Postgres cascade), "
              f"{mongo_res.deleted_count} Mongo metadata docs, {n_minio} MinIO objects.")
        print("Teardown complete.")


if __name__ == "__main__":
    asyncio.run(main(confirm="--yes" in sys.argv))
