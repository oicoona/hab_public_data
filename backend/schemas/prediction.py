"""
Prediction Pydantic schemas
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class ECLOPredictionRequest(BaseModel):
    """Request schema for ECLO prediction"""
    weather: str = Field(..., description="날씨 (맑음, 흐림, 비, 눈 등)")
    road_surface: str = Field(..., description="노면 상태 (건조, 습기, 젖음 등)")
    road_type: str = Field(..., description="도로 형태 (교차로, 단일로, 기타 등)")
    accident_type: str = Field(..., description="사고 유형 (차대차, 차대사람 등)")
    time_period: str = Field(..., description="시간대 (낮, 밤)")
    district: str = Field(..., description="구 (중구, 남구 등)")
    day_of_week: str = Field(..., description="요일 (월요일, 화요일 등)")
    accident_hour: int = Field(..., ge=0, le=23, description="사고 시각 (0-23)")
    accident_year: int = Field(..., description="사고 연도")
    accident_month: int = Field(..., ge=1, le=12, description="사고 월 (1-12)")
    accident_day: int = Field(..., ge=1, le=31, description="사고 일 (1-31)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "weather": "맑음",
                "road_surface": "건조",
                "road_type": "교차로",
                "accident_type": "차대차",
                "time_period": "낮",
                "district": "중구",
                "day_of_week": "월요일",
                "accident_hour": 14,
                "accident_year": 2024,
                "accident_month": 12,
                "accident_day": 8
            }
        }


class ECLOPredictionResponse(BaseModel):
    """Response schema for ECLO prediction"""
    eclo: float = Field(..., description="ECLO 예측값")
    interpretation: str = Field(..., description="해석 (경미, 일반, 심각, 사망)")
    detail: str = Field(..., description="상세 설명")
    prediction_id: Optional[str] = Field(None, description="예측 ID")
    model_version: str = Field(..., description="모델 버전")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="예측 시각")
    
    class Config:
        json_schema_extra = {
            "example": {
                "eclo": 0.23,
                "interpretation": "일반",
                "detail": "일반적인 사고 수준입니다. 경상 가능성이 있으며, 치료가 필요할 수 있습니다.",
                "prediction_id": "pred_789",
                "model_version": "v1.0",
                "timestamp": "2024-12-10T00:00:00Z"
            }
        }
