"""Configuration module for loading settings from environment variables."""

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

load_dotenv()

# Path to tokens.yaml, relative to this file
TOKENS_YAML_PATH = Path(__file__).parent / "tokens.yaml"


def load_tokens_config(path: Path | None = None) -> dict[str, Any]:
    """Load token definitions from tokens.yaml.

    Args:
        path: Optional path to tokens.yaml. Defaults to TOKENS_YAML_PATH.

    Returns:
        Dictionary of token definitions keyed by token ID.
    """
    yaml_path = path or TOKENS_YAML_PATH
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    tokens = data.get("tokens", {})
    required_fields = {"symbol", "name", "decimals", "addresses"}
    for token_id, token_def in tokens.items():
        missing = required_fields - set(token_def)
        if missing:
            raise ValueError(f"Token '{token_id}' missing required fields: {missing}")
    return tokens


# Loaded once at import time (same pattern as `settings = Settings()` below)
_tokens_config: dict[str, Any] = load_tokens_config()


def get_available_tokens(network: str) -> list[dict[str, Any]]:
    """Get tokens available on the given network.

    Args:
        network: Network name (e.g. "base", "base-sepolia").

    Returns:
        List of token info dicts with id, symbol, name, decimals, address.
    """
    all_tokens = _tokens_config
    result = []
    for token_id, token_def in all_tokens.items():
        addresses = token_def.get("addresses", {})
        if network in addresses:
            result.append(
                {
                    "id": token_id,
                    "symbol": token_def["symbol"],
                    "name": token_def["name"],
                    "decimals": token_def["decimals"],
                    "address": addresses[network],
                }
            )
    return result


def get_token_by_id(token_id: str, network: str) -> dict[str, Any] | None:
    """Look up a specific token by ID and network.

    Args:
        token_id: Token identifier (e.g. "usdc", "kii").
        network: Network name (e.g. "base", "base-sepolia").

    Returns:
        Token info dict, or None if not found on the given network.
    """
    all_tokens = _tokens_config
    token_def = all_tokens.get(token_id)
    if not token_def:
        return None
    addresses = token_def.get("addresses", {})
    if network not in addresses:
        return None
    return {
        "id": token_id,
        "symbol": token_def["symbol"],
        "name": token_def["name"],
        "decimals": token_def["decimals"],
        "address": addresses[network],
    }


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self) -> None:
        """Initialize settings from environment variables."""
        # Application settings
        self.app_name: str = os.getenv("APP_NAME", "Payment Link Service")
        self.app_logo: str = os.getenv("APP_LOGO", "/static/logo.png")
        self.app_host: str = os.getenv("APP_HOST", "0.0.0.0")
        self.app_port: int = int(os.getenv("APP_PORT", "8000"))
        self.app_base_url: str = os.getenv("APP_BASE_URL", "http://localhost:8000")

        # x402 Payment settings
        # Valid networks: base-sepolia (testnet), base (mainnet)
        self.network: str = os.getenv("NETWORK", "base-sepolia")
        self.facilitator_url: str = os.getenv(
            "FACILITATOR_URL", "https://x402f1.secondstate.io"
        )
        self.max_timeout_seconds: int = int(os.getenv("MAX_TIMEOUT_SECONDS", "60"))

        # Chain settings
        self.chain_id: int = int(os.getenv("CHAIN_ID", "84532"))
        self.explorer_url: str = os.getenv(
            "EXPLORER_URL", "https://sepolia.basescan.org/tx/"
        )

        # Database settings
        self.database_path: str = os.getenv("DATABASE_PATH", "payments.db")


settings = Settings()
