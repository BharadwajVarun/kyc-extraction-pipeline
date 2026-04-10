import uuid
import shutil
import os
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from api.schemas import UploadResponse, ExtractionResult, JobStatus
from workers.ocr_engine import extract_text
from workers.regex_extractor import extract_fields

app = FastAPI(
    title="KYC Extraction Pipeline",
    description="Self-hosted offline KYC document extraction API",
    version="1.0.0"
)

# In-memory job store — will be replaced with Redis in Day 7
JOBS = {}

# Upload directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}
MAX_FILE_SIZE = 8 * 1024 * 1024  # 8MB


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0"
    }


@app.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    # Validate file extension
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type {ext} not supported. Use JPG, PNG or PDF."
        )

    # Validate file size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="File too large. Maximum size is 8MB."
        )

    # Generate unique job ID
    job_id = str(uuid.uuid4())

    # Save file to disk
    file_path = UPLOAD_DIR / f"{job_id}{ext}"
    with open(file_path, "wb") as f:
        f.write(contents)

    # Store job as pending
    JOBS[job_id] = {
        "status": JobStatus.PENDING,
        "file_path": str(file_path)
    }

    # Process synchronously for now — Celery in Day 7
    try:
        JOBS[job_id]["status"] = JobStatus.PROCESSING
        raw_text = extract_text(str(file_path))
        result = extract_fields(raw_text)
        JOBS[job_id].update({
            "status": JobStatus.COMPLETED,
            "result": result
        })
    except Exception as e:
        JOBS[job_id].update({
            "status": JobStatus.FAILED,
            "error": str(e)
        })

    return UploadResponse(
        job_id=job_id,
        status=JOBS[job_id]["status"],
        message="Document processed successfully"
    )


@app.get("/status/{job_id}", response_model=ExtractionResult)
def get_status(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found"
        )

    job = JOBS[job_id]

    if job["status"] == JobStatus.FAILED:
        return ExtractionResult(
            job_id=job_id,
            status=job["status"],
            error=job.get("error", "Unknown error")
        )

    if job["status"] == JobStatus.COMPLETED:
        result = job.get("result", {})
        return ExtractionResult(
            job_id=job_id,
            status=job["status"],
            document_type=result.get("document_type"),
            fields=result.get("fields"),
            validation=result.get("validation"),
            overall_confidence=result.get("overall_confidence")
        )

    return ExtractionResult(
        job_id=job_id,
        status=job["status"]
    )


@app.get("/jobs")
def list_jobs():
    return {
        "total": len(JOBS),
        "jobs": [
            {
                "job_id": jid,
                "status": job["status"]
            }
            for jid, job in JOBS.items()
        ]
    }