#!/bin/bash

# Railway Traffic Management API - cURL Test Scripts
# Test all endpoints with realistic data

BASE_URL="http://localhost:8000"
TOKEN=""

echo "🚂 Railway Traffic Management API - cURL Tests"
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print test results
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ PASS${NC}: $2"
    else
        echo -e "${RED}❌ FAIL${NC}: $2"
    fi
}

# Function to extract token from login response
extract_token() {
    echo "$1" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4
}

echo -e "\n${BLUE}1. Health Check Tests${NC}"
echo "-------------------"

# Test root endpoint
echo "Testing root endpoint..."
curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/" | grep -q "200"
print_result $? "Root endpoint"

# Test health check
echo "Testing health check..."
curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/health" | grep -q "200"
print_result $? "Health check endpoint"

# Test database check
echo "Testing database check..."
curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/db-check" | grep -q "200"
print_result $? "Database check endpoint"

echo -e "\n${BLUE}2. Authentication Tests${NC}"
echo "---------------------"

# Test demo credentials endpoint
echo "Getting demo credentials..."
DEMO_RESPONSE=$(curl -s "$BASE_URL/api/auth/demo-credentials")
echo "Demo credentials response: $DEMO_RESPONSE"

# Test login with demo credentials
echo "Testing login..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "employee_id": "CTR001",
    "password": "password_CTR001"
  }')

if echo "$LOGIN_RESPONSE" | grep -q "access_token"; then
    TOKEN=$(extract_token "$LOGIN_RESPONSE")
    print_result 0 "Login with valid credentials"
    echo "Token extracted: ${TOKEN:0:20}..."
else
    print_result 1 "Login with valid credentials"
    echo "Login response: $LOGIN_RESPONSE"
fi

# Test invalid login
echo "Testing invalid login..."
INVALID_LOGIN=$(curl -s -w "%{http_code}" -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "employee_id": "INVALID",
    "password": "wrong_password"
  }')

echo "$INVALID_LOGIN" | grep -q "401"
print_result $? "Login with invalid credentials (should fail)"

# Test get current controller (requires token)
if [ -n "$TOKEN" ]; then
    echo "Testing get current controller..."
    curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/auth/me" \
      -H "Authorization: Bearer $TOKEN" | grep -q "200"
    print_result $? "Get current controller info"
    
    # Test token validation
    echo "Testing token validation..."
    curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/auth/validate-token" \
      -H "Authorization: Bearer $TOKEN" | grep -q "200"
    print_result $? "Token validation"
fi

echo -e "\n${BLUE}3. Position Tracking Tests${NC}"
echo "-------------------------"

# Test single position update
echo "Testing single position update..."
POSITION_RESPONSE=$(curl -s -w "%{http_code}" -X POST "$BASE_URL/api/trains/position" \
  -H "Content-Type: application/json" \
  -d '{
    "train_id": 1,
    "section_id": 1,
    "coordinates": {
      "latitude": 40.7128,
      "longitude": -74.0060,
      "altitude": 10.0
    },
    "speed_kmh": 85.5,
    "heading": 45.0,
    "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)'",
    "distance_from_start": 150.0,
    "signal_strength": 95,
    "gps_accuracy": 2.5
  }')

echo "$POSITION_RESPONSE" | grep -q "200"
print_result $? "Single position update"

# Test bulk position update (requires authentication)
if [ -n "$TOKEN" ]; then
    echo "Testing bulk position update..."
    BULK_RESPONSE=$(curl -s -w "%{http_code}" -X POST "$BASE_URL/api/trains/position/bulk" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $TOKEN" \
      -d '{
        "positions": [
          {
            "train_id": 1,
            "section_id": 2,
            "coordinates": {
              "latitude": 40.7589,
              "longitude": -73.9851
            },
            "speed_kmh": 90.0,
            "heading": 90.0,
            "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)'"
          },
          {
            "train_id": 2,
            "section_id": 3,
            "coordinates": {
              "latitude": 40.7505,
              "longitude": -73.9934
            },
            "speed_kmh": 75.0,
            "heading": 180.0,
            "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)'"
          }
        ]
      }')
    
    echo "$BULK_RESPONSE" | grep -q "200"
    print_result $? "Bulk position update"
fi

# Test get train position
echo "Testing get train position..."
curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/trains/1/position" | grep -q "200"
print_result $? "Get train position"

