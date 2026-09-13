from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    tavily_api_key: str = ""
    groq_api_key: str = ""
    openai_api_key: str = ""
    nvidia_api_key: str = ""

    # Chat completion / structured output model — active provider is chosen via llm_provider
    llm_provider: str = "nvidia"
    groq_model: str = "openai/gpt-oss-120b"
    openai_model: str = "gpt-5.4-mini"
    ollama_model: str = "qwen2.5:7b"
    ollama_base_url: str = "http://localhost:11434"
    nvidia_model: str = "openai/gpt-oss-20b"
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"

    # Reflection loop bounds
    max_reflections: int = 2
    quality_threshold: float = 0.70

    # Human-in-the-loop rejection loop bound (safety valve, not a normal stopping point)
    max_human_rejections: int = 10

    # RAG chunking and embedding model
    chunk_size: int = 1000
    chunk_overlap: int = 150
    ollama_embedding_model: str = "nomic-embed-text"


settings = Settings()
