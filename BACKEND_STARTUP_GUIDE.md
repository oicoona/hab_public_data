# 백엔드 서버 & Streamlit 프론트엔드 실행 가이드

이 가이드는 Phase 1-6까지 작업 완료 후, 백엔드 서버(FastAPI)와 Streamlit 프론트엔드를 Docker Compose로 실행하여 전체 시스템이 정상 동작하는지 확인하는 방법을 안내합니다.

---

## 📋 목차

1. [사전 요구사항](#1-사전-요구사항)
2. [환경 변수 설정](#2-환경-변수-설정)
3. [Docker Compose 실행](#3-docker-compose-실행)
4. [데이터베이스 마이그레이션](#4-데이터베이스-마이그레이션)
5. [서비스 헬스 체크](#5-서비스-헬스-체크)
6. [Streamlit에서 백엔드 연결 확인](#6-streamlit에서-백엔드-연결-확인)
7. [API 테스트](#7-api-테스트)
8. [문제 해결](#8-문제-해결)

---

## 1. 사전 요구사항

### 1.1 필수 소프트웨어 설치

다음 소프트웨어가 설치되어 있어야 합니다:

- **Docker**: 24.0 이상
- **Docker Compose**: 2.20 이상
- **curl** (헬스 체크용, 대부분의 Linux/Mac에 기본 포함)

### 1.2 설치 확인

터미널에서 다음 명령어로 버전을 확인하세요:

```bash
docker --version
docker compose version
curl --version
```

**예상 출력:**
```
Docker version 24.0.0
Docker Compose version v2.20.0
curl 7.68.0
```

### 1.3 포트 확인

다음 포트들이 사용 가능한지 확인하세요:

| 포트 | 서비스 | 설명 |
|------|--------|------|
| 5432 | PostgreSQL | 데이터베이스 |
| 6379 | Redis | 캐시 및 메시지 브로커 |
| 8000 | FastAPI Backend | REST API 서버 |
| 8501 | Streamlit | 프론트엔드 UI |
| 5555 | Flower | Celery 모니터링 |

포트가 이미 사용 중이라면, 해당 프로세스를 종료하거나 `docker-compose.yml`에서 포트를 변경해야 합니다.

**포트 사용 확인 명령어:**
```bash
# Linux/Mac
lsof -i :8000  # 또는 netstat -an | grep 8000

# Windows (PowerShell)
netstat -ano | findstr :8000
```

### 1.4 필수 파일 확인

프로젝트 루트 디렉토리에서 다음 파일들이 존재하는지 확인하세요:

```bash
# 프로젝트 루트에서 실행
ls -la docker-compose.yml
ls -la backend/Dockerfile
ls -la Dockerfile.streamlit
ls -la alembic.ini
ls -la alembic/versions/20241210_initial_schema.py
ls -la model/accident_lgbm_model.pkl
```

모든 파일이 존재해야 정상적으로 실행할 수 있습니다.

---

## 2. 환경 변수 설정

### 2.1 프론트엔드 환경 변수 (`.env`)

프로젝트 루트 디렉토리에 `.env` 파일을 생성합니다:

```bash
# 프로젝트 루트에서 실행
cat > .env << 'EOF'
# Streamlit Frontend Environment Variables
BACKEND_URL=http://localhost:8000
CLAUDE_API_KEY=sk-ant-api03-xxxxx  # 선택사항: Anthropic API 키 (없으면 나중에 UI에서 입력)
EOF
```

**주요 변수:**
- `BACKEND_URL`: Streamlit이 백엔드 API를 호출할 때 사용하는 URL
  - Docker 내부에서는 `http://backend:8000` 사용
  - 로컬 테스트 시 `http://localhost:8000` 사용
- `CLAUDE_API_KEY`: Anthropic Claude API 키 (선택사항, UI에서도 입력 가능)

### 2.2 백엔드 환경 변수 (`backend/.env`)

`backend/` 디렉토리에 `.env` 파일을 생성합니다:

```bash
# 프로젝트 루트에서 실행
cat > backend/.env << 'EOF'
# Database
DATABASE_URL=postgresql://postgres:password@postgres:5432/hab_public_data
DATABASE_POOL_SIZE=10

# Redis
REDIS_URL=redis://redis:6379/0
CACHE_TTL=3600

# Celery
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# Backend Server
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
BACKEND_RELOAD=false

# CORS (자동으로 설정되지만 명시적으로 지정 가능)
CORS_ORIGINS=http://localhost:8501,http://streamlit:8501
EOF
```

**주요 변수 설명:**
- `DATABASE_URL`: PostgreSQL 연결 문자열
  - 형식: `postgresql://사용자명:비밀번호@호스트:포트/데이터베이스명`
  - Docker Compose에서는 서비스명(`postgres`)을 호스트로 사용
- `REDIS_URL`: Redis 연결 URL (캐시용)
- `CELERY_BROKER_URL`: Celery 작업 큐 브로커 URL
- `CELERY_RESULT_BACKEND`: Celery 작업 결과 저장소 URL

**⚠️ 중요:**
- `backend/.env`의 `DATABASE_URL`에서 호스트는 `postgres` (Docker 서비스명)를 사용합니다
- 로컬에서 직접 실행하는 경우에만 `localhost`를 사용합니다

### 2.3 환경 변수 파일 권한 확인 (선택사항)

보안을 위해 `.env` 파일의 권한을 제한하는 것을 권장합니다:

```bash
chmod 600 .env
chmod 600 backend/.env
```

---

## 3. Docker Compose 실행

### 3.1 전체 스택 실행

프로젝트 루트 디렉토리에서 다음 명령어를 실행합니다:

```bash
docker compose up -d
```

`-d` 옵션은 백그라운드(데몬) 모드로 실행합니다.

**예상 출력:**
```
[+] Running 7/7
 ✔ Network hab_public_data_default    Created
 ✔ Volume "hab_public_data_postgres_data"  Created
 ✔ Volume "hab_public_data_backend_uploads" Created
 ✔ Container hab-postgres            Started
 ✔ Container hab-redis              Started
 ✔ Container hab-backend            Started
 ✔ Container hab-celery-worker      Started
 ✔ Container hab-flower             Started
 ✔ Container hab-streamlit          Started
```

### 3.2 서비스 상태 확인

다음 명령어로 모든 서비스가 정상적으로 실행 중인지 확인합니다:

```bash
docker compose ps
```

**예상 출력:**
```
NAME                  COMMAND                  SERVICE           STATUS          PORTS
hab-backend           "alembic upgrade head…"  backend           Up (healthy)    0.0.0.0:8000->8000/tcp
hab-celery-worker     "celery -A backend.ta…"  celery-worker     Up               
hab-flower            "celery -A backend.ta…"  flower            Up               0.0.0.0:5555->5555/tcp
hab-postgres          "docker-entrypoint.s…"   postgres          Up (healthy)    0.0.0.0:5432->5432/tcp
hab-redis             "docker-entrypoint.s…"   redis             Up (healthy)    0.0.0.0:6379->6379/tcp
hab-streamlit         "streamlit run app.py"   streamlit         Up               0.0.0.0:8501->8501/tcp
```

**상태 설명:**
- `Up (healthy)`: 서비스가 정상 실행 중이며 헬스 체크 통과
- `Up`: 서비스가 실행 중이지만 헬스 체크 아직 진행 중
- `Restarting`: 서비스가 반복적으로 재시작 중 (문제 발생 가능)

### 3.3 로그 확인

서비스 실행 로그를 확인하려면:

```bash
# 모든 서비스의 로그 확인
docker compose logs -f

# 특정 서비스의 로그만 확인
docker compose logs -f backend
docker compose logs -f streamlit

# 최근 100줄만 확인
docker compose logs --tail=100 backend
```

**정상적인 백엔드 로그 예시:**
```
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**정상적인 Streamlit 로그 예시:**
```
You can now view your Streamlit app in your browser.
Local URL: http://0.0.0.0:8501
Network URL: http://172.18.0.7:8501
```

### 3.4 서비스 시작 대기

모든 서비스가 정상적으로 시작되기까지 약 30-60초 정도 소요될 수 있습니다. 다음 명령어로 백엔드가 완전히 시작될 때까지 기다릴 수 있습니다:

```bash
# 백엔드 헬스 체크 반복 확인 (최대 60초)
timeout 60 bash -c 'until curl -f http://localhost:8000/health; do sleep 2; done'
```

또는 간단하게:

```bash
sleep 30
curl http://localhost:8000/health
```

---

## 4. 데이터베이스 마이그레이션

### 4.1 마이그레이션 실행

데이터베이스 스키마를 생성하기 위해 Alembic 마이그레이션을 실행합니다:

```bash
docker compose exec backend alembic upgrade head
```

**예상 출력:**
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 20241210_initial_schema, Initial schema
```

### 4.2 마이그레이션 상태 확인

현재 마이그레이션 상태를 확인하려면:

```bash
docker compose exec backend alembic current
```

**예상 출력:**
```
20241210_initial_schema (head)
```

### 4.3 마이그레이션 이력 확인

모든 마이그레이션 파일 목록을 확인하려면:

```bash
docker compose exec backend alembic history
```

**⚠️ 참고:**
- `backend/Dockerfile`의 `CMD`에 `alembic upgrade head &&`가 포함되어 있어, 백엔드 컨테이너 시작 시 자동으로 마이그레이션이 실행됩니다.
- 하지만 처음 실행 시에는 수동으로 실행하는 것을 권장합니다.

### 4.4 데이터베이스 테이블 확인

마이그레이션이 성공적으로 적용되었는지 확인하려면:

```bash
docker compose exec postgres psql -U postgres -d hab_public_data -c "\dt"
```

**예상 출력:**
```
              List of relations
 Schema |      Name       | Type  |  Owner   
--------+-----------------+-------+----------
 public | alembic_version | table | postgres
 public | conversations   | table | postgres
 public | datasets        | table | postgres
 public | messages        | table | postgres
 public | predictions     | table | postgres
 public | share_tokens    | table | postgres
```

다음 테이블들이 생성되어야 합니다:
- `datasets`: 데이터셋 메타데이터
- `conversations`: 대화 이력
- `messages`: 메시지 내용
- `predictions`: ECLO 예측 결과
- `share_tokens`: 공유 토큰

---

## 5. 서비스 헬스 체크

### 5.1 백엔드 헬스 체크

```bash
curl http://localhost:8000/health
```

**예상 응답:**
```json
{
  "status": "healthy",
  "timestamp": "2024-12-10T12:34:56.789012"
}
```

### 5.2 Streamlit 헬스 체크

```bash
curl http://localhost:8501/_stcore/health
```

**예상 응답:**
```json
{"status":"healthy"}
```

### 5.3 PostgreSQL 연결 확인

```bash
docker compose exec postgres pg_isready -U postgres
```

**예상 출력:**
```
postgres:5432 - accepting connections
```

### 5.4 Redis 연결 확인

```bash
docker compose exec redis redis-cli ping
```

**예상 출력:**
```
PONG
```

### 5.5 전체 헬스 체크 스크립트

다음 스크립트로 모든 서비스의 헬스 체크를 한 번에 수행할 수 있습니다:

```bash
#!/bin/bash
echo "=== 서비스 헬스 체크 ==="
echo ""

echo "1. Backend Health Check..."
curl -s http://localhost:8000/health | jq '.' || echo "❌ Backend 연결 실패"
echo ""

echo "2. Streamlit Health Check..."
curl -s http://localhost:8501/_stcore/health | jq '.' || echo "❌ Streamlit 연결 실패"
echo ""

echo "3. PostgreSQL Check..."
docker compose exec -T postgres pg_isready -U postgres || echo "❌ PostgreSQL 연결 실패"
echo ""

echo "4. Redis Check..."
docker compose exec -T redis redis-cli ping || echo "❌ Redis 연결 실패"
echo ""

echo "=== 헬스 체크 완료 ==="
```

`jq`가 설치되어 있지 않다면 `| jq '.'` 부분을 제거하세요.

---

## 6. Streamlit에서 백엔드 연결 확인

### 6.1 Streamlit UI 접속

브라우저에서 다음 URL을 열어주세요:

```
http://localhost:8501
```

### 6.2 백엔드 연결 상태 확인

1. Streamlit UI의 **사이드바**를 확인합니다.
2. "🗄️ Backend 데이터셋" 섹션을 찾습니다.
3. **"✅ Backend 연결됨"** 메시지가 표시되어야 합니다.

**연결되지 않은 경우:**
- "❌ Backend 연결 실패" 또는 에러 메시지가 표시됩니다.
- 브라우저 콘솔(F12)에서 네트워크 오류를 확인하세요.
- `docker compose logs streamlit`으로 Streamlit 로그를 확인하세요.

### 6.3 ECLO 예측 테스트 (단일 예측)

Streamlit UI에서 ECLO 예측 기능을 테스트합니다:

1. 메인 화면에서 **"ECLO 예측"** 또는 **"예측"** 탭을 선택합니다.
2. 다음 정보를 입력합니다:
   - 날씨: 맑음
   - 노면 상태: 건조
   - 도로 형태: 교차로
   - 사고 유형: 차대차
   - 시간대: 낮
   - 구: 중구
   - 요일: 월요일
   - 사고 시각: 14
   - 사고 연도: 2024
   - 사고 월: 12
   - 사고 일: 10
3. **"예측"** 또는 **"예측하기"** 버튼을 클릭합니다.
4. 예측 결과가 1초 이내에 표시되어야 합니다:
   - ECLO 값 (예: 0.23)
   - 해석 (예: "일반")
   - 상세 설명

**성공 시:**
- 예측 결과가 즉시 표시됩니다.
- 에러 메시지가 없습니다.

**실패 시:**
- "서버에 연결할 수 없습니다" 에러가 표시될 수 있습니다.
- 백엔드 로그를 확인하세요: `docker compose logs backend`

---

## 7. API 테스트

### 7.1 FastAPI Docs 접속

브라우저에서 다음 URL을 열어주세요:

```
http://localhost:8000/docs
```

Swagger UI가 표시되며, 모든 API 엔드포인트를 테스트할 수 있습니다.

### 7.2 단일 ECLO 예측 API 테스트

#### 방법 1: FastAPI Docs에서 테스트

1. `POST /api/predict/eclo` 엔드포인트를 클릭합니다.
2. **"Try it out"** 버튼을 클릭합니다.
3. Request body에 다음 JSON을 입력합니다:

```json
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
  "accident_day": 10
}
```

4. **"Execute"** 버튼을 클릭합니다.
5. Response에서 예측 결과를 확인합니다.

**예상 응답:**
```json
{
  "eclo": 0.23,
  "interpretation": "일반",
  "detail": "일반적인 사고 수준입니다. 경상 가능성이 있으며, 치료가 필요할 수 있습니다.",
  "prediction_id": null,
  "model_version": "v1.0"
}
```

#### 방법 2: curl로 테스트

```bash
curl -X POST http://localhost:8000/api/predict/eclo \
  -H "Content-Type: application/json" \
  -d '{
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
    "accident_day": 10
  }'
```

### 7.3 배치 예측 API 테스트 (선택사항)

배치 예측 기능을 테스트하려면:

1. **배치 작업 제출:**
```bash
curl -X POST http://localhost:8000/api/predict/eclo/batch \
  -H "Content-Type: application/json" \
  -d '{
    "accidents": [
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
        "accident_day": 10
      }
    ]
  }'
```

2. **배치 작업 상태 확인:**
```bash
# 응답에서 받은 batch_id를 사용
curl http://localhost:8000/api/predict/batch/{batch_id}/results
```

### 7.4 Flower 모니터링 대시보드

Celery 작업을 모니터링하려면:

1. 브라우저에서 다음 URL을 엽니다:
   ```
   http://localhost:5555
   ```
2. 대시보드에서 다음을 확인할 수 있습니다:
   - 활성 작업 (Active Tasks)
   - 작업 이력 (Tasks)
   - Worker 상태 (Workers)
   - 통계 정보 (Monitor)

---

## 8. 문제 해결

### 8.1 포트 충돌

**증상:**
```
Error: bind: address already in use
```

**해결 방법:**

1. 포트를 사용 중인 프로세스 확인:
```bash
# Linux/Mac
lsof -i :8000

# Windows (PowerShell)
netstat -ano | findstr :8000
```

2. 프로세스 종료 또는 `docker-compose.yml`에서 포트 변경:
```yaml
services:
  backend:
    ports:
      - "8001:8000"  # 8000 대신 8001 사용
```

### 8.2 데이터베이스 연결 실패

**증상:**
```
could not connect to server: Connection refused
OperationalError: (psycopg2.OperationalError)
```

**해결 방법:**

1. PostgreSQL 컨테이너 상태 확인:
```bash
docker compose ps postgres
```

2. PostgreSQL 로그 확인:
```bash
docker compose logs postgres
```

3. `backend/.env`의 `DATABASE_URL` 확인:
   - 호스트가 `postgres` (Docker 서비스명)인지 확인
   - 비밀번호가 `docker-compose.yml`과 일치하는지 확인

4. PostgreSQL 컨테이너 재시작:
```bash
docker compose restart postgres
```

### 8.3 Redis 연결 실패

**증상:**
```
redis.exceptions.ConnectionError
```

**해결 방법:**

1. Redis 컨테이너 상태 확인:
```bash
docker compose ps redis
```

2. Redis 연결 테스트:
```bash
docker compose exec redis redis-cli ping
```

3. Redis 컨테이너 재시작:
```bash
docker compose restart redis
```

### 8.4 마이그레이션 오류

**증상:**
```
alembic.util.exc.CommandError: Target database is not up to date
```

**해결 방법:**

1. 현재 마이그레이션 상태 확인:
```bash
docker compose exec backend alembic current
```

2. 마이그레이션 히스토리 확인:
```bash
docker compose exec backend alembic history
```

3. 마이그레이션 강제 실행:
```bash
docker compose exec backend alembic upgrade head
```

4. 데이터베이스 초기화가 필요한 경우 (⚠️ 데이터 소실):
```bash
docker compose down -v
docker compose up -d postgres
docker compose exec backend alembic upgrade head
```

### 8.5 환경 변수 누락

**증상:**
```
KeyError: 'DATABASE_URL'
pydantic_settings.exceptions.SettingsError
```

**해결 방법:**

1. `.env` 파일 존재 확인:
```bash
ls -la .env
ls -la backend/.env
```

2. 환경 변수 형식 확인:
   - 공백이나 따옴표 없는지 확인
   - 주석(`#`)이 올바른지 확인

3. Docker Compose 재시작:
```bash
docker compose down
docker compose up -d
```

### 8.6 백엔드가 시작되지 않음

**증상:**
```
Container hab-backend is restarting
```

**해결 방법:**

1. 백엔드 로그 확인:
```bash
docker compose logs backend
```

2. 일반적인 원인:
   - 환경 변수 오류
   - 데이터베이스 연결 실패
   - 모델 파일 누락 (`model/accident_lgbm_model.pkl`)

3. 모델 파일 확인:
```bash
ls -la model/accident_lgbm_model.pkl
```

4. 백엔드 컨테이너 내부 접속하여 디버깅:
```bash
docker compose exec backend bash
# 컨테이너 내부에서
python -c "from backend.config import settings; print(settings.DATABASE_URL)"
```

### 8.7 Streamlit이 백엔드에 연결되지 않음

**증상:**
- Streamlit UI에서 "Backend 연결 실패" 메시지
- ECLO 예측 버튼 클릭 시 에러

**해결 방법:**

1. `.env` 파일의 `BACKEND_URL` 확인:
```bash
cat .env | grep BACKEND_URL
```
   - 로컬 테스트: `BACKEND_URL=http://localhost:8000`
   - Docker 내부: `BACKEND_URL=http://backend:8000` (자동 설정됨)

2. Streamlit 로그 확인:
```bash
docker compose logs streamlit
```

3. 백엔드 헬스 체크 확인:
```bash
curl http://localhost:8000/health
```

4. Streamlit 컨테이너 재시작:
```bash
docker compose restart streamlit
```

### 8.8 전체 재시작

모든 문제를 해결하기 위해 전체 스택을 재시작하는 방법:

```bash
# 모든 서비스 중지 및 제거
docker compose down

# 볼륨은 유지하고 재시작
docker compose up -d

# 또는 볼륨까지 삭제하고 완전히 초기화 (⚠️ 데이터 소실)
docker compose down -v
docker compose up -d
```

---

## ✅ 체크리스트

다음 항목들을 모두 확인했으면 성공적으로 설정된 것입니다:

- [ ] Docker 및 Docker Compose 설치 확인 완료
- [ ] `.env` 및 `backend/.env` 파일 생성 완료
- [ ] `docker compose up -d` 실행 성공
- [ ] 모든 서비스가 `Up (healthy)` 상태
- [ ] `alembic upgrade head` 실행 성공
- [ ] 데이터베이스 테이블 생성 확인 완료
- [ ] `curl http://localhost:8000/health` 응답 정상
- [ ] `curl http://localhost:8501/_stcore/health` 응답 정상
- [ ] Streamlit UI에서 "Backend 연결됨" 확인
- [ ] Streamlit UI에서 ECLO 예측 기능 테스트 성공
- [ ] FastAPI Docs (`http://localhost:8000/docs`) 접속 가능
- [ ] API 테스트 성공

---

## 📚 추가 자료

- [DOCKER_README.md](./DOCKER_README.md): Docker Compose 상세 가이드
- [MVP_TESTING_GUIDE.md](./MVP_TESTING_GUIDE.md): MVP 기능 테스트 가이드
- [specs/005-app-v1.3-backend-sep/quickstart.md](./specs/005-app-v1.3-backend-sep/quickstart.md): 빠른 시작 가이드
- [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md): 구현 상태 문서

---

## 💡 다음 단계

백엔드와 프론트엔드가 정상적으로 실행되면:

1. **Phase 4 (User Story 2)**: AI 챗봇 기능 테스트
2. **Phase 5 (User Story 3)**: 데이터셋 업로드 및 관리 기능 테스트
3. **Phase 6 (User Story 4)**: 데이터 시각화 기능 확인

---

**작성일**: 2024-12-10  
**버전**: v1.3  
**문서 상태**: Phase 1-6 완료 후 실행 가이드

