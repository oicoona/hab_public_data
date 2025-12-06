# 대구 공공데이터 시각화 앱 개선 제안서 (v1.1.3 → v1.2)

**문서 버전**: v1.2
**작성일**: 2025-12-06
**참고 문서**: `docs/v1.2/note.md`

---

## 1. 개요

본 문서는 대구 공공데이터 시각화 앱 v1.1.3의 현재 상태(AS-IS)와 v1.2에서 목표하는 개선 상태(TO-BE)를 비교 분석한다.

v1.2의 핵심 목표:
1. **LangChain/LangGraph 기반 Tool Calling 아키텍처 전환**
2. **ECLO 예측 모델 통합** (대화형 모델 실행)
3. **uv 기반 패키지 관리 도입**
4. **프로젝트 개요 탭 확장** (버전 히스토리, 챗봇 그래프 구조 시각화)

---

## 2. 기능별 AS-IS / TO-BE 비교

### 2.1 Tool Calling 아키텍처

| 구분 | AS-IS (v1.1.3) | TO-BE (v1.2) |
|:-----|:---------------|:-------------|
| **Tool Calling 방식** | Anthropic API 직접 호출 | LangChain + LangGraph |
| **도구 실행 노드** | 커스텀 루프 (`run_tool_calling`) | LangGraph `ToolNode` |
| **그래프 구조** | 없음 (순차 처리) | StateGraph 기반 워크플로우 |
| **메모리 관리** | 없음 | LangGraph Checkpointer (선택) |
| **상태 관리** | 수동 메시지 리스트 관리 | `add_messages` Reducer |

#### 2.1.1 현재 구조 (AS-IS)

```python
# utils/chatbot.py - 현재 구조
def run_tool_calling(client, model, messages, data_context, df, max_tokens):
    for iteration in range(MAX_TOOL_ITERATIONS):
        response = client.messages.create(
            model=model,
            tools=TOOLS,
            messages=working_messages
        )
        # 수동 tool_use 처리
        if response.stop_reason == "tool_use":
            tool_results = [execute_tool(...) for tool_use in tool_uses]
            working_messages.append(...)
```

#### 2.1.2 목표 구조 (TO-BE)

```python
# LangGraph 기반 구조
from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, add_messages

class State(TypedDict):
    messages: Annotated[list, add_messages]
    current_dataset: str  # train, test 등

# 도구 정의 (@tool 데코레이터)
@tool
def get_dataframe_info(df: pd.DataFrame) -> str:
    """DataFrame 기본 정보를 반환합니다."""
    ...

# 그래프 구성
graph_builder = StateGraph(State)
graph_builder.add_node("chatbot", chatbot_node)
graph_builder.add_node("tools", ToolNode(tools=all_tools))
graph_builder.add_conditional_edges("chatbot", route_tools)
```

---

### 2.2 ECLO 예측 기능

| 구분 | AS-IS (v1.1.3) | TO-BE (v1.2) |
|:-----|:---------------|:-------------|
| **ECLO 예측** | 지원 안 함 | 대화형 예측 지원 |
| **모델 파일** | 없음 | `model/accident_lgbm_model.pkl` |
| **활성화 조건** | - | train/test 데이터셋 선택 시 |
| **데이터 수집** | - | 재질문을 통한 대화형 수집 |
| **응답 방식** | - | 예측 결과를 자연어로 응답 |

#### 2.2.1 ECLO 예측 모델 구성

```
model/
├── accident_lgbm_model.pkl    # LightGBM 예측 모델 (1.4MB)
├── feature_config.json        # 피처 설정
└── label_encoders.pkl         # 라벨 인코더
```

#### 2.2.2 필수 입력 피처 (11개)

| 피처 | 타입 | 설명 |
|:-----|:-----|:-----|
| 기상상태 | 범주형 | 맑음, 흐림, 비, 눈 등 |
| 노면상태 | 범주형 | 건조, 젖음, 적설 등 |
| 도로형태 | 범주형 | 직선, 곡선, 교차로 등 |
| 사고유형 | 범주형 | 차대차, 차대사람 등 |
| 시간대 | 범주형 | 새벽, 아침, 낮, 저녁 등 |
| 시군구 | 범주형 | 대구 시군구 |
| 요일 | 범주형 | 월~일 |
| 사고시 | 수치형 | 사고 발생 시각 (0-23) |
| 사고연 | 수치형 | 사고 발생 연도 |
| 사고월 | 수치형 | 사고 발생 월 (1-12) |
| 사고일 | 수치형 | 사고 발생 일 (1-31) |

