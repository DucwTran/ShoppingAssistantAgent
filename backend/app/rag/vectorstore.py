import shutil
import sys
from functools import lru_cache

from langchain_qdrant import QdrantVectorStore

from app.core.config import settings
from app.rag.embeddings import get_embeddings
from app.rag.ingestion import load_and_chunk

QDRANT_PATH = settings.data_dir / "qdrant_local"
COLLECTION_NAME = "laptop_knowledge"


def index_exists() -> bool:
    """Whether the knowledge index has been built, read from the storage layout without opening it."""
    return (QDRANT_PATH / "collection" / COLLECTION_NAME).is_dir()


@lru_cache(maxsize=1)
def get_vectorstore() -> QdrantVectorStore:
    # Cached: Qdrant's embedded mode holds a file lock, so a second client in the same process would fail.
    return QdrantVectorStore.from_existing_collection(
        collection_name=COLLECTION_NAME,
        embedding=get_embeddings(),
        path=str(QDRANT_PATH),
    )


def build_index() -> QdrantVectorStore:
    """Rebuild the index from scratch.

    The local storage directory is removed outright rather than relying on
    QdrantVectorStore's own recreate-collection check, which can miss a stale
    collection left behind by an unclean shutdown and end up appending to it
    instead of replacing it.
    """
    if QDRANT_PATH.exists():
        shutil.rmtree(QDRANT_PATH)

    chunks = load_and_chunk()
    return QdrantVectorStore.from_texts(
        texts=[chunk.text for chunk in chunks],
        embedding=get_embeddings(),
        metadatas=[{"source": chunk.source} for chunk in chunks],
        collection_name=COLLECTION_NAME,
        path=str(QDRANT_PATH),
    )


if __name__ == "__main__":
    # --if-missing: used at container start, where rebuilding on every restart would spend embedding quota
    if "--if-missing" in sys.argv and index_exists():
        print(f"Index already present at {QDRANT_PATH}; not rebuilt.")
    else:
        store = build_index()
        count = store.client.count(COLLECTION_NAME).count
        print(f"Index built at {QDRANT_PATH} — {count} points in collection '{COLLECTION_NAME}'.")
