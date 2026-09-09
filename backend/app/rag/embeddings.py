from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.core.config import settings


def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(
        model=settings.embedding_model,
        google_api_key=settings.google_api_key,
    )