#### 2.2.3 대화형 예측 흐름

```
┌─────────────────────────────────────────────────────────────┐
│  사용자: "ECLO를 예측해줘"                                    │
│       ↓                                                     │
│  LLM: train/test 활성화 확인 → 필수 피처 재질문               │
│       "기상상태, 도로형태 등을 알려주세요"                      │
│       ↓                                                     │
│  사용자: "맑음, 직선도로, 월요일 오후 3시..."                   │
│       ↓                                                     │
│  LLM: 정보 충분? → 부족 시 추가 재질문                         │
│       ↓                                                     │
│  [모든 피처 수집 완료]                                        │
│       ↓                                                     │
│  predict_eclo Tool 호출 → 모델 실행                          │
│       ↓                                                     │
│  LLM: "예측 결과 ECLO는 X입니다. 이는..." (자연어 응답)         │
└─────────────────────────────────────────────────────────────┘
```

#### 2.2.4 ECLO 예측 Tool 정의

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
    사고일: int
) -> str:
    """
    ECLO(Equivalent Casualty Loss of life)를 예측합니다.
    모든 피처가 제공되어야 예측이 가능합니다.

    train 또는 test 데이터셋이 활성화된 경우에만 사용 가능합니다.
    """
    # 라벨 인코딩 → 모델 예측 → 결과 반환
    ...
```

---

### 2.3 패키지 관리

| 구분 | AS-IS (v1.1.3) | TO-BE (v1.2) |
|:-----|:---------------|:-------------|
| **패키지 관리자** | pip | uv |
| **가상환경 생성** | `python -m venv venv` | `uv venv` |
| **의존성 설치** | `pip install -r requirements.txt` | `uv pip install -r requirements.txt` |
| **속도** | 기본 | 10-100배 빠름 |
| **락 파일** | 없음 | `uv.lock` (선택) |

#### 2.3.1 README 변경 사항

```bash
# AS-IS (v1.1.3)
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# TO-BE (v1.2)
uv venv
source .venv/bin/activate  # uv 기본 디렉토리
uv pip install -r requirements.txt
```

---

### 2.4 프로젝트 개요 탭 확장

| 구분 | AS-IS (v1.1.3) | TO-BE (v1.2) |
|:-----|:---------------|:-------------|
| **버전 히스토리** | 없음 | 버전별 발전 사항 타임라인 표시 |
| **챗봇 구조 시각화** | 없음 | 현재 Tool Calling 그래프 다이어그램 |
| **기존 콘텐츠** | 소개 + 업로드 + 기술 스택 | 기존 유지 + 신규 섹션 추가 |

#### 2.4.1 현재 프로젝트 개요 구조 (AS-IS)

```
📖 프로젝트 개요 탭
├── 프로젝트 소개 (대구 공공데이터 시각화)
├── 📤 데이터 업로드 (7개 데이터셋)
│   └── 각 데이터셋 expander (파일 업로드, 미리보기)
└── 🔧 기술 스택 (3 columns)
    ├── 프론트엔드 (Streamlit, Plotly, Folium)
    ├── 데이터 처리 (Pandas, NumPy)
    └── AI (Anthropic Claude, Python 3.10+)
```

#### 2.4.2 목표 프로젝트 개요 구조 (TO-BE)

```
📖 프로젝트 개요 탭
├── 프로젝트 소개 (기존 유지)
├── 📤 데이터 업로드 (기존 유지)
├── 🔧 기술 스택 (기존 유지)
├── 📊 버전 히스토리 (🆕)                    ← 신규 추가
│   └── v1.0 → v1.1 → v1.1.1 → v1.1.2 → v1.1.3 → v1.2 타임라인
└── 🤖 AI 챗봇 아키텍처 (🆕)                 ← 신규 추가
    ├── 현재 Tool Calling 그래프 구조
    └── 도구 목록 및 데이터 흐름 시각화
