"""
Dataset API routes.

Handles dataset upload, listing, sharing, and retrieval.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional

from backend.api.deps import get_db
from backend.schemas.dataset import (
    DatasetUploadResponse,
    DatasetListResponse,
    DatasetInfo,
    ShareLinkResponse,
    SharedDatasetResponse
)
from backend.services.dataset_service import (
    upload_dataset,
    get_dataset,
    list_datasets,
    create_share_token,
    get_dataset_by_token,
    delete_dataset
)
from backend.config import settings


router = APIRouter()


@router.post("/upload", response_model=DatasetUploadResponse)
async def upload_dataset_file(
    file: UploadFile = File(..., description="CSV file to upload"),
    description: Optional[str] = Form(None, description="Dataset description"),
    db: Session = Depends(get_db)
):
    """
    Upload a CSV dataset file.

    Args:
        file: CSV file (multipart/form-data)
        description: Optional dataset description
        db: Database session

    Returns:
        DatasetUploadResponse with dataset metadata

    Raises:
        HTTPException: 400 if validation fails, 500 if upload fails
    """
    try:
        # Read file
        contents = await file.read()
        file_size = len(contents)

        # Create file-like object for validation
        from io import BytesIO
        file_obj = BytesIO(contents)

        # Upload dataset
        dataset = upload_dataset(
            file=file_obj,
            filename=file.filename,
            size=file_size,
            description=description,
            db=db
        )

        return DatasetUploadResponse(
            id=dataset.id,
            name=dataset.name,
            description=dataset.description,
            file_path=dataset.file_path,
            rows=dataset.rows,
            columns=dataset.columns,
            size_bytes=dataset.size_bytes,
            uploaded_at=dataset.uploaded_at
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload dataset: {str(e)}"
        )


@router.get("", response_model=DatasetListResponse)
async def list_datasets_endpoint(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    List all datasets with pagination.

    Args:
        limit: Maximum number of datasets to return (default: 20)
        offset: Number of datasets to skip (default: 0)
        db: Database session

    Returns:
        DatasetListResponse with list of datasets and pagination info
    """
    datasets, total = list_datasets(limit=limit, offset=offset, db=db)

    return DatasetListResponse(
        datasets=[
            DatasetInfo(
                id=d.id,
                name=d.name,
                description=d.description,
                rows=d.rows,
                columns=d.columns,
                size_bytes=d.size_bytes,
                uploaded_at=d.uploaded_at
            )
            for d in datasets
        ],
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/{dataset_id}", response_model=DatasetInfo)
async def get_dataset_endpoint(
    dataset_id: int,
    db: Session = Depends(get_db)
):
    """
    Get dataset by ID.

    Args:
        dataset_id: Dataset ID
        db: Database session

    Returns:
        DatasetInfo with dataset metadata

    Raises:
        HTTPException: 404 if dataset not found
    """
    dataset = get_dataset(dataset_id, db)

    if not dataset:
        raise HTTPException(
            status_code=404,
            detail=f"Dataset {dataset_id} not found"
        )

    return DatasetInfo(
        id=dataset.id,
        name=dataset.name,
        description=dataset.description,
        rows=dataset.rows,
        columns=dataset.columns,
        size_bytes=dataset.size_bytes,
        uploaded_at=dataset.uploaded_at
    )


@router.post("/{dataset_id}/share", response_model=ShareLinkResponse)
async def create_share_link(
    dataset_id: int,
    db: Session = Depends(get_db)
):
    """
    Create a shareable link for a dataset.

    The share link is valid for 7 days.

    Args:
        dataset_id: Dataset ID
        db: Database session

    Returns:
        ShareLinkResponse with share token and URL

    Raises:
        HTTPException: 404 if dataset not found, 500 if token creation fails
    """
    try:
        share_token = create_share_token(dataset_id, db)

        # Construct share URL
        # In production, use settings.FRONTEND_URL
        share_url = f"http://localhost:8501?share_token={share_token.token}"

        return ShareLinkResponse(
            dataset_id=dataset_id,
            share_token=share_token.token,
            share_url=share_url,
            expires_at=share_token.expires_at
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create share link: {str(e)}"
        )


@router.get("/shared/{token}", response_model=SharedDatasetResponse)
async def get_shared_dataset(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Access a dataset via share token.

    Args:
        token: Share token
        db: Database session

    Returns:
        SharedDatasetResponse with dataset info

    Raises:
        HTTPException: 404 if token invalid or expired
    """
    dataset = get_dataset_by_token(token, db)

    if not dataset:
        raise HTTPException(
            status_code=404,
            detail="Share link invalid or expired"
        )

    # Get share token info
    from backend.db.models import ShareToken
    share_token = db.query(ShareToken).filter(
        ShareToken.token == token
    ).first()

    return SharedDatasetResponse(
        dataset=DatasetInfo(
            id=dataset.id,
            name=dataset.name,
            description=dataset.description,
            rows=dataset.rows,
            columns=dataset.columns,
            size_bytes=dataset.size_bytes,
            uploaded_at=dataset.uploaded_at
        ),
        share_token=token,
        expires_at=share_token.expires_at
    )


@router.delete("/{dataset_id}")
async def delete_dataset_endpoint(
    dataset_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a dataset.

    Args:
        dataset_id: Dataset ID
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: 404 if dataset not found
    """
    success = delete_dataset(dataset_id, db)

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Dataset {dataset_id} not found"
        )

    return {"message": f"Dataset {dataset_id} deleted successfully"}
