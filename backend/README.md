# AI Shopping Assistant — Backend

Phase 1/7 của roadmap: LangGraph Agent Core, chạy qua CLI (chưa có FastAPI/RAG/Guards/HITL — xem `initial_plan.md` ở thư mục gốc và roadmap 7 phase).

## Setup

```bash
cd backend
python -m venv .venv
./.venv/Scripts/activate        # Windows
pip install -r requirements.txt
cp .env.example .env
```

Điền vào `.env`:
- `GOOGLE_API_KEY` — lấy tại Google AI Studio (https://aistudio.google.com/apikey)
- `TAVILY_API_KEY` — lấy tại https://tavily.com (free tier)

## Chạy thử (CLI demo)

```bash
python -m app.cli "laptop dưới 25 triệu cho lập trình AI và gaming"
```

## Chạy test

```bash
pytest -v
```

2 test end-to-end trong `tests/test_graph.py` sẽ tự skip nếu chưa có API key thật trong `.env`; sẽ chạy đầy đủ khi đã điền key.

## Cấu trúc

Xem chi tiết trong plan gốc. Các thư mục `guards/`, `rag/`, `api/`, `evals/` hiện là placeholder rỗng, sẽ được implement ở Phase 2–5.

## Roadmap

Phase 1 (hiện tại) → Phase 2 (RAG + Router + Guards) → Phase 3 (Evaluation + Reflection) → Phase 4 (HITL + Checkpoint) → Phase 5 (FastAPI + Streaming) → Phase 6 (React Chatbot UI) → Phase 7 (Docker).
