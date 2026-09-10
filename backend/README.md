# AI Shopping Assistant — Backend

Backend LangGraph cho agent tư vấn mua laptop: trích xuất yêu cầu từ câu hỏi tự nhiên, tự quyết định tìm web và/hoặc tra kiến thức nền (RAG), tự chấm điểm và tự sửa khuyến nghị của chính mình, rồi dừng lại chờ người dùng duyệt trước khi kết thúc. Câu hỏi ngoài chủ đề (chào hỏi, hỏi lung tung) được nhận diện và trả lời nhẹ nhàng thay vì bị từ chối cứng. Chạy qua CLI hoặc FastAPI JSON API.

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
- `GROQ_API_KEY` — lấy tại https://console.groq.com/keys, dùng cho LLM chat/structured output
- `OPENAI_API_KEY` — tuỳ chọn, provider thay thế cho Groq (xem `app/core/llm.py`)

## RAG — build knowledge index

Đặt tài liệu (`.pdf` hoặc `.md`) vào `data/knowledge/`, sau đó build lại index (chạy lại mỗi khi thêm/sửa tài liệu):

```bash
python -m app.rag.vectorstore
```

Lệnh này đọc toàn bộ `.pdf`/`.md` trong `data/knowledge/`, chunk, embed (Gemini `gemini-embedding-001`), và lưu vào Qdrant local mode tại `data/qdrant_local/`.

## Chạy thử (CLI)

```bash
python -m app.cli "laptop dưới 25 triệu cho lập trình AI và gaming"
python -m app.cli "RTX 4060 có đủ cho AI development không?"
```

Câu hỏi kỹ thuật thuần (không cần sản phẩm cụ thể) được định tuyến qua RAG, trả lời dựa trên kiến thức trong `data/knowledge/` thay vì so sánh sản phẩm cụ thể.

Sau khi có khuyến nghị, agent tự chấm điểm chất lượng (0-1). Nếu chưa đạt ngưỡng, agent tự tìm ra chỗ thiếu cụ thể và search/retrieve lại có mục tiêu, tối đa vài lần trước khi trả kết quả tốt nhất hiện có kèm cảnh báo rõ ràng — không bao giờ bịa dữ liệu để đạt điểm cao.

Trước khi kết thúc, CLI luôn dừng lại hỏi bạn duyệt (`Approve this recommendation? [y/n]`) — kể cả khi đã đạt ngưỡng chất lượng. Gõ `n` rồi nhập góp ý sẽ khiến agent tạo lại khuyến nghị theo đúng góp ý đó và hỏi duyệt lại, lặp tới khi bạn approve.

## Chạy thử (API)

```bash
uvicorn app.main:app --reload
```

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

`approved: false` kèm `feedback` tạo lại khuyến nghị rồi trả `status: "pending_approval"` lần nữa — lặp `POST /resume` tới khi `status == "done"`. Lỗi trả `{"error": {"code", "message"}}`: 400 (query không hợp lệ), 404 (`thread_id` không tồn tại), 409 (thread đã xong).

## Eval offline (golden queries)

```bash
python -m app.evals.run_eval
```

Chạy graph qua một bộ câu hỏi mẫu cố định, in `quality_score`/`reflection_count`/sản phẩm mỗi câu để quan sát chất lượng theo thời gian — không phải test tự động, không gate pass/fail.

## Test

```bash
pytest -v
```

Test cần gọi LLM/web search thật sẽ tự skip nếu `.env` chưa đủ key; chạy đầy đủ khi đã điền key (miễn còn quota).