```

#### 2.4.3 버전 히스토리 섹션

버전별 핵심 변경사항을 시각적 타임라인으로 표시:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        📊 버전 히스토리                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  v1.0 ──→ v1.1 ──→ v1.1.1 ──→ v1.1.2 ──→ v1.1.3 ──→ v1.2           │
│   │        │         │          │          │         │             │
│   │        │         │          │          │         └─ LangGraph  │
│   │        │         │          │          │            ECLO 예측   │
│   │        │         │          │          │            uv 도입     │
│   │        │         │          │          │                        │
│   │        │         │          │          └─ UI 간소화            │
│   │        │         │          │             Tool 피드백 수정      │
│   │        │         │          │                                   │
│   │        │         │          └─ UX 개선                         │
│   │        │         │             도구 5개 추가 (→20개)            │
│   │        │         │                                              │
│   │        │         └─ Tool Calling 도입 (15개 도구)              │
│   │        │            스트리밍, 성능 최적화                        │
│   │        │                                                        │
│   │        └─ CSV 업로드, AI 챗봇                                  │
│   │           session_state 캐싱                                    │
│   │                                                                 │
│   └─ 7개 데이터셋 기초 탐색                                         │
│      Folium 지도 시각화                                             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**버전별 핵심 마일스톤:**

| 버전 | 핵심 기능 | 도구 수 |
|:-----|:---------|:--------|
| v1.0 | 기초 데이터 탐색, Folium 지도 | - |
| v1.1 | CSV 업로드, AI 챗봇 도입 | - |
| v1.1.1 | Tool Calling 도입, 스트리밍 | 15개 |
| v1.1.2 | UX 개선, 도구 확장 | 20개 |
| v1.1.3 | UI 간소화, 버그 수정 | 20개 |
| v1.2 | LangGraph, ECLO 예측 | 21개 |

#### 2.4.4 AI 챗봇 아키텍처 섹션

현재 구현된 Tool Calling 그래프 구조를 시각적으로 표시:

```
┌─────────────────────────────────────────────────────────────────────┐
│                     🤖 AI 챗봇 아키텍처                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│    ┌──────────────────────────────────────────────────────────┐     │
│    │                    LangGraph Workflow                     │     │
│    ├──────────────────────────────────────────────────────────┤     │
│    │                                                          │     │
│    │   [사용자 질문]                                           │     │
│    │        ↓                                                 │     │
│    │   ┌─────────┐    tool_calls?    ┌─────────┐              │     │
│    │   │ Chatbot │ ───────Yes──────→ │  Tools  │              │     │
│    │   │ (Claude)│ ←─────────────────│ (20+1개)│              │     │
│    │   └────┬────┘                   └─────────┘              │     │
│    │        │                                                 │     │
│    │        │ No                                              │     │
│    │        ↓                                                 │     │
│    │   [최종 응답]                                             │     │
│    │                                                          │     │
│    └──────────────────────────────────────────────────────────┘     │
│                                                                     │
│    📦 사용 가능한 도구 (21개)                                        │
│    ├── 데이터 분석 (20개): get_dataframe_info, get_column_statistics,│
│    │   get_missing_values, get_value_counts, filter_dataframe, ...  │
│    └── ECLO 예측 (1개): predict_eclo (train/test 전용)             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### 2.4.5 구현 방식

```python
# app.py - 프로젝트 개요 탭 확장

def render_project_overview_tab():
    st.header("📖 프로젝트 개요")

    # === 기존 섹션 (유지) ===
    # 1. 프로젝트 소개
    # 2. 데이터 업로드
    # 3. 기술 스택

    st.markdown("---")

    # === 신규 섹션 ===
    # 4. 버전 히스토리
    st.subheader("📊 버전 히스토리")
    render_version_timeline()

    # 5. AI 챗봇 아키텍처
    st.subheader("🤖 AI 챗봇 아키텍처")
    render_chatbot_architecture()

def render_version_timeline():
    """버전별 발전 사항을 타임라인 형태로 표시"""
    versions = [
        {"version": "v1.0", "title": "기초 구현", "features": ["7개 데이터셋 탐색", "Folium 지도"]},
        {"version": "v1.1", "title": "AI 도입", "features": ["CSV 업로드", "Claude 챗봇"]},
        # ...
    ]
    # Streamlit columns 또는 expander로 시각화

def render_chatbot_architecture():
    """현재 Tool Calling 그래프 구조 시각화"""
    # Mermaid 다이어그램 또는 ASCII art 표시
    # 도구 목록 테이블
```

---

## 3. 코드 품질 개선

### 3.1 의존성 추가

| 패키지 | 버전 | 용도 |
|:-------|:-----|:-----|
| `langchain` | 0.3+ | LLM 추상화 레이어 |
| `langchain-anthropic` | 0.3+ | Claude 모델 래퍼 |
| `langgraph` | 0.2+ | 상태 기반 그래프 |
| `uv` | 0.5+ | 패키지 관리 (시스템 설치) |

### 3.2 파일 구조 변경

```
utils/
├── chatbot.py        # 리팩토링: LangGraph 기반
├── tools.py          # 리팩토링: @tool 데코레이터 사용
├── predictor.py      # 🆕 ECLO 예측 모듈
├── graph.py          # 🆕 LangGraph 워크플로우 정의
└── ...
```

