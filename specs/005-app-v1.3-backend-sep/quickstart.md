# Quick Start Guide: v1.3 Backend Architecture

**Feature**: Backend Server Architecture Implementation
**Date**: 2025-12-09
**Target**: 개발자 및 초보자

## 빠른 시작 (5분)

### 전제 조건

- Docker 24+ 및 Docker Compose 2.20+ 설치
- Python 3.10+ (로컬 개발 시)
- 8GB+ RAM 권장

### 1. 환경 변수 설정

```bash
# 프론트엔드 환경 변수 (.env)
cat > .env << EOF
BACKEND_URL=http://localhost:8000
CLAUDE_API_KEY=sk-ant-api03-xxxxx  # 선택사항
EOF

# 백엔드 환경 변수 (backend/.env)
cat > backend/.env << EOF
DATABASE_URL=postgresql://postgres:password@postgres:5432/hab_public_data
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
EOF
```

### 2. 전체 스택 실행

```bash
# Docker Compose로 한 번에 실행
docker compose up -d

# 로그 확인
docker compose logs -f
```

### 3. 서비스 접속

- **Streamlit UI**: http://localhost:8501
- **FastAPI Docs**: http://localhost:8000/docs
- **Flower (Celery 모니터링)**: http://localhost:5555

### 4. 헬스 체크

```bash
# 백엔드 헬스체크
curl http://localhost:8000/health

# Streamlit 헬스체크
curl http://localhost:8501/_stcore/health
```

---

## 개발 워크플로우

### 백엔드 코드 수정 (Hot Reload)

```bash
# backend/.env 파일에서 설정
BACKEND_RELOAD=true

# 코드 수정 후 자동 재시작
# backend/ 디렉토리 변경 감지 → Uvicorn 자동 reload
```

### 데이터베이스 마이그레이션

```bash
# 마이그레이션 생성
docker compose exec backend alembic revision --autogenerate -m "Add new table"

# 마이그레이션 적용
docker compose exec backend alembic upgrade head

# 마이그레이션 롤백
docker compose exec backend alembic downgrade -1
```

### Redis 캐시 관리

```bash
# 캐시 전체 조회
docker compose exec redis redis-cli KEYS "*"

# 특정 캐시 조회
docker compose exec redis redis-cli GET "chat:dataset_123:hash_456"

# 캐시 전체 삭제
docker compose exec redis redis-cli FLUSHALL
```

---

## 문제 해결

### 포트 충돌

```bash
# .env 파일에서 포트 변경
BACKEND_PORT=8001
STREAMLIT_PORT=8502
```

### 컨테이너 재시작

```bash
# 특정 서비스만 재시작
docker compose restart backend

# 전체 재시작
docker compose restart
```

### 볼륨 초기화

```bash
# 볼륨 삭제 (주의: 데이터 소실)
docker compose down -v

# 재시작
docker compose up -d
```

### 이미지 재빌드

```bash
# 캐시 없이 재빌드
docker compose build --no-cache

# 재시작
docker compose up -d
```

---

## API 사용 예시

### ECLO 예측

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
    "accident_day": 8
  }'
```

### AI 챗봇

```bash
curl -X POST http://localhost:8000/api/chat/message \
  -H "Content-Type: application/json" \
  -H "X-Anthropic-API-Key: sk-ant-api03-xxxxx" \
  -d '{
    "dataset_id": "ds_456",
    "message": "사고가 가장 많은 시간대는?"
  }'
```

---

## 다음 단계

1. ✅ 환경 설정 완료
2. ✅ 전체 스택 실행
3. → **Phase 2: /speckit.tasks 실행** (작업 목록 생성)
4. → 구현 시작 (backend/ 디렉토리 생성)

---

## 참고 자료

- [plan.md](./plan.md): 전체 구현 계획
- [data-model.md](./data-model.md): 데이터베이스 스키마
- [contracts/openapi.yaml](./contracts/openapi.yaml): API 명세
- [research.md](./research.md): 기술 조사 결과
