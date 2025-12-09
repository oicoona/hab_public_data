# 대구 공공데이터 시각화 앱 개선 제안서 (v1.2.3 → v1.3)

**문서 버전**: v1.3
**작성일**: 2025-12-08
**참고 문서**: `docs/v1.3/note.md`

---

## 1. 개요

본 문서는 대구 공공데이터 시각화 앱 v1.2.3의 현재 상태(AS-IS)와 v1.3에서 목표하는 개선 상태(TO-BE)를 비교 분석한다.

v1.3의 핵심 목표:
1. **백엔드 서버(WAS) 추가** - FastAPI 기반 REST API 서버 구축
2. **프론트엔드/백엔드 분리** - Streamlit(Frontend) ↔ FastAPI(Backend) 아키텍처
3. **성능 최적화** - Redis 캐싱, PostgreSQL 데이터 영구 저장
4. **확장성 향상** - 모델 서빙 최적화, 배치 예측 큐잉
5. **데이터 영속성** - 데이터셋 및 대화 이력 영구 저장

**중요:** API 키는 v1.2.3처럼 클라이언트에서 개별 관리합니다 (사용자가 직접 입력).

---

## 2. 아키텍처 비교

### 2.1 전체 아키텍처

| 구분 | AS-IS (v1.2.3) | TO-BE (v1.3) |
|:-----|:---------------|:-------------|
| **구조** | 모노리식 (Streamlit 단일 앱) | 마이크로서비스 (Frontend + Backend) |
| **프론트엔드** | Streamlit + utils/ 모듈 | Streamlit (시각화 + UI만) |
| **백엔드** | 없음 | FastAPI (비즈니스 로직 + ML 서빙) |
| **데이터베이스** | 없음 (파일 기반, session_state) | PostgreSQL (데이터셋, 대화이력, 예측결과) |
| **캐시** | Streamlit @cache_data | Redis (응답 캐싱) |
| **통신** | 내부 함수 호출 | HTTP REST API |
| **API 키 관리** | 사용자 직접 입력 (session_state) | 동일 (클라이언트에서 관리) ✅ |
| **API 키 설정** | 매번 수동 입력 | env 파일 자동 로드 지원 🆕 |

#### 2.1.1 현재 구조 (AS-IS)

```
┌─────────────────────────────┐
│     Streamlit App (app.py)   │
│  ┌────────────────────────┐  │
│  │  utils/ 모듈 직접 호출   │  │
│  │  - chatbot.py          │  │
│  │  - tools.py (22개)     │  │
│  │  - predictor.py        │  │
│  │  - loader.py           │  │
│  │  - visualizer.py       │  │
│  │  - geo.py              │  │
│  └────────────────────────┘  │
└─────────────────────────────┘

- API 키: 사용자가 직접 입력 (session_state)
- 데이터: session_state에만 존재 (휘발성)
- 모델: 사용자마다 메모리 로드 (1.4MB)
```

#### 2.1.2 목표 구조 (TO-BE)

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
      │                           ▲ │                  ┌──────────────┐
      │                           │ │        TCP       │    Redis     │
      └─ API 키 헤더 전달          │ └─────────────────►│   (Cache)    │
         (X-Anthropic-API-Key)    │                    │  - 응답캐싱   │
                                  │                    └──────────────┘
                                  │
                                  │                    ┌──────────────┐
                                  │        AMQP        │    Celery    │
                                  └───────────────────►│   (Queue)    │
                                                       │  - 배치예측   │
                                                       └──────────────┘

