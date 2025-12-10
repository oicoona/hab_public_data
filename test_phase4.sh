#!/bin/bash

echo "======================================"
echo "Phase 4: AI Chatbot Testing Script"
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
echo "Test 4: Conversation History"
echo "-------------------------------------"
HISTORY=$(curl -s http://localhost:8000/api/chat/conversations/$CONV_ID/messages | jq -r '.messages | length')

echo "Messages in conversation: $HISTORY"

if [ "$HISTORY" -ge "2" ]; then
    echo "✅ Conversation history persisted ($HISTORY messages)"
else
    echo "❌ Conversation history incomplete"
fi

echo ""
echo "======================================"
echo "Phase 4 Testing Complete"
echo "======================================"
echo ""
echo "Summary:"
echo "- Backend health: $HEALTH"
echo "- New message time: ${ELAPSED}s (target: <5s)"
echo "- Cached message time: ${ELAPSED2}s (target: <0.1s)"
echo "- Messages persisted: $HISTORY"
echo ""
echo "Next: Test Streamlit UI at http://localhost:8501"