# Test get train position history
echo "Testing get train position history..."
curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/trains/1/position/history?hours=1&limit=10" | grep -q "200"
print_result $? "Get train position history"

echo -e "\n${BLUE}4. Section Status Tests${NC}"
echo "---------------------"

if [ -n "$TOKEN" ]; then
    # Test get sections status
    echo "Testing get sections status..."
    curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/sections/status" \
      -H "Authorization: Bearer $TOKEN" | grep -q "200"
    print_result $? "Get sections status"
    
    # Test get specific section status
    echo "Testing get specific section status..."
    curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/sections/1/status" \
      -H "Authorization: Bearer $TOKEN" | grep -q "200"
    print_result $? "Get specific section status"
    
    # Test get section occupancy history
    echo "Testing get section occupancy history..."
    curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/sections/1/occupancy-history?hours=24" \
      -H "Authorization: Bearer $TOKEN" | grep -q "200"
    print_result $? "Get section occupancy history"
    
    # Test list sections
    echo "Testing list sections..."
    curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/sections/" \
      -H "Authorization: Bearer $TOKEN" | grep -q "200"
    print_result $? "List sections"
fi

echo -e "\n${BLUE}5. WebSocket Tests${NC}"
echo "----------------"

# Test WebSocket stats
echo "Testing WebSocket stats..."
curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/ws/stats" | grep -q "200"
print_result $? "WebSocket statistics"

echo -e "\n${BLUE}6. Performance Tests${NC}"
echo "------------------"

# Test performance metrics
echo "Testing performance metrics..."
curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/performance" | grep -q "200"
print_result $? "Performance metrics"

# Test system info
echo "Testing system info..."
curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/system-info" | grep -q "200"
print_result $? "System information"

echo -e "\n${BLUE}7. Error Handling Tests${NC}"
echo "---------------------"

# Test non-existent train
echo "Testing non-existent train position..."
curl -s -w "%{http_code}" "$BASE_URL/api/trains/99999/position" | grep -q "404"
print_result $? "Non-existent train (should return 404)"

# Test invalid coordinates
echo "Testing invalid coordinates..."
INVALID_COORDS=$(curl -s -w "%{http_code}" -X POST "$BASE_URL/api/trains/position" \
  -H "Content-Type: application/json" \
  -d '{
    "train_id": 1,
    "section_id": 1,
    "coordinates": {
      "latitude": 91.0,
      "longitude": -74.0060
    },
    "speed_kmh": 80.0,
    "heading": 45.0
  }')

echo "$INVALID_COORDS" | grep -q "422"
print_result $? "Invalid coordinates (should return 422)"

# Test unauthorized access
echo "Testing unauthorized access..."
curl -s -w "%{http_code}" "$BASE_URL/api/auth/me" | grep -q "401"
print_result $? "Unauthorized access (should return 401)"

echo -e "\n${BLUE}8. Rate Limiting Tests${NC}"
echo "--------------------"

echo "Testing rate limiting (sending multiple requests)..."
RATE_LIMIT_PASSED=0
for i in {1..5}; do
    RESPONSE=$(curl -s -w "%{http_code}" -X POST "$BASE_URL/api/trains/position" \
      -H "Content-Type: application/json" \
      -d '{
        "train_id": 1,
        "section_id": 1,
        "coordinates": {
          "latitude": 40.7128,
          "longitude": -74.0060
        },
        "speed_kmh": 80.0,
        "heading": 45.0
      }')
    
    if echo "$RESPONSE" | grep -q "200"; then
        RATE_LIMIT_PASSED=$((RATE_LIMIT_PASSED + 1))
    fi
    sleep 0.1
done

if [ $RATE_LIMIT_PASSED -ge 3 ]; then
    print_result 0 "Rate limiting (allowing reasonable requests)"
else
    print_result 1 "Rate limiting (too restrictive)"
fi

echo -e "\n${YELLOW}Test Summary${NC}"
echo "============"
echo "All cURL tests completed!"
echo "Check the results above for any failures."
echo ""
echo "To run individual tests:"
echo "  curl $BASE_URL/api/health"
echo "  curl -X POST $BASE_URL/api/auth/login -H 'Content-Type: application/json' -d '{\"employee_id\":\"CTR001\",\"password\":\"password_CTR001\"}'"
echo "  curl $BASE_URL/api/trains/1/position"
echo ""
echo "For WebSocket testing, use the websocket_test.py script."