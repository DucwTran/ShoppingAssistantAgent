import shutil
from pathlib import Path

from langchain_qdrant import QdrantVectorStore

from app.rag.embeddings import get_embeddings
from app.rag.ingestion import load_and_chunk

QDRANT_PATH = Path(__file__).resolve().parents[2] / "data" / "qdrant_local"
COLLECTION_NAME = "laptop_knowledge"


def get_vectorstore() -> QdrantVectorStore:
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
    texts = [chunk.text for chunk in chunks]
    metadatas = [{"source": chunk.source} for chunk in chunks]

    return QdrantVectorStore.from_texts(
        texts=texts,
        embedding=get_embeddings(),
        metadatas=metadatas,
        collection_name=COLLECTION_NAME,
        path=str(QDRANT_PATH),
    )


if __name__ == "__main__":
    store = build_index()
    count = store.client.count(COLLECTION_NAME).count
    print(f"Index built at {QDRANT_PATH} — {count} points in collection '{COLLECTION_NAME}'.")
