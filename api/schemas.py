from pydantic import BaseModel
from typing import Optional, Dict, Any
from enum import Enum


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class UploadResponse(BaseModel):
    job_id: str
    status: JobStatus
    message: str


class ExtractionResult(BaseModel):
    job_id: str
    status: JobStatus
    document_type: Optional[str] = None
    fields: Optional[Dict[str, Any]] = None
    validation: Optional[Dict[str, Any]] = None
    overall_confidence: Optional[float] = None
    error: Optional[str] = None