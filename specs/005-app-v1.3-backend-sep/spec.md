# Feature Specification: Backend Server Architecture Implementation

**Feature Branch**: `005-app-v1.3-backend-sep`
**Created**: 2025-12-09
**Status**: Draft
**Input**: User description: "대구 공공데이터 시각화 앱 v1.3 - 백엔드 서버 추가 및 프론트엔드/백엔드 분리 아키텍처 전환"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - ECLO Prediction via Backend API (Priority: P1)

사용자는 현재 Streamlit 앱에서 사용하던 ECLO 예측 기능을 동일하게 사용할 수 있으며, 백엔드 서버를 통해 더 빠르고 안정적인 예측을 받는다.

**Why this priority**:
- ECLO 예측은 앱의 핵심 기능
- 백엔드 아키텍처 검증을 위한 첫 단계
- 사용자 영향이 가장 적은 단순 마이그레이션
- 모델 서빙 최적화로 즉각적인 성능 개선 효과

**Independent Test**:
Streamlit 앱에서 교통사고 조건(날씨, 도로 상태 등)을 입력하고 "예측" 버튼을 클릭하여 ECLO 값과 해석이 반환되는지 확인. 백엔드 서버가 실행 중이지 않으면 오류 메시지가 표시되어야 함.

**Acceptance Scenarios**:

1. **Given** 사용자가 앱에서 교통사고 조건(날씨: 맑음, 도로상태: 건조, 사고유형: 차대차)을 입력했을 때, **When** "ECLO 예측" 버튼을 클릭하면, **Then** 1초 이내에 ECLO 값(0.23)과 해석("일반")이 화면에 표시된다
2. **Given** 백엔드 서버가 실행 중이고 모델이 로드되어 있을 때, **When** 여러 사용자가 동시에 예측 요청을 보내면, **Then** 모든 요청이 2초 이내에 처리된다
3. **Given** 사용자가 대량의 데이터(100건)에 대한 배치 예측을 요청했을 때, **When** 배치 예측 API를 호출하면, **Then** 작업 ID와 예상 완료 시간이 반환되고, 결과 조회 API로 진행 상황을 확인할 수 있다
4. **Given** 백엔드 서버가 다운되었을 때, **When** 사용자가 예측을 시도하면, **Then** "서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요."라는 명확한 오류 메시지가 표시된다

---

### User Story 2 - Chat with AI via Backend API (Priority: P2)

사용자는 데이터셋에 대해 AI 챗봇과 대화하며, 자신의 Anthropic API 키를 사용하여 질문에 답변을 받는다. 대화 이력은 영구적으로 저장되어 나중에 다시 확인할 수 있다.

**Why this priority**:
- AI 챗봇은 앱의 두 번째 핵심 기능
- 대화 이력 영속화는 사용자 경험 향상의 핵심
- Redis 캐싱으로 동일 질문에 대한 빠른 응답 제공
- API 키 개별 관리 방식 유지로 사용자 편의성 보장

**Independent Test**:
사용자가 Streamlit 사이드바에 Anthropic API 키를 입력하고, 업로드된 데이터셋에 대해 "사고가 가장 많은 시간대는?"이라는 질문을 입력하면, AI 챗봇이 데이터를 분석하여 답변을 반환. 대화 이력은 PostgreSQL에 저장되며, 페이지를 새로고침해도 이전 대화가 유지됨.

**Acceptance Scenarios**:

1. **Given** 사용자가 Anthropic API 키를 입력하고 데이터셋을 업로드했을 때, **When** "사고가 가장 많은 시간대는?" 질문을 입력하면, **Then** 5초 이내에 데이터 분석 결과와 함께 답변이 표시된다
2. **Given** 사용자가 동일한 데이터셋에 대해 동일한 질문을 두 번째로 했을 때, **When** 질문을 전송하면, **Then** Redis 캐시에서 즉시(100ms 이내) 답변이 반환되고 "캐시에서 반환됨" 표시가 나타난다
3. **Given** 사용자가 이전에 대화를 나눴던 세션을 떠났을 때, **When** 나중에 같은 브라우저로 다시 접속하면, **Then** 이전 대화 이력이 그대로 표시된다
4. **Given** 사용자가 잘못된 API 키를 입력했을 때, **When** 챗봇에 질문하면, **Then** "API 키가 유효하지 않습니다. 다시 확인해주세요."라는 메시지가 표시된다
5. **Given** 사용자가 env 파일에 API 키를 설정해두었을 때, **When** 앱을 시작하면, **Then** 사이드바에 API 키가 자동으로 입력되어 있어 수동 입력이 불필요하다

---

### User Story 3 - Upload and Manage Datasets via Backend (Priority: P3)

사용자는 CSV 데이터셋을 업로드하면 영구적으로 저장되며, 나중에 언제든지 다시 불러올 수 있다. 또한 팀원과 공유 링크를 생성하여 데이터셋을 공유할 수 있다.

**Why this priority**:
- 데이터 영속화는 사용자 경험 향상의 기반
- 팀 협업 기능으로 활용도 증가
- 파일 기반 시스템에서 DB 기반 시스템으로의 전환
- 데이터 버전 관리 및 추적 가능

**Independent Test**:
사용자가 "대구_교통사고_2024.csv" 파일을 업로드하면, 파일 정보(행 수, 열 수, 크기)가 표시되고 데이터셋 목록에 추가됨. 페이지를 닫고 다시 열어도 업로드한 데이터셋이 목록에 남아있으며, "공유" 버튼을 클릭하여 공유 링크를 생성할 수 있음.

**Acceptance Scenarios**:

1. **Given** 사용자가 새로운 CSV 파일(5MB, 15,000행, 28열)을 선택했을 때, **When** "업로드" 버튼을 클릭하면, **Then** 10초 이내에 업로드가 완료되고 데이터셋 정보(행/열 수, 크기)가 표시된다
2. **Given** 사용자가 이전에 여러 데이터셋을 업로드했을 때, **When** 데이터셋 목록 페이지를 열면, **Then** 모든 데이터셋이 업로드 날짜 순으로 정렬되어 표시되며, 각 항목에 이름/행수/열수/업로드 날짜가 포함된다
3. **Given** 사용자가 특정 데이터셋을 선택했을 때, **When** "공유" 버튼을 클릭하면, **Then** 7일 동안 유효한 공유 링크가 생성되고 클립보드에 복사된다
4. **Given** 공유 링크를 받은 다른 사용자가 해당 링크를 열었을 때, **When** 링크에 접속하면, **Then** 데이터셋이 자동으로 로드되고 AI 챗봇과 시각화 기능을 사용할 수 있다
5. **Given** 사용자가 잘못된 형식의 파일(xlsx, json)을 업로드하려고 할 때, **When** 파일을 선택하면, **Then** "CSV 형식만 지원됩니다."라는 오류 메시지가 표시된다

---

### User Story 4 - Visualize Data in Frontend (Priority: P4)

사용자는 백엔드에 저장된 데이터를 기반으로 Plotly 차트와 Folium 지도를 통해 시각화할 수 있다. 시각화는 클라이언트 사이드에서 빠르게 렌더링되며 인터랙티브한 조작이 가능하다.

**Why this priority**:
- 시각화 기능은 기존 방식을 유지 (프론트엔드에서 처리)
- 백엔드 변경의 영향을 최소화
- 사용자 인터랙션 성능 유지
- 백엔드에서 데이터만 제공하면 되므로 구현 난이도 낮음

**Independent Test**:
사용자가 데이터셋을 선택하고 "시각화" 탭으로 이동하면, 사고 유형별 막대 그래프와 사고 발생 지점을 표시한 지도가 화면에 표시됨. 차트를 줌/팬하거나 지도 마커를 클릭하면 즉각적으로 반응함.

