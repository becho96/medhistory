"""
Создаёт текстовый индекс на document_metadata.extracted_data.summary
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

    index_name = coll.create_index(
        [("extracted_data.summary", TEXT)],
        default_language="russian",
        name="summary_text_ru",
    )
    print(f"✅ Created index: {index_name}")
    print("Existing indexes:")
    for idx in coll.list_indexes():
        print(f"  - {idx['name']}: {dict(idx.get('key', {}))}")


if __name__ == "__main__":
    main()
