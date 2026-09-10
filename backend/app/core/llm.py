# from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq

from app.core.config import settings


def get_llm(temperature: float = 0.2):
    # Swap the return statement below to switch provider (e.g. when one runs out of quota).
    # return ChatOpenAI(
    #     model=settings.openai_model,
    #     api_key=settings.openai_api_key,
    #     temperature=temperature,
    # )
    return ChatGroq(
        model=settings.groq_model,
        api_key=settings.groq_api_key,
        temperature=temperature,
    )
