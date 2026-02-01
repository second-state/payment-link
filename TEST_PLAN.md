# Test Plan

This document describes how to start a local development server and manually test all API endpoints.

## Prerequisites

- Python 3.10+
- uv package manager
- curl (for testing)

## Setup

1. **Install dependencies:**

```bash
uv sync
```

2. **Configure environment:**

```bash
cp .env.example .env
```

3. **Edit `.env` to use port 8080:**

```bash
APP_PORT=8080
APP_BASE_URL=http://localhost:8080
```

## Start the Server

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8080
```

Expected output:
```
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
```

## Test Cases

Open a new terminal and run the following tests.

### Test 1: Health Check

**Request:**
```bash
curl -s http://localhost:8080/ | jq
```

**Expected Response:**
```json
{
  "service": "Payment Link Service",
  "status": "running"
}
```

**Pass Criteria:** Status code 200, response contains `"status": "running"`

---

### Test 2: Create Payment Link

**Request:**
```bash
curl -s "http://localhost:8080/create-payment-link?amount=0.01" | jq
```

**Expected Response:**
```json
{
  "payment_id": "<uuid>",
  "payment_url": "http://localhost:8080/pay/<uuid>",
  "amount": "0.01"
}
```

**Pass Criteria:**
- Status code 200
- Response contains `payment_id`, `payment_url`, and `amount`
- `payment_url` matches the format `http://localhost:8080/pay/<payment_id>`

**Save the payment_id for subsequent tests:**
```bash
PAYMENT_ID=$(curl -s "http://localhost:8080/create-payment-link?amount=0.05" | jq -r '.payment_id')
echo "Payment ID: $PAYMENT_ID"
```

---

### Test 2b: Verify Database Record

Directly query the SQLite database to confirm the payment was stored correctly.

**Request:**
```bash
sqlite3 payments.db "SELECT payment_id, amount, status, tx_hash FROM payments WHERE payment_id='$PAYMENT_ID';"
```

**Expected Output:**
```
<payment_id>|0.05|pending|
```

**Alternative (formatted output):**
```bash
sqlite3 -header -column payments.db "SELECT payment_id, amount, status, tx_hash, created_at FROM payments WHERE payment_id='$PAYMENT_ID';"
```

**Expected Output:**
```
payment_id                            amount      status      tx_hash     created_at
------------------------------------  ----------  ----------  ----------  -------------------
xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx  0.05        pending                 2024-01-01 12:00:00
```

**Pass Criteria:**
- Record exists in the database
- `amount` matches the requested amount (0.05)
- `status` is `pending`
- `tx_hash` is empty/null

**View all payments in the database:**
```bash
sqlite3 -header -column payments.db "SELECT * FROM payments;"
```

---

### Test 3: Create Payment Link - Invalid Amount

**Request:**
```bash
curl -s -w "\nHTTP Status: %{http_code}\n" "http://localhost:8080/create-payment-link?amount=-5"
```

**Expected Response:**
- HTTP Status: 422
- Response contains validation error

**Pass Criteria:** Status code 422 (Unprocessable Entity)

---

### Test 4: Create Payment Link - Missing Amount

**Request:**
```bash
curl -s -w "\nHTTP Status: %{http_code}\n" "http://localhost:8080/create-payment-link"
```

**Expected Response:**
- HTTP Status: 422
- Response contains missing parameter error

**Pass Criteria:** Status code 422 (Unprocessable Entity)

---

### Test 5: Check Payment Status (Pending)

**Request:**
```bash
curl -s "http://localhost:8080/status/$PAYMENT_ID" | jq
```

**Expected Response:**
```json
{
  "payment_id": "<uuid>",
  "amount": 0.05,
  "paid": false,
  "tx": null
}
```

**Pass Criteria:**
- Status code 200
- `paid` is `false`
- `tx` is `null`

---

### Test 6: Check Payment Status - Not Found

**Request:**
```bash
curl -s -w "\nHTTP Status: %{http_code}\n" "http://localhost:8080/status/nonexistent-id"
```

