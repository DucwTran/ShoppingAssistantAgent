from app.rag.retriever import retrieve
from app.schemas.knowledge_search import KnowledgeSearchArgs
from app.tools.base import RegisteredTool

search_knowledge_base_tool = RegisteredTool(
    name="search_knowledge_base",
    description="Search the internal hardware/domain knowledge base (CPU/GPU/RAM/battery guides) for conceptual questions.",
    args_schema=KnowledgeSearchArgs,
    func=retrieve,
)
