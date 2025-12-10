# Data Model: Backend Server Architecture (v1.3)

**Feature**: Backend Server Architecture Implementation
**Date**: 2025-12-09
**Database**: PostgreSQL 15+

## Overview

이 문서는 대구 공공데이터 시각화 앱 v1.3의 데이터베이스 스키마를 정의합니다. 모든 엔티티는 spec.md의 "Key Entities" 섹션에서 도출되었습니다.

---

## Entity Relationship Diagram

```
┌──────────────┐
│   Dataset    │
│  (데이터셋)   │
└──────┬───────┘
       │ 1
       │
       │ N
┌──────▼──────────┐     ┌────────────────┐
│  Conversation   │     │   ShareToken   │
│   (대화 세션)    │     │  (공유 링크)    │
└──────┬──────────┘     └────────────────┘
       │ 1                      │
       │                        │ N
       │ N                      │ 1
┌──────▼──────┐          ┌──────▼───────┐
│   Message   │          │   Dataset    │
│  (메시지)    │          └──────────────┘
└─────────────┘

┌──────────────┐
│  Prediction  │
│ (예측 결과)   │
└──────────────┘
       │ N
       │
       │ 1 (optional)
┌──────▼───────┐
│   Dataset    │
└──────────────┘
```

---

## Entities

### 1. Dataset (데이터셋)

사용자가 업로드한 CSV 데이터셋의 메타데이터를 저장합니다.

**Table**: `datasets`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | SERIAL | PRIMARY KEY | 데이터셋 고유 ID |
| `name` | VARCHAR(255) | NOT NULL | 데이터셋 이름 (예: "대구_교통사고_2024") |
| `description` | TEXT | NULL | 데이터셋 설명 (선택사항) |
| `file_path` | VARCHAR(500) | NOT NULL | 서버 파일 시스템 경로 (예: "/uploads/ds_456.csv") |
| `rows` | INTEGER | NULL | 데이터 행 수 |
| `columns` | INTEGER | NULL | 데이터 열 수 |
| `size_bytes` | BIGINT | NULL | 파일 크기 (바이트) |
| `uploaded_at` | TIMESTAMP | DEFAULT NOW() | 업로드 시각 |

**Relationships**:
- → Conversation (1:N): 이 데이터셋에 대한 대화 세션들
- → Prediction (1:N): 이 데이터셋에 대한 예측 결과들 (선택사항)
- → ShareToken (1:N): 이 데이터셋의 공유 링크들

**Indexes**:
```sql
CREATE INDEX idx_datasets_uploaded_at ON datasets(uploaded_at DESC);
CREATE INDEX idx_datasets_name ON datasets(name);
```

**Validation Rules**:
- `name`: 비어있지 않음, 최대 255자
- `file_path`: 파일 존재 여부 확인
- `rows`, `columns`: 0 이상
- `size_bytes`: 0 이상, 최대 50MB (52,428,800 bytes)

**SQL Definition**:
```sql
CREATE TABLE datasets (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    file_path VARCHAR(500) NOT NULL,
    rows INTEGER CHECK (rows >= 0),
    columns INTEGER CHECK (columns >= 0),
    size_bytes BIGINT CHECK (size_bytes >= 0 AND size_bytes <= 52428800),
    uploaded_at TIMESTAMP DEFAULT NOW()
);
```

---

### 2. Conversation (대화 세션)

AI 챗봇과의 대화 세션을 나타냅니다. 하나의 데이터셋에 대해 여러 대화 세션이 있을 수 있습니다.

**Table**: `conversations`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | SERIAL | PRIMARY KEY | 대화 세션 고유 ID |
| `dataset_id` | INTEGER | FOREIGN KEY (datasets.id) | 연결된 데이터셋 ID |
| `title` | VARCHAR(255) | NULL | 대화 제목 (첫 질문에서 자동 생성) |
| `created_at` | TIMESTAMP | DEFAULT NOW() | 대화 시작 시각 |
| `updated_at` | TIMESTAMP | DEFAULT NOW() | 마지막 메시지 시각 |

