"""
Celery Task Queue Configuration
"""
from celery import Celery
from backend.config import settings

# Create Celery app
celery_app = Celery(
    "hab_public_data",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["backend.tasks.prediction_tasks"]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes max
    worker_prefetch_multiplier=1,
)

__all__ = ["celery_app"]
