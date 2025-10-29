from __future__ import annotations

from functools import lru_cache
from typing import Literal, Optional

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict  # type: ignore[import]


class Settings(BaseSettings):
    """Configuration for the H.A.R.V.E.Y. API service."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Core service
    app_name: str = Field(default="harvey-pricing-assistant")
    environment: Literal["local", "development", "staging", "production"] = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # MCP gateway
    mcp_server_module: str = Field(
        default="pricing_mcp.mcp_server",
        description="Python module path for the Pricing MCP server entrypoint",
    )
    mcp_python_executable: Optional[str] = Field(
        default=None,
        description="Optional override for the Python executable used to launch the MCP server",
    )
    mcp_extra_python_paths: Optional[str] = Field(
        default=None,
        description="Additional os.pathsep-separated paths appended to PYTHONPATH for the MCP server",
    )

    # Async behaviour
    http_timeout_seconds: float = 60.0
    max_retry_attempts: int = 3
    retry_backoff_seconds: float = 1.5

    # LLM
    gemini_api_key: Optional[str] = Field(default=None, description="Gemini API key")
    gemini_model: str = "gemini-2.5-flash"
    gemini_base_url: Optional[AnyHttpUrl] = Field(
        default=None, description="Override for the Gemini OpenAI-compatible endpoint"
    )
    gemini_better_model: Optional[str] = Field(
        default="gemini-2.5-pro", description="Fallback model used when higher quality is required"
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()  # type: ignore[arg-type]
