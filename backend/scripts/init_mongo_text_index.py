"""
Создаёт текстовый индекс на извлечённом контенте document_metadata
с русским стеммингом — нужен для тула search_documents в MCP-сервере.

Запуск:
    cd backend && python scripts/init_mongo_text_index.py
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from pymongo import MongoClient, TEXT
from app.core.config import settings


def main() -> None:
    client = MongoClient(settings.MONGODB_URL)
    db = client.medhistory
    coll = db.document_metadata

    for idx in coll.list_indexes():
        keys = dict(idx.get("key", {}))
        if idx["name"] != "_id_" and any(value == "text" for value in keys.values()):
            coll.drop_index(idx["name"])
            print(f"🗑️  Dropped old text index: {idx['name']}")

    index_name = coll.create_index(
        [
            ("extracted_data.summary", TEXT),
            ("extracted_data.full_text", TEXT),
        ],
        default_language="russian",
        weights={
            "extracted_data.summary": 5,
            "extracted_data.full_text": 1,
        },
        name="document_content_text_ru",
    )
    print(f"✅ Created index: {index_name}")
    print("Existing indexes:")
    for idx in coll.list_indexes():
        print(f"  - {idx['name']}: {dict(idx.get('key', {}))}")


if __name__ == "__main__":
    main()
