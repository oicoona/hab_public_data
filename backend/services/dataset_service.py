"""
Dataset management service.

Handles CSV file upload, validation, metadata extraction, and sharing.
"""
import os
import uuid
import secrets
from datetime import datetime, timedelta
from typing import Optional, BinaryIO
from pathlib import Path
import pandas as pd
from sqlalchemy.orm import Session

from backend.db.models import Dataset, ShareToken
from backend.config import settings


# Constants
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {'.csv'}
SHARE_TOKEN_EXPIRY_DAYS = 7
UPLOADS_DIR = Path("backend/uploads")


def ensure_uploads_directory() -> Path:
    """
    Ensure uploads directory exists.

    Returns:
        Path to uploads directory
    """
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    return UPLOADS_DIR


def validate_csv_file(file: BinaryIO, filename: str, size: int) -> None:
    """
    Validate uploaded CSV file.

    Args:
        file: File object
        filename: Original filename
        size: File size in bytes

    Raises:
        ValueError: If validation fails
    """
    # Check file extension
    file_ext = Path(filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Invalid file type. Only CSV files are allowed. Got: {file_ext}"
        )

    # Check file size
    if size > MAX_FILE_SIZE:
        max_mb = MAX_FILE_SIZE / (1024 * 1024)
        actual_mb = size / (1024 * 1024)
        raise ValueError(
            f"File too large. Maximum size: {max_mb}MB, uploaded: {actual_mb:.2f}MB"
        )

    # Try to read as CSV to validate format
    try:
        # Read first few rows to validate CSV format
        file.seek(0)
        df = pd.read_csv(file, nrows=5, encoding='utf-8')

        # Check if DataFrame has data
        if df.empty:
            raise ValueError("CSV file is empty")

        # Check if it has columns
        if len(df.columns) == 0:
            raise ValueError("CSV file has no columns")

    except pd.errors.EmptyDataError:
        raise ValueError("CSV file is empty")
    except pd.errors.ParserError as e:
        raise ValueError(f"Invalid CSV format: {str(e)}")
    except UnicodeDecodeError:
        raise ValueError("File encoding error. Please use UTF-8 encoding")
    finally:
        file.seek(0)  # Reset file pointer


def extract_metadata(file_path: Path) -> dict:
    """
    Extract metadata from CSV file.

    Args:
        file_path: Path to CSV file

    Returns:
        Dict with rows, columns, and size_bytes

    Raises:
        ValueError: If file cannot be read
    """
    try:
        # Read CSV to get row and column counts
        df = pd.read_csv(file_path, encoding='utf-8')

        # Get file size
        size_bytes = file_path.stat().st_size

        return {
            "rows": len(df),
            "columns": len(df.columns),
            "size_bytes": size_bytes
        }
    except Exception as e:
        raise ValueError(f"Failed to extract metadata: {str(e)}")


def upload_dataset(
    file: BinaryIO,
    filename: str,
    size: int,
    description: Optional[str],
    db: Session
) -> Dataset:
    """
    Upload and save dataset.

    Args:
        file: File object
        filename: Original filename
        size: File size in bytes
        description: Optional dataset description
        db: Database session

    Returns:
        Created Dataset model

    Raises:
        ValueError: If validation or upload fails
    """
    # Validate file
    validate_csv_file(file, filename, size)

    # Ensure uploads directory exists
    uploads_dir = ensure_uploads_directory()

    # Generate unique filename
    file_uuid = str(uuid.uuid4())
    file_ext = Path(filename).suffix
    unique_filename = f"{file_uuid}{file_ext}"
    file_path = uploads_dir / unique_filename

    # Save file
    try:
        file.seek(0)
        with open(file_path, 'wb') as f:
            f.write(file.read())
    except Exception as e:
        raise ValueError(f"Failed to save file: {str(e)}")

    # Extract metadata
    try:
        metadata = extract_metadata(file_path)
    except Exception as e:
        # Clean up file if metadata extraction fails
        file_path.unlink(missing_ok=True)
        raise e

    # Create dataset record
    dataset = Dataset(
        name=Path(filename).stem,  # Filename without extension
        description=description,
        file_path=str(file_path),
        rows=metadata["rows"],
        columns=metadata["columns"],
        size_bytes=metadata["size_bytes"],
        uploaded_at=datetime.utcnow()
    )

    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    return dataset


def get_dataset(dataset_id: int, db: Session) -> Optional[Dataset]:
    """
    Get dataset by ID.

    Args:
        dataset_id: Dataset ID
        db: Database session

    Returns:
        Dataset model or None if not found
    """
    return db.query(Dataset).filter(Dataset.id == dataset_id).first()


def list_datasets(
    limit: int,
    offset: int,
    db: Session
) -> tuple[list[Dataset], int]:
    """
    List datasets with pagination.

    Args:
        limit: Maximum number of datasets to return
        offset: Number of datasets to skip
        db: Database session

    Returns:
        Tuple of (datasets list, total count)
    """
    # Get total count
    total = db.query(Dataset).count()

    # Get paginated datasets
    datasets = db.query(Dataset).order_by(
        Dataset.uploaded_at.desc()
    ).limit(limit).offset(offset).all()

    return datasets, total


def create_share_token(dataset_id: int, db: Session) -> ShareToken:
    """
    Create share token for dataset.

    Args:
        dataset_id: Dataset ID
        db: Database session

    Returns:
        Created ShareToken model

    Raises:
        ValueError: If dataset not found
    """
    # Check dataset exists
    dataset = get_dataset(dataset_id, db)
    if not dataset:
        raise ValueError(f"Dataset {dataset_id} not found")

    # Check if active share token already exists
    existing_token = db.query(ShareToken).filter(
        ShareToken.dataset_id == dataset_id,
        ShareToken.expires_at > datetime.utcnow()
    ).first()

    if existing_token:
        return existing_token

    # Generate secure random token
    token = secrets.token_urlsafe(32)

    # Set expiry
    expires_at = datetime.utcnow() + timedelta(days=SHARE_TOKEN_EXPIRY_DAYS)

    # Create share token record
    share_token = ShareToken(
        dataset_id=dataset_id,
        token=token,
        expires_at=expires_at,
        created_at=datetime.utcnow()
    )

    db.add(share_token)
    db.commit()
    db.refresh(share_token)

    return share_token


def get_dataset_by_token(token: str, db: Session) -> Optional[Dataset]:
    """
    Get dataset by share token.

    Args:
        token: Share token
        db: Database session

    Returns:
        Dataset model or None if token invalid/expired
    """
    share_token = db.query(ShareToken).filter(
        ShareToken.token == token,
        ShareToken.expires_at > datetime.utcnow()
    ).first()

    if not share_token:
        return None

    return get_dataset(share_token.dataset_id, db)


def delete_dataset(dataset_id: int, db: Session) -> bool:
    """
    Delete dataset and associated file.

    Args:
        dataset_id: Dataset ID
        db: Database session

    Returns:
        True if deleted, False if not found
    """
    dataset = get_dataset(dataset_id, db)
    if not dataset:
        return False

    # Delete file
    try:
        file_path = Path(dataset.file_path)
        file_path.unlink(missing_ok=True)
    except Exception:
        pass  # Continue even if file deletion fails

    # Delete database record
    db.delete(dataset)
    db.commit()

    return True
