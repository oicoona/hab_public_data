# v1.3 백엔드 서버(WAS) 구축 가이드

## 목표

현재 Streamlit 모노리식 애플리케이션에 백엔드 서버를 추가하여 프론트엔드/백엔드 분리 아키텍처로 전환합니다.

**핵심 목적:**
- 응답 캐싱으로 성능 향상
- 데이터 영구 저장 및 공유
- 모델 서빙 최적화
- 확장 가능한 아키텍처 구축

**중요:** API 키는 v1.2.3처럼 클라이언트에서 개별 관리합니다. 사용자가 직접 입력하고 관리합니다.

---

## 현재 구조 분석

### 프로젝트 모듈 현황

| 모듈 | 라인 수 | 역할 | 백엔드 이관 추천 |
|------|---------|------|-----------------|
| `tools.py` | 1,180 | 22개 데이터 분석 도구 (Tool Calling) | ⭐⭐⭐⭐⭐ |
| `chatbot.py` | 559 | LangGraph 기반 AI 챗봇 | ⭐⭐⭐⭐⭐ |
| `visualizer.py` | 517 | Plotly 시각화 | ❌ (프론트엔드 유지) |
| `prompts.py` | 271 | 시스템 프롬프트 | ⭐⭐⭐⭐⭐ |
| `predictor.py` | 268 | ECLO 예측 모델 (LightGBM) | ⭐⭐⭐⭐⭐ |
| `geo.py` | 232 | Folium 지도 생성 | ❌ (프론트엔드 유지) |
| `narration.py` | 192 | 나레이션 텍스트 생성 | ⭐⭐⭐ |
| `loader.py` | 188 | CSV 파일 로딩 | ⭐⭐⭐⭐ |
| `graph.py` | 147 | LangGraph StateGraph 정의 | ⭐⭐⭐⭐⭐ |

### 모델 파일

```
model/
├── accident_lgbm_model.pkl  # 1.4MB - LightGBM 모델
├── label_encoders.pkl       # 8.3KB - 라벨 인코더
└── feature_config.json      # 458B - 피처 설정
```

### 현재 아키텍처

```
┌─────────────────────────────┐
│     Streamlit App (app.py)   │
│  ┌────────────────────────┐  │
│  │  utils/ 모듈 직접 호출   │  │
│  │  - chatbot.py          │  │
│  │  - tools.py            │  │
│  │  - predictor.py        │  │
│  │  - loader.py           │  │
│  └────────────────────────┘  │
└─────────────────────────────┘

- API 키: 사용자가 직접 입력 (session_state)
- 데이터: session_state에만 존재 (휘발성)
- 모델: 사용자마다 메모리 로드 (1.4MB)
```

---

## 백엔드 이관 추천 기능 (우선순위별)

### 🔴 우선순위 1: 강력 추천

#### 1. AI 챗봇 전체 스택
**모듈:** `chatbot.py` + `graph.py` + `tools.py` + `prompts.py`

**현재 문제점:**
- 동일 질문에도 매번 API 호출 (캐싱 없음)
- 대화 이력 휘발성 (세션 종료 시 사라짐)
- 데이터 분석 결과 저장 안 됨

**백엔드 이관 시 해결:**
- Redis 캐싱으로 응답 속도 향상
- PostgreSQL에 대화 이력 영구 저장
- 분석 결과 재사용 가능

**API 설계:**
```http
POST /api/chat/message
Content-Type: application/json
X-Anthropic-API-Key: sk-ant-api03-xxxxx  ⬅ 클라이언트가 전달

{
  "dataset_id": "train_001",
  "message": "사고가 가장 많은 시간대는?",
  "conversation_id": "conv_456"
}

→ Response:
{
  "response": "...",
  "tool_calls": [...],
  "token_usage": {"input": 1234, "output": 567},
  "cache_hit": false
}
```

---

#### 2. ECLO 예측 모델 서빙
**모듈:** `predictor.py` + `model/`

**현재 문제점:**
- 사용자마다 1.4MB 모델을 메모리에 로드
- 배치 예측 시 순차 처리 (비효율)
- 예측 결과 저장 안 됨
- 모델 업데이트 시 전체 앱 재배포 필요