---

## 4. 변경 요약표

| 영역 | 변경 유형 | 내용 |
|:-----|:---------|:-----|
| Tool Calling | 🔄 변경 | Anthropic API → LangChain/LangGraph |
| 도구 정의 | 🔄 변경 | JSON Schema → `@tool` 데코레이터 |
| 상태 관리 | ➕ 추가 | LangGraph StateGraph 도입 |
| ECLO 예측 | ➕ 추가 | 대화형 모델 예측 기능 |
| predict_eclo Tool | ➕ 추가 | LGBM 모델 호출 도구 |
| 패키지 관리 | 🔄 변경 | pip → uv |
| README | 🔧 개선 | uv 기반 설치 가이드 |
| requirements.txt | 🔧 개선 | LangChain 의존성 추가 |
| 프로젝트 개요 탭 | ➕ 추가 | 버전 히스토리 타임라인 섹션 |
| 프로젝트 개요 탭 | ➕ 추가 | AI 챗봇 아키텍처 시각화 섹션 |

---

## 5. 구현 우선순위

### 🔴 P0 - 핵심 기능 (필수)

| 순위 | 항목 | 설명 |
|:-----|:-----|:-----|
| 1 | LangGraph 구조 설계 | StateGraph, 노드, 엣지 정의 |
| 2 | 기존 도구 마이그레이션 | 20개 도구를 `@tool` 데코레이터로 변환 |
| 3 | ToolNode 통합 | LangGraph ToolNode로 도구 실행 |
| 4 | ECLO 예측 도구 구현 | `predict_eclo` Tool 및 모델 로딩 |

### 🟡 P1 - 대화형 기능

| 순위 | 항목 | 설명 |
|:-----|:-----|:-----|
| 5 | 재질문 로직 | 필수 피처 미수집 시 추가 질문 |
| 6 | 데이터셋 조건 검증 | train/test 활성화 시에만 ECLO 예측 허용 |
| 7 | 자연어 응답 생성 | 예측 결과를 사용자 친화적으로 설명 |

### 🟢 P2 - 환경 및 UI 개선

| 순위 | 항목 | 설명 |
|:-----|:-----|:-----|
| 8 | uv 마이그레이션 | pip → uv 전환 |
| 9 | README 업데이트 | 설치 가이드 변경 |
| 10 | requirements.txt 갱신 | 새 의존성 추가 |
| 11 | 프로젝트 개요: 버전 히스토리 | v1.0~v1.2 타임라인 UI 구현 |
| 12 | 프로젝트 개요: 챗봇 아키텍처 | Tool Calling 그래프 시각화 구현 |

---

## 6. 예상 그래프 구조

```
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph Workflow                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│    START                                                     │
│      ↓                                                       │
│  ┌──────────┐                                                │
│  │ chatbot  │ ← Claude + bind_tools()                        │
│  └────┬─────┘                                                │
│       │                                                      │
│       ├─── [tool_calls?] ───→ ┌──────────┐                   │
│       │         Yes           │  tools   │ ← ToolNode        │
│       │                       └────┬─────┘                   │
│       │                            │                         │
│       │         ←──────────────────┘                         │
│       │                                                      │
│       ├─── [no tools] ───→ END                               │
│       │                                                      │
└───────┴──────────────────────────────────────────────────────┘
```

### 상태 스키마

```python
class State(TypedDict):
    messages: Annotated[list, add_messages]  # 대화 이력
    current_dataset: str                      # 현재 선택된 데이터셋
    collected_features: dict                  # ECLO 예측용 수집된 피처
```

---

## 7. 다음 단계

1. **P0 구현**: LangGraph 구조 설계 및 기존 도구 마이그레이션
2. **P1 구현**: ECLO 예측 도구 및 대화형 피처 수집 로직
3. **P2 구현**: uv 마이그레이션 및 README 업데이트
4. **P2 구현**: 프로젝트 개요 탭 확장 (버전 히스토리 + 챗봇 아키텍처)
5. **테스트**: 전체 기능 통합 테스트 (기존 20개 도구 + ECLO 예측)
6. **문서화**: 사용자 가이드 및 API 문서 업데이트

---

## 8. 참고 자료

- **모델 학습 노트북**: `material/3-7/3_2_데이콘_데이터_제출해보기.ipynb`
- **LangGraph 문서**: https://langchain-ai.github.io/langgraph/
- **LangChain Tools**: https://python.langchain.com/docs/concepts/tools/
- **uv 문서**: https://docs.astral.sh/uv/
