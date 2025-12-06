# Data Model: 대구 공공데이터 시각화 앱 v1.2

**Date**: 2025-12-06
**Feature**: 004-app-v12-upgrade

## 개요

v1.2에서 도입되는 주요 데이터 구조와 상태 관리 모델을 정의한다.

---

## 1. LangGraph State (상태)

LangGraph 워크플로우에서 사용하는 상태 구조.

```python
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages

class ChatState(TypedDict):
    """AI 챗봇 워크플로우 상태"""

    # 대화 이력 (LangGraph add_messages reducer 사용)
    messages: Annotated[list, add_messages]

    # 현재 활성화된 데이터셋 이름
    # 유효 값: "train", "test", "cctv", "security_light",
    #          "child_zone", "parking", "accident"
    current_dataset: str
```

### 필드 설명

| 필드 | 타입 | 설명 | 기본값 |
|------|------|------|--------|
| `messages` | `list[BaseMessage]` | 대화 이력. HumanMessage, AIMessage, ToolMessage 포함 | `[]` |
| `current_dataset` | `str` | 현재 분석 중인 데이터셋 이름 | `""` |

### 상태 전이

```
[초기 상태]
    │
    ├── messages: []
    └── current_dataset: ""

[사용자 메시지 추가]
    │
    ├── messages: [HumanMessage("데이터 구조를 알려줘")]
    └── current_dataset: "train"

[AI 응답 + 도구 호출]
    │
    ├── messages: [
    │       HumanMessage("데이터 구조를 알려줘"),
    │       AIMessage(tool_calls=[...]),
    │       ToolMessage(content="..."),
    │       AIMessage("분석 결과...")
    │   ]
    └── current_dataset: "train"
```

---

## 2. ECLO 예측 입력 (Feature Input)

predict_eclo 도구에 전달되는 피처 구조.

```python
from pydantic import BaseModel, Field
from typing import Literal

class ECLOFeatures(BaseModel):
    """ECLO 예측을 위한 11개 필수 피처"""

    # 범주형 피처 (7개)
    기상상태: str = Field(description="맑음, 흐림, 비, 눈, 안개 등")
    노면상태: str = Field(description="건조, 젖음, 적설, 결빙 등")
    도로형태: str = Field(description="직선, 곡선, 교차로 등")
    사고유형: str = Field(description="차대차, 차대사람, 차량단독 등")
    시간대: str = Field(description="새벽, 아침, 낮, 저녁, 밤")
    시군구: str = Field(description="대구 시군구명")
    요일: str = Field(description="월요일~일요일")

    # 수치형 피처 (4개)
    사고시: int = Field(ge=0, le=23, description="사고 발생 시각 (0-23)")
    사고연: int = Field(ge=2000, le=2030, description="사고 발생 연도")
    사고월: int = Field(ge=1, le=12, description="사고 발생 월")
    사고일: int = Field(ge=1, le=31, description="사고 발생 일")
```

### 유효 값 목록 (Label Encoders 기준)

```python
VALID_VALUES = {
    "기상상태": ["맑음", "흐림", "비", "눈", "안개", "기타"],
    "노면상태": ["건조", "젖음/습기", "적설", "결빙", "기타"],
    "도로형태": ["단일로", "교차로", "횡단보도", "철길건널목", "기타"],
    "사고유형": ["차대차", "차대사람", "차량단독"],
    "시간대": ["새벽", "아침", "낮", "저녁", "밤"],
    "요일": ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
    # 시군구는 대구 지역 목록 (label_encoders.pkl에서 로드)
}
```

---

## 3. ECLO 예측 결과 (Prediction Output)

predict_eclo 도구의 반환 구조.

```python
class ECLOPrediction(BaseModel):
    """ECLO 예측 결과"""

    # 예측된 ECLO 값 (연속형)
    eclo_value: float = Field(description="예측된 ECLO 값")

    # 해석 (자연어)
    interpretation: str = Field(description="ECLO 값의 의미 해석")

    # 입력된 피처 요약
    input_summary: dict = Field(description="예측에 사용된 피처 요약")
```

### ECLO 해석 기준

| ECLO 범위 | 해석 |
|-----------|------|
| 0 ~ 0.1 | 경미한 사고 (부상 미미) |
| 0.1 ~ 0.5 | 일반적 사고 (경상 가능) |
| 0.5 ~ 1.0 | 심각한 사고 (중상 가능) |
| 1.0 이상 | 매우 심각한 사고 (치명상 가능) |

---

## 4. 도구 정의 (Tool Definition)

