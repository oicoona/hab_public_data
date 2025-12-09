FROM python:3.12-slim

LABEL maintainer="hab_public_data"
LABEL description="FastAPI Backend with Celery for HAB Public Data Visualization"

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 필수 패키지 설치
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 파일 복사
COPY requirements-backend.txt .

# Python 패키지 설치
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-backend.txt

# 애플리케이션 코드 복사
COPY backend/ ./backend/
COPY utils/ ./utils/
COPY model/ ./model/

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 포트 노출
EXPOSE 8000

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# 기본 명령어 (docker-compose에서 오버라이드됨)
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
