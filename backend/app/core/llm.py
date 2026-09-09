from langchain_groq import ChatGroq

from app.core.config import settings


def get_llm(temperature: float = 0.2) -> ChatGroq:
    return ChatGroq(
        model=settings.groq_model,
        api_key=settings.groq_api_key,
        temperature=temperature,
    )
