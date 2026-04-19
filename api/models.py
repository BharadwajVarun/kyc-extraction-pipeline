from sqlalchemy import (
    Column, String, Float,
    DateTime, JSON, Boolean, Text
)
from sqlalchemy.sql import func
from api.database import Base


class ExtractionJob(Base):
    __tablename__ = "extraction_jobs"

    job_id = Column(String, primary_key=True, index=True)
    status = Column(String, nullable=False, default="pending")
    document_type = Column(String, nullable=True)
    file_path = Column(String, nullable=True)
    minio_url = Column(String, nullable=True)    #added to store the MinIO URL of the uploaded document

    # Extracted fields stored as JSONB
    fields = Column(JSON, nullable=True)

    # Validation results stored as JSONB
    validation = Column(JSON, nullable=True)

    # Overall confidence score
    overall_confidence = Column(Float, nullable=True)

    # Error message if failed
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    completed_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    # Was this manually reviewed
    manually_reviewed = Column(Boolean, default=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True)
    job_id = Column(String, index=True)
    action = Column(String, nullable=False)
    details = Column(JSON, nullable=True)
    timestamp = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )