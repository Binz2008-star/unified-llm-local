"""
Typed Settings — Single source of truth for all configuration.

Replaces scattered os.getenv() calls across brain_agent_v4.py, sb.py, etc.
All components receive Settings via dependency injection.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

KB_ROOT = Path(__file__).parent


class Settings(BaseSettings):
    """Application settings — validated, typed, centralized."""

    # ── App ──────────────────────────────────────────────────────
    app_env: str = "development"
    log_level: str = "INFO"

    # ── Security Policy (immutable in production) ────────────────
    auto_commit: bool = False
    require_human_approval: bool = True
    allow_network: bool = False
    allow_destructive_commands: bool = False

    # ── Execution Limits ─────────────────────────────────────────
    command_timeout_seconds: int = Field(default=120, ge=1, le=3600)
    max_command_output_bytes: int = Field(default=200_000, ge=1024, le=10_000_000)
    max_tool_calls: int = Field(default=30, ge=1, le=200)
    max_context_tokens: int = Field(default=24_000, ge=1000, le=200_000)

    # ── Ollama ───────────────────────────────────────────────────
    ollama_base_url: str = "http://127.0.0.1:11434"
    embed_model: str = "nomic-embed-text"
    embed_dim: int = Field(default=768, ge=1, le=4096)

    # ── Agent Models ─────────────────────────────────────────────
    architect_model: str = "qwen2.5:7b"
    editor_model: str = "qwen2.5:7b"
    tester_model: str = "qwen2.5:7b"
    chat_model: str = "qwen2.5:7b"

    # ── Databases ────────────────────────────────────────────────
    local_dsn: str | None = None
    neon_dsn: str | None = None

    # ── Projects ─────────────────────────────────────────────────
    current_project: str = "second_brain"
    project_content_engine: str | None = None
    project_lvyy: str | None = None
    project_rico: str | None = None
    project_second_brain: str | None = None

    model_config = SettingsConfigDict(
        env_file=str(KB_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("architect_model", "editor_model", "tester_model", "chat_model")
    @classmethod
    def model_must_be_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Model name cannot be empty")
        return v.strip()

    @property
    def ollama_embed_url(self) -> str:
        return f"{self.ollama_base_url}/api/embed"

    @property
    def ollama_chat_url(self) -> str:
        return f"{self.ollama_base_url}/api/chat"


# ── Production safety ────────────────────────────────────────────
def validate_production_settings(settings: Settings) -> list[str]:
    """
    Validate settings for production safety.
    Returns list of warnings/errors.
    """
    issues = []

    if settings.auto_commit and not settings.require_human_approval:
        issues.append("CRITICAL: AUTO_COMMIT=true with REQUIRE_HUMAN_APPROVAL=false is unsafe")

    if settings.allow_destructive_commands:
        issues.append("WARNING: allow_destructive_commands is enabled")

    if settings.allow_network and settings.app_env == "production":
        issues.append("WARNING: network access enabled in production")

    return issues


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached Settings instance. Call get_settings.cache_clear() to reload."""
    return Settings()


def reload_settings() -> Settings:
    """Force reload settings (for testing)."""
    get_settings.cache_clear()
    return get_settings()
