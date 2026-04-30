from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import json
import os
from pathlib import Path


def _project_root() -> Path:
    """Find the project root (directory containing test-cases/ or .git/)."""
    # Start from this file's directory and walk up
    current = Path(__file__).resolve().parent
    for ancestor in [current] + list(current.parents):
        if (ancestor / "test-cases").is_dir() or (ancestor / ".git").is_dir():
            return ancestor
    # Fallback to CWD
    return Path.cwd()


PROJECT_ROOT = _project_root()


class Settings(BaseSettings):
    """Application settings

    Loads settings from (in priority order):
    1. Environment variables
    2. .env file (gitignored, recommended)
    3. config.json file (if exists, NOT recommended for API keys)

    WARNING: Do not commit API keys to git repositories!
    Use .env file or environment variables for sensitive data.
    """

    # API Settings
    api_title: str = "FHIR Query Evaluation API"
    api_version: str = "0.1.0"
    api_description: str = "API for evaluating LLM-generated FHIR queries"

    # FHIR Server
    fhir_server_url: str = "http://localhost:8080"
    fhir_version: str = "fhir"

    # LLM Providers
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None

    # MCP Server
    mcp_server_url: Optional[str] = None

    # Storage — resolved relative to project root
    test_cases_dir: str = str(PROJECT_ROOT / "test-cases")
    results_dir: str = str(PROJECT_ROOT / "results")
    data_dir: str = str(PROJECT_ROOT / "data")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


def load_settings() -> Settings:
    """Load settings with optional JSON config file support

    Priority order:
    1. Environment variables (highest priority)
    2. .env file
    3. config.json file (lowest priority)
    """
    # First, load from .env and environment
    settings = Settings()

    # Then, check for config.json and merge (only if values not already set)
    config_path = Path("config.json")
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                config_data = json.load(f)

            # Only override if not already set from env/.env
            for key, value in config_data.items():
                if key == "comment":
                    continue
                if hasattr(settings, key) and getattr(settings, key) is None:
                    setattr(settings, key, value)
        except Exception as e:
            print(f"Warning: Could not load config.json: {e}")

    return settings


settings = load_settings()
