# Phase 0: Research & Technology Decisions

**Feature**: Backend Server Architecture Implementation (v1.3)
**Date**: 2025-12-09
**Status**: Complete

## Overview

이 문서는 대구 공공데이터 시각화 앱 v1.3의 백엔드 아키텍처 전환을 위한 기술 조사 및 결정 사항을 기록합니다. 모든 기술 선택은 `/home/sk/hab_public_data/docs/v1.3/app_improvement_proposal.md`를 기반으로 합니다.

## Technical Decisions

### 1. Backend Framework: FastAPI

**Decision**: FastAPI 0.104+ 선택

**Rationale**:
- **비동기 지원**: async/await를 통한 높은 동시성 처리
- **자동 문서 생성**: OpenAPI/Swagger 자동 생성으로 API 문서화 간소화
- **타입 안전성**: Pydantic 스키마로 요청/응답 검증
- **성능**: Uvicorn ASGI 서버로 높은 성능 (Streamlit 대비 10배+ 처리량)
- **Python 생태계**: 기존 LangChain, LightGBM 코드 재사용 가능

**Alternatives Considered**:
- Flask: 동기 방식, 확장성 제한
- Django: 무거운 ORM, 교육용으로 과도한 복잡도
- Tornado: 비동기 지원하나 FastAPI보다 생태계 작음

**Implementation Notes**:
- Uvicorn 서버로 실행: `uvicorn backend.main:app --reload`
- CORS 설정으로 Streamlit 프론트엔드 허용
- Middleware로 요청 로깅, 에러 처리

---

### 2. Database: PostgreSQL

**Decision**: PostgreSQL 15+ 선택

**Rationale**:
- **JSONB 타입**: tool_calls, input_features 등 복잡한 데이터 저장
- **트랜잭션 지원**: 데이터 무결성 보장
- **확장성**: 수천 건의 대화 이력 효율적 쿼리
- **무료**: 로컬 개발 환경에서 무료 사용
- **Docker 지원**: postgres:15-alpine 이미지로 간단 설치

**Alternatives Considered**:
- SQLite: 동시성 제한, 프로덕션 부적합
- MySQL: JSONB 미지원 (JSON 타입은 성능 저하)
- MongoDB: NoSQL이지만 트랜잭션 약함, SQL보다 학습 곡선

**Schema Highlights**:
```sql
-- 데이터셋 메타데이터
CREATE TABLE datasets (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    rows INTEGER,
    columns INTEGER,
    uploaded_at TIMESTAMP DEFAULT NOW()
);

-- 대화 이력
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    dataset_id INTEGER REFERENCES datasets(id),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER REFERENCES conversations(id),
    role VARCHAR(20) NOT NULL,  -- user/assistant/system
    content TEXT NOT NULL,
    tool_calls JSONB,  -- ← 복잡한 데이터 저장
    created_at TIMESTAMP DEFAULT NOW()
);

-- ECLO 예측 결과
CREATE TABLE predictions (
    id SERIAL PRIMARY KEY,
    model_version VARCHAR(50),
    input_features JSONB NOT NULL,
    eclo_value DECIMAL(10, 4),
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

### 3. ORM: SQLAlchemy 2.0+

**Decision**: SQLAlchemy 2.0+ 선택

**Rationale**:
- **타입 안전성**: 2.0+ 버전은 타입 힌트 개선
- **마이그레이션**: Alembic과 통합으로 스키마 변경 추적
- **복잡한 쿼리**: JOIN, 집계 등 복잡한 쿼리 지원
- **비동기 지원**: async/await와 호환 (AsyncSession)

**Alternatives Considered**:
- raw SQL: 타입 안전성 없음, 마이그레이션 수동 관리
- Peewee: 경량하나 비동기 지원 약함
- Tortoise ORM: 비동기 전용이나 생태계 작음

**Implementation Pattern**:
```python
# backend/db/models/dataset.py
from sqlalchemy import Column, Integer, String, TIMESTAMP
from sqlalchemy.orm import relationship
from backend.db.base import Base

class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    rows = Column(Integer)
    columns = Column(Integer)
    uploaded_at = Column(TIMESTAMP, server_default="now()")

    # Relationships
    conversations = relationship("Conversation", back_populates="dataset")
