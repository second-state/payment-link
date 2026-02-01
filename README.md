# Payment Link Service

A Python web service for creating x402-protected payment links. This service allows you to generate unique payment URLs that require cryptocurrency payments before granting access.

## Quick Start with Docker

1. **Configure environment:**

```bash
cp .env.example .env
# Edit .env with your wallet address and settings
```

2. **Build the image:**

```bash
docker build -t payment-link .
```

3. **Run the container:**

```bash
touch payments.db
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/payments.db:/app/payments.db \
  --env-file .env \
  --name payment-link \
  payment-link
```

The `touch` command creates an empty database file, and the `-v` flag mounts it into the container for persistence.

4. **Verify it's running:**

```bash
curl http://localhost:8000/
```

## Configuration

Configure the service using environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `PAY_TO_ADDRESS` | `0xYourWalletAddress` | Wallet address to receive payments |
| `NETWORK` | `base-sepolia` | Blockchain network (`base-sepolia` for testnet, `base` for mainnet) |
| `APP_BASE_URL` | `http://localhost:8000` | Public base URL for generated payment links |
| `APP_NAME` | `Payment Link Service` | Service name displayed in payment UI |
| `APP_LOGO` | `/static/logo.png` | Logo URL for payment UI |
| `FACILITATOR_URL` | `https://x402f1.secondstate.io` | x402 facilitator service endpoint |
| `MAX_TIMEOUT_SECONDS` | `60` | Payment timeout in seconds |
| `DATABASE_PATH` | `/data/payments.db` | SQLite database file path |

## API Endpoints

### GET /

Health check endpoint.

**Response:**
```json
{
  "service": "Payment Link Service",
  "status": "running"
}
```

---

### GET /create-payment-link

Creates a new payment link with a unique ID.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `amount` | float | Yes | Payment amount in USD (must be > 0) |

**Example Request:**
```bash
curl "http://localhost:8000/create-payment-link?amount=0.01"
```

**Response:**
```json
{
  "payment_id": "550e8400-e29b-41d4-a716-446655440000",
  "payment_url": "http://localhost:8000/pay/550e8400-e29b-41d4-a716-446655440000",
  "amount": "0.01"
}
```

---

### GET /pay/{payment_id}

x402-protected payment endpoint. This endpoint handles the payment flow.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `payment_id` | string | Unique payment identifier from `/create-payment-link` |

**Behavior:**

1. **If payment is pending (no X-Payment header):** Returns HTTP 402 with payment requirements
2. **If payment is pending (with valid X-Payment header):** Processes payment and returns success
3. **If payment is already completed:** Returns the transaction details

**Response (Payment Required - 402):**

For API clients (non-browser):
```json
{
  "x402Version": 1,
  "accepts": [...],
  "error": "No X-PAYMENT header provided"
}
```

For browsers: Returns an HTML payment page.

**Response (Payment Successful - 200):**
```json
{
  "status": "paid",
  "tx": "0x1234567890abcdef..."
}
```

**Response (Not Found - 404):**
```json
{
  "error": "Payment not found"
}
```

---

### GET /status/{payment_id}

Check the current status of a payment.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `payment_id` | string | Unique payment identifier |

**Example Request:**
```bash
curl "http://localhost:8000/status/550e8400-e29b-41d4-a716-446655440000"
```

**Response (Pending):**
```json
{
  "payment_id": "550e8400-e29b-41d4-a716-446655440000",
  "amount": 0.01,
  "status": "pending",
  "tx": null
}
```

**Response (Paid):**
```json
{
  "payment_id": "550e8400-e29b-41d4-a716-446655440000",
  "amount": 0.01,
  "status": "paid",
  "tx": "0x1234567890abcdef..."
}
```

**Response (Not Found - 404):**
```json
{
  "error": "Payment not found"
}
```

## Usage Example

1. **Create a payment link:**

```bash
curl "http://localhost:8000/create-payment-link?amount=0.01"
```

2. **Share the `payment_url` with the payer.** When they open it in a browser, they'll see a payment interface.

3. **After payment, the payer can reload the page** to see the confirmation with the transaction hash.

4. **Check payment status programmatically:**

```bash
curl "http://localhost:8000/status/{payment_id}"
```

## Development Setup

For local development without Docker:

1. **Install dependencies:**

```bash
uv sync
```

2. **Configure environment:**

```bash
cp .env.example .env
# Edit .env with your settings
```

3. **Run the server:**

```bash
uv run python main.py
```

4. **Run tests:**

```bash
uv run pytest tests/ -v
```

## How x402 Works

The [x402 protocol](https://github.com/coinbase/x402) enables HTTP-native payments:

1. Client requests a protected resource
2. Server responds with HTTP 402 and payment requirements
3. Client makes a blockchain payment and includes proof in the `X-Payment` header
4. Server verifies the payment and grants access

This service uses USDC on Base (or Base Sepolia for testing) for payments.
