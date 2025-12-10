"""
Chat service with LangGraph-based AI chatbot logic (backend version).

Migrated from utils/chatbot.py and utils/graph.py with database and Redis integration.
Handles conversation management, caching, and LLM interaction.
"""
import hashlib
import json
from typing import Optional, Generator, Literal
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict
from typing import Annotated

from backend.core.cache import redis_client
from backend.services.analysis_service import get_all_tools


# ============================================================================
# Constants
# ============================================================================

MAX_TOOL_ITERATIONS = 3

# System prompts
SYSTEM_PROMPT_BASE = """당신은 데이터 분석 전문가입니다. 사용자가 업로드한 CSV 데이터셋에 대한 질문에 답변합니다.

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
- 시각화 코드 요청 시 Plotly 기반 예시 제공

중요: 데이터 분석 질문에 답변할 때는 제공된 도구(tools)를 사용하여 정확한 정보를 얻으세요.
데이터와 관련 없는 일반 질문에는 도구 없이 직접 답변해도 됩니다."""

ECLO_PREDICTION_PROMPT = """
## ECLO 예측 기능

사용자가 교통사고 ECLO(사고 심각도) 예측을 요청하면, **어떤 데이터셋이 활성화되어 있든** predict_eclo 도구를 사용할 수 있습니다.
단일 건 또는 여러 건의 사고 데이터를 동시에 예측할 수 있습니다.

### ECLO 예측 요청 감지
다음과 같은 표현이 나오면 ECLO 예측 의도로 판단하세요:
- "ECLO 예측해줘", "사고 심각도 예측", "ECLO 값 알려줘"
- 날짜, 시간, 장소, 기상 조건 등 사고 정보와 함께 "예측" 언급
- "여러 건", "다음 사고들", "N개 사고" 등 배치 예측 요청

### 필수 피처 11개
ECLO 예측에는 다음 11개 정보가 필요합니다:
1. weather (기상상태): 맑음, 흐림, 비, 눈, 안개, 기타
2. road_surface (노면상태): 건조, 젖음/습기, 적설, 서리/결빙, 침수, 기타
3. road_type (도로형태): 교차로 - 교차로안, 단일로 - 기타 등
4. accident_type (사고유형): 차대차, 차대사람, 차량단독
5. time_period (시간대): 심야, 출근시간대, 일반시간대, 퇴근시간대
6. district (시군구): 대구광역시 내 상세 주소
7. day_of_week (요일): 월요일~일요일
8. accident_hour (사고시): 0-23
9. accident_year (사고연): 연도
10. accident_month (사고월): 1-12
11. accident_day (사고일): 1-31

### 재질문 규칙
사용자가 일부 정보만 제공한 경우, 제공된 정보를 파싱하여 확인하고 누락된 피처를 친절하게 질문하세요.
"""

SYSTEM_PROMPT = SYSTEM_PROMPT_BASE + ECLO_PREDICTION_PROMPT


# ============================================================================
# LangGraph State Definition
# ============================================================================

class ChatState(TypedDict):
    """AI chatbot workflow state."""
    messages: Annotated[list[BaseMessage], add_messages]
    current_dataset: str


# ============================================================================
# Helper Functions
# ============================================================================

def create_data_context(df, dataset_name: str) -> str:
    """
    Create context string from DataFrame for AI prompts.

    Args:
        df: pandas DataFrame
        dataset_name: Name of the dataset

    Returns:
        Formatted context string
    """
    import pandas as pd

    row_count = len(df)
    col_count = len(df.columns)

    col_info = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        missing = df[col].isnull().sum()
        missing_pct = (missing / row_count * 100) if row_count > 0 else 0

        if pd.api.types.is_numeric_dtype(df[col]):
            col_min = df[col].min()
            col_max = df[col].max()
            col_mean = df[col].mean()
            if pd.isna(col_min) or pd.isna(col_max) or pd.isna(col_mean):
                stats = "모든 값이 결측치입니다"
            else:
                stats = f"min={col_min:.2f}, max={col_max:.2f}, mean={col_mean:.2f}"
        else:
            unique = df[col].nunique()
            top_values = df[col].value_counts().head(3).to_dict()
            stats = f"unique={unique}, top3={top_values}"

        col_info.append(f"  - {col} ({dtype}): {stats}, 결측값 {missing_pct:.1f}%")

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


