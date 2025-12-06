"""
LangGraph-based AI chatbot module for data Q&A.

v1.2: LangGraph StateGraph 기반 Tool Calling
- 기존 Anthropic API 직접 호출 → LangGraph 워크플로우
- astream_events를 통한 스트리밍 지원
"""
import time
import asyncio
import pandas as pd
from typing import Generator, AsyncGenerator

from anthropic import Anthropic, APIError, APIConnectionError, RateLimitError
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_anthropic import ChatAnthropic

from utils.tools import get_all_tools, TOOLS, execute_tool
from utils.graph import ChatState, build_graph

# Maximum iterations for tool calling loop
MAX_TOOL_ITERATIONS = 3

# System prompt for data analysis
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
- 시각화 코드 요청 시 Plotly 기반 예시 제공

중요: 데이터 분석 질문에 답변할 때는 제공된 도구(tools)를 사용하여 정확한 정보를 얻으세요.
데이터와 관련 없는 일반 질문에는 도구 없이 직접 답변해도 됩니다."""


def create_data_context(df: pd.DataFrame, dataset_name: str) -> str:
    """
    Create context string from DataFrame for AI prompts.

    Parameters:
        df (pd.DataFrame): Dataset to analyze
        dataset_name (str): Name of the dataset

    Returns:
        str: Formatted context string
    """
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


def handle_chat_error(error: Exception) -> str:
    """
    Handle API errors and return user-friendly message.

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
    return api_key.startswith('sk-ant-') and len(api_key) > 20


# ============================================================================
# LangGraph-based Implementation (v1.2)
# ============================================================================

