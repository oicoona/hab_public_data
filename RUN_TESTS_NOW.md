# Run Phase 4 Tests - Quick Guide

Docker is not available in the Claude Code environment, so please run these tests on your local machine.

## Step-by-Step Testing Instructions

### Step 1: Start Docker Services (2 minutes)

Open your terminal and run:

```bash
cd /home/sk/hab_public_data

# Start all services
docker compose up -d

# Wait for services to be ready (watch for "Application startup complete")
docker compose logs -f backend
```

**Press Ctrl+C when you see:**
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 2: Verify Services (30 seconds)

```bash
# Check all services are running
docker compose ps

# All should show "Up (healthy)"
```

```bash
# Test backend health
curl http://localhost:8000/health

# Expected: {"status":"healthy","timestamp":"..."}
```

### Step 3: Run Automated Tests (1 minute)

```bash
# Set your Anthropic API key
export ANTHROPIC_API_KEY='sk-ant-your-actual-key-here'

# Run the test script
./test_phase4.sh
```

**Expected Output:**
```
======================================
Phase 4: AI Chatbot Testing Script
======================================

Test 1: Backend Health Check
-------------------------------------
✅ Backend is healthy

Test 2: New Chat Message
-------------------------------------
Response time: 2.85s
Cache hit: false
Conversation ID: 1
✅ Response time <5s
✅ Cache hit = false (expected for new message)

Test 3: Cached Message
-------------------------------------
Response time: 0.05s
Cache hit: true
✅ Response time <100ms
✅ Cache hit = true (expected for cached message)

Test 4: Conversation History
-------------------------------------
Messages in conversation: 4
✅ Conversation history persisted (4 messages)

======================================
Phase 4 Testing Complete
======================================
```

### Step 4: Test Streamlit UI (2 minutes)

In a **new terminal**:

```bash
# Start Streamlit
streamlit run app.py

# Browser should open automatically at http://localhost:8501
```

**In the browser:**

1. Click on **"💬 데이터 질의응답"** tab
2. In the **sidebar**, enter your Anthropic API key
3. Ask: **"안녕하세요! 당신은 누구인가요?"**
4. Observe:
   - Spinner shows "AI가 생각하고 있습니다..."
   - Response appears
   - Caption shows: "응답 시간: X.XXs"
   - NO ⚡ icon (not cached)

5. Ask the **SAME question** again: **"안녕하세요! 당신은 누구인가요?"**
6. Observe:
   - Much faster response
   - Caption shows: **"⚡ 캐시된 응답 (응답 시간: 0.0Xs초)"**
   - ⚡ icon IS shown

### Step 5: Verify Database (Optional, 1 minute)

```bash
# Check conversation was saved
docker compose exec postgres psql -U postgres -d hab_public_data -c "SELECT COUNT(*) FROM conversations;"

# Should show at least 1

# Check messages were saved
docker compose exec postgres psql -U postgres -d hab_public_data -c "SELECT COUNT(*) FROM messages;"

# Should show at least 4 (2 user + 2 assistant)
```

### Step 6: Verify Redis Cache (Optional, 1 minute)

```bash
# Connect to Redis
docker compose exec redis redis-cli

# Check cache keys
KEYS "chat:*"

# Should show at least 1 key

# Check TTL (time-to-live)
TTL "chat:general:XXX"  # Use actual key from above

# Should show a number between 0-3600 (seconds)

# Exit
EXIT
```

## ✅ Success Checklist

Mark these as you test:

- [ ] Docker Compose started successfully
- [ ] Backend health check returns "healthy"
- [ ] Automated test script passes all 4 tests
- [ ] Streamlit UI loads without errors
- [ ] First question responds in <5 seconds
- [ ] Second (same) question responds in <100ms
- [ ] Cache indicator (⚡) shows on second response
- [ ] Database has conversations and messages
- [ ] Redis has cache keys with TTL

## 📊 Record Your Results

**Test 1 - New Message:**
- Response time: ________ seconds (target: <5s)
- Cache hit: false ✓ / true ✗

**Test 2 - Cached Message:**
- Response time: ________ seconds (target: <0.1s)
- Cache hit: true ✓ / false ✗

**Test 3 - Streamlit UI:**
- First question time: ________ seconds
- Second question time: ________ seconds
- Cache indicator shown: Yes ✓ / No ✗

## 🐛 If Tests Fail

**Error: "ANTHROPIC_API_KEY environment variable not set"**
```bash
export ANTHROPIC_API_KEY='your-key-here'
```

**Error: "Backend health check failed"**
```bash
# Check logs
docker compose logs backend

# Restart if needed
docker compose restart backend
```

**Error: "Connection refused" or "Cannot connect"**
```bash
# Make sure services are running
docker compose up -d

# Wait 30 seconds for startup
sleep 30
```

**Error: Test script shows cache_hit=false on second message**
```bash
# Check Redis is running
docker compose ps redis

# Test Redis connection
docker compose exec redis redis-cli PING
# Should return: PONG
```

## 📝 Report Results

After testing, please report:

1. **Did automated tests pass?** (Yes/No)
2. **Response times:**
   - New message: ___ seconds
   - Cached message: ___ seconds
3. **Did Streamlit UI work?** (Yes/No)
4. **Was cache indicator shown?** (Yes/No)
5. **Any errors?** (Describe if any)

## ➡️ Next Steps

**If all tests PASS ✅:**
- Phase 4 is complete!
- Ready to proceed to Phase 5: Dataset Management

**If tests FAIL ❌:**
- Share the error messages
- I'll help troubleshoot
- Then retry

---

**Estimated Total Time: 5-7 minutes**

Start now and let me know the results!
