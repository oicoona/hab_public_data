#!/bin/bash
# 백엔드 서버 & Streamlit 프론트엔드 빠른 시작 스크립트
# 
# 이 스크립트는 다음을 수행합니다:
# 1. 환경 변수 파일 생성 (.env, backend/.env)
# 2. Docker Compose 실행
# 3. 데이터베이스 마이그레이션 실행
# 4. 서비스 헬스 체크
# 5. 결과 리포트 출력

set -e  # 에러 발생 시 중단

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 함수: 메시지 출력
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 함수: 명령어 존재 확인
check_command() {
    if ! command -v $1 &> /dev/null; then
        error "$1이(가) 설치되어 있지 않습니다."
        exit 1
    fi
}

# 함수: 포트 사용 확인
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 || netstat -an | grep -q ":$port.*LISTEN" 2>/dev/null; then
        warning "포트 $port가 이미 사용 중입니다."
        read -p "계속하시겠습니까? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# 함수: 환경 변수 파일 생성
create_env_files() {
    info "환경 변수 파일 생성 중..."
    
    # .env 파일 생성
    if [ ! -f .env ]; then
        info ".env 파일 생성 중..."
        cat > .env << 'EOF'
# Streamlit Frontend Environment Variables
BACKEND_URL=http://localhost:8000
CLAUDE_API_KEY=sk-ant-api03-xxxxx  # 선택사항: Anthropic API 키
EOF
        success ".env 파일이 생성되었습니다."
        warning "CLAUDE_API_KEY를 실제 값으로 변경해주세요. (선택사항)"
    else
        warning ".env 파일이 이미 존재합니다. 건너뜁니다."
    fi
    
    # backend/.env 파일 생성
    if [ ! -f backend/.env ]; then
        info "backend/.env 파일 생성 중..."
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

# CORS (JSON array format required by Pydantic)
CORS_ORIGINS=["http://localhost:8501", "http://streamlit:8501"]
EOF
        success "backend/.env 파일이 생성되었습니다."
    else
        warning "backend/.env 파일이 이미 존재합니다. 건너뜁니다."
    fi
}