```

---

### 4. Caching: Redis 7.0+

**Decision**: Redis 7.0+ 선택

**Rationale**:
- **응답 캐싱**: 동일 질문에 대한 LLM 응답 캐싱 (100ms 목표)
- **Celery 브로커**: 배치 예측 작업 큐로 활용
- **세션 공유**: 여러 사용자 간 캐시 공유 (Streamlit @cache_data는 불가)
- **TTL 지원**: 자동 만료 (1시간 기본값)

**Alternatives Considered**:
- Memcached: TTL 지원하나 데이터 구조 단순, Celery 브로커 불가
- 파일 캐시: I/O 병목, 동시성 문제
- Streamlit @cache_data: 단일 세션만 지원, 서버 재시작 시 소실

**Caching Strategy**:
```python
# backend/core/cache.py
import redis
import json
import hashlib

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

def get_cache_key(dataset_id: str, message: str) -> str:
    """dataset_id + message 해시로 캐시 키 생성"""
    content = f"{dataset_id}:{message}"
    return f"chat:{hashlib.md5(content.encode()).hexdigest()}"

def get_cached_response(dataset_id: str, message: str) -> dict | None:
    """캐시된 응답 조회"""
    key = get_cache_key(dataset_id, message)
    cached = redis_client.get(key)
    if cached:
        return json.loads(cached)
    return None

def cache_response(dataset_id: str, message: str, response: dict, ttl: int = 3600):
    """응답 캐싱 (기본 TTL: 1시간)"""
    key = get_cache_key(dataset_id, message)
    redis_client.setex(key, ttl, json.dumps(response))
```

---

### 5. Task Queue: Celery 5.3+

**Decision**: Celery 5.3+ 선택

**Rationale**:
- **비동기 작업**: 배치 예측 (100건) 백그라운드 처리
- **Redis 브로커**: 기존 Redis 활용 (추가 인프라 불필요)
- **결과 백엔드**: Redis에 작업 결과 저장
- **모니터링**: Flower UI로 작업 상태 시각화

**Alternatives Considered**:
- RQ (Redis Queue): 단순하나 기능 제한적
- Dramatiq: 비동기 전용이나 생태계 작음
- APScheduler: 스케줄링만 지원, 분산 큐 불가

**Task Definition**:
```python
# backend/tasks/prediction_tasks.py
from celery import Celery

celery_app = Celery(
    "hab_public_data",
    broker="redis://localhost:6379/1",
    backend="redis://localhost:6379/2"
)

@celery_app.task
def batch_predict_eclo(accidents: list[dict]) -> list[dict]:
    """배치 ECLO 예측 작업"""
    from backend.ml.model_loader import get_model

    model = get_model()
    results = []

    for accident in accidents:
        eclo = model.predict([accident])
        results.append({
            "input": accident,
            "eclo": float(eclo[0]),
            "interpretation": interpret_eclo(eclo[0])
        })

    return results
```

---

### 6. Migration Tool: Alembic 1.12+

**Decision**: Alembic 1.12+ 선택

**Rationale**:
- **SQLAlchemy 통합**: ORM 모델에서 자동 마이그레이션 생성
- **버전 관리**: 스키마 변경 이력 추적
- **롤백 지원**: `alembic downgrade` 명령으로 이전 버전 복구
- **Docker 통합**: 컨테이너 시작 시 자동 마이그레이션 적용

**Alternatives Considered**:
- Django Migrations: Django 프레임워크 종속
- Flyway: Java 기반, Python 생태계 밖
- 수동 SQL: 버전 관리 어려움, 실수 가능성

**Usage**:
```bash
# 마이그레이션 생성
alembic revision --autogenerate -m "Add datasets table"

# 마이그레이션 적용
alembic upgrade head

# 롤백
alembic downgrade -1
```

---

### 7. Container Orchestration: Docker Compose

**Decision**: Docker Compose 2.20+ 선택

**Rationale**:
- **복잡도 은폐**: PostgreSQL, Redis, Celery, FastAPI, Streamlit을 한 번에 실행
- **초보자 친화적**: `docker compose up` 한 줄로 전체 스택 시작
- **환경 일관성**: 로컬/프로덕션 환경 동일
- **헬스체크**: 서비스 의존성 자동 관리

**Alternatives Considered**:
- Kubernetes: 과도한 복잡도, 교육용 부적합
- Docker Swarm: Compose보다 복잡, 로컬 개발 부적합
- 개별 실행: PostgreSQL, Redis 수동 설치 필요 (초보자 진입 장벽)

**docker-compose.yml Structure**:
```yaml
services:
  postgres:
    image: postgres:15-alpine
    ports: ["5432:5432"]
    healthcheck:
      test: ["CMD", "pg_isready"]
      interval: 5s

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s

  backend:
    build: ./backend
    ports: ["8000:8000"]
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  celery-worker:
    build: ./backend
    command: celery -A backend.tasks.celery_app worker
    depends_on:
      - redis

  streamlit:
    build: .
    ports: ["8501:8501"]
    depends_on:
      - backend
