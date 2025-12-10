"""
Dataset API request/response schemas.

This module defines the Pydantic models for dataset-related API endpoints.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class DatasetUploadResponse(BaseModel):
    """Response schema for dataset upload."""

    id: int = Field(..., description="Dataset ID")
    name: str = Field(..., description="Dataset name")
    description: Optional[str] = Field(None, description="Dataset description")
    file_path: str = Field(..., description="Path to uploaded file")
    rows: int = Field(..., description="Number of rows")
    columns: int = Field(..., description="Number of columns")
    size_bytes: int = Field(..., description="File size in bytes")
    uploaded_at: datetime = Field(..., description="Upload timestamp")


class DatasetInfo(BaseModel):
    """Dataset information schema."""

    id: int = Field(..., description="Dataset ID")
    name: str = Field(..., description="Dataset name")
    description: Optional[str] = Field(None, description="Dataset description")
    rows: int = Field(..., description="Number of rows")
    columns: int = Field(..., description="Number of columns")
    size_bytes: int = Field(..., description="File size in bytes")
    uploaded_at: datetime = Field(..., description="Upload timestamp")


class DatasetListResponse(BaseModel):
    """Response schema for dataset listing."""

    datasets: list[DatasetInfo] = Field(..., description="List of datasets")
    total: int = Field(..., description="Total number of datasets")
    limit: int = Field(..., description="Limit per page")
    offset: int = Field(..., description="Offset for pagination")


class ShareLinkResponse(BaseModel):
    """Response schema for share link generation."""

    dataset_id: int = Field(..., description="Dataset ID")
    share_token: str = Field(..., description="Share token")
    share_url: str = Field(..., description="Full shareable URL")
    expires_at: datetime = Field(..., description="Expiration timestamp")


class SharedDatasetResponse(BaseModel):
    """Response schema for shared dataset access."""

    dataset: DatasetInfo = Field(..., description="Dataset information")
    share_token: str = Field(..., description="Share token used")
    expires_at: datetime = Field(..., description="Token expiration")
