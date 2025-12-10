# Phase 4 Testing Guide: AI Chatbot with Backend

**Purpose**: Verify that the AI chatbot backend integration works correctly with proper performance.

**Performance Targets**:
- ✅ New question: <5s response time
- ✅ Cached question: <100ms response time
- ✅ Conversation persistence: Messages saved to PostgreSQL
- ✅ Cache hit indicator: Shows in UI

---

## Prerequisites

- Docker and Docker Compose installed
- Anthropic API key (starts with `sk-ant-`)
- Ports available: 5432, 6379, 8000, 8501, 5555

---

## Test 1: Start and Verify Backend Services

### 1.1 Start Docker Compose

```bash
# From project root
docker compose up -d

# Expected output:
# ✔ Container hab_public_data-postgres-1       Started
# ✔ Container hab_public_data-redis-1          Started
# ✔ Container hab_public_data-backend-1        Started
# ✔ Container hab_public_data-celery-worker-1  Started
# ✔ Container hab_public_data-flower-1         Started
# ✔ Container hab_public_data-streamlit-1      Started
```

### 1.2 Wait for Services to Start

```bash
# Watch logs until you see "Application startup complete"
docker compose logs -f backend

# Look for:
# backend-1  | INFO:     Application startup complete.
# backend-1  | INFO:     Uvicorn running on http://0.0.0.0:8000

# Press Ctrl+C to exit logs
```

### 1.3 Check Service Health

```bash
# Test backend health
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","timestamp":"2024-12-10T..."}
```

```bash
# Check all services status
docker compose ps

# Expected output: All services should be "Up"
# NAME                              STATUS
# hab_public_data-backend-1         Up
# hab_public_data-celery-worker-1   Up
# hab_public_data-flower-1          Up
# hab_public_data-postgres-1        Up
# hab_public_data-redis-1           Up
# hab_public_data-streamlit-1       Up
```

**✅ PASS CRITERIA**: All services showing "Up (healthy)"

---

## Test 2: Backend Chat API - New Message (No Cache)

### 2.1 Send First Chat Message

**Important**: Replace `YOUR_API_KEY` with your actual Anthropic API key!

```bash
curl -X POST http://localhost:8000/api/chat/message \
  -H "Content-Type: application/json" \
  -H "X-Anthropic-API-Key: YOUR_API_KEY" \
  -d '{
    "dataset_id": null,
    "message": "안녕하세요! 오늘 날씨가 어떤가요?",
    "conversation_id": null
  }' | jq '.'
```

### 2.2 Expected Response

```json
{
  "conversation_id": 1,
  "message_id": 2,
  "content": "안녕하세요! 저는 AI 데이터 분석 전문가입니다...",
  "cache_hit": false,
  "timestamp": "2024-12-10T12:34:56.789Z",
  "usage": {
    "input_tokens": 0,
    "output_tokens": 0
  }
}
```

**✅ PASS CRITERIA**:
- Status code: 200 OK
- `cache_hit`: false
- `conversation_id`: integer (save this for next test)
- `content`: non-empty string
- Response time: <5 seconds

### 2.3 Measure Response Time

```bash
# Use time command to measure
time curl -X POST http://localhost:8000/api/chat/message \
  -H "Content-Type: application/json" \
  -H "X-Anthropic-API-Key: YOUR_API_KEY" \
  -d '{
    "dataset_id": null,
    "message": "대구에 대해 알려주세요",
    "conversation_id": null
  }' -o /dev/null -s -w "%{time_total}s\n"

# Expected: < 5.0s
```

---

## Test 3: Backend Chat API - Cached Message

### 3.1 Send Same Message Again

**Use the SAME message as Test 2.1**

```bash
curl -X POST http://localhost:8000/api/chat/message \
  -H "Content-Type: application/json" \
  -H "X-Anthropic-API-Key: YOUR_API_KEY" \
  -d '{
    "dataset_id": null,
    "message": "안녕하세요! 오늘 날씨가 어떤가요?",
    "conversation_id": 1
  }' | jq '.'
```

### 3.2 Expected Response

```json
{
  "conversation_id": 1,
  "message_id": 4,
  "content": "안녕하세요! 저는 AI 데이터 분석 전문가입니다...",
  "cache_hit": true,
  "timestamp": "2024-12-10T12:35:10.123Z",
  "usage": null
}
```