**Acceptance Scenarios**:

1. **Given** 사용자가 데이터셋을 선택하고 시각화 탭을 열었을 때, **When** 페이지가 로드되면, **Then** 2초 이내에 모든 차트와 지도가 렌더링된다
2. **Given** 사용자가 Plotly 차트에서 특정 영역을 선택했을 때, **When** 마우스로 드래그하여 줌인하면, **Then** 즉시 해당 영역이 확대되고 축 레이블이 업데이트된다
3. **Given** 사용자가 Folium 지도에서 특정 마커를 클릭했을 때, **When** 마커를 클릭하면, **Then** 팝업이 표시되어 해당 사고의 상세 정보(날짜, 시간, 사고 유형, ECLO 값)가 보여진다

---

### Edge Cases

- **백엔드 서버 다운**: 프론트엔드에서 "서버 연결 실패" 메시지를 표시하고, 5초 후 자동으로 재시도. 3회 실패 시 "관리자에게 문의하세요" 안내
- **데이터베이스 연결 실패**: 백엔드에서 500 오류 대신 503 Service Unavailable 반환하고, 로그에 상세 오류 기록
- **Redis 캐시 만료**: 캐시 미스 시 자동으로 LLM 호출하여 응답 생성 후 캐시에 저장
- **대용량 파일 업로드**: 50MB 이상 파일은 업로드 거부하고 "파일 크기는 50MB를 초과할 수 없습니다" 메시지 표시
- **동시 예측 요청 폭주**: Celery 큐가 100개 이상의 작업을 보유하면 새 요청에 대해 "서버가 혼잡합니다. 잠시 후 다시 시도해주세요" 반환
- **잘못된 API 키**: 401 Unauthorized 반환하고 프론트엔드에서 "API 키가 유효하지 않습니다" 메시지 표시
- **네트워크 타임아웃**: 백엔드 요청이 30초 이내에 응답 없으면 타임아웃 처리하고 "요청 시간 초과. 다시 시도해주세요" 표시
- **데이터셋 삭제 중 사용**: 사용자가 현재 사용 중인 데이터셋을 삭제하려고 하면 "사용 중인 데이터셋은 삭제할 수 없습니다" 경고 표시
- **공유 링크 만료**: 만료된 공유 링크로 접속 시 "이 링크는 만료되었습니다" 메시지와 함께 메인 페이지로 리다이렉트
- **세션 충돌**: 같은 사용자가 여러 브라우저/탭에서 동시에 같은 대화를 수정하면 마지막 저장이 우선 적용되고 "대화가 다른 곳에서 수정되었습니다" 경고 표시

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 시스템은 FastAPI 기반 백엔드 서버를 제공하여 ECLO 예측, AI 챗봇, 데이터셋 관리 API를 노출해야 함
- **FR-002**: ECLO 예측 API는 단일 예측(POST /api/predict/eclo)과 배치 예측(POST /api/predict/eclo/batch)을 지원해야 함
- **FR-003**: 시스템은 ECLO 예측 모델을 서버 시작 시 한 번만 로드하여 메모리에 유지해야 함
- **FR-004**: AI 챗봇 API는 클라이언트가 전달한 Anthropic API 키를 요청 헤더(X-Anthropic-API-Key)로 받아 Anthropic API를 호출해야 함
- **FR-005**: 시스템은 사용자가 env 파일에 설정한 API 키를 자동으로 프론트엔드에 로드하되, 설정이 없으면 수동 입력을 허용해야 함
- **FR-006**: 대화 이력(messages)은 PostgreSQL 데이터베이스에 영구 저장되어야 하며, conversation_id로 그룹화되어야 함
- **FR-007**: 동일한 데이터셋과 질문에 대한 챗봇 응답은 Redis에 1시간 동안 캐싱되어야 함
- **FR-008**: 데이터셋 업로드 API는 CSV 파일만 허용하고, 파일 크기를 50MB로 제한해야 함
- **FR-009**: 업로드된 데이터셋의 메타데이터(이름, 행 수, 열 수, 크기, 업로드 날짜)는 PostgreSQL에 저장되어야 함
- **FR-010**: 시스템은 데이터셋 공유 링크를 생성할 수 있어야 하며, 링크는 7일 후 자동 만료되어야 함
- **FR-011**: 배치 예측은 Celery 큐를 통해 비동기로 처리되어야 하며, 작업 상태를 조회할 수 있는 API를 제공해야 함
- **FR-012**: Plotly 시각화와 Folium 지도 렌더링은 클라이언트 사이드(Streamlit)에서 처리되어야 함
- **FR-013**: 백엔드 API는 Docker Compose로 PostgreSQL, Redis, FastAPI, Celery를 모두 포함한 스택으로 실행 가능해야 함
- **FR-014**: 시스템은 백엔드가 응답하지 않을 때 최대 3회 재시도하고, 실패 시 사용자에게 명확한 오류 메시지를 표시해야 함
- **FR-015**: 모든 API 응답은 성공/실패 상태, 에러 메시지(있는 경우), 타임스탬프를 포함해야 함
- **FR-016**: 시스템은 Tool Calling 분석 도구(22개)를 백엔드 API로 이관하여 dataset_id 기반으로 실행해야 함
- **FR-017**: 시스템은 백엔드 서버의 헬스체크 엔드포인트(GET /health)를 제공하여 서비스 상태를 확인할 수 있어야 함
- **FR-018**: 프론트엔드는 백엔드 URL을 환경 변수(BACKEND_URL)로 설정 가능해야 하며, 기본값은 http://localhost:8000이어야 함
- **FR-019**: 배치 예측 큐가 100개 이상의 작업을 보유하면 새 요청을 거부하고 429 Too Many Requests를 반환해야 함
- **FR-020**: 시스템은 데이터베이스 마이그레이션 도구(Alembic)를 제공하여 스키마 변경을 관리해야 함

