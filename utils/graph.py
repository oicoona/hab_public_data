"""
LangGraph StateGraph definition for AI chatbot workflow.

v1.2: LangGraph 기반 Tool Calling 워크플로우
- ChatState: 대화 상태 관리
- StateGraph: chatbot-tools 라우팅
"""
from typing import Annotated, Literal
from typing_extensions import TypedDict

from langchain_core.messages import BaseMessage, AIMessage
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode


class ChatState(TypedDict):
    """AI 챗봇 워크플로우 상태"""
    # 대화 이력 (LangGraph add_messages reducer 사용)
    messages: Annotated[list[BaseMessage], add_messages]
    # 현재 활성화된 데이터셋 이름
    current_dataset: str


def route_tools(state: ChatState) -> Literal["tools", "__end__"]:
    """
    tool_calls 유무에 따른 조건부 라우팅.

    Parameters:
        state: 현재 ChatState

    Returns:
        "tools" if tool_calls exist, else END
    """
    messages = state.get("messages", [])
    if not messages:
        return END

    last_message = messages[-1]

    # AIMessage이고 tool_calls가 있으면 tools 노드로 라우팅
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"

    return END


def build_graph(
    model: ChatAnthropic,
    tools: list,
    system_prompt: str = ""
) -> StateGraph:
    """
    LangGraph StateGraph를 구성하고 컴파일합니다.

    Parameters:
        model: ChatAnthropic 모델 인스턴스
        tools: 사용할 도구 리스트
        system_prompt: 시스템 프롬프트

    Returns:
        컴파일된 StateGraph
    """
    # 모델에 도구 바인딩
    model_with_tools = model.bind_tools(tools)

    def chatbot_node(state: ChatState) -> dict:
        """chatbot 노드: LLM 호출"""
        messages = state.get("messages", [])

        # 시스템 프롬프트가 있으면 첫 번째 메시지로 추가
        if system_prompt:
            from langchain_core.messages import SystemMessage
            system_msg = SystemMessage(content=system_prompt)
            full_messages = [system_msg] + list(messages)
        else:
            full_messages = list(messages)

        response = model_with_tools.invoke(full_messages)
        return {"messages": [response]}

    # 그래프 빌더 생성
    graph_builder = StateGraph(ChatState)

    # 노드 추가
    graph_builder.add_node("chatbot", chatbot_node)
    graph_builder.add_node("tools", ToolNode(tools=tools))

    # 엣지 설정
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

    # 그래프 컴파일
    return graph_builder.compile()


async def astream_graph_events(
    graph,
    state: ChatState,
    config: dict | None = None
):
    """
    LangGraph 이벤트를 비동기로 스트리밍합니다.

    Parameters:
        graph: 컴파일된 StateGraph
        state: 초기 ChatState
        config: RunnableConfig (optional)

    Yields:
        이벤트 딕셔너리 (텍스트 청크, 도구 이벤트 등)
    """
    config = config or {}

    async for event in graph.astream_events(state, config=config, version="v2"):
        event_type = event.get("event", "")

        if event_type == "on_chat_model_stream":
            # 텍스트 청크 스트리밍
            chunk = event.get("data", {}).get("chunk")
            if chunk and hasattr(chunk, "content") and chunk.content:
                yield {"type": "text", "content": chunk.content}

        elif event_type == "on_tool_start":
            # 도구 시작 이벤트
            yield {
                "type": "tool_start",
                "name": event.get("name", ""),
                "run_id": event.get("run_id", "")
            }

        elif event_type == "on_tool_end":
            # 도구 종료 이벤트
            yield {
                "type": "tool_end",
                "name": event.get("name", ""),
                "run_id": event.get("run_id", "")
            }
