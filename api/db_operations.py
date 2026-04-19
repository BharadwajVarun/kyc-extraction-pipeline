import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from api.models import ExtractionJob, AuditLog


def create_job(db: Session, job_id: str, file_path: str, minio_url: str = None):
    job = ExtractionJob(
        job_id=job_id,
        status="pending",
        file_path=file_path,
        minio_url=minio_url
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def update_job_processing(db: Session, job_id: str):
    job = db.query(ExtractionJob).filter(
        ExtractionJob.job_id == job_id
    ).first()
    if job:
        job.status = "processing"
        db.commit()
    return job


def update_job_completed(
    db: Session,
    job_id: str,
    result: dict
):
    job = db.query(ExtractionJob).filter(
        ExtractionJob.job_id == job_id
    ).first()
    if job:
        job.status = "completed"
        job.document_type = result.get("document_type")
        job.fields = result.get("fields")
        job.validation = result.get("validation")
        job.overall_confidence = result.get(
            "overall_confidence"
        )
        job.completed_at = datetime.utcnow()
        db.commit()
    return job


def update_job_failed(
    db: Session,
    job_id: str,
    error: str
):
    job = db.query(ExtractionJob).filter(
        ExtractionJob.job_id == job_id
    ).first()
    if job:
        job.status = "failed"
        job.error_message = error
        job.completed_at = datetime.utcnow()
        db.commit()
    return job


def get_job(db: Session, job_id: str):
    return db.query(ExtractionJob).filter(
        ExtractionJob.job_id == job_id
    ).first()


def get_all_jobs(
    db: Session,
    skip: int = 0,
    limit: int = 50
):
    return db.query(ExtractionJob)\
             .order_by(ExtractionJob.created_at.desc())\
             .offset(skip)\
             .limit(limit)\
             .all()


def get_low_confidence_jobs(
    db: Session,
    threshold: float = 0.85
):
    return db.query(ExtractionJob).filter(
        ExtractionJob.overall_confidence < threshold,
        ExtractionJob.status == "completed"
    ).all()


def create_audit_log(
    db: Session,
    job_id: str,
    action: str,
    details: dict = None
):
    log = AuditLog(
        id=str(uuid.uuid4()),
        job_id=job_id,
        action=action,
        details=details
    )
    db.add(log)
    db.commit()
    return log