### Key Entities

- **Dataset**: 사용자가 업로드한 CSV 데이터셋을 나타냄. 속성: id, name, description, file_path, rows, columns, size_bytes, uploaded_at. 관계: Conversation, Prediction과 1:N 관계
- **Conversation**: AI 챗봇과의 대화 세션을 나타냄. 속성: id, dataset_id, title, created_at, updated_at. 관계: Dataset과 N:1, Message와 1:N 관계
- **Message**: 대화 내의 개별 메시지를 나타냄. 속성: id, conversation_id, role(user/assistant/system), content, tool_calls(JSON), created_at. 관계: Conversation과 N:1
- **Prediction**: ECLO 예측 결과를 나타냄. 속성: id, model_version, input_features(JSON), eclo_value, interpretation, created_at. 관계: Dataset과 N:1 (선택사항)
- **ShareToken**: 데이터셋 공유 링크를 나타냄. 속성: id, dataset_id, token, expires_at, created_at. 관계: Dataset과 N:1

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: ECLO 예측 API 응답 시간이 평균 1초 이내여야 하며, 90th percentile이 2초를 초과하지 않아야 함
- **SC-002**: AI 챗봇 응답 시간이 캐시 히트 시 100ms 이내, 캐시 미스 시 5초 이내여야 함
- **SC-003**: 동시에 50명의 사용자가 예측 요청을 보낼 때 모든 요청이 3초 이내에 처리되어야 함
- **SC-004**: 백엔드 서버 재시작 후 5초 이내에 모든 서비스(API, Database, Redis)가 정상 작동해야 함
- **SC-005**: 데이터셋 업로드 시 10MB 파일이 5초 이내, 50MB 파일이 15초 이내에 완료되어야 함
- **SC-006**: 대화 이력이 데이터베이스에 저장되어, 사용자가 세션을 종료하고 재접속해도 100% 복원되어야 함
- **SC-007**: 동일한 질문에 대한 두 번째 응답이 첫 번째 응답 대비 95% 이상 빨라야 함 (Redis 캐싱 효과)
- **SC-008**: 배치 예측 작업이 큐에 등록된 후 30초 이내에 처리를 시작해야 하며, 100건 예측이 2분 이내에 완료되어야 함
- **SC-009**: 백엔드 API 가용성이 99% 이상이어야 하며, 서비스 다운타임 시 3분 이내에 복구되어야 함
- **SC-010**: 사용자가 env 파일에 API 키를 설정한 경우, 앱 시작 시 100% 자동으로 로드되어 수동 입력이 불필요해야 함
- **SC-011**: 프론트엔드와 백엔드 간 네트워크 오류 발생 시 5초 이내에 사용자에게 명확한 오류 메시지가 표시되어야 함
- **SC-012**: Docker Compose로 전체 스택을 시작할 때 30초 이내에 모든 서비스가 정상 작동해야 함

