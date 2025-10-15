#!/bin/bash

# Controller Action API Test Suite
# Production-ready cURL commands for testing all endpoints

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# API Base URL
BASE_URL="${API_URL:-http://localhost:8000}"
TOKEN=""

# Print colored output
print_header() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}→ $1${NC}"
}

# ============================================================================
# AUTHENTICATION
# ============================================================================

test_login() {
    print_header "1. AUTHENTICATION TEST"
    
    print_info "Logging in as CTR001..."
    
    RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/login" \
      -H "Content-Type: application/json" \
      -d '{
        "employee_id": "CTR001",
        "password": "railway123"
      }')
    
    TOKEN=$(echo $RESPONSE | jq -r '.access_token')
    
    if [ "$TOKEN" != "null" ] && [ -n "$TOKEN" ]; then
        print_success "Login successful"
        print_info "Token: ${TOKEN:0:50}..."
        echo ""
        echo "$RESPONSE" | jq '.'
    else
        print_error "Login failed"
        echo "$RESPONSE" | jq '.'
        exit 1
    fi
    
    echo ""
}

# ============================================================================
# GET ACTIVE CONFLICTS
# ============================================================================

test_active_conflicts() {
    print_header "2. GET ACTIVE CONFLICTS TEST"
    
    print_info "Fetching active conflicts..."
    
    RESPONSE=$(curl -s -X GET "$BASE_URL/api/conflicts/active" \
      -H "Authorization: Bearer $TOKEN")
    
    TOTAL=$(echo $RESPONSE | jq -r '.total_conflicts')
    
    if [ "$TOTAL" != "null" ]; then
        print_success "Retrieved $TOTAL active conflicts"
        echo ""
        echo "$RESPONSE" | jq '.'
    else
        print_error "Failed to fetch active conflicts"
        echo "$RESPONSE" | jq '.'
    fi
    
    echo ""
}

# ============================================================================
# RESOLVE CONFLICT - ACCEPT
# ============================================================================

