# Research: 대구 공공데이터 시각화 앱 v1.2 업그레이드

**Date**: 2025-12-06
**Feature**: 004-app-v12-upgrade

## 리서치 개요

v1.2 업그레이드를 위해 다음 기술적 결정이 필요하다:
1. LangGraph 통합 방식
2. 기존 도구 마이그레이션 전략
3. ECLO 예측 도구 설계
4. uv 패키지 관리자 도입 방식

---

## 1. LangGraph 통합 방식

### Decision: LangGraph prebuilt 패턴 사용

LangGraph의 `StateGraph`와 `ToolNode` 조합을 사용하여 기존 Tool Calling 루프를 대체한다.

### Rationale

1. **표준화된 패턴**: LangGraph의 prebuilt 모듈(`ToolNode`, `add_messages`)이 Tool Calling 패턴을 표준화
2. **교육적 가치**: material/14-15일차 학습 내용과 직접 연결
3. **확장성**: 향후 Checkpointer 추가 시 코드 변경 최소화
4. **스트리밍 지원**: LangGraph의 스트리밍 API가 기존 구현과 유사한 UX 제공

### Alternatives Considered

| 대안 | 장점 | 거부 사유 |
|------|------|----------|
| 기존 Anthropic API 유지 | 코드 변경 없음 | 교육 커리큘럼 목표 불충족 |
| LangChain만 사용 (LangGraph 없이) | 단순함 | 상태 관리 및 라우팅 직접 구현 필요 |
| Autogen/CrewAI 등 다른 프레임워크 | 다양한 기능 | 프로젝트 범위 초과, 복잡도 증가 |

### Implementation Pattern

```python
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

class State(TypedDict):
    messages: Annotated[list, add_messages]
    current_dataset: str

# 그래프 구성
graph_builder = StateGraph(State)
graph_builder.add_node("chatbot", chatbot_node)
graph_builder.add_node("tools", ToolNode(tools=all_tools))
graph_builder.add_conditional_edges("chatbot", route_tools)
graph_builder.set_entry_point("chatbot")
```

---

## 2. 기존 도구 마이그레이션 전략

### Decision: @tool 데코레이터로 점진적 변환

기존 20개 도구를 LangChain의 `@tool` 데코레이터 형식으로 변환한다.

### Rationale

1. **호환성**: LangGraph ToolNode가 @tool 데코레이터 도구를 네이티브 지원
2. **자동 스키마 생성**: Pydantic 타입 힌트에서 자동으로 JSON Schema 생성
3. **독립성**: 기존 도구 핸들러 로직 재사용 가능

### Migration Example

**AS-IS (기존)**:
```python
TOOLS = [
    {
        "name": "get_dataframe_info",
        "description": "DataFrame 기본 정보를 반환합니다.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    }
]

def get_dataframe_info(df: pd.DataFrame, **kwargs) -> str:
    ...
```

**TO-BE (v1.2)**:
```python
from langchain_core.tools import tool

@tool
def get_dataframe_info() -> str:
    """DataFrame 기본 정보를 반환합니다. 행/열 수, 컬럼명, 데이터 타입을 포함합니다."""
    df = get_current_dataframe()  # context에서 DataFrame 가져오기
    ...
```

### DataFrame 컨텍스트 전달 방식

**Decision**: `RunnableConfig`의 `configurable` 파라미터로 DataFrame 전달

```python
@tool
def get_dataframe_info(config: RunnableConfig) -> str:
    df = config["configurable"]["dataframe"]
    ...
```

---

## 3. ECLO 예측 도구 설계

### Decision: 단일 predict_eclo 도구 + LLM 재질문 로직

11개 피처를 모두 받는 단일 도구로 구현하고, 부족한 피처는 LLM이 자연스럽게 재질문하도록 한다.

### Rationale

1. **단순성**: 복잡한 상태 머신 없이 LLM의 자연어 능력 활용
2. **유연성**: 사용자가 한 번에 여러 피처를 제공하거나 나눠서 제공 가능
3. **교육적**: 도구 설명에서 필수 피처를 명확히 안내

### Tool Definition

