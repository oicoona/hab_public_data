# Docker Compose 가이드 - HAB Public Data v1.3

FastAPI + Redis + Celery + PostgreSQL + Streamlit 전체 스택을 Docker Compose로 실행하는 가이드입니다.

---

## 📋 목차

1. [사전 요구사항](#사전-요구사항)
2. [빠른 시작](#빠른-시작)
3. [서비스 구성](#서비스-구성)
4. [환경 변수 설정](#환경-변수-설정)
5. [사용법](#사용법)
6. [트러블슈팅](#트러블슈팅)
7. [유용한 명령어](#유용한-명령어)

---

## 🔧 사전 요구사항

### 필수 설치
- **Docker**: 24.0 이상
- **Docker Compose**: 2.20 이상

### 설치 확인
```bash
docker --version
docker compose version
```

---

## 🚀 빠른 시작

### 1. 환경 변수 설정
```bash
# .env.example을 복사하여 .env 생성
cp .env.example .env

# .env 파일 편집 (비밀번호 등 수정)
nano .env
```

### 2. 전체 스택 실행
```bash
# 백그라운드에서 모든 서비스 실행
docker compose up -d

# 로그 확인 (실시간)
docker compose logs -f
```

### 3. 서비스 접속
- **Streamlit (프론트엔드)**: http://localhost:8501
- **FastAPI (백엔드)**: http://localhost:8000
- **FastAPI Docs**: http://localhost:8000/docs
- **Flower (Celery 모니터링)**: http://localhost:5555
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

### 4. 종료
```bash
# 모든 서비스 종료 (볼륨 유지)
docker compose down

# 볼륨까지 삭제 (데이터 완전 삭제)
docker compose down -v
```

---

## 🏗️ 서비스 구성

### 전체 아키텍처

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│  Streamlit   │ ──HTTP──► │   FastAPI    │ ──SQL──► │ PostgreSQL   │
│  :8501       │         │   :8000      │         │   :5432      │
└──────────────┘         └──────────────┘         └──────────────┘
                                │
                                │                  ┌──────────────┐
                                └────────Redis─────► │    Redis     │
                                          :6379     │   :6379      │
                                                    └──────────────┘
                                                           │
                                          ┌────────────────┴──────────┐
                                          │                           │
                                    ┌─────▼──────┐           ┌──────▼──────┐
                                    │   Celery   │           │   Flower    │
                                    │   Worker   │           │   :5555     │
                                    └────────────┘           └─────────────┘
```

### 서비스 목록

| 서비스 | 컨테이너명 | 포트 | 역할 |
|:-------|:----------|:-----|:-----|
| **postgres** | hab_postgres | 5432 | PostgreSQL 데이터베이스 |
| **redis** | hab_redis | 6379 | 캐시 + 메시지 브로커 |
| **backend** | hab_backend | 8000 | FastAPI REST API |
| **celery-worker** | hab_celery_worker | - | 비동기 작업 처리 |
| **celery-beat** | hab_celery_beat | - | 스케줄 작업 관리 |
| **flower** | hab_flower | 5555 | Celery 모니터링 UI |
| **streamlit** | hab_streamlit | 8501 | Streamlit 프론트엔드 |

---

## ⚙️ 환경 변수 설정

### .env 파일 구조

```bash
# PostgreSQL
POSTGRES_USER=hab_user
POSTGRES_PASSWORD=strong_password_here  # ⚠️ 반드시 변경!
POSTGRES_DB=hab_public_data
POSTGRES_PORT=5432

# Redis
REDIS_PORT=6379
CACHE_TTL=3600

# Backend
BACKEND_PORT=8000
BACKEND_RELOAD=false
ALLOWED_ORIGINS=http://localhost:8501

# Streamlit
STREAMLIT_PORT=8501
BACKEND_URL=http://backend:8000

# Flower
FLOWER_PORT=5555
```

### Anthropic API 키 설정

**방법 1: env 파일 사용 (추천)**
```bash
# env/.env 파일 생성
mkdir -p env
echo "claude_api_key=sk-ant-api03-xxxxx" > env/.env
```

**방법 2: UI에서 직접 입력**
- Streamlit 사이드바에서 입력

---

## 📖 사용법

### 개별 서비스 제어

```bash
# 특정 서비스만 시작
docker compose up -d postgres redis

# 특정 서비스만 재시작
docker compose restart backend

# 특정 서비스 로그 확인
docker compose logs -f backend

# 특정 서비스 중지
docker compose stop streamlit
```

### 데이터베이스 관리

```bash
# PostgreSQL 접속
docker compose exec postgres psql -U hab_user -d hab_public_data

# 데이터베이스 백업
docker compose exec postgres pg_dump -U hab_user hab_public_data > backup.sql

# 데이터베이스 복원
docker compose exec -T postgres psql -U hab_user hab_public_data < backup.sql
```

### Redis 관리

```bash
# Redis CLI 접속
docker compose exec redis redis-cli

# 캐시 확인
docker compose exec redis redis-cli KEYS "*"

# 캐시 전체 삭제
docker compose exec redis redis-cli FLUSHALL
```

### Celery 작업 확인

```bash
# Celery Worker 로그 확인
docker compose logs -f celery-worker

# Flower UI로 모니터링
# 브라우저: http://localhost:5555

# 활성 작업 확인
docker compose exec celery-worker celery -A backend.tasks.celery_app inspect active

# 등록된 작업 확인
docker compose exec celery-worker celery -A backend.tasks.celery_app inspect registered
```

---

## 🐛 트러블슈팅

### 1. 포트 충돌

**증상:**
```
Error: port is already allocated
```

**해결:**
```bash
# .env 파일에서 포트 번호 변경
BACKEND_PORT=8001
STREAMLIT_PORT=8502
```

### 2. 데이터베이스 연결 실패

**증상:**
```
could not connect to server: Connection refused
```

**해결:**
```bash
# PostgreSQL 헬스체크 확인
docker compose ps

# PostgreSQL 로그 확인
docker compose logs postgres

# 재시작
docker compose restart postgres
```

### 3. Redis 연결 실패

**증상:**
```
redis.exceptions.ConnectionError
```

**해결:**
```bash
# Redis 상태 확인
docker compose exec redis redis-cli ping

# 응답: PONG (정상)

# Redis 재시작
docker compose restart redis
```

### 4. 볼륨 권한 문제

**증상:**
```
Permission denied
```

**해결:**
```bash
# 볼륨 삭제 후 재생성
docker compose down -v
docker compose up -d
```

### 5. 이미지 빌드 실패

**증상:**
```
failed to solve with frontend dockerfile
```

**해결:**
```bash
# 캐시 없이 재빌드
docker compose build --no-cache

# 특정 서비스만 재빌드
docker compose build --no-cache backend
```

---

## 💡 유용한 명령어

### 시스템 정보

```bash
# 실행 중인 컨테이너 확인
docker compose ps

# 리소스 사용량 확인
docker stats

# 네트워크 확인
docker network ls
docker network inspect hab_public_data_hab_network

# 볼륨 확인
docker volume ls
docker volume inspect hab_public_data_postgres_data
```

### 로그 관리

```bash
# 전체 로그 확인
docker compose logs

# 최근 100줄만 보기
docker compose logs --tail=100

# 특정 시간 이후 로그
docker compose logs --since="2024-12-09T10:00:00"

# 여러 서비스 동시에
docker compose logs -f backend celery-worker
```

### 컨테이너 내부 접속

```bash
# Backend 컨테이너 접속
docker compose exec backend bash

# PostgreSQL 접속
docker compose exec postgres psql -U hab_user -d hab_public_data

# Redis 접속
docker compose exec redis redis-cli

# Python 셸 실행
docker compose exec backend python
```

### 정리

```bash
# 중지된 컨테이너 삭제
docker compose rm

# 미사용 이미지 삭제
docker image prune

# 미사용 볼륨 삭제
docker volume prune

# 시스템 전체 정리 (주의!)
docker system prune -a --volumes
```

---

## 🔄 개발 모드

### 코드 변경 시 자동 재시작

```bash
# .env 파일 수정
BACKEND_RELOAD=true

# 재시작
docker compose restart backend
```

### 볼륨 마운트 확인
```yaml
# docker-compose.yml에서 확인
volumes:
  - ./backend:/app/backend  # 로컬 변경 → 즉시 반영
```

---

## 📊 모니터링

### Flower (Celery 모니터링)
```bash
# 접속: http://localhost:5555
# - 활성 작업 확인
# - 작업 이력 조회
# - Worker 상태 확인
```

### FastAPI Docs (Swagger)
```bash
# 접속: http://localhost:8000/docs
# - API 테스트
# - 스키마 확인
```

### 헬스체크
```bash
# Backend
curl http://localhost:8000/health

# Redis
docker compose exec redis redis-cli ping

# PostgreSQL
docker compose exec postgres pg_isready -U hab_user
```

---

## 🎯 프로덕션 배포

### 보안 체크리스트

- [ ] `.env`에서 모든 기본 비밀번호 변경
- [ ] `BACKEND_RELOAD=false` 설정
- [ ] HTTPS 설정 (Nginx 리버스 프록시)
- [ ] 방화벽 설정 (필요한 포트만 개방)
- [ ] 정기적인 백업 설정
- [ ] 로그 로테이션 설정
- [ ] 리소스 제한 설정 (CPU, Memory)

### 리소스 제한 예시

```yaml
# docker-compose.yml에 추가
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

---

## 📚 참고 자료

- [Docker Compose 공식 문서](https://docs.docker.com/compose/)
- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [Celery 공식 문서](https://docs.celeryproject.org/)
- [Redis 공식 문서](https://redis.io/docs/)
- [PostgreSQL 공식 문서](https://www.postgresql.org/docs/)

---

## ❓ FAQ

**Q: 데이터가 컨테이너 재시작 시 사라지나요?**
A: 아니요. PostgreSQL과 Redis 데이터는 Docker 볼륨에 영구 저장됩니다.

**Q: 로컬 개발 환경에서만 사용할 수 있나요?**
A: 아니요. 프로덕션 환경에서도 사용 가능하지만 보안 설정이 필요합니다.

**Q: Celery 없이 실행할 수 있나요?**
A: 네. 필요한 서비스만 선택적으로 실행 가능합니다.
```bash
docker compose up -d postgres redis backend streamlit
```

**Q: 메모리 사용량은 얼마나 되나요?**
A: 기본 설정 기준 약 2-3GB입니다. (모든 서비스 포함)

---

**v1.3 Architecture by HAB Public Data Team**
