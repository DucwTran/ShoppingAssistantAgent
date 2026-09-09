# AI Shopping Assistant — Backend

Phase 2/7 của roadmap: LangGraph Agent Core + RAG + Router + Guards, chạy qua CLI (chưa có FastAPI/HITL/Streaming — xem `reference/initial_plan.md` ở thư mục gốc và roadmap 7 phase).

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

**Lưu ý free tier Gemini**: model `gemini-3.6-flash` (dùng cho chat) hiện giới hạn khoảng 20 request/ngày ở free tier — nếu gặp lỗi `429 RESOURCE_EXHAUSTED`, đợi quota reset (theo ngày) hoặc nâng cấp billing.

## RAG — build knowledge index

Đặt tài liệu (`.pdf` hoặc `.md`) vào `data/knowledge/`, sau đó build lại index (chạy lại mỗi khi thêm/sửa tài liệu):

```bash
python -m app.rag.vectorstore
```

Lệnh này đọc toàn bộ `.pdf`/`.md` trong `data/knowledge/`, chunk, embed (Gemini `gemini-embedding-001`), và lưu vào Qdrant local mode tại `data/qdrant_local/`.

## Chạy thử (CLI demo)

```bash
python -m app.cli "laptop dưới 25 triệu cho lập trình AI và gaming"
python -m app.cli "RTX 4060 có đủ cho AI development không?"
```

Câu hỏi kỹ thuật thuần (không cần sản phẩm cụ thể) sẽ được Router định tuyến qua RAG, `recommend` trả lời dựa trên kiến thức trong `data/knowledge/` thay vì so sánh sản phẩm (`product_name: "N/A"`).

## Chạy test

```bash
pytest -v
```

Các test cần gọi Gemini/Tavily thật (`test_router.py`, `test_rag.py`, phần lớn `test_graph.py`) sẽ tự skip nếu `.env` chưa có key; sẽ chạy đầy đủ khi đã điền key (miễn còn quota).

## Cấu trúc

Xem chi tiết trong plan. Các thư mục `api/`, `evals/` hiện vẫn là placeholder rỗng, sẽ được implement ở Phase 3–5.

## Roadmap

Phase 1 ✅ → Phase 2 (RAG + Router + Guards, hiện tại) → Phase 3 (Evaluation + Reflection) → Phase 4 (HITL + Checkpoint) → Phase 5 (FastAPI + Streaming) → Phase 6 (React Chatbot UI) → Phase 7 (Docker).
