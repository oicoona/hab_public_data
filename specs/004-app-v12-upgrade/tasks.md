# Tasks: 대구 공공데이터 시각화 앱 v1.2 업그레이드

**Feature Branch**: `004-app-v12-upgrade`
**Generated**: 2025-12-06
**Based on**: spec.md, plan.md, research.md, data-model.md, contracts/tools-api.md

## Task Overview

| Phase | 설명 | 작업 수 | 예상 우선순위 |
|-------|------|---------|---------------|
| 1 | 인프라 설정 | 3 | P1 |
| 2 | 도구 마이그레이션 | 4 | P1 |
| 3 | LangGraph 통합 | 5 | P1 |
| 4 | ECLO 예측 | 4 | P1 |
| 5 | UI 확장 | 3 | P3 |
| 6 | 문서화 | 2 | P2 |
| 7 | 검증 및 테스트 | 3 | P1 |

**총 작업 수**: 24개

---

## Phase 1: 인프라 설정 (P1)

**목표**: LangGraph 사용을 위한 의존성 및 기본 구조 설정

### 1.1 requirements.txt 업데이트
- [ ] `requirements.txt`에 LangChain/LangGraph 의존성 추가
  - `langchain>=0.3.0`
  - `langchain-anthropic>=0.3.0`
  - `langgraph>=0.2.0`
- **관련 FR**: FR-012
- **파일**: `requirements.txt`

### 1.2 utils/graph.py 생성
- [ ] `utils/graph.py` 파일 생성
- [ ] `ChatState` TypedDict 정의 (messages, current_dataset)
- [ ] `add_messages` Reducer 설정
- **관련 FR**: FR-001, FR-005
- **참조**: data-model.md §1

### 1.3 모델 파일 확인
- [ ] `model/` 디렉토리 구조 확인
  - `accident_lgbm_model.pkl`
  - `feature_config.json`
  - `label_encoders.pkl`
- **관련 FR**: FR-010

---

## Phase 2: 도구 마이그레이션 (P1)

**목표**: 기존 20개 도구를 @tool 데코레이터 형식으로 변환

**의존성**: Phase 1 완료

### 2.1 도구 기본 구조 변경
- [ ] `utils/tools.py`에서 기존 TOOLS 딕셔너리 구조를 @tool 형식으로 변환
- [ ] `RunnableConfig`를 통한 DataFrame 전달 패턴 구현
- **관련 FR**: FR-002
- **참조**: contracts/tools-api.md §2

### 2.2 데이터프레임 분석 도구 변환 (10개)
- [ ] `get_dataframe_info` → @tool 형식
- [ ] `get_column_statistics` → @tool 형식
- [ ] `get_missing_values` → @tool 형식
- [ ] `get_value_counts` → @tool 형식
- [ ] `filter_dataframe` → @tool 형식
- [ ] `sort_dataframe` → @tool 형식
- [ ] `get_correlation` → @tool 형식
- [ ] `group_by_aggregate` → @tool 형식
- [ ] `get_unique_values` → @tool 형식
- [ ] `get_date_range` → @tool 형식
- **관련 FR**: FR-002
- **파일**: `utils/tools.py`

### 2.3 고급 분석 도구 변환 (10개)
- [ ] `get_outliers` → @tool 형식
- [ ] `get_sample_rows` → @tool 형식
- [ ] `calculate_percentile` → @tool 형식
- [ ] `get_geo_bounds` → @tool 형식
- [ ] `cross_tabulation` → @tool 형식
- [ ] `analyze_missing_pattern` → @tool 형식
- [ ] `get_column_correlation_with_target` → @tool 형식
- [ ] `detect_data_types` → @tool 형식
- [ ] `get_temporal_pattern` → @tool 형식
- [ ] `summarize_categorical_distribution` → @tool 형식
- **관련 FR**: FR-002
- **파일**: `utils/tools.py`

### 2.4 도구 목록 export
- [ ] `get_all_tools()` 함수 추가 (모든 도구 리스트 반환)
- [ ] 기존 `TOOL_HANDLERS`, `execute_tool` 코드 정리/제거
- **파일**: `utils/tools.py`

---

## Phase 3: LangGraph 통합 (P1)

**목표**: LangGraph StateGraph로 챗봇 워크플로우 구축

**의존성**: Phase 1, Phase 2 완료