**✅ PASS CRITERIA**:
- `cache_hit`: **true** (this is critical!)
- Same `content` as Test 2
- Response time: <100ms (much faster!)

### 3.3 Measure Cached Response Time

```bash
time curl -X POST http://localhost:8000/api/chat/message \
  -H "Content-Type: application/json" \
  -H "X-Anthropic-API-Key: YOUR_API_KEY" \
  -d '{
    "dataset_id": null,
    "message": "안녕하세요! 오늘 날씨가 어떤가요?",
    "conversation_id": 1
  }' -o /dev/null -s -w "%{time_total}s\n"

# Expected: < 0.1s (100ms)
```

---

## Test 4: Verify Conversation Persistence

### 4.1 Get Conversation History

```bash
# Use conversation_id from Test 2
curl http://localhost:8000/api/chat/conversations/1/messages | jq '.'
```

### 4.2 Expected Response

```json
{
  "conversation_id": 1,
  "dataset_id": null,
  "title": "안녕하세요! 오늘 날씨가 어떤가요?",
  "messages": [
    {
      "id": 1,
      "role": "user",
      "content": "안녕하세요! 오늘 날씨가 어떤가요?",
      "created_at": "2024-12-10T12:34:56.789Z"
    },
    {
      "id": 2,
      "role": "assistant",
      "content": "안녕하세요! 저는 AI...",
      "created_at": "2024-12-10T12:34:58.123Z"
    },
    {
      "id": 3,
      "role": "user",
      "content": "안녕하세요! 오늘 날씨가 어떤가요?",
      "created_at": "2024-12-10T12:35:10.000Z"
    },
    {
      "id": 4,
      "role": "assistant",
      "content": "안녕하세요! 저는 AI...",
      "created_at": "2024-12-10T12:35:10.123Z"
    }
  ]
}
```

**✅ PASS CRITERIA**:
- All messages persisted in database
- Alternating user/assistant roles
- Timestamps in chronological order

---

## Test 5: Streamlit Frontend Integration

### 5.1 Start Streamlit

```bash
# In a separate terminal (NOT in Docker)
streamlit run app.py

# Expected output:
# You can now view your Streamlit app in your browser.
# Local URL: http://localhost:8501
```

### 5.2 Navigate to Chat Tab

1. Open browser: http://localhost:8501
2. Click on **"💬 데이터 질의응답"** tab
3. You should see API key input warning

### 5.3 Enter API Key

1. Look at the **sidebar** (left side)
2. Find **"Anthropic API Key"** input
3. Enter your API key (starts with `sk-ant-`)
4. Click outside the input to save

### 5.4 Upload a Dataset (Optional for General Chat)

**Note**: Phase 4 chatbot works in "general mode" without datasets.

For testing general questions:
- Skip dataset upload
- Chatbot will work for general questions

For testing with dataset (requires Phase 5):
- Can't test yet - dataset upload to backend not implemented
- Will work after Phase 5

---

## Test 6: Ask New Question in Streamlit

### 6.1 Send First Question

1. In the chat input at bottom, type:
   ```
   안녕하세요! 당신은 누구인가요?
   ```

2. Press Enter

3. **Observe**:
   - Spinner: "AI가 생각하고 있습니다..."
   - Response appears
   - **Response time** shown at bottom (e.g., "응답 시간: 3.24초")

**✅ PASS CRITERIA**:
- Response time: <5 seconds
- NO cache indicator (⚡) shown
- Response content makes sense

### 6.2 Ask Same Question Again

1. Type the **exact same question**:
   ```
   안녕하세요! 당신은 누구인가요?
   ```

2. Press Enter

3. **Observe**:
   - Spinner (very brief)
   - Response appears much faster
   - **Cache indicator**: "⚡ 캐시된 응답 (응답 시간: 0.05초)"

**✅ PASS CRITERIA**:
- Response time: <0.1 seconds (100ms)
- Cache indicator (⚡) SHOWN
- Same response as first question

---

## Test 7: Conversation Persistence (Refresh)

### 7.1 Note Current Messages

- Count how many messages you have
- Note the last message content

### 7.2 Refresh Page

- Press F5 or click refresh button
- Go to "💬 데이터 질의응답" tab again

### 7.3 Expected Behavior