- API 키: 클라이언트가 요청 헤더로 전달 (각자 관리)
- 데이터: PostgreSQL 영구 저장
- 모델: 서버에서 한 번만 로드 (메모리 효율)
```

---

## 3. 기능별 AS-IS / TO-BE 비교

### 3.1 AI 챗봇 스택

| 구분 | AS-IS (v1.2.3) | TO-BE (v1.3) |
|:-----|:---------------|:-------------|
| **로직 위치** | `utils/chatbot.py` (프론트엔드) | `backend/services/chat_service.py` |
| **API 키 관리** | 사용자 입력 (st.sidebar) | 동일 (클라이언트에서 관리) ✅ |
| **API 키 설정** | 매번 수동 입력 | env 파일 자동 로드 + 수동 입력 🆕 |
| **API 키 전달** | - | 요청 헤더 (`X-Anthropic-API-Key`) 🆕 |
| **대화 이력** | session_state (휘발성) | PostgreSQL (영구 저장) |
| **캐싱** | @cache_data (제한적) | Redis (동일 질문 빠른 응답) |

#### 3.1.1 API 엔드포인트 설계

```http
POST /api/chat/message
Content-Type: application/json
X-Anthropic-API-Key: sk-ant-api03-xxxxx  ⬅ 🔑 클라이언트가 전달

{
  "dataset_id": "train_001",
  "message": "사고가 가장 많은 시간대는?",
  "conversation_id": "conv_456"
}

→ Response:
{
  "response": "분석 결과, 오후 5-6시에 사고가 가장 많이 발생합니다...",
  "tool_calls": [
    {
      "name": "get_value_counts",
      "args": {"column": "시간대"},
      "result": "저녁: 3245건, 낮: 2891건..."
    }
  ],
  "token_usage": {
    "input": 1234,
    "output": 567,
    "total": 1801
  },
  "cache_hit": false,
  "conversation_id": "conv_456",
  "timestamp": "2024-12-08T21:30:00Z"
}
```

**API 키 처리 흐름:**
1. 사용자가 Streamlit 사이드바에서 API 키 입력
   - **env 파일 기반 자동 설정 (v1.3 신규):**
     - `env/` 디렉토리 내 설정 파일에서 `claude_api_key` 체크
     - 키가 존재하면 자동으로 화면에 등록 (사용자 편의성 향상)
     - 키가 없으면 사용자가 화면에서 직접 입력하는 방식 제공
2. 프론트엔드가 API 요청 시 `X-Anthropic-API-Key` 헤더에 포함
3. 백엔드가 전달받은 API 키로 Anthropic API 호출
4. 각 사용자가 자신의 API 키 관리

---

### 3.2 ECLO 예측 모델

| 구분 | AS-IS (v1.2.3) | TO-BE (v1.3) |
|:-----|:---------------|:-------------|
| **로직 위치** | `utils/predictor.py` | `backend/ml/predictor.py` |
| **모델 로딩** | 사용자마다 로드 (1.4MB) | 서버에서 한 번만 로드 (싱글톤) |
| **배치 예측** | 순차 처리 | Celery 큐 병렬 처리 |
| **예측 이력** | 저장 안 됨 | PostgreSQL 저장 |
| **모델 업데이트** | 전체 앱 재배포 | 모델만 교체 (zero-downtime) |

#### 3.2.1 API 엔드포인트 설계

**단일 예측:**
```http
POST /api/predict/eclo
Content-Type: application/json

{
  "weather": "맑음",
  "road_surface": "건조",
  "road_type": "교차로",
  "accident_type": "차대차",
  "time_period": "낮",
  "district": "중구",
  "day_of_week": "월요일",
  "accident_hour": 14,
  "accident_year": 2024,
  "accident_month": 12,
  "accident_day": 8
}

→ Response:
{
  "eclo": 0.23,
  "interpretation": "일반",
  "detail": "일반적인 사고 수준입니다. 경상 가능성이 있으며, 치료가 필요할 수 있습니다.",
  "prediction_id": "pred_789",
  "model_version": "v1.0",
  "timestamp": "2024-12-08T21:30:00Z"
}
```

**배치 예측:**
```http
POST /api/predict/eclo/batch
Content-Type: application/json

{
  "accidents": [
    {"weather": "맑음", "road_surface": "건조", ...},
    {"weather": "비", "road_surface": "젖음/습기", ...},
    {"weather": "눈", "road_surface": "적설", ...}
  ]
}

