"""Configuration module for loading settings from environment variables."""

import os

from dotenv import load_dotenv

load_dotenv()


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
        self.pay_to_address: str = os.getenv("PAY_TO_ADDRESS", "0xYourWalletAddress")
        self.network: str = os.getenv("NETWORK", "base-sepolia")
        self.facilitator_url: str = os.getenv(
            "FACILITATOR_URL", "https://x402f1.secondstate.io"
        )
        self.max_timeout_seconds: int = int(os.getenv("MAX_TIMEOUT_SECONDS", "60"))

        # Database settings
        self.database_path: str = os.getenv("DATABASE_PATH", "payments.db")


settings = Settings()
