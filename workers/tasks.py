import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workers.celery_app import celery_app
from workers.ocr_engine import extract_text
from workers.regex_extractor import extract_fields


@celery_app.task(bind=True, max_retries=3)
def process_document(self, job_id: str, file_path: str):
    from api.database import SessionLocal
    from api import db_operations as db_ops

    db = SessionLocal()
    try:
        db_ops.update_job_processing(db, job_id)

        raw_text = extract_text(file_path)
        result = extract_fields(raw_text)

        db_ops.update_job_completed(db, job_id, result)
        db_ops.create_audit_log(
            db, job_id, "completed",
            {"overall_confidence": result.get("overall_confidence")}
        )

        return {
            "job_id": job_id,
            "status": "completed",
            **result
        }

    except Exception as exc:
        db_ops.update_job_failed(db, job_id, str(exc))
        db_ops.create_audit_log(
            db, job_id, "failed",
            {"error": str(exc)}
        )
        raise self.retry(exc=exc, countdown=5)

    finally:
        db.close()