→ Response:
{
  "batch_id": "batch_123",
  "status": "processing",
  "total": 3,
  "results_url": "/api/predict/batch/batch_123/results",
  "estimated_completion": "2024-12-08T21:31:00Z"
}
```

---

### 3.3 데이터 관리

| 구분 | AS-IS (v1.2.3) | TO-BE (v1.3) |
|:-----|:---------------|:-------------|
| **로직 위치** | `utils/loader.py` | `backend/services/dataset_service.py` |
| **데이터 저장** | session_state (휘발성) | PostgreSQL + 파일 스토리지 |
| **용량 제한** | Streamlit 메모리 제한 | 서버 스토리지 (확장 가능) |
| **데이터 공유** | 불가능 | 팀원 간 공유 링크 생성 |
| **버전 관리** | 없음 | 데이터셋 버전 이력 추적 |

#### 3.3.1 API 엔드포인트 설계

```http
# 데이터셋 업로드
POST /api/datasets/upload
Content-Type: multipart/form-data

file: train.csv
name: 대구_교통사고_훈련데이터
description: 2024년 대구 교통사고 데이터

→ Response:
{
  "dataset_id": "ds_456",
  "name": "대구_교통사고_훈련데이터",
  "rows": 15234,
  "columns": 28,
  "size_bytes": 2048576,
  "uploaded_at": "2024-12-08T21:30:00Z",
  "columns_info": [
    {"name": "기상상태", "type": "object", "unique": 6},
    {"name": "노면상태", "type": "object", "unique": 5}
  ]
}

# 데이터셋 목록 조회
GET /api/datasets?limit=10

→ Response:
{
  "datasets": [
    {
      "dataset_id": "ds_456",
      "name": "대구_교통사고_훈련데이터",
      "rows": 15234,
      "columns": 28,
      "uploaded_at": "2024-12-08T21:30:00Z"
    }
  ],
  "total": 5,
  "page": 1
}

# 데이터셋 공유
POST /api/datasets/ds_456/share

→ Response:
{
  "share_token": "abc123def456",
  "share_url": "https://app.example.com/shared/abc123def456",
  "expires_at": "2024-12-15T21:30:00Z"
}
```

---

### 3.4 Tool Calling (22개 분석 도구)

| 구분 | AS-IS (v1.2.3) | TO-BE (v1.3) |
|:-----|:---------------|:-------------|
| **로직 위치** | `utils/tools.py` | `backend/services/analysis_service.py` |
| **데이터 접근** | RunnableConfig (DataFrame 직접 전달) | API 요청으로 dataset_id 전달 |
| **결과 캐싱** | 없음 | Redis (동일 분석 재사용) |
| **실행 환경** | 사용자 세션 | 백엔드 서버 |

#### 3.4.1 Tool 실행 방식 비교

**AS-IS (v1.2.3)**
```python
# 프론트엔드에서 직접 실행
@tool
def get_value_counts(column: str, config: RunnableConfig) -> str:
    df = get_dataframe_from_config(config)  # session_state에서 가져옴
    return df[column].value_counts().to_string()
```

**TO-BE (v1.3)**
```python
# Backend (FastAPI)
@router.post("/analysis/value_counts")
def analyze_value_counts(
    request: ValueCountsRequest,
    api_key: str = Header(alias="X-Anthropic-API-Key")
):
    # API 키는 전달받지만 이 기능에서는 사용 안 함
    # 데이터 분석 도구는 Anthropic API 호출하지 않음

    dataset = db.query(Dataset).filter_by(id=request.dataset_id).first()
    df = load_dataframe(dataset.file_path)

    # 캐시 확인
    cache_key = f"value_counts:{request.dataset_id}:{request.column}"
    cached = redis.get(cache_key)
    if cached:
        return {"result": cached, "cache_hit": True}

    # 분석 실행
    result = df[request.column].value_counts().to_dict()
    redis.setex(cache_key, 3600, json.dumps(result))

    return {"result": result, "cache_hit": False}
