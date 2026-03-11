# Payment Link Service

A Python web service for creating x402-protected payment links. This service allows you to generate unique payment URLs that require cryptocurrency payments before granting access. Supports multiple networks and ERC-3009 tokens (USDC, KII, etc.) via a configurable `tokens.yaml`.

## Quick Start with Docker

1. **Configure environment:**

```bash
cp .env.example .env
# Edit .env to set DEFAULT_NETWORK (must exist in tokens.yaml)
# Edit tokens.yaml to add/remove networks and tokens
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

Networks and tokens are defined in `tokens.yaml`. All networks listed are available simultaneously — each payment link is bound to a specific network at creation time.

Format:

```yaml
networks:
  base:
    chain_id: 8453
    explorer_url: "https://basescan.org/tx/"
    facilitator_url: "https://x402f1.secondstate.io"
  base-sepolia:
    chain_id: 84532
    explorer_url: "https://sepolia.basescan.org/tx/"
    facilitator_url: "https://x402f1.secondstate.io"

tokens:
  usdc:
    symbol: USDC
    name: USD Coin
    decimals: 6
    addresses:
      base:
        address: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
        name: "USD Coin"
      base-sepolia:
        address: "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
        name: "USDC"
```

Each address entry includes an `address` and a `name` (the on-chain EIP-712 contract name used for signing). Tokens without an address on a given network are automatically excluded from that network's token list.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEFAULT_NETWORK` | `base-sepolia` | Default network for new payment links (must exist in `tokens.yaml`) |
| `APP_BASE_URL` | `http://localhost:8000` | Public base URL for generated payment links |
| `APP_NAME` | `Payment Link Service` | Service name displayed in payment UI |
| `APP_LOGO` | `/static/logo.png` | Logo URL for payment UI |
| `MAX_TIMEOUT_SECONDS` | `60` | Payment timeout in seconds |
| `DATABASE_PATH` | `payments.db` | SQLite database file path |

## API Endpoints

### GET /

Serves the web UI for creating and paying payment links.

Open in a browser to access the interactive payment interface.

---

### GET /config

Returns all available networks with their tokens and chain configuration.

```json
{
  "defaultNetwork": "base-sepolia",
  "networks": [
    {
      "name": "base-sepolia",
      "chainId": 84532,
      "explorerUrl": "https://sepolia.basescan.org/tx/",
      "facilitatorUrl": "https://x402f1.secondstate.io",
      "tokens": [
        {
          "id": "usdc",
          "symbol": "USDC",
          "name": "USD Coin",
          "decimals": 6,
          "address": "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
        }
      ]
    }
  ]
}
```

---

### GET /create-payment-link

Creates a new payment link with a unique ID.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `amount` | float | Yes | — | Payment amount (must be > 0) |
| `receiver` | string | Yes | — | Blockchain address to receive the payment |
| `token` | string | No | `usdc` | Token ID (e.g. `usdc`, `kii`) |
| `network` | string | No | `DEFAULT_NETWORK` | Network name (e.g. `base`, `base-sepolia`) |

**Example Request:**
```bash
curl "http://localhost:8000/create-payment-link?amount=0.01&receiver=0x1234567890abcdef1234567890abcdef12345678&token=usdc&network=base-sepolia"
```

**Response:**
```json
{
  "payment_id": "550e8400-e29b-41d4-a716-446655440000",
  "payment_url": "http://localhost:8000/pay/550e8400-e29b-41d4-a716-446655440000",
  "amount": "0.01",
  "receiver": "0x1234567890abcdef1234567890abcdef12345678",
  "token": "usdc",
  "network": "base-sepolia"
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
  "receiver": "0x1234567890abcdef1234567890abcdef12345678",
  "token": "usdc",
  "tokenSymbol": "USDC",
  "network": "base-sepolia",
  "explorerUrl": "https://sepolia.basescan.org/tx/",
  "paid": false,
  "tx": null
}
```

**Response (Paid):**
```json
{
  "payment_id": "550e8400-e29b-41d4-a716-446655440000",
  "amount": 0.01,
  "receiver": "0x1234567890abcdef1234567890abcdef12345678",
  "token": "usdc",
  "tokenSymbol": "USDC",
  "network": "base-sepolia",
  "explorerUrl": "https://sepolia.basescan.org/tx/",
  "paid": true,
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
curl "http://localhost:8000/create-payment-link?amount=0.01&receiver=0x1234567890abcdef1234567890abcdef12345678&token=usdc&network=base-sepolia"
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

This service supports any ERC-3009 (TransferWithAuthorization) token on Base / Base Sepolia.
