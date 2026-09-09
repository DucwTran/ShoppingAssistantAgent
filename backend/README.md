# AI Shopping Assistant — Backend

Phase 5/7 của roadmap: LangGraph Agent Core + RAG + Router + Guards + Evaluation/Reflection loop + Human-in-the-loop approval + FastAPI JSON API (đồng bộ, không streaming), chạy qua CLI hoặc HTTP — xem `reference/initial_plan.md` ở thư mục gốc và roadmap 7 phase.

## Setup

```bash
cd backend
python -m venv .venv
./.venv/Scripts/activate        # Windows
pip install -r requirements.txt
cp .env.example .env
```

Điền vào `.env`:
- `GOOGLE_API_KEY` — lấy tại Google AI Studio (https://aistudio.google.com/apikey), dùng cho embeddings (RAG)
- `TAVILY_API_KEY` — lấy tại https://tavily.com (free tier), dùng cho web search
- `GROQ_API_KEY` — lấy tại https://console.groq.com/keys, dùng cho mọi lệnh gọi LLM chat/structured output

**Lưu ý free tier Groq**: model `openai/gpt-oss-120b` hiện giới hạn 200,000 token/ngày (không phải theo số request). Evaluator và Reflection gửi payload lớn (toàn bộ products/knowledge/recommendation mỗi lần gọi) nên tốn quota nhanh hơn các node khác — nếu gặp lỗi `429 rate_limit_exceeded ... tokens per day`, đợi quota reset (theo ngày) hoặc nâng cấp billing, không phải lỗi code.

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

Sau `recommend`, `evaluator` tự chấm điểm chất lượng khuyến nghị (0-1). Nếu điểm dưới `quality_threshold` (mặc định 0.70), `reflection` sẽ tìm ra chỗ thiếu cụ thể và search/retrieve lại có mục tiêu, tối đa `max_reflections` (mặc định 2) lần trước khi trả kết quả tốt nhất hiện có kèm cảnh báo.

Trước khi kết thúc, CLI luôn dừng lại hỏi bạn duyệt recommendation (`Approve this recommendation? [y/n]`) — kể cả khi đã đạt `quality_threshold`. Gõ `n` rồi nhập góp ý sẽ khiến agent tạo lại recommendation theo đúng góp ý đó và hỏi duyệt lại, lặp tới khi bạn approve. Sau khi approve, CLI in `Final recommendation` kèm `Quality score`/cảnh báo nếu có.

## Chạy thử (API demo)

```bash
uvicorn app.main:app --reload
```

Cùng logic HITL như CLI nhưng qua HTTP, đồng bộ (mỗi request chạy hết graph phía server rồi mới trả response, không streaming):

```bash
curl -X POST http://127.0.0.1:8000/api/v1/shopping/query \
     -H "Content-Type: application/json" \
     -d '{"query": "laptop duoi 25 trieu cho lap trinh AI va gaming"}'
# → { "thread_id": "...", "status": "pending_approval", "data": {...} }

curl -X POST http://127.0.0.1:8000/api/v1/shopping/resume/<thread_id> \
     -H "Content-Type: application/json" \
     -d '{"approved": true, "feedback": null}'
# → { "thread_id": "...", "status": "done", "data": {...} }
```

`approved: false` kèm `feedback` sẽ tạo lại recommendation rồi trả `status: "pending_approval"` lần nữa — lặp `POST /resume` tới khi `status == "done"`. Lỗi trả `{"error": {"code", "message"}}`: 400 (query không hợp lệ), 404 (`thread_id` không tồn tại), 409 (thread đã xong, không còn gì để resume).

## Chạy eval offline (golden queries)

```bash
python -m app.evals.run_eval
```

Chạy graph qua một bộ câu hỏi mẫu cố định, in `quality_score`/`reflection_count`/sản phẩm mỗi câu để quan sát chất lượng theo thời gian — không phải test tự động, không gate pass/fail.

## Chạy test

```bash
pytest -v
```

Các test cần gọi Groq/Tavily/Gemini thật (`test_router.py`, `test_rag.py`, phần lớn `test_graph.py` và `test_api.py`) sẽ tự skip nếu `.env` chưa có đủ `GOOGLE_API_KEY`/`TAVILY_API_KEY`/`GROQ_API_KEY`; sẽ chạy đầy đủ khi đã điền key (miễn còn quota). `test_checkpointer.py`, `test_human_approval.py`, và các case lỗi 400/404 trong `test_api.py` không cần key nào.

## Cấu trúc

Xem chi tiết trong `reference/mapping.md` ở thư mục gốc.

## Roadmap

Phase 1 ✅ → Phase 2 ✅ (RAG + Router + Guards) → Phase 3 ✅ (Evaluation + Reflection) → Phase 4 ✅ (HITL + Checkpoint) → Phase 5 (FastAPI JSON API, hiện tại) → Phase 6 (React Chatbot UI) → Phase 7 (Docker).