```

---

### 3.5 시각화 모듈 (프론트엔드 유지)

| 구분 | AS-IS (v1.2.3) | TO-BE (v1.3) |
|:-----|:---------------|:-------------|
| **Plotly 시각화** | `utils/visualizer.py` | 동일 (프론트엔드 유지) |
| **Folium 지도** | `utils/geo.py` | 동일 (프론트엔드 유지) |
| **렌더링** | 클라이언트 사이드 | 동일 (클라이언트 사이드) |

**프론트엔드 유지 이유:**
- Plotly, Folium은 클라이언트 사이드 렌더링이 효율적
- 사용자 상호작용(줌, 필터, 호버) 즉각 반응
- 서버 부하 감소

---

## 4. 디렉토리 구조 비교

### 4.1 AS-IS (v1.2.3)

```
hab_public_data/
├── app.py                      # Streamlit 메인 앱
├── utils/
│   ├── chatbot.py             # LangGraph 챗봇 (559줄)
│   ├── graph.py               # StateGraph 정의 (147줄)
│   ├── tools.py               # 22개 분석 도구 (1,180줄)
│   ├── predictor.py           # ECLO 예측 (268줄)
│   ├── prompts.py             # 시스템 프롬프트 (271줄)
│   ├── loader.py              # 데이터 로더 (188줄)
│   ├── visualizer.py          # Plotly 시각화 (517줄)
│   ├── geo.py                 # Folium 지도 (232줄)
│   └── narration.py           # 나레이션 (192줄)
├── model/
│   ├── accident_lgbm_model.pkl
│   ├── label_encoders.pkl
│   └── feature_config.json
├── requirements.txt
└── pyproject.toml
```

### 4.2 TO-BE (v1.3)

```
hab_public_data/
├── app.py                      # Streamlit 프론트엔드 (간소화)
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
│   ├── services/              # 비즈니스 로직 (utils 이관)
│   │   ├── chat_service.py
│   │   ├── analysis_service.py
│   │   ├── prediction_service.py
│   │   └── dataset_service.py
│   ├── ml/
│   │   └── model_loader.py   # 모델 로딩 (싱글톤)
│   └── tasks/
│       └── prediction_tasks.py
├── utils/                      # 프론트엔드 전용
│   ├── visualizer.py          # Plotly (유지)
│   ├── geo.py                 # Folium (유지)
│   └── narration.py           # 나레이션 (유지)
├── model/                      # 백엔드로 이동
├── docker-compose.yml         # 🆕 Docker 구성
├── requirements.txt           # 프론트엔드 의존성
├── requirements-backend.txt   # 🆕 백엔드 의존성
└── env/                       # 🆕 프론트엔드 설정 파일
    └── .env                   # API 키 등 사용자 설정 (선택사항)
```

### 4.3 환경 변수 설정

#### 4.3.1 프론트엔드 설정 (신규)

**위치:** `env/.env` 또는 `env/config.env`

```bash
# Anthropic API 키 (선택사항)
claude_api_key=sk-ant-api03-xxxxx

