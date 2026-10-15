# AI Shopping Assistant — Backend

The backend hosts the LangGraph pipeline and exposes it through a FastAPI service. The architecture, objectives and evaluation approach are described in the [project report](../README.md); this document covers the code organization, configuration, interfaces and verification of the backend.

## 1. Code organization

| Module | Responsibility |
|---|---|
| `app/graph/` | The state graph (`graph.py`), the shared state (`state.py`) and one module per step in `nodes/` |
| `app/tools/` | The research agent's two tools (`agent_tools.py`), the Tavily search client, and deterministic helpers for currency conversion, price comparison and specification scoring |
| `app/rag/` | Document loading and chunking, embeddings, the Qdrant index and retrieval |
| `app/guards/` | Input validation, filtering of tool results, product grounding and budget disclosure |
| `app/prompts/` | System prompts, one per LLM step |
| `app/schemas/` | Pydantic schemas for every structured LLM output and tool argument |
| `app/core/` | Configuration, the Gemini client with API key rotation, structured-output calls, error classification, logging, progress events and the checkpointer |
| `app/api/` | HTTP endpoints and request/response schemas |
| `app/cli.py` | Command-line interface to the same graph |
| `evals/` | Evaluation script and its fixed query set |
| `tests/` | Automated tests |

## 2. Configuration

Settings are read from `backend/.env` (template: `.env.example`).

| Variable | Purpose |
|---|---|
| `TAVILY_API_KEY` | Web search ([tavily.com](https://tavily.com)) |
| `GEMMA_API_KEY_1`, `GEMMA_API_KEY_2`, ... | Google AI Studio keys ([aistudio.google.com/apikey](https://aistudio.google.com/apikey)) for the language model and embeddings. Any number of keys may be listed; they are used in numeric order |
| `GEMINI_MODEL` | Optional; chat model, `gemini-3.5-flash` by default |
| `GEMINI_EMBEDDING_MODEL` | Optional; embedding model, `gemini-embedding-001` by default |
| `CHECKPOINT_TTL_HOURS` | Optional; conversations idle for longer are deleted, 24 by default |

**Model access and key rotation.** All LLM and embedding calls go through `with_key_rotation` in `app/core/llm.py`. When a key reaches its quota or is rejected (HTTP 401, 403, 429, or an invalid-key response), the call is repeated with the next key, and the exhausted key is skipped by subsequent requests. Inside the research agent, the same rotation is applied by a model-call middleware. When every key has failed, the request ends with the `llm_quota_exhausted` error described below.

## 3. Knowledge index

```bash
python -m app.rag.vectorstore
```

The command reads every `.pdf` and `.md` file in `data/knowledge/`, splits the text into chunks of 1,000 characters with a 150-character overlap, embeds them, and stores the index in `data/qdrant_local/`. It must be run once before first use and again whenever documents change. The embedded Qdrant index can be opened by only one process at a time, so the server must be stopped while the RAG tests or the evaluation run.

## 4. Running

```bash
uvicorn app.main:app --reload                                        # HTTP API on port 8000
python -m app.cli "laptop dưới 25 triệu cho lập trình AI và gaming"  # command line
```

Conversation state is stored in `data/checkpoints.sqlite`. A recommendation waiting for the user's decision can therefore still be resumed after a server restart.

To keep the database bounded, the server deletes conversations whose last activity is older than `CHECKPOINT_TTL_HOURS` (finished, awaiting a decision, or stopped by an error alike). Pruning runs at startup and then hourly in a background task, and reclaims the freed disk space (`prune_checkpoints` in `app/core/checkpointer.py`). A deleted conversation answers later requests with `404 thread_not_found`.

## 5. HTTP interface

| Endpoint | Purpose |
|---|---|
| `POST /api/v1/shopping/query/stream` | Starts a conversation with `{"query": str}`. Returns Server-Sent Events: `progress` frames for each step, then one `result` or `error` frame |
| `POST /api/v1/shopping/resume/{thread_id}/stream` | Submits the user's decision `{"approved": bool, "feedback": str?}` while the conversation is paused for it |
| `POST /api/v1/shopping/retry/{thread_id}/stream` | Continues a conversation whose last run failed, from the step that failed; completed steps are not repeated |
| `POST /api/v1/shopping/query`, `.../resume/{thread_id}`, `.../retry/{thread_id}` | The same operations as plain JSON responses |

A result carries a `status`: `pending_approval` (awaiting the user's decision), `done` (accepted, or a small-talk reply), or `rejected` (the rejection limit was reached without acceptance).

**Errors** share one format, `{"error": {"code", "message"}}`, where `message` is written for the end user. In a stream, the `error` frame also carries the HTTP `status` that the JSON endpoint would have returned and the `thread_id` to pass to the retry endpoint.

| Status | Code | Meaning |
|---|---|---|
| 400 | `invalid_query` | Empty or over-long question |
| 404 | `thread_not_found` | Unknown conversation |
| 409 | `thread_already_finished` | The conversation has already ended |
| 409 | `not_awaiting_decision` | A decision was sent while the conversation is not paused for one (its last run failed and must be retried) |
| 409 | `nothing_to_retry` | A retry was requested for a conversation that is waiting for a decision |
| 503 | `llm_unavailable` | The model provider is overloaded or did not respond, after automatic retries |
| 503 | `llm_quota_exhausted` | Every configured API key has reached its quota |
| 500 | `internal_error` | Any other failure; the full trace is written to the server log |

## 6. Verification

```bash
pytest                     # offline suite: no network or keys needed
pytest -m live             # live tests against Gemini, Tavily and the knowledge index (consume API quota)
python -m evals.run_eval   # six real queries; results saved in evals/results/
```

The offline suite runs the complete graph with a simulated LLM and covers the HTTP and streaming API (including error responses and retries), the guards (including verification of prices and specifications against the source page), the schemas, the deterministic helpers and the key rotation. Live tests are excluded by default (`pytest.ini`) and are skipped when the required keys are missing.
