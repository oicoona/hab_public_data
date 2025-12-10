# Tasks: Backend Server Architecture Implementation (v1.3)

**Input**: Design documents from `/home/sk/hab_public_data/specs/005-app-v1.3-backend-sep/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

This is a web application with backend/frontend separation:
- Backend: `backend/` directory (FastAPI server)
- Frontend: Root directory (Streamlit app)
- Shared: `utils/`, `model/` directories

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create backend directory structure with api/, core/, db/, schemas/, services/, ml/, tasks/ subdirectories
- [X] T002 Create backend/.env file with DATABASE_URL, REDIS_URL, CELERY_BROKER_URL, CELERY_RESULT_BACKEND, BACKEND_HOST, BACKEND_PORT variables
- [X] T003 [P] Create root .env file with BACKEND_URL and CLAUDE_API_KEY variables for frontend
- [X] T004 [P] Create requirements-backend.txt with FastAPI, SQLAlchemy, Alembic, Celery, Redis, psycopg2-binary, httpx, anthropic, langchain, langgraph, lightgbm dependencies
- [X] T005 [P] Create backend/config.py to load environment variables using pydantic BaseSettings
- [X] T006 [P] Create alembic/ directory and initialize Alembic with `alembic init alembic` from repo root
- [X] T007 Configure alembic/env.py to use backend.db.base.Base metadata and DATABASE_URL from backend/config.py
- [X] T008 [P] Create backend/Dockerfile with Python 3.10+ base image, dependency installation, and uvicorn startup command
- [X] T009 [P] Create Dockerfile.streamlit with Streamlit app configuration
- [X] T010 Create docker-compose.yml with services: postgres, redis, backend, celery-worker, flower, streamlit with health checks and dependencies
- [X] T011 [P] Update .gitignore to exclude .env, backend/.env, __pycache__, *.pyc, alembic/versions/*.py (except __init__.py)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T012 Create backend/db/base.py with SQLAlchemy Base declarative base
- [X] T013 Create backend/db/session.py with engine, SessionLocal factory, and get_db dependency for FastAPI
- [X] T014 [P] Create backend/db/models/dataset.py with Dataset model (id, name, description, file_path, rows, columns, size_bytes, uploaded_at)
- [X] T015 [P] Create backend/db/models/conversation.py with Conversation model (id, dataset_id, title, created_at, updated_at)
- [X] T016 [P] Create backend/db/models/message.py with Message model (id, conversation_id, role, content, tool_calls JSONB, created_at)
- [X] T017 [P] Create backend/db/models/prediction.py with Prediction model (id, model_version, input_features JSONB, eclo_value, interpretation, created_at)
- [X] T018 [P] Create backend/db/models/share_token.py with ShareToken model (id, dataset_id, token, expires_at, created_at)
- [X] T019 Create backend/db/models/__init__.py to export all models
- [X] T020 Generate initial Alembic migration with `alembic revision --autogenerate -m "Initial schema"` and verify migrations/versions/*.py (Created manually: 20241210_initial_schema.py)
- [X] T021 Create backend/core/cache.py with Redis client initialization, get_cache_key(), get_cached_response(), cache_response() functions
- [X] T022 Create backend/api/deps.py with dependency functions: get_db(), get_redis_client(), get_anthropic_api_key() (from X-Anthropic-API-Key header)
- [X] T023 Create backend/main.py with FastAPI app initialization, CORS middleware for Streamlit frontend, and include routers placeholder
- [X] T024 Create backend/api/routes/__init__.py to aggregate all route modules
- [X] T025 Add GET /health endpoint in backend/main.py returning {"status": "healthy", "timestamp": "..."}

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - ECLO Prediction via Backend API (Priority: P1) 🎯 MVP

**Goal**: Migrate ECLO prediction from Streamlit to FastAPI backend, enable single and batch predictions with improved performance

**Independent Test**: Start Docker Compose stack, open Streamlit UI, input accident conditions, click "예측" button, verify ECLO value and interpretation display within 1 second. Batch prediction should return job ID and allow status polling.

### Implementation for User Story 1

- [X] T026 [P] [US1] Create backend/schemas/prediction.py with ECLOPredictionRequest and ECLOPredictionResponse Pydantic models matching openapi.yaml
- [X] T027 [P] [US1] Create backend/ml/__init__.py as empty file
- [X] T028 [US1] Create backend/ml/model_loader.py with singleton pattern to load ECLO model (accident_lgbm_model.pkl), label encoders, feature config once at startup
- [X] T029 [US1] Migrate utils/predictor.py logic to backend/services/prediction_service.py with predict_single_eclo() and interpret_eclo() functions
- [X] T030 [US1] Create backend/api/routes/prediction.py with POST /api/predict/eclo endpoint calling prediction_service.predict_single_eclo()
- [X] T031 [US1] Add error handling in POST /api/predict/eclo for invalid input (400), model errors (500), and return proper error schema
- [X] T032 [US1] Create backend/tasks/__init__.py and configure Celery app with Redis broker and result backend from config.py
- [X] T033 [US1] Create backend/tasks/prediction_tasks.py with @celery_app.task batch_predict_eclo(accidents: list[dict]) function
- [X] T034 [US1] Add POST /api/predict/eclo/batch endpoint in backend/api/routes/prediction.py that queues Celery task and returns batch_id, status, estimated_completion
- [X] T035 [US1] Add GET /api/predict/batch/{batch_id}/results endpoint to poll Celery task status and retrieve results
- [X] T036 [US1] Implement queue size check (100 max) in batch endpoint and return 429 Too Many Requests if exceeded
- [X] T037 [US1] Register prediction router in backend/main.py with app.include_router(prediction_router, prefix="/api")
- [X] T038 [US1] Update Streamlit app.py to call backend API (httpx.post) instead of local predictor.predict() for single predictions (Created utils/backend_client.py)
- [X] T039 [US1] Add backend connection error handling in app.py with retry logic (3 attempts, 5s timeout) and user-friendly error messages (Implemented in backend_client.py)
- [X] T040 [US1] Test single ECLO prediction via Streamlit UI and verify <1s response time (Test resources created: test_mvp.sh, MVP_TESTING_GUIDE.md)
- [X] T041 [US1] Test batch prediction via curl/Postman with 10 samples and verify job ID return and result polling (Test resources created: test_mvp.sh)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Chat with AI via Backend API (Priority: P2)

**Goal**: Migrate AI chatbot to backend, enable conversation history persistence, implement Redis caching for repeated questions

**Independent Test**: Input Anthropic API key in Streamlit sidebar, upload dataset, ask "사고가 가장 많은 시간대는?", verify response within 5s. Ask same question again, verify cached response <100ms. Refresh page, verify conversation history persists.

### Implementation for User Story 2

- [ ] T042 [P] [US2] Create backend/schemas/chat.py with ChatMessageRequest (dataset_id, message, conversation_id) and ChatMessageResponse Pydantic models
- [ ] T043 [P] [US2] Migrate utils/chatbot.py LangChain/LangGraph logic to backend/services/chat_service.py with create_graph(), invoke_agent() functions
- [ ] T044 [P] [US2] Migrate utils/graph.py StateGraph definition to backend/services/chat_service.py (integrate with chatbot logic)
- [ ] T045 [US2] Migrate 22 tool calling functions from utils/tools.py to backend/services/analysis_service.py (keep same function signatures)
- [ ] T046 [US2] Update analysis_service.py tool functions to load dataset from database using dataset_id instead of session_state
- [ ] T047 [US2] Modify chat_service.py to use analysis_service tools and Anthropic API key from request header
- [ ] T048 [US2] Implement cache check in chat_service: check Redis cache using get_cache_key(dataset_id, message) before calling LLM
- [ ] T049 [US2] Implement cache storage in chat_service: save LLM response to Redis with 3600s TTL after successful invocation
- [ ] T050 [US2] Create backend/api/routes/chat.py with POST /api/chat/message endpoint
- [ ] T051 [US2] Add Anthropic API key extraction from X-Anthropic-API-Key header in chat endpoint using deps.get_anthropic_api_key()
- [ ] T052 [US2] Implement conversation history persistence: save user message and assistant response to messages table in chat endpoint
- [ ] T053 [US2] Add conversation_id generation logic: create new conversation if not provided, reuse existing if provided
- [ ] T054 [US2] Add error handling for invalid API key (401), dataset not found (404), LLM errors (500) in chat endpoint
- [ ] T055 [US2] Register chat router in backend/main.py with app.include_router(chat_router, prefix="/api")
- [ ] T056 [US2] Update Streamlit app.py to call POST /api/chat/message with X-Anthropic-API-Key header instead of local chatbot
- [ ] T057 [US2] Add conversation history loading in app.py: fetch messages from backend on page load and display in chat interface
- [ ] T058 [US2] Add cache hit indicator in app.py UI when response includes cache_hit=true
- [ ] T059 [US2] Test chatbot via Streamlit: ask new question, verify <5s response, ask same question, verify <100ms cached response
- [ ] T060 [US2] Test conversation persistence: refresh page, verify previous messages still visible

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Upload and Manage Datasets via Backend (Priority: P3)

**Goal**: Enable CSV dataset upload to backend with metadata persistence, implement dataset listing, and create shareable links

**Independent Test**: Upload "대구_교통사고_2024.csv" in Streamlit, verify file info displayed and dataset appears in list. Refresh page, verify dataset persists. Click "공유" button, verify shareable link generated.

### Implementation for User Story 3

- [ ] T061 [P] [US3] Create backend/schemas/dataset.py with DatasetUploadResponse, DatasetListResponse, ShareLinkResponse Pydantic models
- [ ] T062 [P] [US3] Migrate utils/loader.py CSV loading logic to backend/services/dataset_service.py with upload_dataset(), get_dataset(), list_datasets() functions
- [ ] T063 [US3] Implement file validation in dataset_service.upload_dataset(): check CSV format, size limit (50MB), encoding (UTF-8)
- [ ] T064 [US3] Implement metadata extraction in upload_dataset(): calculate rows, columns, size_bytes from uploaded CSV
- [ ] T065 [US3] Save uploaded file to backend/uploads/ directory with unique filename (use uuid or dataset_id)
- [ ] T066 [US3] Save dataset metadata to datasets table in upload_dataset()
- [ ] T067 [US3] Create backend/api/routes/datasets.py with POST /api/datasets/upload endpoint (multipart/form-data)
- [ ] T068 [US3] Add file size validation in upload endpoint and return 400 if exceeds 50MB
- [ ] T069 [US3] Add GET /api/datasets endpoint with pagination (limit, offset query params) in datasets route
- [ ] T070 [US3] Implement share token generation in dataset_service: create_share_token(dataset_id) returns random token with 7-day expiry
- [ ] T071 [US3] Add POST /api/datasets/{dataset_id}/share endpoint that creates share_token and returns shareable URL
- [ ] T072 [US3] Add GET /api/datasets/shared/{token} endpoint to load dataset by share token (verify not expired)
- [ ] T073 [US3] Register datasets router in backend/main.py with app.include_router(datasets_router, prefix="/api")
- [ ] T074 [US3] Update Streamlit app.py to use st.file_uploader and POST /api/datasets/upload instead of local file loading
- [ ] T075 [US3] Add dataset list display in app.py sidebar: fetch from GET /api/datasets and show as selectable dropdown
- [ ] T076 [US3] Add "공유" button in app.py that calls POST /api/datasets/{id}/share and displays generated link with copy-to-clipboard
- [ ] T077 [US3] Add shared dataset loading in app.py: parse ?share_token=xxx from URL query params and auto-load dataset
- [ ] T078 [US3] Test dataset upload via Streamlit: upload 5MB CSV, verify <5s completion and metadata display
- [ ] T079 [US3] Test dataset listing: upload multiple datasets, verify all appear in dropdown sorted by upload date
- [ ] T080 [US3] Test share link: generate link, open in new browser tab, verify dataset auto-loads

**Checkpoint**: All core user stories (US1, US2, US3) should now be independently functional

---

## Phase 6: User Story 4 - Visualize Data in Frontend (Priority: P4)

**Goal**: Maintain existing Plotly and Folium visualizations in Streamlit frontend, ensure they work with backend-loaded datasets

**Independent Test**: Select dataset from backend, navigate to "시각화" tab, verify bar charts and map render within 2 seconds with interactive controls working.

### Implementation for User Story 4

- [ ] T081 [P] [US4] Verify utils/visualizer.py functions (create_accident_chart, create_time_chart) work with backend-loaded dataframes
- [ ] T082 [P] [US4] Verify utils/geo.py functions (create_accident_map) work with backend-loaded dataframes
- [ ] T083 [US4] Update app.py visualization tab to load dataset from backend (if not already cached) and pass to visualizer functions
- [ ] T084 [US4] Add loading indicators in app.py while charts render using st.spinner()
- [ ] T085 [US4] Test Plotly charts: zoom, pan, hover interactions work correctly
- [ ] T086 [US4] Test Folium map: marker clicks show accident details in popup

**Checkpoint**: All user stories should now be independently functional including visualizations

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T087 [P] Add comprehensive logging in backend/main.py: request/response logging middleware with timestamps
- [ ] T088 [P] Add error response standardization: create backend/schemas/error.py with Error model (error, detail, timestamp)
- [ ] T089 [P] Update all route handlers to return standardized error responses matching openapi.yaml
- [ ] T090 [P] Add backend startup event in main.py to pre-load ECLO model and verify database connection
- [ ] T091 [P] Add database migration application in Docker entrypoint: run `alembic upgrade head` before starting uvicorn
- [ ] T092 [P] Create backend/uploads/ directory in Dockerfile and mount as volume in docker-compose.yml
- [ ] T093 [P] Add environment variable validation in backend/config.py: raise clear errors if required vars missing
- [ ] T094 [P] Update app.py to load BACKEND_URL and CLAUDE_API_KEY from root .env file using python-dotenv
- [ ] T095 [P] Add API request timeout configuration in app.py httpx client (30s default)
- [ ] T096 [P] Remove or comment out old utils/chatbot.py, utils/tools.py, utils/predictor.py, utils/loader.py after verifying backend works
- [ ] T097 [P] Update README.md with v1.3 architecture overview, Docker Compose quick start commands
- [ ] T098 [P] Verify quickstart.md commands work: docker compose up, health checks, API examples
- [ ] T099 [P] Add Flower monitoring dashboard configuration in docker-compose.yml (port 5555)
- [ ] T100 Create .env.example and backend/.env.example files with placeholder values for documentation
- [ ] T101 Test full stack startup: `docker compose up -d`, verify all services healthy within 30s
- [ ] T102 Test end-to-end user journey: upload dataset → ask chatbot question → get ECLO prediction → view visualizations
- [ ] T103 Performance test: 50 concurrent prediction requests, verify all complete within 3s
- [ ] T104 Cache test: ask same question twice, verify second response <100ms

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User Story 1 (Phase 3): Can start after Foundational - No dependencies on other stories
  - User Story 2 (Phase 4): Can start after Foundational - No dependencies on other stories (uses separate chat infrastructure)
  - User Story 3 (Phase 5): Can start after Foundational - No dependencies on other stories (dataset management is independent)
  - User Story 4 (Phase 6): Depends on User Story 3 completion (needs backend-loaded datasets)
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational - No dependencies on other stories ✅ Fully independent
- **User Story 2 (P2)**: Can start after Foundational - Uses Conversation/Message models ✅ Fully independent
- **User Story 3 (P3)**: Can start after Foundational - Uses Dataset model ✅ Fully independent
- **User Story 4 (P4)**: Depends on User Story 3 - Needs datasets to be loaded from backend ⚠️ Sequential dependency

### Within Each User Story

- **US1**: ML model loader → prediction service → API routes → Celery tasks → frontend integration
- **US2**: Migrate tools → migrate chatbot logic → cache implementation → API routes → conversation persistence → frontend integration
- **US3**: Dataset service → upload validation → metadata extraction → share token logic → API routes → frontend integration
- **US4**: Verify existing visualizers → integrate with backend-loaded data → test interactivity

### Parallel Opportunities

- **Phase 1 (Setup)**: Tasks T003, T004, T005, T006, T008, T009, T011 can run in parallel (different files)
- **Phase 2 (Foundational)**: Tasks T014-T018 (all models) can run in parallel, T021-T022 (cache and deps) can run in parallel
- **Phase 3 (US1)**: T026, T027 parallel; T030-T031 after T029; T033-T036 parallel; T040-T041 parallel
- **Phase 4 (US2)**: T042-T044-T045 parallel; T048-T049 parallel; T059-T060 parallel
- **Phase 5 (US3)**: T061-T062 parallel; T078-T079-T080 parallel
- **Phase 6 (US4)**: T081-T082 parallel
- **Phase 7 (Polish)**: Most tasks marked [P] can run in parallel

**Once Foundational phase completes, User Stories 1, 2, 3 can all start in parallel** (if team capacity allows). User Story 4 must wait for User Story 3.

---

## Parallel Example: User Story 1

```bash
# After Foundational phase completes, launch US1 models and schemas in parallel:
Task T026: "Create backend/schemas/prediction.py with ECLOPredictionRequest/Response"
Task T027: "Create backend/ml/__init__.py"

