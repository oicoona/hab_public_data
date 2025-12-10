"""
Prediction model
"""
from sqlalchemy import Column, Integer, String, DECIMAL, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import JSONB
from backend.db.base import Base


class Prediction(Base):
    """Prediction model for ECLO prediction results"""
    __tablename__ = "predictions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    model_version = Column(String(50), nullable=True)
    input_features = Column(JSONB, nullable=False)
    eclo_value = Column(DECIMAL(10, 4), nullable=True)
    interpretation = Column(String(50), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