def create_langgraph_model(api_key: str, model: str = "claude-sonnet-4-20250514") -> ChatAnthropic:
    """
    LangChain ChatAnthropic 모델을 생성합니다.

    Parameters:
        api_key: Anthropic API Key
        model: 모델 ID

    Returns:
        ChatAnthropic 인스턴스
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
    df: pd.DataFrame,
    dataset_name: str = ""
) -> tuple[str, dict]:
    """
    LangGraph를 사용하여 챗봇 응답을 생성합니다.

    Parameters:
        api_key: Anthropic API Key
        model: 모델 ID
        messages: 대화 이력
        data_context: 데이터 컨텍스트
        df: DataFrame
        dataset_name: 데이터셋 이름

    Returns:
        tuple[str, dict]: (응답 텍스트, 사용량 정보)
    """
    try:
        # LangChain 모델 생성
        llm = create_langgraph_model(api_key, model)

        # 도구 가져오기
        tools = get_all_tools()

        # 시스템 프롬프트 구성
        full_system = f"{SYSTEM_PROMPT}\n\n{data_context}"

        # 그래프 빌드
        graph = build_graph(llm, tools, full_system)

        # 메시지 변환
        langchain_messages = []
        for msg in messages:
            if msg["role"] == "user":
                langchain_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                langchain_messages.append(AIMessage(content=msg["content"]))

        # 상태 초기화
        state = ChatState(
            messages=langchain_messages,
            current_dataset=dataset_name
        )

        # RunnableConfig 설정
        config = {
            "configurable": {
                "dataframe": df,
                "current_dataset": dataset_name,
            }
        }

        # 그래프 실행
        result = graph.invoke(state, config=config)

        # 마지막 AI 메시지 추출
        final_messages = result.get("messages", [])
        response_text = ""
        for msg in reversed(final_messages):
            if isinstance(msg, AIMessage) and msg.content:
                response_text = msg.content
                break

        # 사용량 정보 (LangGraph에서는 직접 추적하지 않음)
        usage_info = {"input_tokens": 0, "output_tokens": 0}

        return response_text, usage_info

    except Exception as e:
        error_msg = handle_chat_error(e)
        return error_msg, {"input_tokens": 0, "output_tokens": 0}


def stream_langgraph_chat(
    api_key: str,
    model: str,
    messages: list[dict],
    data_context: str,
    df: pd.DataFrame,
    dataset_name: str = ""
) -> Generator:
    """
    LangGraph를 사용하여 스트리밍 응답을 생성합니다.

    Parameters:
        api_key: Anthropic API Key
        model: 모델 ID
        messages: 대화 이력
        data_context: 데이터 컨텍스트
        df: DataFrame
        dataset_name: 데이터셋 이름

    Yields:
        str 또는 dict: 텍스트 청크 또는 이벤트 딕셔너리
    """
    try:
        # LangChain 모델 생성
        llm = create_langgraph_model(api_key, model)

        # 도구 가져오기
        tools = get_all_tools()

        # 시스템 프롬프트 구성
        full_system = f"{SYSTEM_PROMPT}\n\n{data_context}"

        # 그래프 빌드
        graph = build_graph(llm, tools, full_system)

        # 메시지 변환
        langchain_messages = []
        for msg in messages:
            if msg["role"] == "user":
                langchain_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                langchain_messages.append(AIMessage(content=msg["content"]))

        # 상태 초기화
        state = ChatState(
            messages=langchain_messages,
            current_dataset=dataset_name
        )

        # RunnableConfig 설정
        config = {
            "configurable": {
                "dataframe": df,
                "current_dataset": dataset_name,
            }
        }

        # 비동기 스트리밍을 동기로 래핑
        async def async_stream():
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

            # 최종 사용량 정보
            yield {"__usage__": {"input_tokens": 0, "output_tokens": 0}, "__text__": final_text}

        # 비동기 제너레이터를 동기로 실행
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            async_gen = async_stream()
            while True:
                try:
                    result = loop.run_until_complete(async_gen.__anext__())
                    yield result
                except StopAsyncIteration:
                    break
        finally:
            loop.close()

    except Exception as e:
        error_msg = handle_chat_error(e)
        yield error_msg
        yield {"__usage__": {"input_tokens": 0, "output_tokens": 0}, "__text__": error_msg}


# ============================================================================
# Legacy Support (Backward Compatibility)
# ============================================================================

def create_chat_response(
    client: Anthropic,
    model: str,
    messages: list[dict],
    data_context: str,
    max_tokens: int = 2048
) -> tuple[str, dict]:
    """
    Create chat response using Anthropic API. (Legacy)
    """
    full_system = f"{SYSTEM_PROMPT}\n\n{data_context}"

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=full_system,
        messages=messages
    )

    response_text = response.content[0].text
    usage_info = {
        'input_tokens': response.usage.input_tokens,
        'output_tokens': response.usage.output_tokens
    }

    return response_text, usage_info


def run_tool_calling(
    client: Anthropic,
    model: str,
    messages: list[dict],
    data_context: str,
    df: pd.DataFrame,
    max_tokens: int = 4096
) -> tuple[str, dict]:
    """
    Run Tool Calling conversation loop with max iterations. (Legacy)
    """
    full_system = f"""{SYSTEM_PROMPT}

{data_context}

