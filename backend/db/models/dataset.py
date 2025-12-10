"""
Dataset model
"""
from sqlalchemy import Column, Integer, String, BigInteger, TIMESTAMP, func, CheckConstraint
from sqlalchemy.orm import relationship
from backend.db.base import Base


class Dataset(Base):
    """Dataset model for uploaded CSV files"""
    __tablename__ = "datasets"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)
    file_path = Column(String(500), nullable=False)
    rows = Column(Integer, CheckConstraint("rows >= 0"), nullable=True)
    columns = Column(Integer, CheckConstraint("columns >= 0"), nullable=True)
    size_bytes = Column(BigInteger, CheckConstraint("size_bytes >= 0 AND size_bytes <= 52428800"), nullable=True)
    uploaded_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    
    # Relationships
    conversations = relationship("Conversation", back_populates="dataset", cascade="all, delete-orphan")
    share_tokens = relationship("ShareToken", back_populates="dataset", cascade="all, delete-orphan")
