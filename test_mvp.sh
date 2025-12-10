#!/bin/bash
# MVP Testing Script for User Story 1 (ECLO Prediction)
# Run this after starting Docker Compose

set -e

echo "==================================="
echo "MVP Test: User Story 1 - ECLO Prediction"
echo "==================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

BACKEND_URL=${BACKEND_URL:-http://localhost:8000}
STREAMLIT_URL=${STREAMLIT_URL:-http://localhost:8501}
FLOWER_URL=${FLOWER_URL:-http://localhost:5555}

echo "Configuration:"
echo "  Backend: $BACKEND_URL"
echo "  Streamlit: $STREAMLIT_URL"
echo "  Flower: $FLOWER_URL"
echo ""

# Test 1: Check all services are running
echo "Test 1: Checking service health..."
echo "-----------------------------------"

# Backend health
echo -n "Backend (/health): "
if curl -sf $BACKEND_URL/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PASS${NC}"
    curl -s $BACKEND_URL/health | jq '.'
else
    echo -e "${RED}✗ FAIL${NC}"
    echo "Backend is not responding. Make sure 'docker compose up -d' is running."
    exit 1
fi
echo ""

# Streamlit health
echo -n "Streamlit (/health): "
if curl -sf $STREAMLIT_URL/_stcore/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PASS${NC}"
else
    echo -e "${YELLOW}⚠ WARNING${NC} - Streamlit health check failed"
fi
echo ""

# Flower (optional)
echo -n "Flower (Celery monitoring): "
if curl -sf $FLOWER_URL > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PASS${NC}"
else
    echo -e "${YELLOW}⚠ WARNING${NC} - Flower not responding"
fi
echo ""

# Test 2: Single ECLO Prediction
echo "Test 2: Single ECLO Prediction"
echo "-----------------------------------"
echo "Sending prediction request..."

RESPONSE=$(curl -s -X POST $BACKEND_URL/api/predict/eclo \
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
  }')

if echo "$RESPONSE" | jq -e '.eclo' > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PASS${NC} - Prediction successful"
    echo "$RESPONSE" | jq '.'
    
    ECLO_VALUE=$(echo "$RESPONSE" | jq -r '.eclo')
    INTERPRETATION=$(echo "$RESPONSE" | jq -r '.interpretation')
    echo ""
    echo "ECLO Value: $ECLO_VALUE"
    echo "Interpretation: $INTERPRETATION"
else
    echo -e "${RED}✗ FAIL${NC} - Prediction failed"
    echo "$RESPONSE" | jq '.'
    exit 1
fi
echo ""

# Test 3: Batch ECLO Prediction
echo "Test 3: Batch ECLO Prediction (3 samples)"
echo "-----------------------------------"
echo "Submitting batch prediction..."

BATCH_RESPONSE=$(curl -s -X POST $BACKEND_URL/api/predict/eclo/batch \
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
      },
      {
        "weather": "눈",
        "road_surface": "적설",
        "road_type": "교차로",
        "accident_type": "차량단독",
        "time_period": "새벽",
        "district": "서구",
        "day_of_week": "토요일",
        "accident_hour": 3,
        "accident_year": 2024,
        "accident_month": 1,
        "accident_day": 15
      }
    ]
  }')

if echo "$BATCH_RESPONSE" | jq -e '.batch_id' > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PASS${NC} - Batch submitted"
    echo "$BATCH_RESPONSE" | jq '.'
    
    BATCH_ID=$(echo "$BATCH_RESPONSE" | jq -r '.batch_id')
    RESULTS_URL=$(echo "$BATCH_RESPONSE" | jq -r '.results_url')
    
    echo ""
    echo "Batch ID: $BATCH_ID"
    echo "Results URL: $BACKEND_URL$RESULTS_URL"
    echo ""
    echo "Waiting 5 seconds for processing..."
    sleep 5
    
    # Test 4: Poll batch results
    echo "Test 4: Polling batch results"
    echo "-----------------------------------"
    RESULTS=$(curl -s $BACKEND_URL$RESULTS_URL)
    
    if echo "$RESULTS" | jq -e '.status' > /dev/null 2>&1; then
        STATUS=$(echo "$RESULTS" | jq -r '.status')
        echo "Status: $STATUS"
        
        if [ "$STATUS" = "success" ]; then
            echo -e "${GREEN}✓ PASS${NC} - Batch processing complete"
            echo "$RESULTS" | jq '.results'
        else
            echo -e "${YELLOW}⚠ WARNING${NC} - Batch still processing or failed"
            echo "$RESULTS" | jq '.'
        fi
    else
        echo -e "${RED}✗ FAIL${NC} - Could not retrieve results"
        echo "$RESULTS"
    fi
else
    echo -e "${RED}✗ FAIL${NC} - Batch submission failed"
    echo "$BATCH_RESPONSE" | jq '.'
fi
echo ""

# Test 5: Error handling
echo "Test 5: Error Handling (Invalid Input)"
echo "-----------------------------------"
ERROR_RESPONSE=$(curl -s -X POST $BACKEND_URL/api/predict/eclo \
  -H "Content-Type: application/json" \
  -d '{
    "weather": "INVALID_WEATHER",
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
  }')

if echo "$ERROR_RESPONSE" | jq -e '.detail.error' > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PASS${NC} - Error handling works correctly"
    echo "$ERROR_RESPONSE" | jq '.detail'
else
    echo -e "${YELLOW}⚠ WARNING${NC} - Error response format unexpected"
    echo "$ERROR_RESPONSE" | jq '.'
fi
echo ""

# Summary
echo "==================================="
echo "MVP Test Summary"
echo "==================================="
echo ""
echo -e "${GREEN}✓ All critical tests passed!${NC}"
echo ""
echo "You can now:"
echo "  1. Access FastAPI docs: $BACKEND_URL/docs"
echo "  2. Access Streamlit UI: $STREAMLIT_URL"
echo "  3. Monitor Celery tasks: $FLOWER_URL"
echo ""
echo "Next steps:"
echo "  - Test via Streamlit UI"
echo "  - Implement Phase 4 (AI Chatbot)"
echo "  - Implement Phase 5 (Dataset Management)"
