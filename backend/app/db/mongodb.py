from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from app.core.config import settings

# Async MongoDB client (for async operations)
mongodb_client = AsyncIOMotorClient(settings.MONGODB_URL)
mongodb = mongodb_client.medhistory

# Collections
document_metadata_collection = mongodb.document_metadata

# Sync client for initialization
def get_sync_mongodb():
    return MongoClient(settings.MONGODB_URL).medhistory

# Sync metadata collection for interpretation service
def get_metadata_collection():
    """Get sync MongoDB collection for document metadata"""
    sync_db = get_sync_mongodb()
    return sync_db.document_metadata