# 설정된 경우: 자동으로 화면에 등록
# 설정되지 않은 경우: 사용자가 UI에서 직접 입력
```

**동작 방식:**
1. 애플리케이션 시작 시 `env/` 디렉토리의 설정 파일 체크
2. `claude_api_key` 값이 존재하면 자동으로 Streamlit 사이드바에 등록
3. 값이 없으면 사용자가 UI에서 직접 입력하는 입력 필드 표시
4. 사용자 편의성 향상 (매번 입력 불필요)

#### 4.3.2 백엔드 환경 변수

**위치:** 프로젝트 루트 `.env`

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

**참고:**
- Anthropic API 키는 백엔드 환경 변수에 저장하지 않음
- 클라이언트가 요청 시 헤더로 전달하는 방식 사용
- `env/` 디렉토리는 프론트엔드 사용자 편의성을 위한 옵션

---

## 4.4 Docker Compose 구성

### 4.4.1 전체 서비스 구성

v1.3에서는 Docker Compose를 사용하여 전체 스택을 컨테이너화합니다.

**docker-compose.yml 구조:**

```yaml
services:
  # 데이터베이스
  postgres:
    image: postgres:15-alpine
    ports: ["5432:5432"]
    volumes: [postgres_data:/var/lib/postgresql/data]
    healthcheck: pg_isready

  # 캐시 + 메시지 브로커
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    volumes: [redis_data:/data]
    healthcheck: redis-cli ping

  # FastAPI 백엔드
  backend:
    build: ./backend/Dockerfile
    ports: ["8000:8000"]
    depends_on: [postgres, redis]
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/1

  # Celery Worker (비동기 작업)
  celery-worker:
    build: ./backend/Dockerfile
    command: celery -A backend.tasks.celery_app worker
    depends_on: [postgres, redis]

  # Celery Beat (스케줄러)
  celery-beat:
    build: ./backend/Dockerfile
    command: celery -A backend.tasks.celery_app beat
    depends_on: [postgres, redis]

  # Flower (Celery 모니터링)
  flower:
    build: ./backend/Dockerfile
    ports: ["5555:5555"]
    command: celery -A backend.tasks.celery_app flower

  # Streamlit 프론트엔드
  streamlit:
    build: ./Dockerfile.streamlit
    ports: ["8501:8501"]
    depends_on: [backend]
    environment:
      - BACKEND_URL=http://backend:8000
```

### 4.4.2 서비스 상세 정보

| 서비스 | 컨테이너명 | 포트 | 이미지/빌드 | 역할 |
|:-------|:----------|:-----|:-----------|:-----|
| **postgres** | hab_postgres | 5432 | postgres:15-alpine | PostgreSQL 데이터베이스 |
| **redis** | hab_redis | 6379 | redis:7-alpine | 캐시 + 메시지 브로커 |
| **backend** | hab_backend | 8000 | Custom (backend/Dockerfile) | FastAPI REST API |
| **celery-worker** | hab_celery_worker | - | Custom (backend/Dockerfile) | 비동기 작업 처리 |
| **celery-beat** | hab_celery_beat | - | Custom (backend/Dockerfile) | 스케줄 작업 관리 |
| **flower** | hab_flower | 5555 | Custom (backend/Dockerfile) | Celery 모니터링 UI |
| **streamlit** | hab_streamlit | 8501 | Custom (Dockerfile.streamlit) | Streamlit 프론트엔드 |

### 4.4.3 네트워크 구성

```
┌──────────────────────────────────────────────────────────┐
│                  hab_network (bridge)                     │
│                                                            │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐             │
│  │streamlit │──►│ backend  │──►│postgres  │             │
│  │  :8501   │   │  :8000   │   │  :5432   │             │
│  └──────────┘   └──────────┘   └──────────┘             │
│                       │                                    │
│                       ▼                                    │
│                  ┌──────────┐                             │
│                  │  redis   │                             │
│                  │  :6379   │                             │
│                  └──────────┘                             │
│                       ▲                                    │
│        ┌──────────────┼──────────────┐                   │
│        │              │              │                    │
│   ┌────▼─────┐  ┌────▼─────┐  ┌────▼─────┐             │
│   │  celery  │  │  celery  │  │  flower  │             │
│   │  worker  │  │   beat   │  │  :5555   │             │
│   └──────────┘  └──────────┘  └──────────┘             │
│                                                            │
└──────────────────────────────────────────────────────────┘

호스트 머신:
- localhost:8501 → streamlit
- localhost:8000 → backend (FastAPI)
- localhost:5555 → flower (모니터링)
- localhost:5432 → postgres
- localhost:6379 → redis
```

### 4.4.4 볼륨 구성 (데이터 영속성)

```yaml
volumes:
  postgres_data:
    driver: local
    # 경로: /var/lib/docker/volumes/hab_public_data_postgres_data

  redis_data:
    driver: local
    # 경로: /var/lib/docker/volumes/hab_public_data_redis_data