**백엔드 이관 시 해결:**
- 서버에서 모델 한 번만 로드 (메모리 효율)
- Celery 큐를 통한 배치 예측 병렬 처리
- PostgreSQL에 예측 이력 저장
- 모델만 교체하여 zero-downtime 업데이트

**API 설계:**
```http
POST /api/predict/eclo
Content-Type: application/json

{
  "weather": "맑음",
  "road_surface": "건조",
  "road_type": "교차로",
  ...
}

→ Response:
{
  "eclo": 0.23,
  "interpretation": "일반",
  "detail": "..."
}
```

---

### 🟡 우선순위 2: 추천

#### 3. 데이터 로더 & 저장소
**모듈:** `loader.py`

**현재 문제점:**
- 업로드한 CSV가 세션에만 존재 (휘발성)
- Streamlit 메모리 제한으로 대용량 파일 처리 어려움
- 데이터셋 공유 불가능

**백엔드 이관 시 해결:**
- 서버 스토리지/DB에 영구 저장
- 대용량 파일 처리 가능
- 팀원 간 데이터셋 공유

---

### ❌ 프론트엔드 유지

#### 시각화 모듈
**모듈:** `visualizer.py` (Plotly), `geo.py` (Folium)

**프론트엔드 유지 이유:**
- 클라이언트 사이드 렌더링이 효율적
- 사용자 상호작용 (줌, 필터, 호버 등) 즉각 반응
- 서버 부하 감소

---

## 아키텍처 설계

### 목표 아키텍처 (백엔드 분리형)

```
┌──────────────┐           ┌──────────────┐           ┌──────────────┐
│  Streamlit   │  HTTP     │   FastAPI    │   SQL     │ PostgreSQL   │
│  (Frontend)  │◄─────────►│  (Backend)   │◄─────────►│  (Database)  │
│              │           │              │           │              │
│  - API 키입력 │           │  - API 라우팅 │           │  - 데이터셋   │
│  - 시각화     │           │  - 비즈니스   │           │  - 대화이력   │
│  - 지도       │           │    로직       │           │  - 예측결과   │
│  - UI/UX     │           │  - ML 서빙    │           └──────────────┘
└──────────────┘           └──────────────┘
                                  ▲ │                  ┌──────────────┐
                                  │ │        TCP       │    Redis     │
                                  │ └─────────────────►│   (Cache)    │
                                  │                    │              │
                                  │                    │  - 응답캐싱   │
                                  │                    └──────────────┘
                                  │
                                  │                    ┌──────────────┐
                                  │        AMQP        │    Celery    │
                                  └───────────────────►│   (Queue)    │
                                                       │              │
                                                       │  - 배치예측   │
                                                       └──────────────┘
```

**API 키 흐름:**
1. 사용자가 Streamlit 사이드바에서 API 키 입력
   - **env 파일 기반 자동 설정 (신규):**
     - `env/` 디렉토리 내 설정 파일에서 `claude_api_key` 체크
     - 키가 존재하면 자동으로 화면에 등록 (사용자 편의성 향상)
     - 키가 없으면 사용자가 화면에서 직접 입력
2. 프론트엔드가 API 요청 시 헤더에 포함 (`X-Anthropic-API-Key`)
3. 백엔드가 전달받은 API 키로 Anthropic API 호출
4. 사용자별 독립적인 API 키 관리

### 백엔드 디렉토리 구조

```
hab_public_data/
├── app.py                      # Streamlit 프론트엔드
├── backend/                    # 🆕 백엔드 서버
│   ├── main.py                # FastAPI 엔트리포인트
│   ├── config.py              # 환경 설정
│   ├── api/
│   │   └── routes/
│   │       ├── chat.py       # 챗봇 API
│   │       ├── prediction.py # ECLO 예측 API
│   │       └── datasets.py   # 데이터셋 관리 API
│   ├── core/
│   │   └── cache.py          # Redis 캐싱
│   ├── db/
│   │   ├── session.py        # DB 세션
│   │   └── models/
│   │       ├── dataset.py
│   │       ├── conversation.py
│   │       └── prediction.py
│   ├── schemas/               # Pydantic 스키마
│   ├── services/              # 비즈니스 로직
│   │   ├── chat_service.py
│   │   ├── analysis_service.py
│   │   ├── prediction_service.py
│   │   └── dataset_service.py
│   ├── ml/
│   │   └── model_loader.py   # 모델 로딩 (싱글톤)
│   └── tasks/
│       └── prediction_tasks.py
├── utils/                      # 프론트엔드 전용
│   ├── visualizer.py
│   └── geo.py
└── docker-compose.yml
```