### 3.1 StateGraph 구성
- [ ] `utils/graph.py`에 `StateGraph` 빌더 구현
- [ ] `chatbot` 노드 추가 (LLM 호출)
- [ ] `tools` 노드 추가 (ToolNode 사용)
- **관련 FR**: FR-001, FR-003
- **파일**: `utils/graph.py`

### 3.2 라우팅 로직 구현
- [ ] `route_tools` 조건부 엣지 함수 구현
- [ ] tool_calls 유무에 따른 분기 처리
- [ ] START → chatbot, chatbot → tools/END, tools → chatbot 엣지 설정
- **관련 FR**: FR-004
- **파일**: `utils/graph.py`

### 3.3 그래프 컴파일 및 실행 함수
- [ ] `build_graph(tools: list)` 함수 구현
- [ ] `run_graph(graph, state, config)` 함수 구현
- **파일**: `utils/graph.py`

### 3.4 chatbot.py 통합
- [ ] `utils/chatbot.py`에서 기존 `run_tool_calling` 로직을 LangGraph 호출로 대체
- [ ] `stream_chat_response_with_tools`를 LangGraph 스트리밍으로 전환
- [ ] `astream_events` 사용한 토큰 단위 스트리밍 구현
- **관련 FR**: FR-001
- **참조**: research.md §6
- **파일**: `utils/chatbot.py`

### 3.5 오류 처리 및 폴백
- [ ] 도구 실행 오류 시 사용자 친화적 메시지 반환
- [ ] 대화 중단 없이 오류 복구 로직 구현
- **관련 FR**: 없음 (Edge Case)
- **파일**: `utils/chatbot.py`, `utils/graph.py`

---

## Phase 4: ECLO 예측 (P1)

**목표**: predict_eclo 도구 및 예측 모듈 구현

**의존성**: Phase 1 완료, Phase 2와 병렬 가능

### 4.1 predictor.py 생성
- [ ] `utils/predictor.py` 파일 생성
- [ ] 모델 로딩 함수 구현 (`load_model`, `load_encoders`, `load_feature_config`)
- [ ] 피처 인코딩 함수 구현 (`encode_features`)
- [ ] 예측 함수 구현 (`predict_eclo_value`)
- **관련 FR**: FR-010
- **파일**: `utils/predictor.py`

### 4.2 predict_eclo 도구 구현
- [ ] `predict_eclo` @tool 함수 구현 (11개 피처 파라미터)
- [ ] 데이터셋 조건 검증 (train/test만 허용)
- [ ] 유효하지 않은 피처 값 처리
- **관련 FR**: FR-006, FR-007, FR-008
- **참조**: contracts/tools-api.md §3.1, data-model.md §2
- **파일**: `utils/tools.py`

### 4.3 ECLO 해석 로직
- [ ] ECLO 값 범위별 해석 문자열 생성
  - 0~0.1: 경미한 사고
  - 0.1~0.5: 일반적 사고
  - 0.5~1.0: 심각한 사고
  - 1.0 이상: 매우 심각한 사고
- **관련 FR**: FR-006
- **참조**: data-model.md §3
- **파일**: `utils/predictor.py`

### 4.4 피처 수집 대화 지원
- [ ] predict_eclo 도구 docstring에 필수 피처 및 유효 값 명시
- [ ] LLM이 부족한 피처를 자연스럽게 재질문하도록 프롬프트 설계
- **관련 FR**: FR-009
- **참조**: research.md §3

---

## Phase 5: UI 확장 (P3)

**목표**: 프로젝트 개요 탭에 버전 히스토리 및 아키텍처 시각화 추가

**의존성**: Phase 3 완료 (아키텍처 시각화에 도구 목록 필요)

### 5.1 버전 히스토리 데이터 정의
- [ ] `VERSION_HISTORY` 데이터 구조 정의 (v1.0~v1.2)
- [ ] 각 버전별 핵심 기능, 도구 수 정보 포함
- **관련 FR**: FR-013, FR-014
- **참조**: data-model.md §5
- **파일**: `app.py`

### 5.2 버전 히스토리 UI 구현
- [ ] 프로젝트 개요 탭에 "버전 히스토리" 섹션 추가
- [ ] `st.expander` + `st.columns`로 타임라인 형식 구현
- **관련 FR**: FR-013, FR-014
- **파일**: `app.py`