```

---

### 8. API Client: httpx 0.25+

**Decision**: httpx 0.25+ (프론트엔드에서 사용)

**Rationale**:
- **비동기 지원**: async/await로 Streamlit에서 효율적 호출
- **Requests 호환**: requests 라이브러리와 유사한 API
- **HTTP/2 지원**: 더 나은 성능
- **타입 힌트**: 타입 안전성

**Alternatives Considered**:
- requests: 동기 전용, 비동기 불가
- aiohttp: 더 로우레벨, httpx가 더 사용하기 쉬움
- urllib: 표준 라이브러리이나 불편한 API

**Usage Pattern**:
```python
# app.py (Streamlit Frontend)
import httpx
import streamlit as st

BACKEND_URL = st.secrets.get("BACKEND_URL", "http://localhost:8000")

def predict_eclo(accident_data: dict) -> dict:
    """백엔드 ECLO 예측 API 호출"""
    with httpx.Client() as client:
        response = client.post(
            f"{BACKEND_URL}/api/predict/eclo",
            json=accident_data,
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()
```

---

## Code Migration Strategy

### utils/ → backend/services 이관 계획

| AS-IS (utils/) | TO-BE (backend/services) | 변경사항 |
|----------------|-------------------------|----------|
| chatbot.py (559줄) | chat_service.py | LangGraph 로직 유지, API 인터페이스 추가 |
| graph.py (147줄) | chat_service.py (통합) | StateGraph 정의 포함 |
| tools.py (1,180줄) | analysis_service.py | 22개 도구 API 엔드포인트로 변환 |
| predictor.py (268줄) | prediction_service.py | 모델 로딩을 ml/model_loader.py로 분리 |
| prompts.py (271줄) | prompts.py (유지) | 프론트엔드에서도 사용하므로 유지 |
| loader.py (188줄) | dataset_service.py | DB 저장 로직 추가 |
| visualizer.py (517줄) | visualizer.py (유지) | 프론트엔드 전용 |
| geo.py (232줄) | geo.py (유지) | 프론트엔드 전용 |
| narration.py (192줄) | narration.py (유지) | 프론트엔드 전용 |

**총 이관 코드**: ~2,342줄 (chatbot + graph + tools + predictor + loader)
**유지 코드**: ~1,212줄 (prompts + visualizer + geo + narration)

---

## Environment Variables

### 프론트엔드 (.env)
```bash
# Streamlit Frontend Configuration
BACKEND_URL=http://localhost:8000
CLAUDE_API_KEY=sk-ant-api03-xxxxx  # 선택사항 (자동 로드)
```

### 백엔드 (backend/.env)
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/hab_public_data
DATABASE_POOL_SIZE=10

# Redis
REDIS_URL=redis://localhost:6379/0
CACHE_TTL=3600

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Backend
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
BACKEND_RELOAD=true  # 개발 모드
```

---

## Performance Benchmarks (참고 자료)

| 항목 | AS-IS (v1.2.3) | TO-BE (v1.3 목표) | 비고 |
|------|----------------|------------------|------|
| ECLO 예측 | 사용자당 2초 (모델 로딩) | 1초 이내 | 모델 사전 로드 |
| AI 챗봇 (신규 질문) | 3-5초 | 5초 이내 | LLM 호출 시간 |
| AI 챗봇 (캐시 히트) | N/A | 100ms 이내 | Redis 캐싱 |
| 동시 사용자 | ~10명 | ~100명 | 백엔드 확장성 |
| 데이터셋 업로드 (10MB) | N/A (파일 기반) | 5초 이내 | multipart/form-data |

---

## Open Questions (해결됨)

모든 기술 결정은 app_improvement_proposal.md에 명시되어 완료되었습니다. 추가 조사 불필요.

---

## Next Steps

**Phase 0 Complete** ✅

**Phase 1 (Design & Contracts) 진행 가능**:
1. data-model.md 작성 (DB 스키마 상세)
2. contracts/ 디렉토리에 OpenAPI 스키마 생성
3. quickstart.md 작성 (빠른 시작 가이드)
