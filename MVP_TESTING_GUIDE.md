# MVP Testing Guide: User Story 1 - ECLO Prediction

## Prerequisites

- Docker 24+ installed
- Docker Compose 2.20+ installed
- 8GB+ RAM available
- Ports 5432, 6379, 8000, 8501, 5555 available

## Quick Start

### 1. Start the Stack

```bash
# From project root
docker compose up -d
```

This will start:
- **postgres**: PostgreSQL 15 database (port 5432)
- **redis**: Redis 7 cache (port 6379)
- **backend**: FastAPI server (port 8000)
- **celery-worker**: Celery worker for batch processing
- **flower**: Celery monitoring (port 5555)
- **streamlit**: Streamlit UI (port 8501)

### 2. Wait for Services to Start

```bash
# Watch logs
docker compose logs -f

# Or check service status
docker compose ps
```

Wait until you see:
- Backend: "Application startup complete"
- Celery: "celery@<hostname> ready"
- Streamlit: "You can now view your Streamlit app"

### 3. Verify Services are Healthy

```bash
# Backend health check
curl http://localhost:8000/health

# Streamlit health check
curl http://localhost:8501/_stcore/health
```

Expected output from backend:
```json
{
  "status": "healthy",
  "timestamp": "2024-12-10T..."
}
```

### 4. Run Automated Tests

```bash
# Make sure jq is installed (for JSON parsing)
sudo apt-get install jq  # Ubuntu/Debian
brew install jq          # macOS

# Run test script
./test_mvp.sh
```

## Manual Testing

### Test 1: Single ECLO Prediction via API

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

**Expected Response:**
```json
{
  "eclo": 0.23,
  "interpretation": "일반",
  "detail": "일반적인 사고 수준입니다. 경상 가능성이 있으며, 치료가 필요할 수 있습니다.",
  "prediction_id": null,
  "model_version": "v1.0",
  "timestamp": "2024-12-10T..."
}
```

**Success Criteria:**
- ✓ Response time < 1 second
- ✓ ECLO value is a float
- ✓ Interpretation is one of: 경미, 일반, 심각, 매우 심각
- ✓ Detail contains Korean explanation

### Test 2: Batch ECLO Prediction

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
      },
      {
        "weather": "비",
        "road_surface": "젖음/습기",
        "road_type": "단일로",
        "accident_type": "차대사람",
        "time_period": "밤",
        "district": "남구",
        "day_of_week": "금요일",
        "accident_hour": 22,
        "accident_year": 2024,
        "accident_month": 12,
        "accident_day": 10
      }
    ]
  }'
```

**Expected Response (202 Accepted):**
```json
{
  "batch_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "processing",
  "total": 2,
  "results_url": "/api/predict/batch/{batch_id}/results",
  "estimated_completion": "2024-12-10T..."
}
```

**Poll for results:**
```bash
# Replace {batch_id} with actual batch_id from response
curl http://localhost:8000/api/predict/batch/{batch_id}/results
```

**Success Criteria:**
- ✓ Returns 202 status immediately
- ✓ batch_id is a valid UUID
- ✓ Polling returns status: pending → processing → success
- ✓ Results contain predictions for all accidents

### Test 3: Error Handling

```bash
# Test invalid weather value
curl -X POST http://localhost:8000/api/predict/eclo \
  -H "Content-Type: application/json" \
  -d '{
    "weather": "INVALID",
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

**Expected Response (400 Bad Request):**
```json
{
  "detail": {
    "error": "Invalid input",
    "message": "'INVALID'은(는) '기상상태'의 유효한 값이 아닙니다...",
    "timestamp": "2024-12-10T..."
  }
}
```

**Success Criteria:**
- ✓ Returns 400 status code
- ✓ Error message clearly explains the problem
- ✓ Lists valid values

### Test 4: Queue Limit

```bash
# Test batch size limit (>100)
# Create a JSON file with 101 accidents
python3 << 'PYEOF'
import json

accident = {
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

payload = {"accidents": [accident] * 101}
print(json.dumps(payload))
PYEOF > /tmp/large_batch.json

curl -X POST http://localhost:8000/api/predict/eclo/batch \
  -H "Content-Type: application/json" \
  -d @/tmp/large_batch.json
```

**Expected Response (429 Too Many Requests):**
```json
{
  "detail": {
    "error": "Queue full",
    "message": "Batch size exceeds limit. Maximum 100 predictions allowed, got 101.",
    "timestamp": "2024-12-10T..."
  }
}
```