```python
@tool
def predict_eclo(
    기상상태: str,
    노면상태: str,
    도로형태: str,
    사고유형: str,
    시간대: str,
    시군구: str,
    요일: str,
    사고시: int,
    사고연: int,
    사고월: int,
    사고일: int,
    config: RunnableConfig
) -> str:
    """
    ECLO(Equivalent Casualty Loss of life)를 예측합니다.

    이 도구는 train 또는 test 데이터셋이 활성화된 경우에만 사용 가능합니다.
    모든 11개 피처가 제공되어야 예측이 가능합니다.

    피처별 유효 값:
    - 기상상태: 맑음, 흐림, 비, 눈, 안개 등
    - 노면상태: 건조, 젖음, 적설, 결빙 등
    - 도로형태: 직선, 곡선, 교차로 등
    - 사고유형: 차대차, 차대사람, 차량단독 등
    - 시간대: 새벽, 아침, 낮, 저녁, 밤
    - 시군구: 대구 시군구명
    - 요일: 월요일~일요일
    - 사고시: 0-23 (시간)
    - 사고연: 연도 (예: 2023)
    - 사고월: 1-12
    - 사고일: 1-31

    사용자가 피처 정보를 충분히 제공하지 않았다면,
    이 도구를 호출하기 전에 추가 정보를 요청하세요.
    """
```

### 데이터셋 조건 검증

```python
def predict_eclo(..., config: RunnableConfig) -> str:
    current_dataset = config["configurable"].get("current_dataset", "")
    if current_dataset not in ["train", "test"]:
        return "ECLO 예측은 train 또는 test 데이터셋에서만 사용 가능합니다."
    ...
```

---

## 4. uv 패키지 관리자 도입

### Decision: uv 권장, pip 대안 유지

README에 uv를 기본 설치 방법으로 안내하되, pip 대안도 유지한다.

### Rationale

1. **속도**: uv는 pip 대비 10-100배 빠른 의존성 설치
2. **호환성**: requirements.txt 형식 그대로 사용 가능
3. **사용자 편의**: uv 미설치 사용자를 위해 pip 대안 유지

### README 업데이트

```markdown
## 빠른 시작

### uv 사용 (권장)

```bash
# uv 설치 (최초 1회)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 가상환경 생성 및 의존성 설치
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -r requirements.txt

# 앱 실행
streamlit run app.py
```

### pip 사용 (대안)

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```
```

---

## 5. 의존성 버전 결정

### Decision: 최신 안정 버전 사용

| 패키지 | 버전 | 선택 사유 |
|--------|------|----------|
| langchain | >=0.3.0 | 2024.12 기준 최신 안정 버전 |
| langchain-anthropic | >=0.3.0 | Claude 모델 래퍼 |
| langgraph | >=0.2.0 | StateGraph, ToolNode 지원 |

### requirements.txt 추가 내용

```
langchain>=0.3.0
langchain-anthropic>=0.3.0
langgraph>=0.2.0
```

---

## 6. 스트리밍 구현 방식

### Decision: LangGraph의 astream_events 사용

기존 `stream_chat_response_with_tools`의 UX를 유지하면서 LangGraph 스트리밍으로 전환한다.

### Rationale

1. **기존 UX 유지**: 토큰 단위 스트리밍, 도구 실행 상태 표시
2. **LangGraph 네이티브**: `astream_events` API가 도구 호출 이벤트 제공
3. **간단한 전환**: 기존 yield 패턴과 유사한 구조

### Implementation Pattern

```python
async def stream_with_langgraph(graph, state):
    async for event in graph.astream_events(state, version="v2"):
        if event["event"] == "on_chat_model_stream":
            # 텍스트 청크 yield
            yield event["data"]["chunk"].content
        elif event["event"] == "on_tool_start":
            # 도구 시작 이벤트
            yield {"__tool_start__": {"name": event["name"]}}
        elif event["event"] == "on_tool_end":
            # 도구 종료 이벤트
            yield {"__tool_end__": {"name": event["name"]}}
```

---

## 7. 프로젝트 개요 탭 확장

### Decision: Streamlit 네이티브 컴포넌트 사용

버전 히스토리와 아키텍처 시각화를 Streamlit의 기본 컴포넌트로 구현한다.

### Rationale

1. **단순성**: 추가 의존성 없음
2. **일관성**: 기존 UI 스타일과 동일
3. **교육적**: Streamlit 기본 기능만 사용

### Implementation

**버전 히스토리**: `st.expander` + `st.columns`로 타임라인 구현
**아키텍처 시각화**: Markdown 코드 블록 + `st.dataframe`으로 도구 목록 표시

---

## Research Summary

| 항목 | 결정 | 확신도 |
|------|------|--------|
| LangGraph 통합 | StateGraph + ToolNode 조합 | 높음 |
| 도구 마이그레이션 | @tool 데코레이터 + RunnableConfig | 높음 |
| ECLO 예측 | 단일 도구 + LLM 재질문 | 중간 |
| uv 도입 | 권장 (pip 대안 유지) | 높음 |
| 의존성 버전 | langchain>=0.3.0, langgraph>=0.2.0 | 높음 |
| 스트리밍 | astream_events | 중간 |
| UI 확장 | Streamlit 네이티브 | 높음 |

**다음 단계**: Phase 1 (data-model.md, contracts/, quickstart.md 생성)