```

**데이터 보존:**
- `docker compose down`: 볼륨 유지 ✅
- `docker compose down -v`: 볼륨 삭제 ❌

### 4.4.5 빠른 시작 가이드

```bash
# 1. 환경 변수 설정
cp .env.example .env
nano .env  # POSTGRES_PASSWORD 등 수정

# 2. 전체 스택 실행
docker compose up -d

# 3. 로그 확인 (실시간)
docker compose logs -f

# 4. 서비스 접속 확인
curl http://localhost:8000/health      # Backend
curl http://localhost:8501/_stcore/health  # Streamlit

# 5. 브라우저 접속
# - Streamlit UI: http://localhost:8501
# - FastAPI Docs: http://localhost:8000/docs
# - Flower UI: http://localhost:5555
```

### 4.4.6 개발 워크플로우

**코드 변경 시 (Hot Reload):**

```bash
# .env 파일 설정
BACKEND_RELOAD=true

# 백엔드 재시작
docker compose restart backend

# 볼륨 마운트로 즉시 반영
# backend/ 디렉토리 수정 → 자동 재시작
```

**데이터베이스 마이그레이션:**

```bash
# 마이그레이션 생성
docker compose exec backend alembic revision --autogenerate -m "Add users table"

# 마이그레이션 적용
docker compose exec backend alembic upgrade head

# 마이그레이션 롤백
docker compose exec backend alembic downgrade -1
```

**Redis 캐시 관리:**

```bash
# 캐시 확인
docker compose exec redis redis-cli KEYS "*"

# 특정 키 조회
docker compose exec redis redis-cli GET "chat:dataset_123:hash_456"

# 캐시 전체 삭제
docker compose exec redis redis-cli FLUSHALL
```

**Celery 작업 모니터링:**

```bash
# Worker 로그 확인
docker compose logs -f celery-worker

# 활성 작업 조회
docker compose exec celery-worker celery -A backend.tasks.celery_app inspect active

# 등록된 작업 확인
docker compose exec celery-worker celery -A backend.tasks.celery_app inspect registered

# Flower UI로 시각적 모니터링
# http://localhost:5555
```

### 4.4.7 리소스 관리

**메모리 제한 설정 (프로덕션):**

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

**리소스 사용량 모니터링:**

```bash
# 실시간 리소스 확인
docker stats