**Current (Phase 4)**:
- ❌ Messages NOT shown (session-based storage)
- ✅ Conversation ID preserved in backend
- ✅ New message continues same conversation

**After Phase 5**:
- ✅ Messages WILL be loaded from backend
- Full conversation history persisted

**✅ PASS CRITERIA** (Phase 4):
- Can send new messages
- Backend conversation continues (same conversation_id)
- No errors

---

## Test 8: Verify Redis Caching

### 8.1 Check Redis Cache Keys

```bash
# Connect to Redis
docker compose exec redis redis-cli

# List all chat cache keys
KEYS "chat:*"

# Expected output:
# 1) "chat:general:5d41402abc4b2a76b9719d911017c592"
# 2) "chat:general:098f6bcd4621d373cade4e832627b4f6"
```

### 8.2 Check Cache Content

```bash
# Get cached response (use a key from above)
GET "chat:general:5d41402abc4b2a76b9719d911017c592"

# Expected: Full AI response text
```

### 8.3 Check Cache TTL

```bash
# Check time-to-live (should be ~3600s = 1 hour)
TTL "chat:general:5d41402abc4b2a76b9719d911017c592"

# Expected: number between 0 and 3600
# If returns -1, key exists but has no expiry (BUG!)
# If returns -2, key doesn't exist

# Exit Redis CLI
EXIT
```

**✅ PASS CRITERIA**:
- Cache keys exist for asked questions
- TTL is set (not -1)
- Cached content matches AI response

---

## Test 9: Database Verification

### 9.1 Check Conversations Table

```bash
# Connect to PostgreSQL
docker compose exec postgres psql -U postgres -d hab_public_data

# Query conversations
SELECT id, dataset_id, title, created_at FROM conversations;

# Expected output:
#  id | dataset_id |          title          |         created_at
# ----+------------+-------------------------+----------------------------
#   1 |            | 안녕하세요! 오늘...    | 2024-12-10 12:34:56.789
```

### 9.2 Check Messages Table

```sql
-- Get all messages for conversation 1
SELECT id, conversation_id, role,
       LEFT(content, 50) as content_preview,
       created_at
FROM messages
WHERE conversation_id = 1
ORDER BY created_at;

-- Expected: All user and assistant messages
```

### 9.3 Exit PostgreSQL

```sql
\q
```

**✅ PASS CRITERIA**:
- Conversations exist with correct titles
- Messages alternate between user/assistant
- Timestamps are chronological

---

## Test 10: Error Handling

### 10.1 Test Invalid API Key

In Streamlit:
1. Enter invalid API key: `sk-invalid-key`
2. Try to send a message

**Expected**:
- Error message: "백엔드 API 오류: Chat API error: Invalid Anthropic API key format"
- OR 401 error from Anthropic

### 10.2 Test Backend Down

```bash
# Stop backend
docker compose stop backend

# Try to send message in Streamlit
```

**Expected**:
- Error message: "백엔드 API 오류: 챗봇 서버에 연결할 수 없습니다..."
- Info message: "백엔드 서버가 실행 중인지 확인해주세요: `docker compose up -d`"

```bash
# Restart backend
docker compose start backend
```

---

## Performance Summary Table

Fill this out during testing:

| Test | Metric | Target | Actual | Pass? |
|------|--------|--------|--------|-------|
| 1 | Services start time | <30s | _____s | ☐ |
| 2 | New question (curl) | <5s | _____s | ☐ |
| 3 | Cached question (curl) | <100ms | _____ms | ☐ |
| 5 | Conversation load | <2s | _____s | ☐ |
| 6.1 | New question (UI) | <5s | _____s | ☐ |
| 6.2 | Cached question (UI) | <100ms | _____ms | ☐ |
| 8 | Cache TTL set | 3600s | _____s | ☐ |

---

## Troubleshooting

### Issue: "Application startup complete" not appearing
**Solution**:
```bash
# Check logs for errors
docker compose logs backend

# Common issues:
# - Port 8000 already in use
# - Database connection failed
# - Redis connection failed
```

### Issue: 401 Unauthorized
**Solution**: Check API key format, must start with `sk-ant-` and be >20 characters

### Issue: Cache always shows cache_hit=false
**Solution**:
```bash
# Check Redis is running
docker compose ps redis

# Test Redis connection
docker compose exec backend python -c "from backend.core.cache import redis_client; print(redis_client.ping() if redis_client else 'No Redis')"
```