**Expected Response:**
```json
{
  "error": "Payment not found"
}
```

**Pass Criteria:** Status code 404

---

### Test 7: Access Payment Endpoint (No Payment Header)

**Request:**
```bash
curl -s -w "\nHTTP Status: %{http_code}\n" "http://localhost:8080/pay/$PAYMENT_ID"
```

**Expected Response:**
- HTTP Status: 402
- Response contains x402 payment requirements with `accepts` array

**Pass Criteria:** Status code 402 (Payment Required)

---

### Test 8: Access Payment Endpoint - Not Found

**Request:**
```bash
curl -s -w "\nHTTP Status: %{http_code}\n" "http://localhost:8080/pay/nonexistent-id"
```

**Expected Response:**
```json
{
  "error": "Payment not found"
}
```

**Pass Criteria:** Status code 404

---

### Test 9: Browser Request to Payment Endpoint

**Request:**
```bash
curl -s -w "\nHTTP Status: %{http_code}\n" \
  -H "Accept: text/html" \
  -H "User-Agent: Mozilla/5.0" \
  "http://localhost:8080/pay/$PAYMENT_ID"
```

**Expected Response:**
- HTTP Status: 400
- Response contains HTML payment page

**Pass Criteria:** Status code 400, response is HTML content

---

## Automated Test Suite

Run the automated tests:

```bash
uv run pytest tests/ -v
```

Expected output:
```
tests/test_main.py::test_root_endpoint PASSED
tests/test_main.py::test_create_payment_link PASSED
tests/test_main.py::test_create_payment_link_invalid_amount PASSED
tests/test_main.py::test_create_payment_link_missing_amount PASSED
tests/test_main.py::test_pay_nonexistent_payment PASSED
tests/test_main.py::test_status_nonexistent_payment PASSED
tests/test_main.py::test_payment_flow_without_x402_header PASSED
tests/test_main.py::test_status_after_create PASSED

============================== 8 passed ==============================
```

## Full Test Script

Save this as `test_endpoints.sh` and run with `bash test_endpoints.sh`:

```bash
#!/bin/bash

BASE_URL="http://localhost:8080"

echo "=== Test 1: Health Check ==="
curl -s "$BASE_URL/" | jq
echo

echo "=== Test 2: Create Payment Link ==="
RESPONSE=$(curl -s "$BASE_URL/create-payment-link?amount=0.05")
echo "$RESPONSE" | jq
PAYMENT_ID=$(echo "$RESPONSE" | jq -r '.payment_id')
echo "Saved Payment ID: $PAYMENT_ID"
echo

echo "=== Test 2b: Verify Database Record ==="
sqlite3 -header -column payments.db "SELECT payment_id, amount, status, tx_hash, created_at FROM payments WHERE payment_id='$PAYMENT_ID';"
echo

echo "=== Test 3: Invalid Amount ==="
curl -s -w "HTTP Status: %{http_code}\n" "$BASE_URL/create-payment-link?amount=-5" | head -1
echo

echo "=== Test 4: Missing Amount ==="
curl -s -w "HTTP Status: %{http_code}\n" "$BASE_URL/create-payment-link" | head -1
echo

echo "=== Test 5: Check Payment Status (Pending) ==="
curl -s "$BASE_URL/status/$PAYMENT_ID" | jq
echo

echo "=== Test 6: Status Not Found ==="
curl -s -w "HTTP Status: %{http_code}\n" "$BASE_URL/status/nonexistent-id"
echo

echo "=== Test 7: Payment Endpoint (No Header) ==="
curl -s -w "\nHTTP Status: %{http_code}\n" "$BASE_URL/pay/$PAYMENT_ID" | tail -5
echo

echo "=== Test 8: Payment Not Found ==="
curl -s -w "HTTP Status: %{http_code}\n" "$BASE_URL/pay/nonexistent-id"
echo

echo "=== All manual tests completed ==="
```

## Cleanup

1. Stop the server with `Ctrl+C`
2. Remove test database (optional):

```bash
rm -f payments.db
```