# 특정 서비스만
docker stats hab_backend hab_postgres hab_redis
```

### 4.4.8 트러블슈팅

**포트 충돌:**
```bash
# .env에서 포트 변경
BACKEND_PORT=8001
STREAMLIT_PORT=8502
```

**볼륨 권한 문제:**
```bash
# 볼륨 삭제 후 재생성
docker compose down -v
docker compose up -d
```

**이미지 빌드 실패:**
```bash
# 캐시 없이 재빌드
docker compose build --no-cache
```

**상세 가이드:** `DOCKER_README.md` 참고

---

## 5. 기술 스택 비교

### 5.1 AS-IS (v1.2.3)

| 분류 | 기술 |
|------|------|
| **웹 프레임워크** | Streamlit 1.28+ |
| **데이터 처리** | pandas 2.0+, numpy 1.24+ |
| **시각화** | Plotly 5.17+, Folium 0.14+ |
| **AI** | LangChain 0.3+, LangGraph 0.2+, Anthropic |
| **ML** | LightGBM 4.1+, scikit-learn 1.3+ |
| **패키지 관리** | uv, pip |

### 5.2 TO-BE (v1.3)

#### 프론트엔드 (기존 유지)
| 분류 | 기술 |
|------|------|
| **웹 프레임워크** | Streamlit 1.28+ |
| **시각화** | Plotly 5.17+, Folium 0.14+ |
| **HTTP 클라이언트** | httpx 0.25+ ⬅ 🆕 |

#### 백엔드 (신규 추가)
| 분류 | 기술 |
|------|------|
| **웹 프레임워크** | FastAPI 0.104+ ⬅ 🆕 |
| **ASGI 서버** | Uvicorn 0.24+ ⬅ 🆕 |
| **데이터베이스** | PostgreSQL 15+ ⬅ 🆕 |
| **ORM** | SQLAlchemy 2.0+ ⬅ 🆕 |
| **마이그레이션** | Alembic 1.12+ ⬅ 🆕 |
| **캐시** | Redis 7.0+ ⬅ 🆕 |
| **태스크 큐** | Celery 5.3+ ⬅ 🆕 |
| **환경 변수** | python-dotenv 1.0+ ⬅ 🆕 |
| **AI/ML** | LangChain 0.3+, LangGraph 0.2+, Anthropic, LightGBM 4.1+ |

#### 인프라 (신규 추가)
| 분류 | 기술 |
|------|------|
| **컨테이너** | Docker 24+, Docker Compose 2.20+ ⬅ 🆕 |
| **웹 서버** | Nginx 1.25+ ⬅ 🆕 |
| **모니터링** | Prometheus, Grafana ⬅ 🆕 |

---

## 6. 성능 최적화

### 6.1 응답 캐싱

| 구분 | AS-IS (v1.2.3) | TO-BE (v1.3) |
|:-----|:---------------|:-------------|
| **캐싱 방식** | @cache_data (메모리) | Redis (분산 캐시) |
| **캐시 범위** | 단일 사용자 세션 | 전체 사용자 공유 |
| **TTL** | 없음 (영구) | 1시간 (설정 가능) |
| **캐시 키** | 함수 파라미터 해시 | dataset_id + query 해시 |

#### 6.1.1 Redis 캐싱 예시

```python
# 동일 데이터셋 + 동일 질문 → 캐시에서 반환
cache_key = f"chat:{dataset_id}:{hash(message)}"

cached_response = redis.get(cache_key)
if cached_response:
    return {
        "response": cached_response,
        "cache_hit": True
    }

# 캐시 미스 → LLM 호출 (클라이언트 API 키 사용)
response = await chat_service.get_response(api_key, ...)
redis.setex(cache_key, 3600, response)  # TTL: 1시간
```

### 6.2 모델 서빙 최적화

| 구분 | AS-IS (v1.2.3) | TO-BE (v1.3) |
|:-----|:---------------|:-------------|
| **모델 로딩** | 사용자마다 로드 (1.4MB × N명) | 서버에서 한 번만 로드 (1.4MB) |
| **메모리 사용** | 높음 (N × 1.4MB) | 낮음 (1.4MB) |
| **예측 속도** | 느림 (모델 로딩 시간) | 빠름 (이미 로드됨) |

---

## 7. 데이터베이스 스키마

### 7.1 주요 테이블 설계

```sql
-- 데이터셋
CREATE TABLE datasets (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    file_path VARCHAR(500) NOT NULL,
    rows INTEGER,
    columns INTEGER,
    size_bytes BIGINT,
    uploaded_at TIMESTAMP DEFAULT NOW()
);

-- 대화 이력
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    dataset_id INTEGER REFERENCES datasets(id),
    title VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER REFERENCES conversations(id),
    role VARCHAR(20) NOT NULL,  -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    tool_calls JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ECLO 예측 결과
CREATE TABLE predictions (
    id SERIAL PRIMARY KEY,
    model_version VARCHAR(50),
    input_features JSONB NOT NULL,
    eclo_value DECIMAL(10, 4),
    interpretation VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);
