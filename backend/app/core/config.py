from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    google_api_key: str = ""
    tavily_api_key: str = ""
    groq_api_key: str = ""
    openai_api_key: str = ""

    # Chat completion / structured output model — active provider is chosen via llm_provider
    llm_provider: str = "groq"
    groq_model: str = "openai/gpt-oss-120b"
    openai_model: str = "gpt-5.4-mini"
    # Google is used only for embeddings — Groq has no embedding API
    gemini_model: str = "gemini-3.6-flash"

    # Reflection loop bounds
    max_reflections: int = 2
    quality_threshold: float = 0.70

    # Human-in-the-loop rejection loop bound (safety valve, not a normal stopping point)
    max_human_rejections: int = 10

    # RAG chunking and embedding model
    chunk_size: int = 1000
    chunk_overlap: int = 150
    embedding_model: str = "models/gemini-embedding-001"


settings = Settings()
