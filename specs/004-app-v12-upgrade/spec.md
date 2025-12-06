# Feature Specification: 대구 공공데이터 시각화 앱 v1.2 업그레이드

**Feature Branch**: `004-app-v12-upgrade`
**Created**: 2025-12-06
**Status**: Draft
**Input**: docs/v1.2/app_improvement_proposal.md 기반

## User Scenarios & Testing *(mandatory)*

### User Story 1 - LangGraph 기반 AI 챗봇 대화 (Priority: P1)

사용자는 기존과 동일한 방식으로 AI 챗봇에게 데이터 분석 질문을 하고, 시스템은 내부적으로 LangGraph 워크플로우를 통해 더 안정적이고 확장 가능한 방식으로 응답을 생성한다. 사용자는 기존 20개 분석 도구를 모두 동일하게 사용할 수 있으며, 응답 품질과 안정성이 향상된다.

**Why this priority**: Tool Calling 아키텍처는 모든 AI 기능의 기반이므로 가장 먼저 전환해야 한다. ECLO 예측 등 신규 기능도 이 아키텍처 위에서 동작한다.

**Independent Test**: 기존 20개 분석 도구(get_dataframe_info, get_column_statistics 등)가 LangGraph 환경에서 정상 동작하는지 확인하여 독립적으로 테스트할 수 있다.

**Acceptance Scenarios**:

1. **Given** 사용자가 데이터셋을 업로드하고 AI 챗봇 탭에서 "데이터 구조를 알려줘"라고 질문했을 때, **When** 시스템이 질문을 처리하면, **Then** LangGraph 워크플로우를 통해 적절한 도구가 호출되고 데이터 구조 정보가 응답으로 반환된다.

2. **Given** 사용자가 복잡한 분석 질문(예: "컬럼별 결측치를 분석하고 상관관계를 보여줘")을 했을 때, **When** 시스템이 여러 도구를 순차 호출해야 할 때, **Then** LangGraph가 tool_calls를 올바르게 라우팅하고 모든 결과를 종합하여 응답한다.

3. **Given** 도구 실행 중 오류가 발생했을 때(예: 존재하지 않는 컬럼 참조), **When** 시스템이 오류를 감지하면, **Then** 사용자에게 친화적인 오류 메시지를 반환하고 대화가 중단되지 않는다.

---

### User Story 2 - ECLO 예측 기능 (Priority: P1)

사용자는 train 또는 test 데이터셋이 활성화된 상태에서 AI 챗봇에게 "ECLO를 예측해줘"라고 요청할 수 있다. 시스템은 필요한 11개 피처(기상상태, 노면상태, 도로형태 등)가 부족할 경우 대화를 통해 추가 정보를 수집하고, 모든 정보가 수집되면 예측 모델을 실행하여 결과를 자연어로 설명한다.

**Why this priority**: ECLO 예측은 v1.2의 핵심 신규 기능으로, 교육 목적의 예측 모델 활용을 가능하게 하는 가치 있는 기능이다.

**Independent Test**: 모든 11개 피처를 직접 입력하여 predict_eclo 도구 호출과 예측 결과 반환을 독립적으로 테스트할 수 있다.

**Acceptance Scenarios**:

1. **Given** train 데이터셋이 업로드된 상태에서 사용자가 "ECLO 예측해줘"라고 요청했을 때, **When** 필요한 피처 정보가 부족하면, **Then** 시스템은 "기상상태, 노면상태, 도로형태 등을 알려주세요"와 같이 추가 정보를 요청한다.

2. **Given** 사용자가 모든 11개 피처(기상상태, 노면상태, 도로형태, 사고유형, 시간대, 시군구, 요일, 사고시, 사고연, 사고월, 사고일)를 제공했을 때, **When** predict_eclo 도구가 호출되면, **Then** 예측 결과가 "예측된 ECLO는 X입니다. 이는 [해석]을 의미합니다"와 같은 자연어로 반환된다.

3. **Given** CCTV 데이터셋(train/test가 아닌 다른 데이터셋)이 활성화된 상태에서 사용자가 "ECLO 예측해줘"라고 요청했을 때, **When** 시스템이 요청을 처리하면, **Then** "ECLO 예측은 train 또는 test 데이터셋에서만 사용 가능합니다"라는 안내 메시지를 반환한다.

4. **Given** 사용자가 일부 피처만 제공했을 때(예: "맑음, 직선도로, 월요일"), **When** 시스템이 부족한 피처를 감지하면, **Then** 구체적으로 어떤 피처가 더 필요한지 안내하고 추가 입력을 요청한다.

---

### User Story 3 - uv 기반 빠른 환경 설정 (Priority: P2)

