#!/usr/bin/env python3
"""
Найти и удалить семантические дубли документов: записи у одного пользователя
с одинаковыми (original_filename, document_date). Из каждой группы оставляется
самая ранняя по created_at, остальные удаляются из Postgres + MongoDB + MinIO.

Используется как one-off cleanup для записей, попавших в БД до того, как в
DocumentService появилась дедупликация по (filename, document_date).

Запуск из backend/ (или внутри backend-контейнера):
  python -m scripts.dedupe_documents                    # dry-run (только отчёт)
  python -m scripts.dedupe_documents --apply            # реально удалить
  python -m scripts.dedupe_documents --user-id <uuid>   # ограничить пользователем
"""

import argparse
import asyncio
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

env_path = backend_dir.parent / ".env.local"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)

from sqlalchemy import text

from app.db.postgres import AsyncSessionLocal
from app.db.mongodb import document_metadata_collection
from app.db.minio_client import minio_client
from app.core.config import settings


async def find_duplicate_groups(user_id: str | None):
    """Return groups (user_id, original_filename, document_date) with count > 1.
    Each group lists ids/created_ats/file_urls ordered by created_at ASC, so the
    first element is the keeper."""
    sql = """
        SELECT user_id::text                           AS user_id,
               original_filename,
               document_date,
               array_agg(id::text ORDER BY created_at ASC) AS ids,
               array_agg(created_at  ORDER BY created_at ASC) AS created_ats,
               array_agg(file_url    ORDER BY created_at ASC) AS file_urls
        FROM documents
        WHERE document_date IS NOT NULL
          AND original_filename IS NOT NULL
          {user_filter}
        GROUP BY user_id, original_filename, document_date
        HAVING COUNT(*) > 1
        ORDER BY user_id, document_date DESC, original_filename;
    """.format(user_filter="AND user_id = :user_id" if user_id else "")

    async with AsyncSessionLocal() as session:
        params = {"user_id": user_id} if user_id else {}
        result = await session.execute(text(sql), params)
        rows = result.mappings().all()
        return [dict(r) for r in rows]


async def delete_one(doc_id: str, file_url: str | None):
    """Delete a single document from MinIO + Mongo + Postgres. Per-store errors are logged."""
    bucket = settings.MINIO_BUCKET
    if file_url and file_url.startswith(f"s3://{bucket}/"):
        object_name = file_url.replace(f"s3://{bucket}/", "")
        try:
            minio_client.remove_object(bucket, object_name)
        except Exception as e:
            print(f"  ⚠ MinIO delete failed for {object_name}: {e}")
    try:
        await document_metadata_collection.delete_one({"document_id": doc_id})
    except Exception as e:
        print(f"  ⚠ Mongo delete failed for {doc_id}: {e}")
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("DELETE FROM documents WHERE id = :id"), {"id": doc_id})
            await session.commit()
    except Exception as e:
        print(f"  ⚠ Postgres delete failed for {doc_id}: {e}")


async def run(apply: bool, user_id: str | None):
    groups = await find_duplicate_groups(user_id)

    if not groups:
        print("Дублей не найдено.")
        return

    total_extras = 0
    for g in groups:
        ids = g["ids"]
        keep_id = ids[0]
        drop_ids = ids[1:]
        total_extras += len(drop_ids)
        date_str = g["document_date"].strftime("%d.%m.%Y") if g["document_date"] else "?"
        print(
            f"\nuser={g['user_id']}  date={date_str}  "
            f"'{g['original_filename']}'  ({len(ids)} копий)"
        )
        print(f"  keep:  {keep_id}  ({g['created_ats'][0]})")
        for i, doc_id in enumerate(drop_ids, start=1):
            print(f"  drop:  {doc_id}  ({g['created_ats'][i]})")
            if apply:
                await delete_one(doc_id, g["file_urls"][i])

    if apply:
        print(f"\n✅ Удалено {total_extras} дублей в {len(groups)} группах.")
    else:
        print(f"\nDry-run: найдено {total_extras} дублей в {len(groups)} группах. Запустите с --apply.")


def main():
    parser = argparse.ArgumentParser(description="Удалить дубли документов (filename + document_date)")
    parser.add_argument("--apply", action="store_true", help="Реально удалить (по умолчанию dry-run)")
    parser.add_argument("--user-id", default=None, help="Ограничить одним пользователем (UUID)")
    args = parser.parse_args()

    asyncio.run(run(apply=args.apply, user_id=args.user_id))


if __name__ == "__main__":
    main()