test_resolve_conflict_accept() {
    print_header "3. RESOLVE CONFLICT - ACCEPT TEST"
    
    # First, get an active conflict ID
    CONFLICTS=$(curl -s -X GET "$BASE_URL/api/conflicts/active" \
      -H "Authorization: Bearer $TOKEN")
    
    CONFLICT_ID=$(echo $CONFLICTS | jq -r '.conflicts[0].id')
    
    if [ "$CONFLICT_ID" = "null" ] || [ -z "$CONFLICT_ID" ]; then
        print_info "No active conflicts to resolve"
        echo ""
        return
    fi
    
    print_info "Resolving conflict $CONFLICT_ID (Accept AI recommendation)..."
    
    RESPONSE=$(curl -s -X POST "$BASE_URL/api/conflicts/$CONFLICT_ID/resolve" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{
        "action": "accept",
        "solution_id": "ai_solution_test",
        "rationale": "AI recommendation is optimal for current traffic conditions and provides best resolution path"
      }')
    
    SUCCESS=$(echo $RESPONSE | jq -r '.success')
    
    if [ "$SUCCESS" = "true" ]; then
        print_success "Conflict resolved successfully"
        echo ""
        echo "$RESPONSE" | jq '.'
    else
        print_error "Failed to resolve conflict"
        echo "$RESPONSE" | jq '.'
    fi
    
    echo ""
}

# ============================================================================
# RESOLVE CONFLICT - MODIFY
# ============================================================================

test_resolve_conflict_modify() {
    print_header "4. RESOLVE CONFLICT - MODIFY TEST"
    
    # Get another conflict
    CONFLICTS=$(curl -s -X GET "$BASE_URL/api/conflicts/active" \
      -H "Authorization: Bearer $TOKEN")
    
    CONFLICT_ID=$(echo $CONFLICTS | jq -r '.conflicts[1].id')
    
    if [ "$CONFLICT_ID" = "null" ] || [ -z "$CONFLICT_ID" ]; then
        print_info "No additional conflicts to resolve"
        echo ""
        return
    fi
    
    print_info "Resolving conflict $CONFLICT_ID (Modify AI recommendation)..."
    
    RESPONSE=$(curl -s -X POST "$BASE_URL/api/conflicts/$CONFLICT_ID/resolve" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{
        "action": "modify",
        "solution_id": "ai_solution_test",
        "modifications": {
          "train_actions": [
            {
              "train_id": 1,
              "action": "delay",
              "parameters": {
                "delay_minutes": 10
              }
            }
          ]
        },
        "rationale": "Extended delay from 5 to 10 minutes based on current weather conditions and reduced visibility"
      }')
    
    SUCCESS=$(echo $RESPONSE | jq -r '.success')
    
    if [ "$SUCCESS" = "true" ]; then
        print_success "Conflict resolved with modifications"
        echo ""
        echo "$RESPONSE" | jq '.'
    else
        print_error "Failed to resolve conflict"
        echo "$RESPONSE" | jq '.'
    fi
    
    echo ""
}

# ============================================================================
# TRAIN CONTROL - DELAY
# ============================================================================

test_train_control_delay() {
    print_header "5. TRAIN CONTROL - DELAY TEST"
    
    TRAIN_ID=1
    
    print_info "Delaying train $TRAIN_ID by 15 minutes..."
    
    RESPONSE=$(curl -s -X POST "$BASE_URL/api/trains/$TRAIN_ID/control" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{
        "command": "delay",
        "parameters": {
          "delay_minutes": 15
        },
        "reason": "Track maintenance ahead requires schedule adjustment to ensure passenger safety",
        "emergency": false
      }')
    
    SUCCESS=$(echo $RESPONSE | jq -r '.success')
    
    if [ "$SUCCESS" = "true" ]; then
        print_success "Train control executed successfully"
        echo ""
        echo "$RESPONSE" | jq '.'
    else
        print_error "Failed to control train"
        echo "$RESPONSE" | jq '.'
    fi
    
    echo ""
}

# ============================================================================
# TRAIN CONTROL - PRIORITY
# ============================================================================

test_train_control_priority() {
    print_header "6. TRAIN CONTROL - PRIORITY TEST"
    
    TRAIN_ID=2
    
    print_info "Changing train $TRAIN_ID priority to 9..."
    
    RESPONSE=$(curl -s -X POST "$BASE_URL/api/trains/$TRAIN_ID/control" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{
        "command": "priority",
        "parameters": {
          "new_priority": 9
        },
        "reason": "Critical passenger transport with VIP passengers requiring elevated priority status",
        "emergency": false
      }')
    
    SUCCESS=$(echo $RESPONSE | jq -r '.success')
    
    if [ "$SUCCESS" = "true" ]; then
        print_success "Priority changed successfully"
        echo ""
        echo "$RESPONSE" | jq '.'
    else
        print_error "Failed to change priority"
        echo "$RESPONSE" | jq '.'
    fi
    
    echo ""
}

# ============================================================================
# TRAIN CONTROL - REROUTE
# ============================================================================

test_train_control_reroute() {
    print_header "7. TRAIN CONTROL - REROUTE TEST"
    
    TRAIN_ID=3
    
    print_info "Rerouting train $TRAIN_ID..."
    
    RESPONSE=$(curl -s -X POST "$BASE_URL/api/trains/$TRAIN_ID/control" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{
        "command": "reroute",
        "parameters": {
          "new_route": [2, 3, 4, 5]
        },
        "reason": "Original route unavailable due to scheduled maintenance work on primary track section",
        "emergency": false
      }')
    
    SUCCESS=$(echo $RESPONSE | jq -r '.success')
    
    if [ "$SUCCESS" = "true" ]; then
        print_success "Train rerouted successfully"
        echo ""
        echo "$RESPONSE" | jq '.'
    else
        print_error "Failed to reroute train"
        echo "$RESPONSE" | jq '.'
    fi
    
    echo ""
}

# ============================================================================
# LOG DECISION
# ============================================================================

test_log_decision() {
    print_header "8. LOG CONTROLLER DECISION TEST"
    
    print_info "Logging manual decision..."
    
    RESPONSE=$(curl -s -X POST "$BASE_URL/api/decisions/log" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{
        "train_id": 1,
        "action_taken": "delay",
        "rationale": "Manual delay decision to prevent section overload during peak hours based on real-time traffic analysis",
        "parameters": {
          "delay_minutes": 10,
          "original_schedule": "10:30",
          "new_schedule": "10:40"
        },
        "outcome": "Successfully prevented conflict. Train departed at 10:41 with minimal passenger impact."
      }')
    
    SUCCESS=$(echo $RESPONSE | jq -r '.success')
    
    if [ "$SUCCESS" = "true" ]; then
        print_success "Decision logged successfully"
        echo ""
        echo "$RESPONSE" | jq '.'
    else
        print_error "Failed to log decision"
        echo "$RESPONSE" | jq '.'
    fi
    
    echo ""
}

# ============================================================================
# QUERY AUDIT TRAIL
# ============================================================================

test_audit_trail() {
    print_header "9. QUERY AUDIT TRAIL TEST"
    
    print_info "Querying recent decisions..."
    
    RESPONSE=$(curl -s -X GET "$BASE_URL/api/audit/decisions?limit=10&executed_only=true" \
      -H "Authorization: Bearer $TOKEN")
    
    TOTAL=$(echo $RESPONSE | jq -r '.total_records')
    
    if [ "$TOTAL" != "null" ]; then
        print_success "Retrieved $TOTAL audit records"
        echo ""
        echo "$RESPONSE" | jq '.'
    else
        print_error "Failed to query audit trail"
        echo "$RESPONSE" | jq '.'
    fi
    
    echo ""
}

# ============================================================================
# PERFORMANCE METRICS
# ============================================================================

test_performance_metrics() {
    print_header "10. PERFORMANCE METRICS TEST"
    
    print_info "Fetching performance metrics..."
    
    RESPONSE=$(curl -s -X GET "$BASE_URL/api/audit/performance" \
      -H "Authorization: Bearer $TOKEN")
    
    TOTAL_DECISIONS=$(echo $RESPONSE | jq -r '.total_decisions')
    
    if [ "$TOTAL_DECISIONS" != "null" ]; then
        print_success "Retrieved performance metrics"
        echo ""
        echo "$RESPONSE" | jq '.'
    else
        print_error "Failed to fetch performance metrics"
        echo "$RESPONSE" | jq '.'
    fi
    
    echo ""
}

# ============================================================================
# RATE LIMIT TEST
# ============================================================================

test_rate_limit() {
    print_header "11. RATE LIMITING TEST"
    
    print_info "Testing rate limits (sending 12 requests rapidly)..."
    
    SUCCESS_COUNT=0
    RATE_LIMITED_COUNT=0
    
    for i in {1..12}; do
        RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/conflicts/active" \
          -H "Authorization: Bearer $TOKEN")
        
        HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
        
        if [ "$HTTP_CODE" = "200" ]; then
            ((SUCCESS_COUNT++))
        elif [ "$HTTP_CODE" = "429" ]; then
            ((RATE_LIMITED_COUNT++))
        fi
        
        sleep 0.1
    done
    
    print_info "Successful requests: $SUCCESS_COUNT"
    print_info "Rate limited requests: $RATE_LIMITED_COUNT"
    
    if [ $RATE_LIMITED_COUNT -gt 0 ]; then
        print_success "Rate limiting working correctly"
    else
        print_info "No rate limiting triggered (might need more requests)"
    fi
    
    echo ""
}

# ============================================================================
# AUTHORIZATION TEST
# ============================================================================

test_authorization() {
    print_header "12. AUTHORIZATION TEST"
    
    print_info "Testing unauthorized access (no token)..."
    
    RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/conflicts/active")
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    
    if [ "$HTTP_CODE" = "401" ] || [ "$HTTP_CODE" = "403" ]; then
        print_success "Authorization protection working correctly"
    else
        print_error "Authorization not working as expected (HTTP $HTTP_CODE)"
    fi
    
    echo ""
}

# ============================================================================
# VALIDATION TEST
# ============================================================================

test_validation() {
    print_header "13. INPUT VALIDATION TEST"
    
    print_info "Testing invalid input (delay with negative value)..."
    
    RESPONSE=$(curl -s -X POST "$BASE_URL/api/trains/1/control" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{
        "command": "delay",
        "parameters": {
          "delay_minutes": -5
        },
        "reason": "Test invalid input",
        "emergency": false
      }')
    
    # Check if error is returned
    ERROR=$(echo $RESPONSE | jq -r '.detail // empty')
    
    if [ -n "$ERROR" ]; then
        print_success "Validation working correctly (rejected invalid input)"
    else
        print_error "Validation not working as expected"
    fi
    
    echo ""
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

main() {
    clear
    
    print_header "CONTROLLER ACTION API TEST SUITE"
    echo ""
    print_info "API Base URL: $BASE_URL"
    echo ""
    
    # Check dependencies
    if ! command -v jq &> /dev/null; then
        print_error "jq is not installed. Please install jq to run this script."
        exit 1
    fi
    
    if ! command -v curl &> /dev/null; then
        print_error "curl is not installed. Please install curl to run this script."
        exit 1
    fi
    
    # Run tests
    test_login
    sleep 1
    
    test_active_conflicts
    sleep 1
    
    test_resolve_conflict_accept
    sleep 1
    
    test_resolve_conflict_modify
    sleep 1
    
    test_train_control_delay
    sleep 1
    
    test_train_control_priority
    sleep 1
    
    test_train_control_reroute
    sleep 1
    
    test_log_decision
    sleep 1
    
    test_audit_trail
    sleep 1
    
    test_performance_metrics
    sleep 1
    
    test_rate_limit
    sleep 1
    
    test_authorization
    sleep 1
    
    test_validation
    
    print_header "TEST SUITE COMPLETE"
    echo ""
}

# Show usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -u, --url URL       Set API base URL (default: http://localhost:8000)"
    echo "  -h, --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                  # Run with default settings"
    echo "  $0 -u http://api.railway.com        # Run with custom API URL"
    echo "  API_URL=http://localhost:8000 $0    # Run with environment variable"
    echo ""
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--url)
            BASE_URL="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Run main
main
