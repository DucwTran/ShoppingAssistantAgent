from functools import lru_cache

from langchain_core.embeddings import Embeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.core.config import settings
from app.core.llm import with_key_rotation


@lru_cache(maxsize=None)
def _embedding_model(api_key: str) -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(model=settings.gemini_embedding_model, google_api_key=api_key)


class _RotatingEmbeddings(Embeddings):
    """Gemini embeddings that share the chat model's API key rotation."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return with_key_rotation(lambda key: _embedding_model(key).embed_documents(texts))

    def embed_query(self, text: str) -> list[float]:
        return with_key_rotation(lambda key: _embedding_model(key).embed_query(text))


@lru_cache(maxsize=1)
def get_embeddings() -> Embeddings:
    return _RotatingEmbeddings()
