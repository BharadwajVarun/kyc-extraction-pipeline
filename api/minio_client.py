from minio import Minio
from minio.error import S3Error
import io 
import os
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "kyc_minio")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "kyc_minio_pass")
MINIO_BUCKET = "kyc-documents"

client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

def ensure_bucket():
    if not client.bucket_exists(MINIO_BUCKET):
        client.make_bucket(MINIO_BUCKET)
        print(f"Created MinIO bucket: {MINIO_BUCKET}")

def upload_document(job_id: str, file_bytes: bytes, extension: str) -> str:
    """Upload file bytes to MinIO, return object URL."""
    ensure_bucket()
    object_name = f"{job_id}{extension}"
    client.put_object(
        MINIO_BUCKET,
        object_name,
        io.BytesIO(file_bytes),
        length=len(file_bytes),
        content_type="application/octet-stream"
    )
    return f"minio://{MINIO_BUCKET}/{object_name}"