---

## 단계별 구현 로드맵

### Phase 1: MVP - ECLO 예측 API (2주)

**목표:** 가장 간단한 기능부터 백엔드로 분리

**작업 내용:**
1. FastAPI 기본 서버 구축
2. ECLO 예측 API 구현
3. Streamlit에서 API 호출로 전환
4. Docker Compose로 로컬 환경 구축

**완료 기준:**
- [ ] FastAPI 서버 실행 확인
- [ ] ECLO 단일 예측 API 동작
- [ ] ECLO 배치 예측 API 동작
- [ ] Streamlit에서 백엔드 API 호출 성공

---

### Phase 2: AI 챗봇 API화 (3주)

**목표:** 대화 이력 영구 저장 및 캐싱

**작업 내용:**
1. PostgreSQL 설정 및 스키마 생성
2. 챗봇 API 구현 (`POST /api/chat/message`)
   - 클라이언트에서 전달한 API 키로 Anthropic 호출
3. Redis 캐싱 추가
4. 대화 이력 DB 저장

**완료 기준:**
- [ ] PostgreSQL 연동 완료
- [ ] 챗봇 API 동작 확인
- [ ] 대화 이력 DB 저장 확인
- [ ] Redis 캐싱 동작 확인

---

### Phase 3: 데이터 관리 API (2주)

**목표:** 데이터셋 영구 저장 및 공유

**작업 내용:**
1. 파일 업로드 API (`POST /api/datasets/upload`)
2. 데이터셋 조회 API (`GET /api/datasets`)
3. 데이터셋 공유 기능

**완료 기준:**
- [ ] CSV 업로드 API 동작
- [ ] 데이터셋 목록 조회 동작
- [ ] 데이터셋 공유 링크 생성

---

### Phase 4: 고도화 (진행형)

**작업 내용:**
1. Celery 큐 (배치 예측 비동기 처리)
2. Prometheus + Grafana 모니터링
3. 모델 버전 관리

---

## 기술 스택

### 백엔드

| 분류 | 기술 | 용도 |
|------|------|------|
| **웹 프레임워크** | FastAPI 0.104+ | REST API 서버 |
| **ASGI 서버** | Uvicorn 0.24+ | 비동기 서버 |
| **데이터베이스** | PostgreSQL 15+ | 데이터 영구 저장 |
| **ORM** | SQLAlchemy 2.0+ | 데이터베이스 ORM |
| **마이그레이션** | Alembic 1.12+ | DB 스키마 관리 |
| **캐시** | Redis 7.0+ | 응답 캐싱 |
| **태스크 큐** | Celery 5.3+ | 비동기 작업 처리 |
| **환경 변수** | python-dotenv 1.0+ | 환경 설정 |
| **ML** | LightGBM 4.1+, scikit-learn 1.3+ | ECLO 예측 모델 |
| **AI** | LangChain 0.3+, LangGraph 0.2+, Anthropic | AI 챗봇 |

### 프론트엔드 (기존 유지)

| 분류 | 기술 | 용도 |
|------|------|------|
| **웹 프레임워크** | Streamlit 1.28+ | UI 프레임워크 |
| **시각화** | Plotly 5.17+ | 차트 생성 |
| **지도** | Folium 0.14+, streamlit-folium 0.15+ | 지도 시각화 |
| **HTTP 클라이언트** | httpx 0.25+ | 백엔드 API 호출 |

### 인프라

| 분류 | 기술 | 용도 |
|------|------|------|
| **컨테이너** | Docker 24+, Docker Compose 2.20+ | 컨테이너화 |
| **웹 서버** | Nginx 1.25+ | 리버스 프록시 |
| **모니터링** | Prometheus, Grafana | 성능 모니터링 |

---

## 환경 변수 설정

### `.env` 파일 예시

