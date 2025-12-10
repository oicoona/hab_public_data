# Implementation Plan: Backend Server Architecture Implementation (v1.3)

**Branch**: `005-app-v1.3-backend-sep` | **Date**: 2025-12-09 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-app-v1.3-backend-sep/spec.md`

**Note**: This plan is based on `/home/sk/hab_public_data/docs/v1.3/app_improvement_proposal.md`

## Summary

대구 공공데이터 시각화 앱 v1.2.3에서 v1.3으로의 아키텍처 전환을 계획한다. 핵심 목표는 모노리식 Streamlit 앱을 프론트엔드/백엔드 분리 아키텍처로 전환하여 성능, 확장성, 데이터 영속성을 향상시키는 것이다.

**주요 변경사항:**
- FastAPI 기반 백엔드 서버 추가 (ECLO 예측, AI 챗봇, 데이터셋 관리 API)
- PostgreSQL 데이터베이스 도입 (데이터셋, 대화 이력, 예측 결과 영구 저장)
- Redis 캐싱 시스템 (응답 캐싱, Celery 브로커)
- Docker Compose 기반 전체 스택 컨테이너화
- 기존 Streamlit 프론트엔드 유지 (시각화는 클라이언트 사이드)

**기술적 접근:**
- 단계별 마이그레이션: Phase 1 (ECLO 예측 API) → Phase 2 (AI 챗봇 API) → Phase 3 (데이터 관리 API)
- API 키 관리 방식 유지: 사용자가 클라이언트에서 개별 관리 (헤더로 전달)
- 기존 utils/ 모듈 로직을 backend/services로 이관
- 시각화 모듈(visualizer.py, geo.py)은 프론트엔드에 유지

## Technical Context

**Language/Version**: Python 3.10+ (현재 환경 3.12, 호환 유지)
**Primary Dependencies**:
- Backend: FastAPI 0.104+, SQLAlchemy 2.0+, Alembic 1.12+, Celery 5.3+, LangChain 0.3+, LangGraph 0.2+, Anthropic, LightGBM 4.1+
- Frontend: Streamlit 1.28+, Plotly 5.17+, Folium 0.14+, httpx 0.25+
- Infrastructure: Docker 24+, Docker Compose 2.20+

**Storage**:
- PostgreSQL 15+ (데이터셋 메타데이터, 대화 이력, 예측 결과)
- Redis 7.0+ (응답 캐싱, Celery 브로커)
- 파일 시스템 (업로드된 CSV 파일, ECLO 모델 파일)

**Testing**: pytest (수동 탐색적 테스트 중심, 자동화 테스트는 선택사항)

**Target Platform**: Linux localhost 개발 환경 (Docker Compose 스택)

**Project Type**: Web application (Frontend: Streamlit, Backend: FastAPI)

**Performance Goals**:
- ECLO 예측 API: 평균 1초 이내, 90th percentile 2초 이내
- AI 챗봇 API: 캐시 히트 100ms 이내, 캐시 미스 5초 이내
- 동시 사용자: 50명 동시 예측 요청 처리 (3초 이내)
- 파일 업로드: 10MB/5초, 50MB/15초

**Constraints**:
- API 키는 클라이언트에서 관리 (서버에 저장하지 않음)
- CSV 파일 크기 제한: 50MB
- 배치 예측 큐 크기 제한: 100개
- 캐시 TTL: 1시간
- Docker 전체 스택 시작 시간: 30초 이내

**Scale/Scope**:
- 동시 접속자: ~100명 (현재 ~10명에서 10배 증가)
- 데이터셋 저장: PostgreSQL (확장 가능)
- API 엔드포인트: 10+ (ECLO 예측, 챗봇, 데이터셋 관리, 분석 도구 22개)
- 코드 이관: utils/ 모듈 (~3,000줄) → backend/services

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### ⚠️ Constitution 위반 사항 (임시 예외 승인)

이 프로젝트는 현행 Constitution v1.2.1의 일부 원칙을 **임시로 예외 처리**합니다:

**예외 1: Simplicity & Accessibility (섹션 II)**
- **원칙**: "별도 백엔드 서버나 데이터베이스 구축 금지"
- **이 프로젝트**: FastAPI 백엔드 + PostgreSQL + Redis 추가
- **정당화**: 데이터 영속성, 확장성, 성능 개선을 위해 불가피함

**예외 2: Scope Discipline (섹션 V - 제외 범위)**
- **원칙**: "별도 백엔드 API 개발", "데이터베이스 구축" 제외
- **이 프로젝트**: 프론트엔드/백엔드 분리 아키텍처 도입
- **정당화**: 교육 목적 확장 (백엔드 아키텍처 학습), 실무 환경 경험

### 준수하는 Constitution 원칙

✅ **I. Data-First Exploration** (유지)
- 데이터 탐색 기능 유지
- 시각화 우선 접근 유지
- 22개 분석 도구 백엔드로 이관하되 기능 동일

✅ **III. Educational Purpose** (확장)
- 기존: Streamlit 기초 학습
- v1.3: 백엔드 아키텍처, API 설계, DB 모델링 학습 추가
- 학습자가 실무 환경 경험 가능

✅ **IV. Streamlit-Based Visualization** (부분 유지)
- Streamlit 프론트엔드 유지
- 시각화 모듈(Plotly, Folium) 클라이언트 사이드 유지
- UI/UX 변경 최소화

✅ **VI. Git Commit Convention** (완전 준수)
✅ **VII. Python Code Style** (완전 준수)
✅ **VIII. Data Handling Rules** (완전 준수)
✅ **IX. Dependencies** (확장)
✅ **X. Documentation & Comments** (완전 준수)

### 복잡도 관리 전략

Constitution 섹션 II "Simplicity & Accessibility" 위반을 최소화하기 위한 전략:

1. **단계별 마이그레이션**
   - Phase 1: ECLO 예측 API만 (단순)
   - Phase 2: AI 챗봇 API (중간)
   - Phase 3: 데이터 관리 API (복잡)

2. **Docker Compose로 복잡도 은폐**
   - 초보자: `docker compose up` 한 줄로 전체 스택 실행
   - 내부 복잡도 (PostgreSQL, Redis, Celery)는 컨테이너로 추상화

3. **기존 코드 구조 유지**
   - utils/ 모듈 로직을 backend/services로 이관 시 구조 동일 유지
   - 함수 시그니처 최대한 보존

4. **v1.2.3 병행 유지**
   - 초보자용: v1.2.3 Streamlit 단일 앱 (ver/1.2.3 브랜치)
   - 중급자용: v1.3 백엔드 분리 (ver/1.3 브랜치)

### Gate Decision: ✅ PROCEED WITH CAUTION

**승인 조건:**
- Constitution 위반을 인지하고 진행
- 향후 Constitution v1.3.0 개정 시 이 프로젝트 반영
- v1.2.3 단일 앱 버전 병행 유지

**Phase 0 진행 가능**

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

**선택한 구조**: Option 2 - Web application (Frontend + Backend 분리)

```text
hab_public_data/
├── app.py                      # Streamlit 프론트엔드 (간소화)
├── .env                       # 🆕 프론트엔드 환경 변수
├── backend/                    # 🆕 FastAPI 백엔드 서버
│   ├── .env                   # 🆕 백엔드 환경 변수
│   ├── main.py                # FastAPI 엔트리포인트
│   ├── config.py              # 환경 설정
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py           # 의존성 (DB 세션, Redis 클라이언트)
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── chat.py       # POST /api/chat/message
│   │       ├── prediction.py # POST /api/predict/eclo, /api/predict/eclo/batch
│   │       ├── datasets.py   # POST /api/datasets/upload, GET /api/datasets
│   │       └── analysis.py   # 22개 Tool Calling API
│   ├── core/
│   │   ├── __init__.py
│   │   └── cache.py          # Redis 캐싱 유틸리티
│   ├── db/
│   │   ├── __init__.py
│   │   ├── session.py        # SQLAlchemy 세션 관리
│   │   ├── base.py           # Base 모델
│   │   └── models/
│   │       ├── __init__.py
│   │       ├── dataset.py    # Dataset 모델
│   │       ├── conversation.py # Conversation, Message 모델
│   │       └── prediction.py # Prediction 모델
│   ├── schemas/               # Pydantic 스키마
│   │   ├── __init__.py
│   │   ├── chat.py
│   │   ├── prediction.py
│   │   └── dataset.py
│   ├── services/              # 비즈니스 로직 (utils 이관)
│   │   ├── __init__.py
│   │   ├── chat_service.py   # utils/chatbot.py, graph.py 이관
│   │   ├── analysis_service.py # utils/tools.py 이관
│   │   ├── prediction_service.py # utils/predictor.py 이관
│   │   └── dataset_service.py # utils/loader.py 이관
│   ├── ml/
│   │   ├── __init__.py
│   │   └── model_loader.py   # ECLO 모델 싱글톤 로더
│   ├── tasks/
│   │   ├── __init__.py
│   │   └── prediction_tasks.py # Celery 배치 예측 작업
│   └── Dockerfile             # FastAPI 컨테이너
├── utils/                      # 프론트엔드 전용 (시각화)
│   ├── __init__.py
│   ├── visualizer.py          # Plotly 시각화 (유지)
│   ├── geo.py                 # Folium 지도 (유지)
│   ├── narration.py           # 나레이션 (유지)
│   └── prompts.py             # 시스템 프롬프트 (유지)
├── model/                      # ECLO 모델 파일
│   ├── accident_lgbm_model.pkl
│   ├── label_encoders.pkl
│   └── feature_config.json
├── alembic/                    # 🆕 DB 마이그레이션
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── docker-compose.yml         # 🆕 전체 스택 구성
├── Dockerfile.streamlit       # 🆕 Streamlit 컨테이너
├── requirements.txt           # 프론트엔드 의존성
├── requirements-backend.txt   # 🆕 백엔드 의존성
└── pyproject.toml
```

**환경 변수 파일 구조:**
- `hab_public_data/.env`: 프론트엔드 환경 변수 (BACKEND_URL, CLAUDE_API_KEY 등)
- `hab_public_data/backend/.env`: 백엔드 환경 변수 (DATABASE_URL, REDIS_URL, CELERY_BROKER_URL 등)

**Structure Decision**:
- **Web application 구조 선택**: FastAPI 백엔드 + Streamlit 프론트엔드 분리
- **backend/ 디렉토리 신규 생성**: FastAPI 앱 전체 포함
- **utils/ 디렉토리 역할 변경**: 시각화 전용 (chatbot, tools, predictor, loader 제거)
- **model/ 디렉토리 유지**: ECLO 모델 파일 (백엔드에서 참조)
- **alembic/ 디렉토리 신규 생성**: PostgreSQL 마이그레이션 관리

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| FastAPI 백엔드 서버 추가 | 데이터 영속성, 확장성, 성능 개선 | Streamlit 단일 앱으로는 세션 간 데이터 공유 불가, 동시 사용자 제한 (~10명) |
| PostgreSQL 데이터베이스 | 대화 이력, 데이터셋 메타데이터 영구 저장 | 파일 기반 저장은 동시성 문제, 쿼리 성능 저하, 데이터 무결성 보장 어려움 |
| Redis 캐싱 시스템 | 동일 질문 빠른 응답 (100ms 목표) | Streamlit @cache_data는 단일 세션만 지원, 사용자 간 공유 불가 |
| Celery 태스크 큐 | 배치 예측 비동기 처리 (100건 예측) | 동기 처리 시 사용자 대기 시간 과다 (2분+), 타임아웃 발생 |
| Docker Compose 스택 | 복잡도 은폐, 초보자 설치 간소화 | 개별 설치 (PostgreSQL, Redis, Celery) 시 환경 설정 복잡, 초보자 진입 장벽 증가 |
| SQLAlchemy ORM | 타입 안전성, 마이그레이션 지원 | raw SQL은 타입 안전성 없음, 스키마 변경 시 수동 마이그레이션 필요 |

**복잡도 상쇄 전략:**
1. Docker Compose로 `docker compose up` 한 줄 실행
2. 환경 변수 자동 로드 (.env 파일)
3. Alembic 마이그레이션 자동화
4. FastAPI 자동 문서 생성 (/docs)