**Relationships**:
- ← Dataset (N:1): 이 대화가 속한 데이터셋
- → Message (1:N): 이 대화의 메시지들

**Indexes**:
```sql
CREATE INDEX idx_conversations_dataset_id ON conversations(dataset_id);
CREATE INDEX idx_conversations_updated_at ON conversations(updated_at DESC);
```

**Validation Rules**:
- `dataset_id`: datasets 테이블에 존재해야 함
- `title`: 최대 255자

**SQL Definition**:
```sql
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    dataset_id INTEGER REFERENCES datasets(id) ON DELETE CASCADE,
    title VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

### 3. Message (메시지)

대화 내의 개별 메시지를 저장합니다. 사용자 질문, AI 응답, 시스템 메시지를 모두 포함합니다.

**Table**: `messages`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | SERIAL | PRIMARY KEY | 메시지 고유 ID |
| `conversation_id` | INTEGER | FOREIGN KEY (conversations.id) | 연결된 대화 세션 ID |
| `role` | VARCHAR(20) | NOT NULL, CHECK IN ('user', 'assistant', 'system') | 메시지 역할 |
| `content` | TEXT | NOT NULL | 메시지 내용 |
| `tool_calls` | JSONB | NULL | Tool Calling 정보 (LangGraph) |
| `created_at` | TIMESTAMP | DEFAULT NOW() | 메시지 생성 시각 |

**Relationships**:
- ← Conversation (N:1): 이 메시지가 속한 대화

**Indexes**:
```sql
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);
CREATE INDEX idx_messages_role ON messages(role);
```

**Validation Rules**:
- `conversation_id`: conversations 테이블에 존재해야 함
- `role`: 'user', 'assistant', 'system' 중 하나
- `content`: 비어있지 않음
- `tool_calls`: 유효한 JSON 형식

**tool_calls JSONB 구조**:
```json
[
  {
    "name": "get_value_counts",
    "args": {"column": "시간대"},
    "result": "저녁: 3245건, 낮: 2891건..."
  },
  {
    "name": "get_correlation",
    "args": {"column1": "기상상태", "column2": "ECLO"},
    "result": "0.45"
  }
]
```

**SQL Definition**:
```sql
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    tool_calls JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

### 4. Prediction (예측 결과)

ECLO 예측 결과를 저장합니다. 선택적으로 데이터셋과 연결할 수 있습니다.

**Table**: `predictions`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | SERIAL | PRIMARY KEY | 예측 고유 ID |
| `dataset_id` | INTEGER | FOREIGN KEY (datasets.id), NULL | 연결된 데이터셋 (선택사항) |
| `model_version` | VARCHAR(50) | NULL | 모델 버전 (예: "v1.0") |
| `input_features` | JSONB | NOT NULL | 입력 피처 (JSON) |
| `eclo_value` | DECIMAL(10, 4) | NOT NULL | 예측된 ECLO 값 |
| `interpretation` | VARCHAR(50) | NULL | 해석 (경미/일반/심각/사망) |
| `created_at` | TIMESTAMP | DEFAULT NOW() | 예측 시각 |

**Relationships**:
- ← Dataset (N:1, optional): 이 예측이 속한 데이터셋

**Indexes**:
```sql
CREATE INDEX idx_predictions_dataset_id ON predictions(dataset_id);
CREATE INDEX idx_predictions_created_at ON predictions(created_at DESC);
CREATE INDEX idx_predictions_eclo_value ON predictions(eclo_value);
```

**Validation Rules**:
- `input_features`: 유효한 JSON 형식
- `eclo_value`: 0.0 이상
- `interpretation`: 'minor', 'common', 'serious', 'death' 중 하나 (선택사항)

