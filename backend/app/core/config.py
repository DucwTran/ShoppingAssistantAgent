import os
from pathlib import Path
from typing import Literal

from dotenv import dotenv_values
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = ".env"
_BACKEND_DIR = Path(__file__).resolve().parents[2]
GEMINI_KEY_PREFIX = "GEMMA_API_KEY_"


def _gemini_api_keys() -> list[str]:
    """Every non-empty GEMMA_API_KEY_<n> from .env and the environment, ordered by <n>, without duplicates."""
    values = {**dotenv_values(_ENV_FILE), **os.environ}
    named = [(name.removeprefix(GEMINI_KEY_PREFIX), value) for name, value in values.items()
             if name.startswith(GEMINI_KEY_PREFIX) and value]
    ordered = sorted(named, key=lambda item: item[0].zfill(6))
    return list(dict.fromkeys(value for _, value in ordered))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    # In production a missing required key stops the server at startup instead of failing every query
    app_env: Literal["development", "production"] = "development"
    # Runtime state: the checkpoint database and the knowledge index (a volume in a container)
    data_dir: Path = _BACKEND_DIR / "data"
    log_format: Literal["text", "json"] = "text"
    # Browser origins allowed to call the API directly; behind the frontend's proxy requests are same-origin
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    tavily_api_key: str = ""
    web_search_timeout_seconds: float = 30.0

    # Gemini via Google AI Studio; requests rotate through the keys when one is exhausted or rejected
    gemini_api_keys: list[str] = Field(default_factory=_gemini_api_keys)
    gemini_model: str = "gemini-3.5-flash"
    gemini_embedding_model: str = "gemini-embedding-001"
    llm_timeout_seconds: float = 60.0

    quality_threshold: float = 0.70

    # Human-in-the-loop rejection loop bound (safety valve, not a normal stopping point)
    max_human_rejections: int = 10

    # Conversations idle for longer than this are deleted from the checkpoint database
    checkpoint_ttl_hours: float = 24.0

    # Earlier turns of a conversation kept as context for follow-up questions
    max_history_turns: int = 5

    # Requests per client per minute on the endpoints that run the graph
    rate_limit_per_minute: int = 10

    # Research
    research_tool_call_limit: int = 4
    max_products: int = 6
    web_search_max_results: int = 8
    # Vietnamese retailers that list laptop prices/specs; searched first, then the open web if they return nothing
    web_search_domains: list[str] = [
        "thegioididong.com",
        "fptshop.com.vn",
        "cellphones.com.vn",
        "gearvn.com",
        "phongvu.vn",
        "hacom.vn",
    ]

    # RAG chunking
    chunk_size: int = 1000
    chunk_overlap: int = 150

    def missing_required_keys(self) -> list[str]:
        """Keys the app cannot run without."""
        missing = [] if self.tavily_api_key else ["TAVILY_API_KEY"]
        if not self.gemini_api_keys:
            missing.append(f"{GEMINI_KEY_PREFIX}<n>")
        return missing


settings = Settings()