### 5.3 AI 챗봇 아키텍처 시각화
- [ ] `CHATBOT_ARCHITECTURE` 데이터 구조 정의
- [ ] LangGraph 워크플로우 다이어그램 (Markdown 코드 블록)
- [ ] 21개 도구 목록 표시 (`st.dataframe` 또는 리스트)
- **관련 FR**: FR-015, FR-016
- **참조**: data-model.md §6
- **파일**: `app.py`

---

## Phase 6: 문서화 (P2)

**목표**: README 업데이트 및 설치 가이드 개선

**의존성**: Phase 1 완료

### 6.1 README.md uv 설치 가이드
- [ ] "빠른 시작" 섹션에 uv 기반 설치 가이드 추가
- [ ] pip 대안 가이드 유지
- [ ] v1.2 버전 정보 업데이트
- **관련 FR**: FR-011
- **참조**: research.md §4
- **파일**: `README.md`

### 6.2 변경사항 요약
- [ ] README.md에 v1.2 주요 변경사항 요약 추가
  - LangGraph 전환
  - ECLO 예측 기능
  - 21개 도구
- **파일**: `README.md`

---

## Phase 7: 검증 및 테스트 (P1)

**목표**: 전체 기능 검증 및 품질 확인

**의존성**: Phase 1-6 완료

### 7.1 기존 도구 검증
- [ ] 20개 분석 도구 정상 동작 확인
  - get_dataframe_info
  - get_column_statistics
  - get_missing_values
  - (기타 17개)
- [ ] 스트리밍 응답 정상 동작 확인
- [ ] 도구 실행 피드백 표시 확인
- **관련 SC**: SC-001, SC-006

### 7.2 ECLO 예측 검증
- [ ] train 데이터셋에서 ECLO 예측 테스트
- [ ] test 데이터셋에서 ECLO 예측 테스트
- [ ] 비허용 데이터셋(cctv 등)에서 오류 메시지 확인
- [ ] 부분 피처 입력 시 재질문 확인
- [ ] 예측 시간 3초 이내 확인
- **관련 SC**: SC-002, SC-003

### 7.3 UI 및 문서 검증
- [ ] 프로젝트 개요 탭 버전 히스토리 렌더링 확인
- [ ] 프로젝트 개요 탭 아키텍처 시각화 렌더링 확인
- [ ] 렌더링 시간 1초 이내 확인
- [ ] uv 설치 가이드 검증 (새 환경에서 테스트)
- **관련 SC**: SC-004, SC-005

---

## Dependency Graph

```
Phase 1 (인프라)
    │
    ├──────────────┬─────────────────────┐
    ▼              ▼                     ▼
Phase 2        Phase 4.1-4.3         Phase 6
(도구 변환)    (predictor.py)        (문서화)
    │              │
    ▼              │
Phase 3 ◄─────────┘
(LangGraph)
    │
    ├─────────────────┐
    ▼                 ▼
Phase 4.4         Phase 5
(피처 수집)       (UI 확장)
    │                 │
    └────────┬────────┘
             ▼
         Phase 7
         (검증)
```

## 병렬 실행 예시

**독립 작업 그룹 (동시 실행 가능)**:

| 그룹 | 작업 |
|------|------|
| A | 2.2 데이터프레임 분석 도구 변환, 2.3 고급 분석 도구 변환 |
| B | 4.1 predictor.py 생성, 6.1 README 업데이트 |
| C | 5.1 버전 히스토리 데이터, 5.3 아키텍처 시각화 |

---

## Quick Reference

### 주요 파일 변경 목록

| 파일 | 변경 유형 | Phase |
|------|----------|-------|
| `requirements.txt` | 수정 | 1 |
| `utils/graph.py` | 신규 | 1, 3 |
| `utils/tools.py` | 수정 | 2, 4 |
| `utils/predictor.py` | 신규 | 4 |
| `utils/chatbot.py` | 수정 | 3 |
| `app.py` | 수정 | 5 |
| `README.md` | 수정 | 6 |

### 관련 문서 링크

- [spec.md](./spec.md) - 기능 명세서
- [plan.md](./plan.md) - 구현 계획서
- [research.md](./research.md) - 기술 리서치
- [data-model.md](./data-model.md) - 데이터 모델
- [contracts/tools-api.md](./contracts/tools-api.md) - 도구 API 계약
- [quickstart.md](./quickstart.md) - 빠른 시작 가이드
