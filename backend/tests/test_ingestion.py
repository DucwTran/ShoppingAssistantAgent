from app.rag.ingestion import load_and_chunk, load_documents


def test_load_documents_reads_pdf_and_markdown():
    docs = load_documents()
    suffixes = {source.rsplit(".", 1)[-1].lower() for source, _ in docs}
    assert "pdf" in suffixes
    assert "md" in suffixes


def test_load_and_chunk_produces_chunks():
    chunks = load_and_chunk()
    assert len(chunks) > 0
    assert all(chunk.text.strip() for chunk in chunks)
    assert all(chunk.source for chunk in chunks)
