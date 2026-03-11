"""Configuration module for loading settings from environment variables."""

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

load_dotenv()

# Path to tokens.yaml, relative to this file
TOKENS_YAML_PATH = Path(__file__).parent / "tokens.yaml"

def _load_yaml(path: Path | None = None) -> dict[str, Any]:
    """Load and parse tokens.yaml."""
    yaml_path = path or TOKENS_YAML_PATH
    with open(yaml_path) as f:
        return yaml.safe_load(f)  # type: ignore[no-any-return]

def _validate_tokens(tokens: dict[str, Any]) -> dict[str, Any]:
    """Raise ValueError if any token is missing required fields."""
    required_fields = {"symbol", "name", "decimals", "addresses"}
    for token_id, token_def in tokens.items():
        missing = required_fields - set(token_def)
        if missing:
            raise ValueError(f"Token '{token_id}' missing required fields: {missing}")
    return tokens

def _validate_networks(networks: dict[str, Any]) -> dict[str, Any]:
    """Raise ValueError if any network is missing required fields."""
    required_fields = {"chain_id", "explorer_url", "facilitator_url"}
    for network_name, network_def in networks.items():
        missing = required_fields - set(network_def)
        if missing:
            raise ValueError(
                f"Network '{network_name}' missing required fields: {missing}"
            )
    return networks

def load_config(path: Path | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load and validate token and network definitions from tokens.yaml."""
    data = _load_yaml(path)
    tokens = _validate_tokens(data.get("tokens", {}))
    networks = _validate_networks(data.get("networks", {}))
    return tokens, networks

_tokens_config: dict[str, Any]
_networks_config: dict[str, Any]
_tokens_config, _networks_config = load_config()

def get_network_config(network: str) -> dict[str, Any] | None:
    """Return config for a network, or None if not found."""
    net_def = _networks_config.get(network)
    if not net_def:
        return None
    return {
        "name": network,
        "chain_id": net_def["chain_id"],
        "explorer_url": net_def["explorer_url"],
        "facilitator_url": net_def["facilitator_url"],
    }

def get_all_networks() -> list[dict[str, Any]]:
    """Return all networks with their available tokens."""
    result: list[dict[str, Any]] = []
    for network_name, net_def in _networks_config.items():
        tokens = get_available_tokens(network_name)
        result.append(
            {
                "name": network_name,
                "chainId": net_def["chain_id"],
                "explorerUrl": net_def["explorer_url"],
                "facilitatorUrl": net_def["facilitator_url"],
                "tokens": tokens,
            }
        )
    return result

def get_available_tokens(network: str) -> list[dict[str, Any]]:
    """Return tokens available on the given network."""
    result = []
    for token_id, token_def in _tokens_config.items():
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
    """Look up a token by ID on a specific network."""
    token_def = _tokens_config.get(token_id)
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
        # Application settings
        self.app_name: str = os.getenv("APP_NAME", "Payment Link Service")
        self.app_logo: str = os.getenv("APP_LOGO", "/static/logo.png")
        self.app_host: str = os.getenv("APP_HOST", "0.0.0.0")
        self.app_port: int = int(os.getenv("APP_PORT", "8000"))
        self.app_base_url: str = os.getenv("APP_BASE_URL", "http://localhost:8000")

        # x402 Payment settings
        self.default_network: str = os.getenv("DEFAULT_NETWORK", "base-sepolia")
        self.max_timeout_seconds: int = int(os.getenv("MAX_TIMEOUT_SECONDS", "60"))

        if not get_network_config(self.default_network):
            raise ValueError(
                f"DEFAULT_NETWORK '{self.default_network}' not found in tokens.yaml"
            )

        # Database settings
        self.database_path: str = os.getenv("DATABASE_PATH", "payments.db")

settings = Settings()
