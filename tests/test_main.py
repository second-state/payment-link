"""Tests for the payment link service."""

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from database import init_db
from main import app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI app with initialized database."""
    import asyncio

    # Initialize database using asyncio.run for Python 3.10+
    asyncio.run(init_db())

    with TestClient(app) as test_client:
        yield test_client

    # Clean up test database
    db_path = os.environ.get("DATABASE_PATH")
    if db_path and os.path.exists(db_path):
        os.remove(db_path)


def test_root_endpoint(client: TestClient) -> None:
    """Test the root endpoint returns the index.html page."""
    response = client.get("/")
    assert response.status_code == 200
    # Should return HTML content
    assert "<!DOCTYPE html>" in response.text
    assert "Payment Link Service" in response.text


def test_config_endpoint(client: TestClient) -> None:
    """Test the config endpoint returns networks and tokens configuration."""
    response = client.get("/config")
    assert response.status_code == 200
    data = response.json()
    # Check required fields are present
    assert "defaultNetwork" in data
    assert "networks" in data
    assert isinstance(data["networks"], list)
    assert len(data["networks"]) > 0
    # Each network should have required fields
    net = data["networks"][0]
    assert "name" in net
    assert "chainId" in net
    assert "explorerUrl" in net
    assert "facilitatorUrl" in net
    assert "tokens" in net
    assert isinstance(net["chainId"], int)
    # Each token should have required fields
    assert len(net["tokens"]) > 0
    token = net["tokens"][0]
    assert "id" in token
    assert "symbol" in token
    assert "name" in token
    assert "decimals" in token
    assert "address" in token
    assert isinstance(token["decimals"], int)


TEST_RECEIVER = "0x1234567890abcdef1234567890abcdef12345678"


def test_create_payment_link(client: TestClient) -> None:
    """Test creating a payment link."""
    response = client.get(f"/create-payment-link?amount=10.50&receiver={TEST_RECEIVER}")
    assert response.status_code == 200
    data = response.json()
    assert "payment_id" in data
    assert "payment_url" in data
    assert float(data["amount"]) == 10.50
    assert data["receiver"] == TEST_RECEIVER
    assert data["token"] == "usdc"
    assert "network" in data


def test_create_payment_link_with_network(client: TestClient) -> None:
    """Test creating a payment link with explicit network selection."""
    response = client.get(
        f"/create-payment-link?amount=1.00&receiver={TEST_RECEIVER}&network=base"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["network"] == "base"


def test_create_payment_link_invalid_network(client: TestClient) -> None:
    """Test creating a payment link with invalid network returns 400."""
    response = client.get(
        f"/create-payment-link?amount=1.00&receiver={TEST_RECEIVER}&network=invalid"
    )
    assert response.status_code == 400
    data = response.json()
    assert "error" in data


def test_create_payment_link_with_token(client: TestClient) -> None:
    """Test creating a payment link with explicit token selection."""
    response = client.get(
        f"/create-payment-link?amount=5.00&receiver={TEST_RECEIVER}&token=kii"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["token"] == "kii"


def test_create_payment_link_invalid_token(client: TestClient) -> None:
    """Test creating a payment link with invalid token returns 400."""
    response = client.get(
        f"/create-payment-link?amount=1.00&receiver={TEST_RECEIVER}&token=invalid"
    )
    assert response.status_code == 400
    data = response.json()
    assert "error" in data


def test_create_payment_link_invalid_amount(client: TestClient) -> None:
    """Test creating a payment link with invalid amount."""
    response = client.get(f"/create-payment-link?amount=-5&receiver={TEST_RECEIVER}")
    assert response.status_code == 422  # Validation error


def test_create_payment_link_missing_amount(client: TestClient) -> None:
    """Test creating a payment link without amount."""
    response = client.get(f"/create-payment-link?receiver={TEST_RECEIVER}")
    assert response.status_code == 422  # Missing required parameter


def test_create_payment_link_missing_receiver(client: TestClient) -> None:
    """Test creating a payment link without receiver."""
    response = client.get("/create-payment-link?amount=10.50")
    assert response.status_code == 422  # Missing required parameter


def test_pay_nonexistent_payment(client: TestClient) -> None:
    """Test paying for a nonexistent payment ID."""
    response = client.get("/pay/nonexistent-id")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data


def test_status_nonexistent_payment(client: TestClient) -> None:
    """Test checking status of a nonexistent payment."""
    response = client.get("/status/nonexistent-id")
    assert response.status_code == 404


def test_payment_flow_without_x402_header(client: TestClient) -> None:
    """Test the payment flow without x402 header returns 402."""
    # Create a payment link
    create_response = client.get(
        f"/create-payment-link?amount=0.01&receiver={TEST_RECEIVER}"
    )
    assert create_response.status_code == 200
    payment_id = create_response.json()["payment_id"]

    # Try to access without payment header
    pay_response = client.get(f"/pay/{payment_id}")
    # Should return 402 Payment Required (or 400 for browser)
    assert pay_response.status_code in [400, 402]


def test_status_after_create(client: TestClient) -> None:
    """Test checking status after creating a payment."""
    # Create a payment link
    create_response = client.get(
        f"/create-payment-link?amount=5.00&receiver={TEST_RECEIVER}"
    )
    assert create_response.status_code == 200
    payment_id = create_response.json()["payment_id"]

    # Check status
    status_response = client.get(f"/status/{payment_id}")
    assert status_response.status_code == 200
    data = status_response.json()
    assert data["payment_id"] == payment_id
    assert data["amount"] == 5.0
    assert data["paid"] is False
    assert data["tx"] is None


def test_status_returns_network_and_token_fields(client: TestClient) -> None:
    """Test that status endpoint returns network, token, and explorer fields."""
    create_response = client.get(
        f"/create-payment-link?amount=1.00&receiver={TEST_RECEIVER}"
        "&token=usdc&network=base-sepolia"
    )
    assert create_response.status_code == 200
    payment_id = create_response.json()["payment_id"]

    status_response = client.get(f"/status/{payment_id}")
    assert status_response.status_code == 200
    data = status_response.json()
    assert data["network"] == "base-sepolia"
    assert data["token"] == "usdc"
    assert data["tokenSymbol"] == "USDC"
    assert data["explorerUrl"] == "https://sepolia.basescan.org/tx/"
    assert data["receiver"] == TEST_RECEIVER


def test_status_with_explicit_network(client: TestClient) -> None:
    """Test that status returns the correct network when explicitly set."""
    create_response = client.get(
        f"/create-payment-link?amount=2.00&receiver={TEST_RECEIVER}"
        "&token=usdc&network=base"
    )
    assert create_response.status_code == 200
    payment_id = create_response.json()["payment_id"]

    status_response = client.get(f"/status/{payment_id}")
    assert status_response.status_code == 200
    data = status_response.json()
    assert data["network"] == "base"
    assert data["explorerUrl"] == "https://basescan.org/tx/"


def test_config_default_network_exists(client: TestClient) -> None:
    """Test that the defaultNetwork in config actually exists in the networks list."""
    response = client.get("/config")
    assert response.status_code == 200
    data = response.json()
    default_net = data["defaultNetwork"]
    network_names = [n["name"] for n in data["networks"]]
    assert default_net in network_names


def test_config_networks_have_tokens(client: TestClient) -> None:
    """Test that each network in config has a tokens list."""
    response = client.get("/config")
    assert response.status_code == 200
    data = response.json()
    for net in data["networks"]:
        assert "tokens" in net
        assert isinstance(net["tokens"], list)
