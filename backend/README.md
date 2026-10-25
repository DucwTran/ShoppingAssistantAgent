# Backend

FastAPI service that runs the LangGraph pipeline. Architecture overview: [../README.md](../README.md).

## Setup

```bash
python -m venv .venv && ./.venv/Scripts/activate
pip install -r requirements-dev.txt   # runtime dependencies + pytest
cp .env.example .env
python -m app.rag.vectorstore     # build the knowledge index (re-run when data/knowledge/ changes)
```

Run:

```bash
uvicorn app.main:app --reload                                        # API on :8000, docs at /docs
python -m app.cli "laptop dưới 25 triệu cho lập trình AI và gaming"  # CLI, same graph
```

## Configuration

Read from the environment, then `.env`. Invalid values stop the process at startup.

| Variable | Default | Description |
|---|---|---|
| `TAVILY_API_KEY` | – | Web search (required) |
| `GEMMA_API_KEY_1`, `GEMMA_API_KEY_2`, ... | – | Google AI Studio keys, used in numeric order (at least one required) |
| `APP_ENV` | `development` | `production` refuses to start when a required key is missing; `development` only warns |
| `LOG_FORMAT` | `text` | `json`: one JSON object per line with `request_id`, `thread_id`, `node`, `event` |
| `DATA_DIR` | `./data` | Checkpoint database and knowledge index |
| `CORS_ORIGINS` | Vite dev origins | JSON list of browser origins allowed to call the API directly |
| `WEB_SEARCH_TIMEOUT_SECONDS` | `30` | Limit on one Tavily call (Gemini calls have their own 60 s limit) |
| `GEMINI_MODEL` | `gemini-3.5-flash` | Chat model |
| `GEMINI_EMBEDDING_MODEL` | `gemini-embedding-001` | Embedding model |
| `CHECKPOINT_TTL_HOURS` | `24` | Idle conversations older than this are deleted |
| `MAX_HISTORY_TURNS` | `5` | Earlier turns kept as context for follow-up questions |
| `RATE_LIMIT_PER_MINUTE` | `10` | Requests per client in any 60 s |

Other tunables (search domains, tool-call limit, rejection cap, chunk size) live in `app/core/config.py`.

## Operations

| Endpoint | Returns |
|---|---|
| `GET /health/live` | `200` while the process serves requests |
| `GET /health/ready` | `200` when the checkpoint database answers and the knowledge index exists; otherwise `503` with the failing check. Makes no LLM or search call |

Every response carries `X-Request-ID` (the caller's, if well-formed, else a new one). Every log line written while serving a request includes it, along with one access line per request (`event=request`, status, duration). Health checks are not logged.

## API

All routes are under `/api/v1/shopping`. Each has a JSON variant and a `/stream` (SSE) variant; the frontend uses the streams.

| Route | Body | Description |
|---|---|---|
| `POST /query` | `{"query": str, "thread_id": str?}` | Start a conversation, or ask a follow-up in a finished one |
| `POST /resume/{thread_id}` | `{"approved": bool, "feedback": str?}` | Submit the decision for a paused conversation |
| `POST /retry/{thread_id}` | – | Continue a failed run from the step that failed |

Response `status`: `pending_approval`, `done`, or `rejected` (rejection cap reached).

Every route is rate-limited per client address: `RATE_LIMIT_PER_MINUTE` (default 10) requests in any 60 s, counted in memory.

Stream frames: `progress` (one per node event), then a single `result` or `error`. An `error` frame carries `status`, `thread_id` and the error body.

Errors use `{"error": {"code": str, "message": str}}`:

| Status | Code | When |
|---|---|---|
| 400 | `invalid_query` | Query or feedback empty or longer than 500 characters |
| 404 | `thread_not_found` | Unknown or pruned conversation |
| 409 | `thread_already_finished` | Decision sent to a conversation that has ended |
| 409 | `conversation_busy` | Follow-up sent while the conversation waits for a decision or a retry |
| 409 | `not_awaiting_decision` | Decision sent to a run that failed; use `/retry` |
| 409 | `nothing_to_retry` | Retry sent to a conversation waiting for a decision |
| 429 | `rate_limited` | Over the per-client rate limit; `Retry-After` gives the seconds to wait |
| 503 | `llm_unavailable` | Gemini overloaded or timed out after retries |
| 503 | `llm_quota_exhausted` | Every API key is out of quota |
| 500 | `internal_error` | Anything else; traceback in the server log |

## Internals

- **LLM access** (`app/core/llm.py`): every Gemini call, including those inside the agent loop (via middleware) and embeddings, goes through `with_key_rotation`. Quota (429) and auth errors move to the next key; other errors propagate.
- **Retries**: structured output that fails validation is regenerated up to twice (`app/core/structured.py`); LLM nodes retry provider failures after ~3 s and ~6 s (`RetryPolicy`).
- **Conversation memory**: a follow-up re-runs the graph on the same thread. `input_validation` resets every per-turn field, `understand` rewrites the message into `standalone_query` from `history`, and `record_turn` appends the finished turn (`MAX_HISTORY_TURNS`, default 5).
- **Measurement** (`app/core/metrics.py`): each LLM node is wrapped by `measured`, which emits a `node_measured` event (`duration_ms`, `input_tokens`, `output_tokens`, `failed`) per attempt; it is logged and also sent on the stream.
- **Checkpoints** (`app/core/checkpointer.py`): SQLite at `data/checkpoints.sqlite`; pruned at startup and hourly, followed by `VACUUM`.
- **Knowledge index**: `.md`/`.pdf` files in `data/knowledge/`, 1,000-character chunks with 150 overlap, stored in `data/qdrant_local/`. Embedded Qdrant allows one process at a time, so stop the server before running RAG tests or evals.

## Tests

```bash
pytest                    # offline suite (default; live tests excluded in pytest.ini)
pytest -m live            # real services; skipped if keys are missing
python -m evals.run_eval     # labeled query set, eight metrics; writes results to evals/results/
python -m evals.check_judge  # LLM judge vs. hand-labeled recommendations
```

See [../docs/eval.md](../docs/eval.md) for the dataset and metrics.

`tests/conftest.py` replaces every LLM call and the agent loop with a scripted `FakePipeline`, so the offline suite runs the real graph without network access.
