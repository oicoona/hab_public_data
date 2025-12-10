"""
Celery Tasks for Batch Prediction
"""
from celery import Task
from backend.tasks import celery_app
from backend.services import prediction_service


@celery_app.task(bind=True, name="batch_predict_eclo")
def batch_predict_eclo(self: Task, accidents: list[dict]) -> list[dict]:
    """
    Batch ECLO prediction task
    
    Args:
        accidents: List of accident feature dictionaries
        
    Returns:
        List of prediction results
    """
    # Update task state to show progress
    self.update_state(state='PROCESSING', meta={'progress': 0, 'total': len(accidents)})
    
    # Perform batch prediction
    results = prediction_service.predict_eclo_batch(accidents)
    
    # Update task state to show completion
    self.update_state(state='SUCCESS', meta={'progress': len(accidents), 'total': len(accidents)})
    
    return results