```

**참고:** 사용자 인증 기능이 없으므로 `users` 테이블은 제외했습니다.

---

## 8. 단계별 구현 로드맵

### Phase 1: MVP - ECLO 예측 API (2주)

**목표:** 백엔드 아키텍처 검증

**작업 내용:**
1. FastAPI 기본 서버 구축
2. ECLO 예측 API 구현 (`POST /api/predict/eclo`)
3. Streamlit에서 API 호출 전환
4. Docker Compose로 로컬 환경 구축

**완료 기준:**
- [ ] FastAPI 서버 실행 (http://localhost:8000)
- [ ] Swagger 문서 생성 (http://localhost:8000/docs)
- [ ] ECLO 예측 API 동작
- [ ] Streamlit에서 백엔드 호출 성공

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
3. 데이터셋 공유 기능 (`POST /api/datasets/{id}/share`)

**완료 기준:**
- [ ] CSV 업로드 API 동작
- [ ] 데이터셋 목록 조회 동작
- [ ] 데이터셋 공유 링크 생성

---

### Phase 4: 고도화 (진행형)

**작업 내용:**
1. Celery 큐 (배치 예측 비동기 처리)
2. Prometheus + Grafana 모니터링
3. 모델 버전 관리 (A/B 테스트)

---

## 9. 예상 효과

### 9.1 정량적 효과

| 항목 | AS-IS (v1.2.3) | TO-BE (v1.3) | 개선율 |
|:-----|:---------------|:-------------|:-------|
| **모델 로딩 시간** | 사용자당 2초 | 서버 시작 시 1회 (2초) | 99% ↓ |
| **API 응답 시간** | 3-5초 | 0.5-2초 (캐시 적중 시 <100ms) | 60-80% ↓ |
| **동시 접속자** | ~10명 | ~100명 (수평 확장 가능) | 10배 ↑ |
| **데이터 영속성** | 0% (세션 종료 시 소실) | 100% (PostgreSQL) | 100% ↑ |

### 9.2 정성적 효과

- **성능 향상**: Redis 캐싱, 모델 서빙 최적화
- **데이터 안정성**: PostgreSQL 영구 저장, 백업
- **개발 생산성**: 프론트/백 분리로 독립 개발 가능
- **확장성**: 새로운 기능 추가 용이 (API 추가만)
- **사용자 경험**: 대화 이력 저장, 빠른 응답

---

## 10. 위험 요소 및 대응

| 위험 요소 | 발생 확률 | 영향도 | 대응 방안 |
|:---------|:---------|:------|:---------|
| **개발 기간 초과** | 중 | 중 | Phase 1부터 점진적 배포 |
| **복잡도 증가** | 높음 | 중 | Docker Compose로 환경 통일 |
| **운영 비용 증가** | 중 | 중 | 무료 Tier 활용 (Railway, Render) |
| **기존 기능 버그** | 낮음 | 높음 | 철저한 테스트, 롤백 계획 |

---

## 11. 결론

v1.3에서는 **백엔드 서버(WAS) 추가**를 통해 Streamlit 모노리식 애플리케이션을 **프론트엔드/백엔드 분리 아키텍처**로 전환한다.

### 핵심 가치
1. **성능**: Redis 캐싱, 모델 서빙 최적화
2. **영속성**: PostgreSQL 데이터 영구 저장
3. **확장성**: 수평 확장 가능한 아키텍처
4. **유연성**: API 키 개별 관리 유지 (사용자 친화적)

### 추천 구현 순서
1. **Phase 1 (2주)**: ECLO 예측 API만 먼저 구현하여 아키텍처 검증
2. **Phase 2 (3주)**: AI 챗봇 API화 (핵심 기능)
3. **Phase 3 (2주)**: 데이터 관리 API
4. **Phase 4 (진행형)**: 고도화

**총 예상 개발 기간: 6-8주**

---

## 12. 참고 자료

- FastAPI 공식 문서: https://fastapi.tiangolo.com/
- LangChain 문서: https://python.langchain.com/
- SQLAlchemy 문서: https://docs.sqlalchemy.org/
- Docker Compose 문서: https://docs.docker.com/compose/
- PostgreSQL 문서: https://www.postgresql.org/docs/
- Redis 문서: https://redis.io/docs/
