"""
Prediction API Routes
"""
from fastapi import APIRouter, HTTPException, status
from datetime import datetime, timedelta
from typing import List
from pydantic import BaseModel
from backend.schemas.prediction import ECLOPredictionRequest, ECLOPredictionResponse
from backend.services import prediction_service
from backend.tasks.prediction_tasks import batch_predict_eclo

router = APIRouter()


class BatchPredictionRequest(BaseModel):
    """Batch prediction request schema"""
    accidents: List[ECLOPredictionRequest]


class BatchPredictionResponse(BaseModel):
    """Batch prediction response schema"""
    batch_id: str
    status: str
    total: int
    results_url: str
    estimated_completion: datetime


@router.post("/predict/eclo", response_model=ECLOPredictionResponse)
async def predict_eclo(request: ECLOPredictionRequest):
    """
    Single ECLO prediction
    
    Predicts ECLO value based on accident conditions.
    """
    try:
        # Convert request to feature dictionary
        features = {
            "기상상태": request.weather,
            "노면상태": request.road_surface,
            "도로형태": request.road_type,
            "사고유형": request.accident_type,
            "시간대": request.time_period,
            "시군구": request.district,
            "요일": request.day_of_week,
            "사고시": request.accident_hour,
            "사고연": request.accident_year,
            "사고월": request.accident_month,
            "사고일": request.accident_day,
        }
        
        # Predict ECLO
        eclo_value = prediction_service.predict_single_eclo(features)
        interpretation = prediction_service.interpret_eclo(eclo_value)
        detail = prediction_service.interpret_eclo_detail(eclo_value)
        
        # Return response
        return ECLOPredictionResponse(
            eclo=eclo_value,
            interpretation=interpretation,
            detail=detail,
            model_version="v1.0",
            timestamp=datetime.utcnow()
        )
        
    except ValueError as e:
        # Invalid input (400 Bad Request)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Invalid input",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    except FileNotFoundError as e:
        # Model file not found (500 Internal Server Error)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Model not available",
                "message": "ECLO prediction model files are missing. Please contact the administrator.",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        # Other errors (500 Internal Server Error)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Prediction failed",
                "message": f"An unexpected error occurred: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.post("/predict/eclo/batch", response_model=BatchPredictionResponse, status_code=status.HTTP_202_ACCEPTED)
async def batch_predict_eclo_endpoint(request: BatchPredictionRequest):
    """
    Batch ECLO prediction

    Queues multiple accident predictions for background processing via Celery.
    Returns a batch_id that can be used to poll for results.
    """
    # Check queue size limit (100 max)
    if len(request.accidents) > 100:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Queue full",
                "message": f"Batch size exceeds limit. Maximum 100 predictions allowed, got {len(request.accidents)}.",
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    # Convert requests to feature dictionaries
    accidents_data = []
    for acc in request.accidents:
        features = {
            "기상상태": acc.weather,
            "노면상태": acc.road_surface,
            "도로형태": acc.road_type,
            "사고유형": acc.accident_type,
            "시간대": acc.time_period,
            "시군구": acc.district,
            "요일": acc.day_of_week,
            "사고시": acc.accident_hour,
            "사고연": acc.accident_year,
            "사고월": acc.accident_month,
            "사고일": acc.accident_day,
        }
        accidents_data.append(features)

    # Queue Celery task
    task = batch_predict_eclo.delay(accidents_data)

    # Estimate completion time (roughly 2 seconds per prediction)
    estimated_seconds = len(accidents_data) * 2
    estimated_completion = datetime.utcnow() + timedelta(seconds=estimated_seconds)

    return BatchPredictionResponse(
        batch_id=task.id,
        status="processing",
        total=len(accidents_data),
        results_url=f"/api/predict/batch/{task.id}/results",
        estimated_completion=estimated_completion
    )


@router.get("/predict/batch/{batch_id}/results")
async def get_batch_results(batch_id: str):
    """
    Poll batch prediction results

    Returns the status and results of a batch prediction task.
    """
    from celery.result import AsyncResult

    task = AsyncResult(batch_id)

    if task.state == 'PENDING':
        return {
            "batch_id": batch_id,
            "status": "pending",
            "message": "Task is queued and waiting to be processed."
        }
    elif task.state == 'PROCESSING':
        return {
            "batch_id": batch_id,
            "status": "processing",
            "progress": task.info.get('progress', 0),
            "total": task.info.get('total', 0),
            "message": "Task is currently being processed."
        }
    elif task.state == 'SUCCESS':
        return {
            "batch_id": batch_id,
            "status": "success",
            "results": task.result,
            "message": "Batch prediction completed successfully."
        }
    elif task.state == 'FAILURE':
        return {
            "batch_id": batch_id,
            "status": "failed",
            "error": str(task.info),
            "message": "Batch prediction failed."
        }
    else:
        return {
            "batch_id": batch_id,
            "status": task.state.lower(),
            "message": f"Task state: {task.state}"
        }
