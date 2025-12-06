# Implementation Plan: 대구 공공데이터 시각화 앱 v1.2 업그레이드

**Branch**: `004-app-v12-upgrade` | **Date**: 2025-12-06 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-app-v12-upgrade/spec.md`

## Summary

v1.2 업그레이드의 핵심 목표는 기존 Anthropic API 직접 호출 방식의 Tool Calling을 LangGraph 기반 워크플로우로 전환하고, ECLO(Equivalent Casualty Loss of life) 예측 기능을 추가하는 것이다. 또한 uv 패키지 관리자를 도입하고 프로젝트 개요 탭에 버전 히스토리 및 AI 챗봇 아키텍처 시각화를 추가한다.

**주요 변경사항**:
1. Tool Calling 아키텍처: Anthropic API → LangChain/LangGraph
2. 신규 기능: predict_eclo 도구 (대화형 피처 수집 + 모델 예측)
3. 패키지 관리: pip → uv
4. UI 확장: 프로젝트 개요 탭에 버전 히스토리, 챗봇 아키텍처 시각화 추가

## Technical Context

**Language/Version**: Python 3.10+ (현재 환경 Python 3.12 호환)
**Primary Dependencies**:
- 기존: Streamlit 1.28+, pandas 2.0+, numpy 1.24+, plotly 5.17+, folium 0.14+, anthropic 0.39+
- 신규: langchain 0.3+, langchain-anthropic 0.3+, langgraph 0.2+
**Storage**: 파일 기반 (CSV 업로드, session_state 캐싱), model/ 디렉토리 (pkl 파일)
**Testing**: 수동 탐색적 테스트 (교육 프로젝트 특성상 자동화 테스트 선택사항)
**Target Platform**: 로컬 실행 (Windows, macOS, Linux 크로스 플랫폼)
**Project Type**: Single project (Streamlit 단일 앱)
**Performance Goals**: ECLO 예측 3초 이내, 페이지 렌더링 1초 이내
**Constraints**: 코드 단순성 유지, Python 초보자 이해 가능한 수준
**Scale/Scope**: 로컬 단일 사용자, 7개 데이터셋, 21개 분석/예측 도구

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 원칙 | 검증 항목 | 상태 | 비고 |
|------|----------|------|------|
| I. Data-First Exploration | 데이터 탐색 우선 | ✅ PASS | 기존 20개 분석 도구 유지, ECLO 예측은 데이터 기반 |
| II. Simplicity & Accessibility | 코드 단순성 | ⚠️ JUSTIFY | LangGraph 도입은 복잡성 증가, 단 교육적 가치로 정당화 |
| III. Educational Purpose | 교육 목적 | ✅ PASS | Tool Calling/LangGraph 학습, 예측 모델 활용 교육 |
| IV. Streamlit-Based Visualization | Streamlit 기반 | ✅ PASS | Streamlit 유지, 별도 백엔드 없음 |
| V. Scope Discipline | 범위 준수 | ✅ PASS | 모델 학습 없음(기학습 모델 사용), 배포 없음 |

**Constitution Check 결과**: PASS (1개 항목 정당화 필요 → Complexity Tracking 참조)

## Project Structure

### Documentation (this feature)

```text
specs/004-app-v12-upgrade/
├── spec.md              # 기능 명세서
├── plan.md              # 이 문서
├── research.md          # Phase 0 리서치 결과
├── data-model.md        # Phase 1 데이터 모델
├── quickstart.md        # Phase 1 빠른 시작 가이드
├── contracts/           # Phase 1 API 계약
│   └── tools-api.md     # 도구 API 정의
└── tasks.md             # Phase 2 작업 목록 (/speckit.tasks 명령으로 생성)
```

### Source Code (repository root)

```text
# 기존 구조 유지 + 신규 파일 추가
app.py                    # 🔧 수정: 프로젝트 개요 탭 확장
requirements.txt          # 🔧 수정: LangChain/LangGraph 의존성 추가
README.md                 # 🔧 수정: uv 설치 가이드

utils/
├── __init__.py
├── chatbot.py           # 🔧 수정: LangGraph 워크플로우로 전환
├── tools.py             # 🔧 수정: @tool 데코레이터 형식으로 마이그레이션
├── graph.py             # 🆕 신규: LangGraph StateGraph 정의
├── predictor.py         # 🆕 신규: ECLO 예측 모듈
├── visualizer.py        # (변경 없음)
├── geo.py               # (변경 없음)
├── loader.py            # (변경 없음)
└── narration.py         # (변경 없음)

model/
├── accident_lgbm_model.pkl    # (기존) LightGBM 예측 모델
├── feature_config.json        # (기존) 피처 설정
└── label_encoders.pkl         # (기존) 라벨 인코더
```

**Structure Decision**: 기존 단일 프로젝트 구조를 유지하며, utils/ 디렉토리에 graph.py와 predictor.py만 추가한다. 복잡한 모듈 분리는 피하고 기존 패턴을 따른다.

## Complexity Tracking

> **Constitution Check 위반 항목 정당화**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| LangGraph 도입 (복잡성 증가) | 1) 교육 커리큘럼의 LangGraph 학습 목표 충족 2) 향후 확장성 (Checkpointer, 다중 에이전트) 3) 도구 관리 표준화 | 기존 Anthropic API 직접 호출 방식은 교육 목표에 부합하지 않음. material/14-15일차가 LangGraph 학습을 다루므로 실제 적용 사례 필요 |

**정당화 근거**:
- Constitution III (Educational Purpose)에 명시된 "Streamlit, 데이터 분석, 시각화 기초의 실습 학습 지원"을 LangGraph까지 확장
- syllabus.md의 14-15일차가 LangGraph를 다루므로 실제 동작하는 예제 코드 필요
- 코드 복잡도 증가를 최소화하기 위해 LangGraph의 고급 기능(Checkpointer)은 v1.2에서 제외
