from workers.celery_app import celery_app
from workers.ocr_engine import extract_text
from workers.regex_extractor import extract_fields


@celery_app.task(bind=True, max_retries=3)
def process_document(self, job_id: str, file_path: str):
    try:
        # Update status to processing
        self.update_state(
            state="PROCESSING",
            meta={"job_id": job_id, "status": "processing"}
        )

        # Run full pipeline
        raw_text = extract_text(file_path)
        result = extract_fields(raw_text)

        return {
            "job_id": job_id,
            "status": "completed",
            "document_type": result.get("document_type"),
            "fields": result.get("fields"),
            "validation": result.get("validation"),
            "overall_confidence": result.get("overall_confidence")
        }

    except Exception as exc:
        # Retry up to 3 times with 5 second delay
        raise self.retry(exc=exc, countdown=5)