신규 사용자는 uv를 사용하여 기존 pip 대비 빠른 속도로 프로젝트 의존성을 설치하고 가상환경을 설정할 수 있다. README의 설치 가이드가 uv 기반으로 업데이트되어 더 빠른 시작 경험을 제공한다.

**Why this priority**: 개발 환경 설정은 핵심 기능은 아니지만, 사용자 경험 향상에 기여하며 다른 기능에 영향을 주지 않아 독립적으로 적용 가능하다.

**Independent Test**: README의 uv 설치 가이드를 따라 새 환경에서 의존성 설치 후 앱 실행이 정상 동작하는지 확인할 수 있다.

**Acceptance Scenarios**:

1. **Given** 사용자가 uv가 설치된 환경에서 프로젝트를 클론했을 때, **When** README의 가이드를 따라 `uv venv && source .venv/bin/activate && uv pip install -r requirements.txt`를 실행하면, **Then** 모든 의존성이 설치되고 `streamlit run app.py`로 앱이 정상 실행된다.

2. **Given** requirements.txt에 새로운 의존성(langchain, langchain-anthropic, langgraph)이 추가되었을 때, **When** 사용자가 의존성을 설치하면, **Then** 모든 패키지가 충돌 없이 설치된다.

---

### User Story 4 - 프로젝트 개요 탭: 버전 히스토리 (Priority: P3)

사용자는 프로젝트 개요 탭에서 v1.0부터 v1.2까지의 버전별 발전 사항을 시각적 타임라인으로 확인할 수 있다. 각 버전의 핵심 기능과 도구 수 변화를 한눈에 파악할 수 있어 프로젝트의 발전 과정을 이해하는 데 도움이 된다.

**Why this priority**: 교육 목적으로 유용하지만 핵심 기능이 아니므로 P3로 분류한다. 기존 기능에 영향 없이 독립적으로 추가 가능하다.

**Independent Test**: 프로젝트 개요 탭에서 버전 히스토리 섹션이 렌더링되고 각 버전 정보가 올바르게 표시되는지 확인할 수 있다.

**Acceptance Scenarios**:

1. **Given** 사용자가 프로젝트 개요 탭을 열었을 때, **When** 페이지가 로드되면, **Then** 버전 히스토리 섹션이 기존 콘텐츠(소개, 업로드, 기술 스택) 아래에 표시된다.

2. **Given** 버전 히스토리 섹션이 표시되었을 때, **When** 사용자가 내용을 확인하면, **Then** v1.0→v1.1→v1.1.1→v1.1.2→v1.1.3→v1.2 순서로 각 버전의 핵심 기능이 나열된다.

---

### User Story 5 - 프로젝트 개요 탭: AI 챗봇 아키텍처 시각화 (Priority: P3)

사용자는 프로젝트 개요 탭에서 현재 AI 챗봇의 LangGraph 워크플로우 구조와 사용 가능한 21개 도구 목록을 시각적으로 확인할 수 있다. 이를 통해 시스템 구조를 학습하고 이해하는 데 도움을 받는다.

**Why this priority**: 교육 목적으로 유용하지만 핵심 기능이 아니므로 P3로 분류한다.

**Independent Test**: 프로젝트 개요 탭에서 AI 챗봇 아키텍처 섹션이 렌더링되고 도구 목록이 올바르게 표시되는지 확인할 수 있다.

**Acceptance Scenarios**:

1. **Given** 사용자가 프로젝트 개요 탭을 열었을 때, **When** 페이지가 로드되면, **Then** AI 챗봇 아키텍처 섹션이 버전 히스토리 아래에 표시된다.

2. **Given** AI 챗봇 아키텍처 섹션이 표시되었을 때, **When** 사용자가 내용을 확인하면, **Then** LangGraph 워크플로우 다이어그램(Chatbot→Tools 라우팅)과 21개 도구 목록(데이터 분석 20개 + ECLO 예측 1개)이 표시된다.

---

### Edge Cases

- **API 키 미입력**: 사용자가 Anthropic API 키를 입력하지 않고 AI 챗봇을 사용하려 할 때, 명확한 안내 메시지를 표시해야 한다.
- **모델 파일 누락**: ECLO 예측 모델 파일(accident_lgbm_model.pkl)이 없을 때, predict_eclo 도구는 적절한 오류 메시지를 반환해야 한다.
- **잘못된 피처 값**: 사용자가 유효하지 않은 피처 값(예: 기상상태에 "폭풍")을 입력했을 때, 시스템은 유효한 값 목록을 안내해야 한다.
- **빈 데이터셋**: 업로드된 데이터셋이 비어있을 때, 분석 도구는 적절한 오류 메시지를 반환해야 한다.
- **대화 컨텍스트 유실**: 데이터셋 전환 시 기존 대화 컨텍스트는 데이터셋별로 분리 관리되어야 한다.

