import uuid
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from api.schemas import UploadResponse, ExtractionResult, JobStatus
from api.database import get_db, create_tables
from api.models import ExtractionJob
from api import db_operations as db_ops
from api.minio_client import upload_document
from workers.tasks import process_document
from workers.celery_app import celery_app
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(
    title="KYC Extraction Pipeline",
    description="Self-hosted offline KYC document extraction API",
    version="1.0.0"
)


# after app = FastAPI(...)
Instrumentator().instrument(app).expose(app)

app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
def serve_frontend():
    return FileResponse("frontend/index.html")

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}
MAX_FILE_SIZE = 8 * 1024 * 1024


@app.on_event("startup")
def startup():
    create_tables()
    print("Database tables created successfully")


@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "1.0.0"}


@app.post("/upload", response_model=UploadResponse)
async def upload_document_endpoint(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type {ext} not supported."
        )

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="File too large. Maximum 8MB."
        )

    job_id = str(uuid.uuid4())

    # Save locally for OCR processing
    file_path = UPLOAD_DIR / f"{job_id}{ext}"
    with open(file_path, "wb") as f:
        f.write(contents)

    # Upload to MinIO for permanent storage
    try:
        minio_url = upload_document(job_id, contents, ext)
    except Exception as e:
        minio_url = None
        print(f"MinIO upload failed for {job_id}: {e}")

    # Save job to PostgreSQL
    db_ops.create_job(db, job_id, str(file_path), minio_url=minio_url)
    db_ops.create_audit_log(
        db, job_id, "uploaded",
        {"filename": file.filename, "size": len(contents), "minio_url": minio_url}
    )

    # Dispatch to Celery
    process_document.apply_async(
        args=[job_id, str(file_path)],
        task_id=job_id
    )

    return UploadResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        message="Document queued for processing"
    )


@app.get("/status/{job_id}", response_model=ExtractionResult)
def get_status(
    job_id: str,
    db: Session = Depends(get_db)
):
    job = db_ops.get_job(db, job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found"
        )

    return ExtractionResult(
        job_id=job.job_id,
        status=JobStatus(job.status),
        document_type=job.document_type,
        fields=job.fields,
        validation=job.validation,
        overall_confidence=job.overall_confidence,
        error=job.error_message
    )


@app.get("/jobs")
def list_jobs(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    jobs = db_ops.get_all_jobs(db, skip, limit)
    return {
        "total": len(jobs),
        "jobs": [
            {
                "job_id": j.job_id,
                "status": j.status,
                "document_type": j.document_type,
                "overall_confidence": j.overall_confidence,
                "created_at": j.created_at
            }
            for j in jobs
        ]
    }


@app.get("/jobs/review")
def jobs_needing_review(
    db: Session = Depends(get_db)
):
    jobs = db_ops.get_low_confidence_jobs(db, threshold=0.85)
    return {
        "total": len(jobs),
        "jobs": [
            {
                "job_id": j.job_id,
                "overall_confidence": j.overall_confidence,
                "document_type": j.document_type,
                "created_at": j.created_at
            }
            for j in jobs
        ]
    }