```bash
# Backend
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
BACKEND_RELOAD=true

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/hab_public_data
DATABASE_POOL_SIZE=10

# Redis
REDIS_URL=redis://localhost:6379/0
CACHE_TTL=3600

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

### `env/` 디렉토리 설정 파일 (프론트엔드용) 🆕

```bash
# env/.env 또는 env/config.env
# Anthropic API 키 (선택사항)
claude_api_key=sk-ant-api03-xxxxx

# 설정된 경우: 자동으로 화면에 등록
# 설정되지 않은 경우: 사용자가 UI에서 직접 입력
```

**참고:**
- Anthropic API 키는 백엔드 환경 변수에 저장하지 않습니다. 클라이언트가 요청 시 전달합니다.
- `env/` 디렉토리의 설정 파일은 프론트엔드에서 사용자 편의성을 위해 제공되는 옵션입니다.

---

## Docker Compose 구성

### 서비스 구성

v1.3에서는 Docker Compose를 사용하여 전체 스택을 컨테이너화합니다.

```yaml
# docker-compose.yml 주요 서비스
services:
  postgres:     # PostgreSQL 15-alpine
  redis:        # Redis 7-alpine
  backend:      # FastAPI + Uvicorn
  celery-worker # Celery Worker (비동기 작업)
  celery-beat   # Celery Beat (스케줄러)
  flower:       # Celery 모니터링 UI
  streamlit:    # Streamlit 프론트엔드
```

### 빠른 시작

```bash
# 1. 환경 변수 설정
cp .env.example .env

# 2. 전체 스택 실행
docker compose up -d

# 3. 로그 확인
docker compose logs -f

# 4. 서비스 접속
# - Streamlit: http://localhost:8501
# - FastAPI: http://localhost:8000
# - Flower: http://localhost:5555
```

### 주요 명령어

```bash
# 서비스 상태 확인
docker compose ps

# 특정 서비스만 재시작
docker compose restart backend

# PostgreSQL 접속
docker compose exec postgres psql -U hab_user -d hab_public_data

# Redis 캐시 확인
docker compose exec redis redis-cli KEYS "*"

# 종료 (볼륨 유지)
docker compose down

# 종료 (볼륨 삭제)
docker compose down -v
```

### 리소스 요구사항

| 구성 | 메모리 | CPU |
|:-----|:------|:----|
| **최소** (backend + redis + postgres) | 1GB | 0.5 cores |
| **권장** (전체 스택) | 2-3GB | 2 cores |
| **프로덕션** | 4GB | 4 cores |

**상세 가이드:** `DOCKER_README.md` 참고

---

## 비용/이익 분석

| 기능 | 개발 공수 | 운영 비용 | 사용자 가치 | ROI | 추천도 |
|------|----------|-----------|------------|-----|-------|
| **ECLO 예측 API** | 1주 | 낮음 (CPU만) | 높음 (속도↑) | 높음 | ⭐⭐⭐⭐⭐ |
| **AI 챗봇 API** | 2-3주 | 낮음 | 높음 (대화 이력 저장) | 높음 | ⭐⭐⭐⭐⭐ |
| **데이터 저장소** | 1-2주 | 중간 (스토리지+DB) | 중간 (편의성↑) | 중간 | ⭐⭐⭐⭐ |
| **캐싱** | 3일 | 낮음 (Redis) | 높음 (속도↑) | 매우 높음 | ⭐⭐⭐⭐⭐ |

**총 예상 개발 기간:** 6-8주

---

## 다음 단계

1. **Phase 1부터 시작**
   - ECLO 예측 API만 먼저 구현하여 백엔드 아키텍처 검증
   - 성공 후 Phase 2로 확장

2. **기술 스택 확정**
   - FastAPI (권장)
   - PostgreSQL (권장)

3. **개발 환경 구축**
   - Docker Compose로 로컬 개발 환경 세팅

4. **API 명세 작성**
   - OpenAPI (Swagger) 문서 자동 생성

---

## 참고 자료

- FastAPI 공식 문서: https://fastapi.tiangolo.com/
- LangChain 문서: https://python.langchain.com/
- SQLAlchemy 문서: https://docs.sqlalchemy.org/
- Docker Compose 문서: https://docs.docker.com/compose/