## Requirements *(mandatory)*

### Functional Requirements

**Tool Calling 아키텍처**:
- **FR-001**: 시스템은 LangGraph StateGraph를 사용하여 AI 챗봇 워크플로우를 관리해야 한다(MUST).
- **FR-002**: 시스템은 기존 20개 분석 도구를 LangChain @tool 데코레이터 형식으로 마이그레이션해야 한다(MUST).
- **FR-003**: 시스템은 LangGraph ToolNode를 통해 도구 실행을 처리해야 한다(MUST).
- **FR-004**: 시스템은 tool_calls 여부에 따라 chatbot 노드와 tools 노드 간 라우팅을 수행해야 한다(MUST).
- **FR-005**: 시스템은 add_messages Reducer를 사용하여 대화 상태를 관리해야 한다(MUST).

**ECLO 예측**:
- **FR-006**: 시스템은 predict_eclo 도구를 제공하여 ECLO(Equivalent Casualty Loss of life)를 예측해야 한다(MUST).
- **FR-007**: predict_eclo 도구는 11개 필수 피처(기상상태, 노면상태, 도로형태, 사고유형, 시간대, 시군구, 요일, 사고시, 사고연, 사고월, 사고일)를 입력받아야 한다(MUST).
- **FR-008**: predict_eclo 도구는 train 또는 test 데이터셋이 활성화된 경우에만 사용 가능해야 한다(MUST).
- **FR-009**: 시스템은 필수 피처가 부족할 경우 대화를 통해 추가 정보를 수집해야 한다(MUST).
- **FR-010**: 시스템은 모델 파일(accident_lgbm_model.pkl, feature_config.json, label_encoders.pkl)을 로드하여 예측을 수행해야 한다(MUST).

**패키지 관리**:
- **FR-011**: README는 uv 기반 설치 가이드를 제공해야 한다(MUST).
- **FR-012**: requirements.txt는 langchain, langchain-anthropic, langgraph 의존성을 포함해야 한다(MUST).

**프로젝트 개요 탭**:
- **FR-013**: 프로젝트 개요 탭은 버전 히스토리 섹션을 포함해야 한다(MUST).
- **FR-014**: 버전 히스토리는 v1.0부터 v1.2까지 각 버전의 핵심 기능을 표시해야 한다(MUST).
- **FR-015**: 프로젝트 개요 탭은 AI 챗봇 아키텍처 섹션을 포함해야 한다(MUST).
- **FR-016**: AI 챗봇 아키텍처는 LangGraph 워크플로우 구조와 21개 도구 목록을 표시해야 한다(MUST).

### Key Entities

- **State (상태)**: LangGraph 워크플로우의 상태를 나타내며, messages(대화 이력), current_dataset(현재 선택된 데이터셋)을 포함한다.
- **Tool (도구)**: AI 챗봇이 사용할 수 있는 분석/예측 기능 단위. 기존 20개 분석 도구 + 1개 ECLO 예측 도구로 구성.
- **ECLO 예측 모델**: LightGBM 기반 예측 모델로, 11개 피처를 입력받아 ECLO 값을 예측한다.
- **Version History (버전 히스토리)**: 프로젝트의 버전별 핵심 기능과 변경사항을 담은 데이터 구조.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 기존 20개 분석 도구가 LangGraph 환경에서 100% 정상 동작한다.
- **SC-002**: ECLO 예측 요청 시 모든 11개 피처 수집 후 3초 이내에 예측 결과가 반환된다.
- **SC-003**: 사용자는 평균 3회 이내의 대화로 ECLO 예측에 필요한 모든 피처를 입력할 수 있다.
- **SC-004**: uv를 사용한 의존성 설치 시간이 pip 대비 단축된다.
- **SC-005**: 프로젝트 개요 탭에서 버전 히스토리와 아키텍처 섹션이 1초 이내에 렌더링된다.
- **SC-006**: 도구 실행 오류 발생 시 100% 사용자 친화적인 오류 메시지가 반환되고 대화가 중단되지 않는다.

## Assumptions

- uv는 사용자 시스템에 별도로 설치되어 있다고 가정한다 (시스템 레벨 설치).
- ECLO 예측 모델 파일(model/ 디렉토리)은 프로젝트에 포함되어 배포된다.
- 사용자는 Anthropic API 키를 보유하고 있다.
- LangGraph의 Checkpointer(메모리 지속성)는 v1.2에서는 구현하지 않는다 (선택적 기능으로 향후 고려).
