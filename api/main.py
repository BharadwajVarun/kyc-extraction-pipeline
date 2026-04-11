import uuid
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from api.schemas import UploadResponse, ExtractionResult, JobStatus
from workers.tasks import process_document
from workers.celery_app import celery_app

app = FastAPI(
    title="KYC Extraction Pipeline",
    description="Self-hosted offline KYC document extraction API",
    version="1.0.0"
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}
MAX_FILE_SIZE = 8 * 1024 * 1024


@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "1.0.0"}


@app.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    # Validate extension
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type {ext} not supported."
        )

    # Validate size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="File too large. Maximum 8MB."
        )

    # Save file
    job_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{job_id}{ext}"
    with open(file_path, "wb") as f:
        f.write(contents)

    # Dispatch to Celery — returns immediately
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
def get_status(job_id: str):
    task = celery_app.AsyncResult(job_id)

    if task.state == "PENDING":
        return ExtractionResult(
            job_id=job_id,
            status=JobStatus.PENDING
        )

    if task.state == "PROCESSING":
        return ExtractionResult(
            job_id=job_id,
            status=JobStatus.PROCESSING
        )

    if task.state == "SUCCESS":
        result = task.result
        return ExtractionResult(
            job_id=job_id,
            status=JobStatus.COMPLETED,
            document_type=result.get("document_type"),
            fields=result.get("fields"),
            validation=result.get("validation"),
            overall_confidence=result.get("overall_confidence")
        )

    if task.state == "FAILURE":
        return ExtractionResult(
            job_id=job_id,
            status=JobStatus.FAILED,
            error=str(task.result)
        )

    return ExtractionResult(
        job_id=job_id,
        status=JobStatus.PENDING
    )