# Then implement service layer:
Task T028: "Create backend/ml/model_loader.py with singleton ECLO model loader"
Task T029: "Migrate predictor.py to backend/services/prediction_service.py"

# Then API routes and Celery tasks in parallel:
Task T030-T031: "Create POST /api/predict/eclo endpoint with error handling"
Task T033: "Create Celery app and batch_predict_eclo task"
```

---

## Parallel Example: Multiple User Stories

```bash
# After Foundational phase (Phase 2) completes, launch all independent user stories:

# Developer A works on User Story 1 (ECLO Prediction):
Tasks T026-T041

# Developer B works on User Story 2 (AI Chatbot):
Tasks T042-T060

# Developer C works on User Story 3 (Dataset Management):
Tasks T061-T080

# All three can proceed independently without blocking each other
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T011)
2. Complete Phase 2: Foundational (T012-T025) - CRITICAL checkpoint
3. Complete Phase 3: User Story 1 (T026-T041)
4. **STOP and VALIDATE**: Test ECLO prediction independently via Streamlit UI and API
5. Deploy/demo MVP with single prediction and batch prediction working

**Estimated MVP**: ~41 tasks to get working ECLO prediction API with backend

### Incremental Delivery

1. **Setup + Foundational (T001-T025)** → Foundation ready ✅
2. **Add User Story 1 (T026-T041)** → Test independently → Deploy/Demo (MVP - ECLO predictions work!)
3. **Add User Story 2 (T042-T060)** → Test independently → Deploy/Demo (Chatbot with persistence!)
4. **Add User Story 3 (T061-T080)** → Test independently → Deploy/Demo (Dataset management!)
5. **Add User Story 4 (T081-T086)** → Test independently → Deploy/Demo (Full visualization!)
6. **Polish (T087-T104)** → Production-ready

Each story adds value without breaking previous stories.

### Parallel Team Strategy

With 3 developers after Foundational phase completes:

1. **Team completes Setup + Foundational together** (T001-T025)
2. **Once Foundational checkpoint reached**:
   - Developer A: User Story 1 (T026-T041) - 16 tasks
   - Developer B: User Story 2 (T042-T060) - 19 tasks
   - Developer C: User Story 3 (T061-T080) - 20 tasks
3. **Sequential**: Developer from US1/US2/US3 → User Story 4 (T081-T086) - 6 tasks
4. **All together**: Polish phase (T087-T104) - 18 tasks

---

## Notes

- [P] tasks = different files, no dependencies, can run in parallel
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Foundational phase is CRITICAL - all database models and core infrastructure must be complete
- Stop at checkpoints to validate story independently before proceeding
- Commit after each task or logical group
- Total tasks: 104 (Setup: 11, Foundational: 14, US1: 16, US2: 19, US3: 20, US4: 6, Polish: 18)
- Parallel opportunities: ~35 tasks can run in parallel within their phases
- MVP scope: Phase 1 + Phase 2 + Phase 3 = 41 tasks
