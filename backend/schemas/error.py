"""
Standardized error response schemas.

This module defines the error models for consistent API error responses.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """
    Standardized error response model.

    Used across all API endpoints for consistent error handling.
    """

    error: str = Field(..., description="Error type or code")
    detail: str = Field(..., description="Human-readable error message")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Error occurrence timestamp"
    )
    path: Optional[str] = Field(None, description="Request path that caused the error")

    class Config:
        schema_extra = {
            "example": {
                "error": "ValidationError",
                "detail": "Invalid input format",
                "timestamp": "2024-12-10T12:00:00Z",
                "path": "/api/datasets/upload"
            }
        }


class ValidationErrorResponse(BaseModel):
    """
    Validation error response with field-level details.
    """

    error: str = Field(default="ValidationError", description="Error type")
    detail: str = Field(..., description="General validation error message")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Error occurrence timestamp"
    )
    fields: Optional[dict] = Field(
        None,
        description="Field-specific validation errors"
    )

    class Config:
        schema_extra = {
            "example": {
                "error": "ValidationError",
                "detail": "Request validation failed",
                "timestamp": "2024-12-10T12:00:00Z",
                "fields": {
                    "email": "Invalid email format",
                    "age": "Must be a positive integer"
                }
            }
        }
