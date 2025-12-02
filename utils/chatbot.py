"""
Anthropic Claude chatbot module for data Q&A.
"""
import pandas as pd
from anthropic import Anthropic, APIError, APIConnectionError, RateLimitError

# System prompt for data analysis (T037)
SYSTEM_PROMPT = """당신은 데이터 분석 전문가입니다. 사용자가 업로드한 CSV 데이터셋에 대한 질문에 답변합니다.

핵심 역할:
- 데이터의 구조, 통계, 패턴에 대해 명확하게 설명
- 분석 인사이트와 해석 제공
- 추가 탐색 방향 제안

답변 가이드라인:
1. 한국어로 친절하게 답변
2. 데이터에 기반한 정확한 정보만 제공
3. 불확실한 경우 그 점을 명시
4. 기술적 용어는 쉽게 설명
5. 가능하면 구체적인 수치 포함

주의사항:
- 데이터에 없는 정보는 추측하지 않음
- 개인정보 보호 관련 민감 데이터 언급 자제
- 시각화 코드 요청 시 Plotly 기반 예시 제공"""


def create_data_context(df: pd.DataFrame, dataset_name: str) -> str:
    """
    Create context string from DataFrame for AI prompts. (T038)

    Parameters:
        df (pd.DataFrame): Dataset to analyze
        dataset_name (str): Name of the dataset

    Returns:
        str: Formatted context string
    """
    # Basic info
    row_count = len(df)
    col_count = len(df.columns)

    # Column info
    col_info = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        missing = df[col].isnull().sum()
        missing_pct = (missing / row_count * 100) if row_count > 0 else 0

        if pd.api.types.is_numeric_dtype(df[col]):
            stats = f"min={df[col].min():.2f}, max={df[col].max():.2f}, mean={df[col].mean():.2f}"
        else:
            unique = df[col].nunique()
            top_values = df[col].value_counts().head(3).to_dict()
            stats = f"unique={unique}, top3={top_values}"

        col_info.append(f"  - {col} ({dtype}): {stats}, 결측값 {missing_pct:.1f}%")

    # Sample data (first 3 rows as string)
    sample = df.head(3).to_string(index=False, max_colwidth=30)

    context = f"""## 데이터셋 정보: {dataset_name}

**기본 정보:**
- 행 수: {row_count:,}
- 컬럼 수: {col_count}

**컬럼 상세:**
{chr(10).join(col_info)}

**샘플 데이터 (처음 3행):**
```
{sample}
```"""

    return context


def create_chat_response(
    client: Anthropic,
    model: str,
    messages: list[dict],
    data_context: str,
    max_tokens: int = 2048
) -> tuple[str, dict]:
    """
    Create chat response using Anthropic API. (T039)

    Parameters:
        client: Anthropic client instance
        model (str): Model ID (e.g., 'claude-sonnet-4-20250514')
        messages (list[dict]): Conversation history
        data_context (str): Data context from create_data_context()
        max_tokens (int): Maximum tokens in response

    Returns:
        tuple[str, dict]: (response_text, usage_info)
            usage_info: {'input_tokens': int, 'output_tokens': int}
    """
    # Combine system prompt with data context
    full_system = f"{SYSTEM_PROMPT}\n\n{data_context}"

    # Create API request
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=full_system,
        messages=messages
    )

    # Extract response text
    response_text = response.content[0].text

    # Extract usage info
    usage_info = {
        'input_tokens': response.usage.input_tokens,
        'output_tokens': response.usage.output_tokens
    }

    return response_text, usage_info


def handle_chat_error(error: Exception) -> str:
    """
    Handle API errors and return user-friendly message. (T040)

    Parameters:
        error: Exception from API call

    Returns:
        str: User-friendly error message in Korean
    """
    if isinstance(error, APIConnectionError):
        return "네트워크 연결 오류가 발생했습니다. 인터넷 연결을 확인해주세요."
    elif isinstance(error, RateLimitError):
        return "API 요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요."
    elif isinstance(error, APIError):
        error_msg = str(error)
        if "authentication" in error_msg.lower() or "invalid" in error_msg.lower():
            return "API Key가 유효하지 않습니다. 올바른 API Key를 입력해주세요."
        elif "model" in error_msg.lower():
            return "선택한 모델을 사용할 수 없습니다. 다른 모델을 선택해주세요."
        else:
            return f"API 오류가 발생했습니다: {error_msg}"
    else:
        return f"예상치 못한 오류가 발생했습니다: {str(error)}"


def validate_api_key(api_key: str) -> bool:
    """
    Basic validation of API key format.

    Parameters:
        api_key (str): API key to validate

    Returns:
        bool: True if key appears valid
    """
    if not api_key:
        return False
    # Anthropic keys typically start with 'sk-ant-'
    return api_key.startswith('sk-ant-') and len(api_key) > 20
