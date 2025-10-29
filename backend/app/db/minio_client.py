from minio import Minio
from minio.error import S3Error
from app.core.config import settings

# Create MinIO client
minio_client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=settings.MINIO_SECURE
)

def ensure_bucket_exists():
    """Ensure the bucket exists, create if not"""
    try:
        if not minio_client.bucket_exists(settings.MINIO_BUCKET):
            minio_client.make_bucket(settings.MINIO_BUCKET)
            print(f"✅ Created MinIO bucket: {settings.MINIO_BUCKET}")
        else:
            print(f"✅ MinIO bucket exists: {settings.MINIO_BUCKET}")
    except S3Error as e:
        print(f"❌ Error creating MinIO bucket: {e}")
        raise