**input_features JSONB 구조**:
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
  "accident_day": 8
}
```

**SQL Definition**:
```sql
CREATE TABLE predictions (
    id SERIAL PRIMARY KEY,
    dataset_id INTEGER REFERENCES datasets(id) ON DELETE SET NULL,
    model_version VARCHAR(50),
    input_features JSONB NOT NULL,
    eclo_value DECIMAL(10, 4) NOT NULL CHECK (eclo_value >= 0),
    interpretation VARCHAR(50) CHECK (interpretation IN ('minor', 'common', 'serious', 'death')),
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

### 5. ShareToken (공유 토큰)

데이터셋 공유 링크를 관리합니다. 7일 후 자동 만료됩니다.

**Table**: `share_tokens`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | SERIAL | PRIMARY KEY | 토큰 고유 ID |
| `dataset_id` | INTEGER | FOREIGN KEY (datasets.id) | 연결된 데이터셋 ID |
| `token` | VARCHAR(255) | NOT NULL, UNIQUE | 공유 토큰 (랜덤 생성) |
| `expires_at` | TIMESTAMP | NOT NULL | 만료 시각 (생성 + 7일) |
| `created_at` | TIMESTAMP | DEFAULT NOW() | 생성 시각 |

**Relationships**:
- ← Dataset (N:1): 이 토큰이 속한 데이터셋

**Indexes**:
```sql
CREATE INDEX idx_share_tokens_dataset_id ON share_tokens(dataset_id);
CREATE INDEX idx_share_tokens_token ON share_tokens(token);
CREATE INDEX idx_share_tokens_expires_at ON share_tokens(expires_at);
```

**Validation Rules**:
- `dataset_id`: datasets 테이블에 존재해야 함
- `token`: 비어있지 않음, 고유해야 함
- `expires_at`: 현재 시각 이후

**Token Generation**:
```python
import secrets
import hashlib
from datetime import datetime, timedelta

def generate_share_token() -> str:
    """랜덤 공유 토큰 생성 (16바이트 hex)"""
    return secrets.token_hex(16)  # 32글자

def create_share_token(dataset_id: int) -> dict:
    """공유 토큰 생성 (7일 만료)"""
    token = generate_share_token()
    expires_at = datetime.now() + timedelta(days=7)

    return {
        "token": token,
        "expires_at": expires_at,
        "share_url": f"https://app.example.com/shared/{token}"
    }
```

**SQL Definition**:
```sql
CREATE TABLE share_tokens (
    id SERIAL PRIMARY KEY,
    dataset_id INTEGER REFERENCES datasets(id) ON DELETE CASCADE,
    token VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT check_expires_future CHECK (expires_at > created_at)
);
```

---

## State Transitions

### Conversation 상태 전이

```
[생성] → [진행 중] → [완료]
  ↓          ↓           ↓
  └──────────┴───────────┘
       (updated_at 업데이트)
```

- **생성**: 첫 메시지 작성 시 `conversations` 레코드 생성
- **진행 중**: 메시지 추가 시 `updated_at` 업데이트
- **완료**: 사용자가 대화 종료 (상태 필드 없음, `updated_at`로 판단)

### ShareToken 상태 전이

```
[생성] → [유효] → [만료]
         (7일)
```

- **생성**: `create_share_token()` 호출 시 생성
- **유효**: `expires_at > NOW()`
- **만료**: `expires_at <= NOW()` (자동 만료, 크론잡으로 삭제)

---

## Data Lifecycle

### Dataset 삭제 시

```sql
-- CASCADE 옵션으로 관련 데이터 자동 삭제
DELETE FROM datasets WHERE id = 123;

-- 자동 삭제됨:
-- 1. conversations (ON DELETE CASCADE)
-- 2. messages (conversations 삭제 시 cascade)
-- 3. share_tokens (ON DELETE CASCADE)
-- 4. predictions (ON DELETE SET NULL, dataset_id만 NULL로 변경)
```

### 만료된 ShareToken 정리 (크론잡)

```sql
-- 매일 자정 실행
DELETE FROM share_tokens WHERE expires_at < NOW();
```

---

## Migration Strategy

### Alembic 마이그레이션 생성

```bash
# 초기 스키마 생성
alembic revision --autogenerate -m "Create initial schema"

# 마이그레이션 적용
alembic upgrade head
```

### 마이그레이션 파일 예시

```python
# alembic/versions/001_create_initial_schema.py
def upgrade():
    op.create_table(
        'datasets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('rows', sa.Integer(), nullable=True),
        sa.Column('columns', sa.Integer(), nullable=True),
        sa.Column('size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('uploaded_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_datasets_uploaded_at', 'datasets', ['uploaded_at'], unique=False)

    # ... 나머지 테이블 생성 ...

def downgrade():
    op.drop_table('datasets')
    # ... 나머지 테이블 삭제 ...
```

---

## Query Examples

### 1. 특정 데이터셋의 최근 대화 조회

```sql
SELECT c.id, c.title, c.updated_at, COUNT(m.id) as message_count
FROM conversations c
LEFT JOIN messages m ON c.id = m.conversation_id
WHERE c.dataset_id = 123
GROUP BY c.id, c.title, c.updated_at
ORDER BY c.updated_at DESC
LIMIT 10;
```

### 2. 대화 이력 전체 조회 (메시지 포함)

```sql
SELECT
    m.role,
    m.content,
    m.tool_calls,
    m.created_at
FROM messages m
WHERE m.conversation_id = 456
ORDER BY m.created_at ASC;
```

### 3. 최근 7일간 예측 통계

```sql
SELECT
    DATE(created_at) as date,
    COUNT(*) as total_predictions,
    AVG(eclo_value) as avg_eclo,
    MAX(eclo_value) as max_eclo
FROM predictions
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

### 4. 만료된 공유 링크 정리

```sql
DELETE FROM share_tokens
WHERE expires_at < NOW()
RETURNING id, dataset_id, token;
```

---

## Performance Considerations

### Indexing Strategy

- **datasets**: `uploaded_at DESC` (최근 업로드 순 조회)
- **conversations**: `updated_at DESC` (최근 대화 순 조회), `dataset_id` (JOIN 최적화)
- **messages**: `conversation_id` (JOIN 최적화), `created_at` (시간순 조회)
- **predictions**: `created_at DESC` (최근 예측 순 조회), `dataset_id` (JOIN 최적화)
- **share_tokens**: `token` (공유 링크 조회), `expires_at` (만료 체크)

### JSONB Indexing (필요시 추가)

```sql
-- tool_calls에서 특정 도구 검색
CREATE INDEX idx_messages_tool_calls_name ON messages USING GIN ((tool_calls -> 'name'));

-- input_features에서 특정 피처 검색
CREATE INDEX idx_predictions_input_features ON predictions USING GIN (input_features);
```

### Connection Pooling

```python
# backend/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://user:password@localhost:5432/hab_public_data"

engine = create_engine(
    DATABASE_URL,
    pool_size=10,          # 최대 10개 연결 유지
    max_overflow=20,       # 피크 시 20개 추가 연결
    pool_pre_ping=True,    # 연결 재사용 전 헬스 체크
    pool_recycle=3600      # 1시간 후 연결 재생성
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

---

## Backup & Recovery

### 백업 전략

```bash
# 전체 데이터베이스 백업
pg_dump hab_public_data > backup_$(date +%Y%m%d).sql

# 특정 테이블만 백업
pg_dump -t datasets -t conversations hab_public_data > backup_conversations.sql
```

### 복구

```bash
# 전체 복구
psql hab_public_data < backup_20241209.sql

# 테이블 단위 복구
psql hab_public_data < backup_conversations.sql
```

---

## Next Steps

- [x] data-model.md 작성 완료
- [ ] contracts/ 디렉토리에 OpenAPI 스키마 생성
- [ ] quickstart.md 작성
- [ ] Agent context 업데이트