def get_cache_key(dataset_id: Optional[int], message: str) -> str:
    """
    Generate Redis cache key for chat response.

    Args:
        dataset_id: ID of the dataset (None for general questions)
        message: User's message

    Returns:
        Cache key string
    """
    # Normalize message (lowercase, strip whitespace)
    normalized = message.strip().lower()

    # Create hash of message for consistent key length
    msg_hash = hashlib.md5(normalized.encode()).hexdigest()

    # Include dataset_id in key to separate caches per dataset
    dataset_part = f"dataset_{dataset_id}" if dataset_id else "general"

    return f"chat:{dataset_part}:{msg_hash}"


def get_cached_response(dataset_id: Optional[int], message: str) -> Optional[str]:
    """
    Get cached response from Redis if available.

    Args:
        dataset_id: ID of the dataset
        message: User's message

    Returns:
        Cached response text or None if not found
    """
    if not redis_client:
        return None

    try:
        cache_key = get_cache_key(dataset_id, message)
        cached = redis_client.get(cache_key)

        if cached:
            # Redis returns bytes, decode to string
            return cached.decode('utf-8') if isinstance(cached, bytes) else cached

        return None
    except Exception as e:
        # Log error but don't fail the request
        print(f"Cache get error: {e}")
        return None


def cache_response(dataset_id: Optional[int], message: str, response: str, ttl: int = 3600):
    """
    Cache response in Redis with TTL.

    Args:
        dataset_id: ID of the dataset
        message: User's message
        response: Assistant's response
        ttl: Time to live in seconds (default: 1 hour)
    """
    if not redis_client:
        return

    try:
        cache_key = get_cache_key(dataset_id, message)
        redis_client.setex(cache_key, ttl, response)
    except Exception as e:
        # Log error but don't fail the request
        print(f"Cache set error: {e}")


# ============================================================================
# LangGraph Building Functions
# ============================================================================

def route_tools(state: ChatState) -> Literal["tools", "__end__"]:
    """
    Conditional routing based on tool_calls existence.

    Args:
        state: Current ChatState

    Returns:
        "tools" if tool_calls exist, else END
    """
    messages = state.get("messages", [])
    if not messages:
        return END

    last_message = messages[-1]

    # If AIMessage has tool_calls, route to tools node
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"

    return END


def build_graph(
    model: ChatAnthropic,
    tools: list,
    system_prompt: str = ""
):
    """
    Build and compile LangGraph StateGraph.

    Args:
        model: ChatAnthropic model instance
        tools: List of tools to use
        system_prompt: System prompt

    Returns:
        Compiled StateGraph
    """
    # Bind tools to model
    model_with_tools = model.bind_tools(tools)

    def chatbot_node(state: ChatState) -> dict:
        """Chatbot node: LLM invocation."""
        messages = state.get("messages", [])

        # Add system prompt as first message if provided
        if system_prompt:
            system_msg = SystemMessage(content=system_prompt)
            full_messages = [system_msg] + list(messages)
        else:
            full_messages = list(messages)

        response = model_with_tools.invoke(full_messages)
        return {"messages": [response]}

    # Create graph builder
    graph_builder = StateGraph(ChatState)

    # Add nodes
    graph_builder.add_node("chatbot", chatbot_node)
    graph_builder.add_node("tools", ToolNode(tools=tools))

    # Set edges
    graph_builder.set_entry_point("chatbot")
    graph_builder.add_conditional_edges(
        "chatbot",
        route_tools,
        {
            "tools": "tools",
            END: END
        }
    )
    graph_builder.add_edge("tools", "chatbot")

    # Compile graph
    return graph_builder.compile()


# ============================================================================
# Chat Execution Functions
# ============================================================================

def create_langgraph_model(api_key: str, model: str = "claude-sonnet-4-20250514") -> ChatAnthropic:
    """
    Create LangChain ChatAnthropic model.

    Args:
        api_key: Anthropic API Key
        model: Model ID

    Returns:
        ChatAnthropic instance
    """
    return ChatAnthropic(
        api_key=api_key,
        model=model,
        max_tokens=4096,
    )


