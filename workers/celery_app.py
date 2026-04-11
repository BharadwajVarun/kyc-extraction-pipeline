from celery import Celery

celery_app = Celery(
    "kyc_pipeline",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
    include=["workers.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    result_expires=86400,  # Results expire after 24 hours
)