LangChain @tool 데코레이터를 사용하는 도구 구조.

```python
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

@tool
def get_dataframe_info(config: RunnableConfig) -> str:
    """
    DataFrame 기본 정보를 반환합니다.
    행/열 수, 컬럼명, 데이터 타입을 포함합니다.
    """
    df = config["configurable"]["dataframe"]
    # ... 기존 로직
```

### Config 구조

```python
config = {
    "configurable": {
        "dataframe": pd.DataFrame,      # 현재 활성 DataFrame
        "current_dataset": str,          # 데이터셋 이름
        "thread_id": str                 # (선택) 대화 스레드 ID
    }
}
```

---

## 5. 버전 히스토리 (Version History)

프로젝트 개요 탭에 표시할 버전 정보 구조.

```python
VERSION_HISTORY = [
    {
        "version": "v1.0",
        "title": "기초 구현",
        "features": ["7개 데이터셋 탐색", "Folium 지도 시각화"],
        "tools_count": None
    },
    {
        "version": "v1.1",
        "title": "AI 도입",
        "features": ["CSV 업로드", "Claude 챗봇"],
        "tools_count": None
    },
    {
        "version": "v1.1.1",
        "title": "Tool Calling",
        "features": ["Tool Calling 도입", "스트리밍"],
        "tools_count": 15
    },
    {
        "version": "v1.1.2",
        "title": "UX 개선",
        "features": ["도구 피드백 개선", "5개 도구 추가"],
        "tools_count": 20
    },
    {
        "version": "v1.1.3",
        "title": "UI 간소화",
        "features": ["UI 간소화", "버그 수정"],
        "tools_count": 20
    },
    {
        "version": "v1.2",
        "title": "LangGraph & ECLO",
        "features": ["LangGraph 전환", "ECLO 예측"],
        "tools_count": 21
    }
]
```

---

## 6. 챗봇 아키텍처 정보

프로젝트 개요 탭의 아키텍처 시각화 데이터.

```python
CHATBOT_ARCHITECTURE = {
    "workflow": {
        "nodes": ["chatbot", "tools"],
        "edges": [
            {"from": "START", "to": "chatbot"},
            {"from": "chatbot", "to": "tools", "condition": "tool_calls"},
            {"from": "chatbot", "to": "END", "condition": "no_tools"},
            {"from": "tools", "to": "chatbot"}
        ]
    },
    "tools": {
        "analysis": [
            "get_dataframe_info",
            "get_column_statistics",
            "get_missing_values",
            "get_value_counts",
            "filter_dataframe",
            "sort_dataframe",
            "get_correlation",
            "group_by_aggregate",
            "get_unique_values",
            "get_date_range",
            "get_outliers",
            "get_sample_rows",
            "calculate_percentile",
            "get_geo_bounds",
            "cross_tabulation",
            "analyze_missing_pattern",
            "get_column_correlation_with_target",
            "detect_data_types",
            "get_temporal_pattern",
            "summarize_categorical_distribution"
        ],
        "prediction": [
            "predict_eclo"
        ]
    }
}
```

---

## Entity Relationship

```
┌─────────────────┐      ┌─────────────────┐
│   ChatState     │      │  ECLOFeatures   │
├─────────────────┤      ├─────────────────┤
│ messages        │      │ 기상상태        │
│ current_dataset │──────│ 노면상태        │
└─────────────────┘      │ 도로형태        │
        │                │ ...             │
        │                └────────┬────────┘
        │                         │
        ▼                         ▼
┌─────────────────┐      ┌─────────────────┐
│     Tool        │      │ ECLOPrediction  │
├─────────────────┤      ├─────────────────┤
│ name            │      │ eclo_value      │
│ description     │      │ interpretation  │
│ input_schema    │      │ input_summary   │
└─────────────────┘      └─────────────────┘
```

---

## 데이터 흐름

```
1. 사용자 입력
   │
   ▼
2. ChatState.messages에 HumanMessage 추가
   │
   ▼
3. LangGraph chatbot 노드 실행
   │
   ├── tool_calls 있음 → tools 노드 실행
   │   │
   │   ├── 일반 분석 도구 → DataFrame 분석 결과
   │   │
   │   └── predict_eclo → ECLOFeatures 검증 → 모델 예측 → ECLOPrediction
   │
   └── tool_calls 없음 → 최종 응답 생성
   │
   ▼
4. ChatState.messages에 AIMessage 추가
   │
   ▼
5. 사용자에게 응답 스트리밍
```
