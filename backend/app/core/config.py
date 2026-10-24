import os

from dotenv import dotenv_values
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = ".env"
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

    tavily_api_key: str = ""

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