중요: 데이터 분석 질문에 답변할 때는 제공된 도구(tools)를 사용하여 정확한 정보를 얻으세요.
데이터와 관련 없는 일반 질문에는 도구 없이 직접 답변해도 됩니다."""

    total_usage = {'input_tokens': 0, 'output_tokens': 0}
    working_messages = messages.copy()

    for iteration in range(MAX_TOOL_ITERATIONS):
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=full_system,
            tools=TOOLS,
            messages=working_messages
        )

        total_usage['input_tokens'] += response.usage.input_tokens
        total_usage['output_tokens'] += response.usage.output_tokens

        if response.stop_reason != "tool_use":
            response_text = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    response_text += block.text
            return response_text, total_usage

        tool_uses = [b for b in response.content if b.type == "tool_use"]
        tool_results = []

        for tool_use in tool_uses:
            result = execute_tool(tool_use.name, tool_use.input, df)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": str(result)
            })

        working_messages.append({"role": "assistant", "content": response.content})
        working_messages.append({"role": "user", "content": tool_results})

    return "현재 앱이 답변할 수 없는 질문입니다. 질문을 더 구체적으로 해주세요.", total_usage


def create_chat_response_with_tools(
    client: Anthropic,
    model: str,
    messages: list[dict],
    data_context: str,
    df: pd.DataFrame,
    max_tokens: int = 4096
) -> tuple[str, dict]:
    """
    Create chat response using Tool Calling. (Legacy)
    """
    try:
        return run_tool_calling(client, model, messages, data_context, df, max_tokens)
    except Exception as e:
        error_msg = handle_chat_error(e)
        return error_msg, {'input_tokens': 0, 'output_tokens': 0}


def stream_chat_response_with_tools(
    client: Anthropic,
    model: str,
    messages: list[dict],
    data_context: str,
    df: pd.DataFrame,
    max_tokens: int = 4096
):
    """
    Stream chat response with Tool Calling support. (Legacy)
    """
    full_system = f"""{SYSTEM_PROMPT}

{data_context}

중요: 데이터 분석 질문에 답변할 때는 제공된 도구(tools)를 사용하여 정확한 정보를 얻으세요.
데이터와 관련 없는 일반 질문에는 도구 없이 직접 답변해도 됩니다."""

    total_usage = {'input_tokens': 0, 'output_tokens': 0}
    working_messages = messages.copy()
    final_text = ""

    for iteration in range(MAX_TOOL_ITERATIONS):
        with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=full_system,
            tools=TOOLS,
            messages=working_messages
        ) as stream:
            current_text = ""
            for text in stream.text_stream:
                current_text += text
                yield text

            final_message = stream.get_final_message()
            total_usage['input_tokens'] += final_message.usage.input_tokens
            total_usage['output_tokens'] += final_message.usage.output_tokens

            if final_message.stop_reason != "tool_use":
                final_text = current_text
                break

            tool_uses = [b for b in final_message.content if b.type == "tool_use"]

            if not tool_uses:
                final_text = current_text
                break

            total_tools = len(tool_uses)
            yield {'__tool_batch_start__': {'total': total_tools}}

            tool_results = []
            for idx, tool_use in enumerate(tool_uses, 1):
                tool_start_time = time.time()
                yield {'__tool_start__': {'name': tool_use.name, 'index': idx, 'total': total_tools}}

                result = execute_tool(tool_use.name, tool_use.input, df)

                elapsed = time.time() - tool_start_time
                yield {'__tool_end__': {'name': tool_use.name, 'index': idx, 'total': total_tools, 'elapsed': elapsed}}

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": str(result)
                })

            yield {'__tool_batch_end__': {'total': total_tools}}

            working_messages.append({"role": "assistant", "content": final_message.content})
            working_messages.append({"role": "user", "content": tool_results})

    if not final_text and iteration == MAX_TOOL_ITERATIONS - 1:
        yield {'__fallback_start__': True}
        try:
            fallback_system = f"""{SYSTEM_PROMPT}

{data_context}

주의: 데이터 분석 도구를 사용할 수 없습니다. 데이터셋 정보를 기반으로 가능한 범위 내에서 답변해주세요."""

            with client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                system=fallback_system,
                messages=messages
            ) as fallback_stream:
                for text in fallback_stream.text_stream:
                    final_text += text
                    yield text

                fallback_message = fallback_stream.get_final_message()
                total_usage['input_tokens'] += fallback_message.usage.input_tokens
                total_usage['output_tokens'] += fallback_message.usage.output_tokens

        except Exception:
            final_text = "현재 앱이 답변할 수 없는 질문입니다. 질문을 더 구체적으로 해주세요."
            yield final_text

        yield {'__fallback_end__': True}

    yield {'__usage__': total_usage, '__text__': final_text}
