from dataclasses import dataclass
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from app.core.config import settings

KNOWLEDGE_DIR = Path(__file__).resolve().parents[2] / "data" / "knowledge"


@dataclass
class Chunk:
    text: str
    source: str


def _read_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _read_markdown(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_documents(knowledge_dir: Path = KNOWLEDGE_DIR) -> list[tuple[str, str]]:
    """Return a list of (source_filename, raw_text) for every .pdf/.md file."""
    documents: list[tuple[str, str]] = []
    for path in sorted(knowledge_dir.glob("*")):
        if path.suffix.lower() == ".pdf":
            documents.append((path.name, _read_pdf(path)))
        elif path.suffix.lower() == ".md":
            documents.append((path.name, _read_markdown(path)))
    return documents


def load_and_chunk(knowledge_dir: Path = KNOWLEDGE_DIR) -> list[Chunk]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    chunks: list[Chunk] = []
    for source, text in load_documents(knowledge_dir):
        for piece in splitter.split_text(text):
            chunks.append(Chunk(text=piece, source=source))
    return chunks