## Assumptions *(optional)*

- 사용자는 Anthropic API 키를 보유하고 있으며, 사용 요금을 스스로 관리함
- CSV 파일은 UTF-8 인코딩을 사용하며, 첫 행에 헤더가 포함되어 있음
- 사용자는 단일 브라우저 세션에서 작업하며, 멀티 디바이스 동기화는 지원하지 않음
- 네트워크 환경은 안정적이며, 프론트엔드와 백엔드 간 통신 지연은 100ms 이내임
- Docker와 Docker Compose가 사용자 환경에 설치되어 있음
- PostgreSQL 데이터베이스는 최소 1GB의 저장 공간을 가지고 있음
- Redis는 최소 512MB의 메모리를 사용 가능함
- ECLO 예측 모델 파일(1.4MB)은 model/ 디렉토리에 존재함
- 사용자는 localhost 환경에서 개발 및 테스트를 진행함
- 공유 링크는 익명 사용자도 접근 가능하며, 별도 인증을 요구하지 않음

## Dependencies *(optional)*

- **외부 API**: Anthropic API (claude-sonnet-4-5 모델) - AI 챗봇 응답 생성에 필수
- **데이터베이스**: PostgreSQL 15+ - 데이터 영속화에 필수
- **캐시**: Redis 7.0+ - 응답 캐싱 및 Celery 브로커에 필수
- **컨테이너**: Docker 24+, Docker Compose 2.20+ - 전체 스택 배포에 필수
- **Python 버전**: Python 3.10+ (현재 환경 3.12 호환)
- **기존 코드**: utils/ 모듈의 chatbot.py, tools.py, predictor.py 등을 백엔드로 이관 필요
- **ECLO 모델**: model/accident_lgbm_model.pkl, label_encoders.pkl, feature_config.json

## Out of Scope *(optional)*

- 사용자 인증 및 권한 관리 (API 키는 클라이언트가 관리)
- 결제 시스템 및 사용량 과금
- 멀티 테넌시 및 사용자별 데이터 격리
- 모바일 앱 지원 (Streamlit 웹 앱만 지원)
- 실시간 협업 기능 (동시 편집, 멀티 커서 등)
- A/B 테스트를 위한 모델 버전 관리 (단일 모델만 서빙)
- 프로덕션 배포 및 CI/CD 파이프라인 (로컬 개발 환경에 집중)
- 성능 모니터링 대시보드 (Prometheus, Grafana는 Phase 4에서 고려)
- API 속도 제한(Rate Limiting) 및 사용량 추적
- 데이터 백업 및 복구 전략
- 다국어 지원 (한국어만 지원)
- 데이터셋 버전 관리 및 변경 이력 추적
- 고급 분석 도구 추가 (현재 22개 도구만 이관)
- 웹훅 및 외부 시스템 통합
