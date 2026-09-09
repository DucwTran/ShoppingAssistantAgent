from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    google_api_key: str = ""
    tavily_api_key: str = ""

    gemini_model: str = "gemini-3.6-flash"

    # Reserved for Phase 3 (Evaluation + Reflection)
    max_reflections: int = 2
    quality_threshold: float = 0.70

    # Reserved for Phase 2 (RAG)
    chunk_size: int = 1000
    chunk_overlap: int = 150
    embedding_model: str = "models/text-embedding-004"


settings = Settings()