# 함수: 필수 파일 확인
check_required_files() {
    info "필수 파일 확인 중..."
    
    local missing_files=()
    
    [ ! -f docker-compose.yml ] && missing_files+=("docker-compose.yml")
    [ ! -f backend/Dockerfile ] && missing_files+=("backend/Dockerfile")
    [ ! -f Dockerfile.streamlit ] && missing_files+=("Dockerfile.streamlit")
    [ ! -f alembic.ini ] && missing_files+=("alembic.ini")

    # Check for at least one migration file (flexible check)
    if [ ! -d alembic/versions ] || [ -z "$(ls -A alembic/versions/*.py 2>/dev/null | grep -v __init__)" ]; then
        missing_files+=("alembic/versions/[migration files]")
    fi
    
    if [ ${#missing_files[@]} -gt 0 ]; then
        error "다음 필수 파일들이 누락되었습니다:"
        for file in "${missing_files[@]}"; do
            echo "  - $file"
        done
        exit 1
    fi
    
    success "모든 필수 파일이 존재합니다."
}

# 함수: Docker Compose 실행
start_docker_compose() {
    info "Docker Compose로 서비스 시작 중..."
    
    if docker compose ps | grep -q "Up"; then
        warning "일부 서비스가 이미 실행 중입니다."
        read -p "기존 서비스를 중지하고 재시작하시겠습니까? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            info "기존 서비스 중지 중..."
            docker compose down
        else
            info "기존 서비스를 유지합니다."
            return
        fi
    fi
    
    docker compose up -d
    
    info "서비스 시작을 기다리는 중... (30초)"
    sleep 30
    
    success "Docker Compose 서비스가 시작되었습니다."
}

# 함수: 마이그레이션 확인 (실행은 Dockerfile에서 자동 처리)
check_migrations() {
    info "데이터베이스 마이그레이션 상태 확인 중..."

    local max_attempts=15
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if docker compose exec -T backend alembic current >/dev/null 2>&1; then
            local current_rev=$(docker compose exec -T backend alembic current 2>/dev/null | grep -oP '(?<=\(head\)|\s)[a-f0-9]+' | head -1)
            if [ -n "$current_rev" ]; then
                success "마이그레이션 적용 완료: $current_rev"
                return 0
            fi
        fi

        info "백엔드 서비스 및 마이그레이션 준비 대기 중... ($attempt/$max_attempts)"
        sleep 5
        attempt=$((attempt + 1))
    done

    warning "마이그레이션 상태를 확인할 수 없습니다."
    warning "백엔드 로그를 확인하세요: docker compose logs backend"
    return 1
}

# 참고: 마이그레이션은 backend/Dockerfile의 CMD에서 자동으로 실행됩니다:
#       CMD alembic upgrade head && uvicorn backend.main:app ...

# 함수: 헬스 체크
health_check() {
    info "서비스 헬스 체크 중..."
    
    local all_healthy=true
    
    # Backend 헬스 체크
    info "Backend 헬스 체크..."
    if curl -f -s http://localhost:8000/health >/dev/null 2>&1; then
        success "✓ Backend: 정상"
    else
        error "✗ Backend: 연결 실패"
        all_healthy=false
    fi
    
    # Streamlit 헬스 체크
    info "Streamlit 헬스 체크..."
    if curl -f -s http://localhost:8501/_stcore/health >/dev/null 2>&1; then
        success "✓ Streamlit: 정상"
    else
        error "✗ Streamlit: 연결 실패"
        all_healthy=false
    fi
    
    # PostgreSQL 헬스 체크
    info "PostgreSQL 헬스 체크..."
    if docker compose exec -T postgres pg_isready -U postgres >/dev/null 2>&1; then
        success "✓ PostgreSQL: 정상"
    else
        error "✗ PostgreSQL: 연결 실패"
        all_healthy=false
    fi
    
    # Redis 헬스 체크
    info "Redis 헬스 체크..."
    if docker compose exec -T redis redis-cli ping >/dev/null 2>&1; then
        success "✓ Redis: 정상"
    else
        error "✗ Redis: 연결 실패"
        all_healthy=false
    fi
    
    if [ "$all_healthy" = true ]; then
        success "모든 서비스가 정상적으로 실행 중입니다."
        return 0
    else
        warning "일부 서비스에 문제가 있습니다. 로그를 확인하세요."
        return 1
    fi
}

# 함수: 결과 리포트 출력
print_report() {
    echo ""
    echo "=========================================="
    echo "  🎉 빠른 시작 스크립트 완료"
    echo "=========================================="
    echo ""
    echo "📊 서비스 상태:"
    docker compose ps
    echo ""
    echo "🌐 접속 URL:"
    echo "  - Streamlit UI:     http://localhost:8501"
    echo "  - FastAPI Docs:     http://localhost:8000/docs"
    echo "  - Flower (Celery):  http://localhost:5555"
    echo ""
    echo "📝 다음 단계:"
    echo "  1. 브라우저에서 http://localhost:8501 접속"
    echo "  2. 사이드바에서 'Backend 연결됨' 확인"
    echo "  3. ECLO 예측 기능 테스트"
    echo ""
    echo "📚 추가 정보:"
    echo "  - 가이드 문서: BACKEND_STARTUP_GUIDE.md"
    echo "  - 로그 확인: docker compose logs -f"
    echo "  - 서비스 중지: docker compose down"
    echo ""
}

# 메인 실행
main() {
    echo "=========================================="
    echo "  백엔드 서버 빠른 시작 스크립트"
    echo "=========================================="
    echo ""
    
    # 사전 요구사항 확인
    info "사전 요구사항 확인 중..."
    check_command docker
    check_command curl
    
    # 포트 확인
    check_port 8000
    check_port 8501
    check_port 5432
    check_port 6379
    
    # 필수 파일 확인
    check_required_files
    
    # 환경 변수 파일 생성
    create_env_files
    
    # Docker Compose 실행
    start_docker_compose

    # 마이그레이션 상태 확인 (실제 실행은 Dockerfile에서 자동)
    check_migrations

    # 헬스 체크
    if health_check; then
        print_report
        success "모든 설정이 완료되었습니다! 🚀"
        exit 0
    else
        error "일부 서비스에 문제가 있습니다."
        echo ""
        echo "문제 해결 방법:"
        echo "  1. 로그 확인: docker compose logs -f [서비스명]"
        echo "  2. 서비스 재시작: docker compose restart [서비스명]"
        echo "  3. 전체 재시작: docker compose down && docker compose up -d"
        echo ""
        echo "자세한 내용은 BACKEND_STARTUP_GUIDE.md를 참고하세요."
        exit 1
    fi
}

# 스크립트 실행
main