### Issue: Conversation not persisting
**Solution**:
```bash
# Check PostgreSQL
docker compose ps postgres

# Check tables exist
docker compose exec postgres psql -U postgres -d hab_public_data -c "\dt"
```

---

## Test Completion Checklist

- [ ] All services started successfully
- [ ] Backend health check passes
- [ ] New message response time <5s
- [ ] Cached message response time <100ms
- [ ] Cache hit indicator shows (⚡)
- [ ] Conversation persisted in database
- [ ] Redis cache keys created with TTL
- [ ] Streamlit UI shows responses
- [ ] Error handling works correctly

---

## Next Steps

✅ **If all tests pass**:
- Mark Phase 4 as complete
- Document any issues found
- Proceed to Phase 5: Dataset Management

❌ **If tests fail**:
- Document specific failures
- Check logs: `docker compose logs -f backend`
- Review PHASE4_COMPLETE.md for debugging tips

---

## Quick Test Script

Save this as `test_phase4.sh`:

```bash
#!/bin/bash

echo "======================================"
echo "Phase 4 Testing Script"
echo "======================================"

# Check if API key is set
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ Error: ANTHROPIC_API_KEY environment variable not set"
    echo "   Run: export ANTHROPIC_API_KEY='your-key-here'"
    exit 1
fi

echo ""
echo "Test 1: Backend Health Check"
echo "-------------------------------------"
HEALTH=$(curl -s http://localhost:8000/health | jq -r '.status')
if [ "$HEALTH" == "healthy" ]; then
    echo "✅ Backend is healthy"
else
    echo "❌ Backend health check failed"
    exit 1
fi

echo ""
echo "Test 2: New Chat Message"
echo "-------------------------------------"
START=$(date +%s.%N)
RESPONSE=$(curl -s -X POST http://localhost:8000/api/chat/message \
  -H "Content-Type: application/json" \
  -H "X-Anthropic-API-Key: $ANTHROPIC_API_KEY" \
  -d '{"dataset_id":null,"message":"테스트 메시지입니다","conversation_id":null}')
END=$(date +%s.%N)
ELAPSED=$(echo "$END - $START" | bc)

CACHE_HIT=$(echo $RESPONSE | jq -r '.cache_hit')
CONV_ID=$(echo $RESPONSE | jq -r '.conversation_id')

echo "Response time: ${ELAPSED}s"
echo "Cache hit: $CACHE_HIT"
echo "Conversation ID: $CONV_ID"

if (( $(echo "$ELAPSED < 5.0" | bc -l) )); then
    echo "✅ Response time <5s"
else
    echo "❌ Response time >5s"
fi

if [ "$CACHE_HIT" == "false" ]; then
    echo "✅ Cache hit = false (expected for new message)"
else
    echo "⚠️  Cache hit = true (unexpected for new message)"
fi

echo ""
echo "Test 3: Cached Message"
echo "-------------------------------------"
START=$(date +%s.%N)
RESPONSE2=$(curl -s -X POST http://localhost:8000/api/chat/message \
  -H "Content-Type: application/json" \
  -H "X-Anthropic-API-Key: $ANTHROPIC_API_KEY" \
  -d "{\"dataset_id\":null,\"message\":\"테스트 메시지입니다\",\"conversation_id\":$CONV_ID}")
END=$(date +%s.%N)
ELAPSED2=$(echo "$END - $START" | bc)

CACHE_HIT2=$(echo $RESPONSE2 | jq -r '.cache_hit')

echo "Response time: ${ELAPSED2}s"
echo "Cache hit: $CACHE_HIT2"

if (( $(echo "$ELAPSED2 < 0.1" | bc -l) )); then
    echo "✅ Response time <100ms"
else
    echo "❌ Response time >100ms"
fi

if [ "$CACHE_HIT2" == "true" ]; then
    echo "✅ Cache hit = true (expected for cached message)"
else
    echo "❌ Cache hit = false (should be cached!)"
fi

echo ""
echo "======================================"
echo "Phase 4 Testing Complete"
echo "======================================"
```

Make it executable and run:
```bash
chmod +x test_phase4.sh
export ANTHROPIC_API_KEY='your-key-here'
./test_phase4.sh
```