def run_langgraph_chat(
    api_key: str,
    model: str,
    messages: list[dict],
    data_context: str,
    df,
    dataset_name: str = "",
    dataset_id: Optional[int] = None
) -> tuple[str, dict, bool]:
    """
    Run LangGraph-based chatbot with caching.

    Args:
        api_key: Anthropic API Key
        model: Model ID
        messages: Conversation history
        data_context: Data context string
        df: pandas DataFrame
        dataset_name: Dataset name
        dataset_id: Dataset ID for caching

    Returns:
        tuple[str, dict, bool]: (response_text, usage_info, cache_hit)
    """
    # Check cache first
    if len(messages) > 0:
        last_user_message = messages[-1].get("content", "")
        cached = get_cached_response(dataset_id, last_user_message)

        if cached:
            return cached, {"input_tokens": 0, "output_tokens": 0}, True

    try:
        # Create LangChain model
        llm = create_langgraph_model(api_key, model)

        # Get tools
        tools = get_all_tools()

        # Construct system prompt
        full_system = f"{SYSTEM_PROMPT}\n\n{data_context}"

        # Build graph
        graph = build_graph(llm, tools, full_system)

        # Convert messages to LangChain format
        langchain_messages = []
        for msg in messages:
            if msg["role"] == "user":
                langchain_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                langchain_messages.append(AIMessage(content=msg["content"]))

        # Initialize state
        state = ChatState(
            messages=langchain_messages,
            current_dataset=dataset_name
        )

        # RunnableConfig with dataframe
        config = {
            "configurable": {
                "dataframe": df,
                "current_dataset": dataset_name,
            }
        }

        # Execute graph
        result = graph.invoke(state, config=config)

        # Extract final AI message
        final_messages = result.get("messages", [])
        response_text = ""
        for msg in reversed(final_messages):
            if isinstance(msg, AIMessage) and msg.content:
                response_text = msg.content
                break

        # Usage info (not directly tracked in LangGraph)
        usage_info = {"input_tokens": 0, "output_tokens": 0}

        # Cache the response
        if len(messages) > 0 and response_text:
            cache_response(dataset_id, last_user_message, response_text)

        return response_text, usage_info, False

    except Exception as e:
        error_msg = f"챗봇 실행 중 오류가 발생했습니다: {str(e)}"
        return error_msg, {"input_tokens": 0, "output_tokens": 0}, False


async def stream_langgraph_chat(
    api_key: str,
    model: str,
    messages: list[dict],
    data_context: str,
    df,
    dataset_name: str = "",
    dataset_id: Optional[int] = None
) -> Generator:
    """
    Stream LangGraph-based chatbot responses.

    Args:
        api_key: Anthropic API Key
        model: Model ID
        messages: Conversation history
        data_context: Data context string
        df: pandas DataFrame
        dataset_name: Dataset name
        dataset_id: Dataset ID for caching

    Yields:
        str or dict: Text chunks or event dictionaries
    """
    # Check cache first
    if len(messages) > 0:
        last_user_message = messages[-1].get("content", "")
        cached = get_cached_response(dataset_id, last_user_message)

        if cached:
            yield cached
            yield {"__usage__": {"input_tokens": 0, "output_tokens": 0}, "__text__": cached, "__cache_hit__": True}
            return

    try:
        # Create LangChain model
        llm = create_langgraph_model(api_key, model)

        # Get tools
        tools = get_all_tools()

        # Construct system prompt
        full_system = f"{SYSTEM_PROMPT}\n\n{data_context}"

        # Build graph
        graph = build_graph(llm, tools, full_system)

        # Convert messages
        langchain_messages = []
        for msg in messages:
            if msg["role"] == "user":
                langchain_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                langchain_messages.append(AIMessage(content=msg["content"]))

        # Initialize state
        state = ChatState(
            messages=langchain_messages,
            current_dataset=dataset_name
        )

        # RunnableConfig
        config = {
            "configurable": {
                "dataframe": df,
                "current_dataset": dataset_name,
            }
        }

        # Stream events
        final_text = ""
        tool_count = 0

        async for event in graph.astream_events(state, config=config, version="v2"):
            event_type = event.get("event", "")

            if event_type == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    content = chunk.content
                    if isinstance(content, str):
                        final_text += content
                        yield content
                    elif isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict) and item.get("type") == "text":
                                text = item.get("text", "")
                                final_text += text
                                yield text

            elif event_type == "on_tool_start":
                tool_count += 1
                yield {
                    "__tool_start__": {
                        "name": event.get("name", ""),
                        "index": tool_count,
                        "total": tool_count
                    }
                }

            elif event_type == "on_tool_end":
                yield {
                    "__tool_end__": {
                        "name": event.get("name", ""),
                        "index": tool_count,
                        "total": tool_count,
                        "elapsed": 0
                    }
                }

        # Cache the response
        if len(messages) > 0 and final_text:
            cache_response(dataset_id, last_user_message, final_text)

        # Final usage info
        yield {"__usage__": {"input_tokens": 0, "output_tokens": 0}, "__text__": final_text, "__cache_hit__": False}

    except Exception as e:
        error_msg = f"챗봇 스트리밍 중 오류가 발생했습니다: {str(e)}"
        yield error_msg
        yield {"__usage__": {"input_tokens": 0, "output_tokens": 0}, "__text__": error_msg, "__cache_hit__": False}