### Test 5: Via Streamlit UI

1. Open http://localhost:8501
2. Navigate to ECLO prediction section
3. Input accident conditions
4. Click "예측" button
5. Verify result displays within 1 second

**Success Criteria:**
- ✓ UI loads without errors
- ✓ Prediction completes in <1s
- ✓ Result shows ECLO value and interpretation
- ✓ Error messages are user-friendly if backend is down

### Test 6: FastAPI Documentation

1. Open http://localhost:8000/docs
2. Try out the `/api/predict/eclo` endpoint
3. Verify Swagger UI works correctly

## Monitoring

### View Celery Tasks
- Open http://localhost:5555
- Check active workers
- Monitor task queue

### View Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f celery-worker

# Last 100 lines
docker compose logs --tail=100 backend
```

### Database Inspection
```bash
# Connect to PostgreSQL
docker compose exec postgres psql -U postgres -d hab_public_data

# List tables
\dt

# Check if models are created (after migration)
SELECT * FROM datasets LIMIT 1;
```

### Redis Inspection
```bash
# Connect to Redis
docker compose exec redis redis-cli

# Check cache keys
KEYS "chat:*"

# Check cached data
GET "chat:some_key"
```

## Troubleshooting

### Backend not starting

```bash
# Check logs
docker compose logs backend

# Common issues:
# 1. Port 8000 already in use
# 2. Model files not found
# 3. Database connection failed
```

### Model files missing

```bash
# Verify model directory is mounted
docker compose exec backend ls -la /app/model/

# Expected files:
# - accident_lgbm_model.pkl
# - label_encoders.pkl
# - feature_config.json
```

### Database connection failed

```bash
# Check PostgreSQL is running
docker compose ps postgres

# Test connection
docker compose exec backend python -c "from backend.db.session import engine; print(engine.connect())"
```

### Redis connection failed

```bash
# Check Redis is running
docker compose ps redis

# Test connection
docker compose exec backend python -c "from backend.core.cache import redis_client; print(redis_client.ping())"
```

### Celery tasks not processing

```bash
# Check celery worker logs
docker compose logs celery-worker

# Check Flower dashboard
open http://localhost:5555

# Restart celery worker
docker compose restart celery-worker
```

## Performance Benchmarks

### Success Criteria from Spec

| Metric | Target | Test Command |
|--------|--------|--------------|
| Single prediction | <1s average, <2s 90th percentile | `time curl -X POST ...` |
| Batch 50 concurrent | All complete in <3s | `ab -n 50 -c 50 ...` |
| Batch 100 predictions | Complete in <2 minutes | Monitor via Flower |

### Load Testing

```bash
# Install Apache Bench
sudo apt-get install apache2-utils

# Test 50 concurrent requests
ab -n 50 -c 50 -p payload.json -T application/json \
  http://localhost:8000/api/predict/eclo
```

## Cleanup

```bash
# Stop all services
docker compose down

# Stop and remove volumes (WARNING: deletes data)
docker compose down -v

# Remove images
docker compose down --rmi all
```

## Next Steps

After successful MVP testing:

1. ✅ Mark T040 and T041 as complete in tasks.md
2. 🚀 Proceed with Phase 4: AI Chatbot (US2)
3. 🚀 Proceed with Phase 5: Dataset Management (US3)
4. 📝 Document any issues or improvements needed

## Expected Test Results

When running `./test_mvp.sh`, you should see:

```
===================================
MVP Test: User Story 1 - ECLO Prediction
===================================

Test 1: Checking service health...
-----------------------------------
Backend (/health): ✓ PASS
Streamlit (/health): ✓ PASS
Flower: ✓ PASS

Test 2: Single ECLO Prediction
-----------------------------------
✓ PASS - Prediction successful
ECLO Value: 0.23
Interpretation: 일반

Test 3: Batch ECLO Prediction (3 samples)
-----------------------------------
✓ PASS - Batch submitted
Batch ID: a1b2c3d4-...
✓ PASS - Batch processing complete

Test 4: Polling batch results
-----------------------------------
Status: success
✓ PASS - Batch processing complete

Test 5: Error Handling (Invalid Input)
-----------------------------------
✓ PASS - Error handling works correctly

===================================
MVP Test Summary
===================================

✓ All critical tests passed!
```
