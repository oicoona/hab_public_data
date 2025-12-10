"""
Backend API Client for Streamlit Frontend
Handles HTTP requests to FastAPI backend with retry logic and error handling
"""
import os
import httpx
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get backend URL from environment
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


class BackendAPIError(Exception):
    """Custom exception for backend API errors"""
    pass


def predict_eclo_single(
    weather: str,
    road_surface: str,
    road_type: str,
    accident_type: str,
    time_period: str,
    district: str,
    day_of_week: str,
    accident_hour: int,
    accident_year: int,
    accident_month: int,
    accident_day: int,
    timeout: float = 5.0,
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    Call backend API for single ECLO prediction with retry logic
    
    Args:
        weather: 날씨
        road_surface: 노면 상태
        road_type: 도로 형태
        accident_type: 사고 유형
        time_period: 시간대
        district: 구
        day_of_week: 요일
        accident_hour: 사고 시각 (0-23)
        accident_year: 사고 연도
        accident_month: 사고 월 (1-12)
        accident_day: 사고 일 (1-31)
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts
        
    Returns:
        Prediction response dict with eclo, interpretation, detail, etc.
        
    Raises:
        BackendAPIError: If backend is unreachable after retries
    """
    url = f"{BACKEND_URL}/api/predict/eclo"
    payload = {
        "weather": weather,
        "road_surface": road_surface,
        "road_type": road_type,
        "accident_type": accident_type,
        "time_period": time_period,
        "district": district,
        "day_of_week": day_of_week,
        "accident_hour": accident_hour,
        "accident_year": accident_year,
        "accident_month": accident_month,
        "accident_day": accident_day
    }
    
    last_error = None
    for attempt in range(max_retries):
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                return response.json()
                
        except httpx.ConnectError as e:
            last_error = e
            if attempt < max_retries - 1:
                # Wait before retry (exponential backoff: 1s, 2s, 4s)
                import time
                time.sleep(2 ** attempt)
                continue
        except httpx.HTTPStatusError as e:
            # Don't retry on 4xx errors (client errors)
            if 400 <= e.response.status_code < 500:
                error_detail = e.response.json() if e.response.text else {"error": "Bad request"}
                raise BackendAPIError(f"Invalid request: {error_detail.get('message', str(e))}")
            # Retry on 5xx errors (server errors)
            last_error = e
            if attempt < max_retries - 1:
                import time
                time.sleep(2 ** attempt)
                continue
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                import time
                time.sleep(2 ** attempt)
                continue
    
    # All retries failed
    raise BackendAPIError(
        f"서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요. "
        f"(백엔드 URL: {BACKEND_URL}, 에러: {str(last_error)})"
    )


def check_backend_health(timeout: float = 2.0) -> bool:
    """
    Check if backend is healthy

    Args:
        timeout: Request timeout in seconds

    Returns:
        True if backend is healthy, False otherwise
    """
    try:
        url = f"{BACKEND_URL}/health"
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()
            return data.get("status") == "healthy"
    except Exception:
        return False


# ============================================================================
# Chat API Functions (Phase 4)
# ============================================================================

def send_chat_message(
    message: str,
    api_key: str,
    dataset_id: Optional[int] = None,
    conversation_id: Optional[int] = None,
    timeout: float = 30.0,
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    Send a chat message to backend AI chatbot

    Args:
        message: User's question/message
        api_key: Anthropic API key
        dataset_id: Optional dataset ID to analyze
        conversation_id: Optional conversation ID to continue
        timeout: Request timeout in seconds (default 30s for LLM calls)
        max_retries: Maximum retry attempts

    Returns:
        Response dict with:
            - conversation_id: int
            - message_id: int
            - content: str (AI response)
            - cache_hit: bool
            - timestamp: str
            - usage: dict (optional, token counts)

    Raises:
        BackendAPIError: If backend is unreachable or returns error
    """
    url = f"{BACKEND_URL}/api/chat/message"
    payload = {
        "message": message,
        "dataset_id": dataset_id,
        "conversation_id": conversation_id
    }
    headers = {
        "X-Anthropic-API-Key": api_key
    }

    last_error = None
    for attempt in range(max_retries):
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()

        except httpx.ConnectError as e:
            last_error = e
            if attempt < max_retries - 1:
                import time
                time.sleep(2 ** attempt)
                continue
        except httpx.HTTPStatusError as e:
            # Don't retry on 4xx errors
            if 400 <= e.response.status_code < 500:
                try:
                    error_detail = e.response.json()
                    error_msg = error_detail.get('detail', str(e))
                except:
                    error_msg = str(e)
                raise BackendAPIError(f"Chat API error: {error_msg}")
            # Retry on 5xx errors
            last_error = e
            if attempt < max_retries - 1:
                import time
                time.sleep(2 ** attempt)
                continue
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                import time
                time.sleep(2 ** attempt)
                continue

    # All retries failed
    raise BackendAPIError(
        f"챗봇 서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요. "
        f"(에러: {str(last_error)})"
    )


def get_conversation_history(
    conversation_id: int,
    timeout: float = 5.0
) -> Dict[str, Any]:
    """
    Get all messages in a conversation

    Args:
        conversation_id: ID of the conversation
        timeout: Request timeout in seconds

    Returns:
        Response dict with:
            - conversation_id: int
            - dataset_id: int or None
            - title: str
            - messages: list of dicts with role, content, created_at

    Raises:
        BackendAPIError: If conversation not found or backend error
    """
    url = f"{BACKEND_URL}/api/chat/conversations/{conversation_id}/messages"

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise BackendAPIError(f"대화 ID {conversation_id}를 찾을 수 없습니다.")
        raise BackendAPIError(f"대화 내역 로드 실패: {str(e)}")
    except Exception as e:
        raise BackendAPIError(f"대화 내역 로드 중 오류: {str(e)}")


def list_conversations(
    dataset_id: Optional[int] = None,
    limit: int = 20,
    offset: int = 0,
    timeout: float = 5.0
) -> Dict[str, Any]:
    """
    List conversations, optionally filtered by dataset

    Args:
        dataset_id: Optional dataset ID to filter by
        limit: Maximum number of conversations to return
        offset: Number of conversations to skip
        timeout: Request timeout in seconds

    Returns:
        Response dict with:
            - conversations: list of dicts with id, dataset_id, title, created_at, updated_at
            - limit: int
            - offset: int

    Raises:
        BackendAPIError: If backend error
    """
    url = f"{BACKEND_URL}/api/chat/conversations"
    params = {
        "limit": limit,
        "offset": offset
    }
    if dataset_id is not None:
        params["dataset_id"] = dataset_id

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        raise BackendAPIError(f"대화 목록 로드 중 오류: {str(e)}")


# ============================================================================
# Dataset API Functions (Phase 5)
# ============================================================================

def upload_dataset(
    file_path: str,
    description: Optional[str] = None,
    timeout: float = 30.0,
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    Upload a CSV dataset file to backend

    Args:
        file_path: Path to CSV file to upload
        description: Optional dataset description
        timeout: Request timeout in seconds (default 30s for large files)
        max_retries: Maximum retry attempts

    Returns:
        Response dict with:
            - id: int (dataset ID)
            - name: str
            - description: str or None
            - file_path: str (backend path)
            - rows: int
            - columns: int
            - size_bytes: int
            - uploaded_at: str

    Raises:
        BackendAPIError: If upload fails or file invalid
        FileNotFoundError: If file_path doesn't exist
    """
    import os
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")

    url = f"{BACKEND_URL}/api/datasets/upload"

    last_error = None
    for attempt in range(max_retries):
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (os.path.basename(file_path), f, 'text/csv')}
                data = {}
                if description:
                    data['description'] = description

                with httpx.Client(timeout=timeout) as client:
                    response = client.post(url, files=files, data=data)
                    response.raise_for_status()
                    return response.json()

        except httpx.HTTPStatusError as e:
            # Don't retry on 4xx errors (validation failures)
            if 400 <= e.response.status_code < 500:
                try:
                    error_detail = e.response.json()
                    error_msg = error_detail.get('detail', str(e))
                except:
                    error_msg = str(e)
                raise BackendAPIError(f"데이터셋 업로드 실패: {error_msg}")
            # Retry on 5xx errors
            last_error = e
            if attempt < max_retries - 1:
                import time
                time.sleep(2 ** attempt)
                continue
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                import time
                time.sleep(2 ** attempt)
                continue

    # All retries failed
    raise BackendAPIError(
        f"데이터셋 업로드 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요. "
        f"(에러: {str(last_error)})"
    )


def list_datasets(
    limit: int = 20,
    offset: int = 0,
    timeout: float = 5.0
) -> Dict[str, Any]:
    """
    List all uploaded datasets

    Args:
        limit: Maximum number of datasets to return
        offset: Number of datasets to skip
        timeout: Request timeout in seconds

    Returns:
        Response dict with:
            - datasets: list of dicts with id, name, description, rows, columns, size_bytes, uploaded_at
            - total: int (total count)
            - limit: int
            - offset: int

    Raises:
        BackendAPIError: If backend error
    """
    url = f"{BACKEND_URL}/api/datasets"
    params = {
        "limit": limit,
        "offset": offset
    }

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        raise BackendAPIError(f"데이터셋 목록 로드 중 오류: {str(e)}")


def get_dataset(
    dataset_id: int,
    timeout: float = 5.0
) -> Dict[str, Any]:
    """
    Get dataset metadata by ID

    Args:
        dataset_id: Dataset ID
        timeout: Request timeout in seconds

    Returns:
        Response dict with:
            - id: int
            - name: str
            - description: str or None
            - rows: int
            - columns: int
            - size_bytes: int
            - uploaded_at: str

    Raises:
        BackendAPIError: If dataset not found or backend error
    """
    url = f"{BACKEND_URL}/api/datasets/{dataset_id}"

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise BackendAPIError(f"데이터셋 ID {dataset_id}를 찾을 수 없습니다.")
        raise BackendAPIError(f"데이터셋 로드 실패: {str(e)}")
    except Exception as e:
        raise BackendAPIError(f"데이터셋 로드 중 오류: {str(e)}")


def create_share_link(
    dataset_id: int,
    timeout: float = 5.0
) -> Dict[str, Any]:
    """
    Create a shareable link for a dataset (valid for 7 days)

    Args:
        dataset_id: Dataset ID
        timeout: Request timeout in seconds

    Returns:
        Response dict with:
            - dataset_id: int
            - share_token: str
            - share_url: str
            - expires_at: str

    Raises:
        BackendAPIError: If dataset not found or backend error
    """
    url = f"{BACKEND_URL}/api/datasets/{dataset_id}/share"

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise BackendAPIError(f"데이터셋 ID {dataset_id}를 찾을 수 없습니다.")
        raise BackendAPIError(f"공유 링크 생성 실패: {str(e)}")
    except Exception as e:
        raise BackendAPIError(f"공유 링크 생성 중 오류: {str(e)}")


def get_shared_dataset(
    token: str,
    timeout: float = 5.0
) -> Dict[str, Any]:
    """
    Access a dataset via share token

    Args:
        token: Share token
        timeout: Request timeout in seconds

    Returns:
        Response dict with:
            - dataset: dict with id, name, description, rows, columns, size_bytes, uploaded_at
            - share_token: str
            - expires_at: str

    Raises:
        BackendAPIError: If token invalid/expired or backend error
    """
    url = f"{BACKEND_URL}/api/datasets/shared/{token}"

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise BackendAPIError("공유 링크가 유효하지 않거나 만료되었습니다.")
        raise BackendAPIError(f"공유 데이터셋 로드 실패: {str(e)}")
    except Exception as e:
        raise BackendAPIError(f"공유 데이터셋 로드 중 오류: {str(e)}")


def delete_dataset(
    dataset_id: int,
    timeout: float = 5.0
) -> bool:
    """
    Delete a dataset

    Args:
        dataset_id: Dataset ID
        timeout: Request timeout in seconds

    Returns:
        True if deleted successfully

    Raises:
        BackendAPIError: If dataset not found or backend error
    """
    url = f"{BACKEND_URL}/api/datasets/{dataset_id}"

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.delete(url)
            response.raise_for_status()
            return True
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise BackendAPIError(f"데이터셋 ID {dataset_id}를 찾을 수 없습니다.")
        raise BackendAPIError(f"데이터셋 삭제 실패: {str(e)}")
    except Exception as e:
        raise BackendAPIError(f"데이터셋 삭제 중 오류: {str(e)}")
