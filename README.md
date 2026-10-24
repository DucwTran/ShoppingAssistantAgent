# AI Shopping Assistant

A laptop shopping assistant for the Vietnamese market, built with LangGraph. It searches current retailer listings, consults a small hardware knowledge base, recommends one laptop with reasons and trade-offs, and waits for the user to accept the result or ask for changes.

## Features

- Recommendations from live listings on six Vietnamese retailers, with price, specs and source link
- Hardware Q&A answered from a RAG knowledge base (CPU, GPU, RAM/storage/battery guides)
- Human-in-the-loop: every recommendation pauses the graph; rejection feedback leads to a re-pick or a new search
- Grounded output: products must come from a retrieved page, and prices or spec numbers missing from that page are dropped; only products with a verified price are recommended
- Follow-up questions in the same conversation ("a cheaper one?"), resolved against the last 5 turns
- Progress streamed over SSE; conversations persist across restarts and can be retried from the failed step
- Vietnamese and English

## Architecture

FastAPI serves a LangGraph state graph; a React app consumes its SSE endpoints.

```mermaid
flowchart TD
    START([START]) --> IV[input_validation] --> MD[metadata] --> UN[understand]
    UN -->|small talk| RT[record_turn]
    UN -->|shopping| RA[research_agent]
    RA --> EP[extract_products] --> REC[recommend] --> EV[evaluator]
    EV --> RQ[request_approval] --> HA{{human_approval}}
    HA -->|accepted / rejection limit| RT
    HA -->|rejected| FR[feedback_router]
    FR -->|new search| RA
    FR -->|re-pick| REC
    RT --> END1([END])
```

| Node | LLM | Purpose |
|---|---|---|
| `input_validation` | – | Normalize Unicode, strip control characters, enforce 1–500 characters; reset the per-turn state of a follow-up |
| `metadata` | – | Detect Vietnamese or English |
| `understand` | 1 call | Classify shopping vs. small talk; rewrite a follow-up as a standalone question using the history; extract budget (VND), purpose, preferences, constraints |
| `research_agent` | agent | Choose between web search and the knowledge base, up to 4 tool calls; falls back to a fixed search on failure |
| `extract_products` | 1 call | Turn search results into products; drop ungrounded ones, clear unverified prices/specs, convert to VND; search once more for missing prices and drop products still without one |
| `recommend` | 1 call | Code ranks candidates, the model picks one by id; name, price and link are copied from the source data |
| `evaluator` | 1 call | Score 0–1: grounding, budget and spec completeness checked in code, purpose fit judged by the model |
| `request_approval` | – | Announce the pause (separate node so it does not repeat on resume) |
| `human_approval` | – | `interrupt()` and record the user's decision |
| `feedback_router` | 1 call | Decide whether rejection feedback needs new products or a re-pick |
| `record_turn` | – | Append the finished turn to the conversation history (last 5 kept) |

## Tech stack

| Area | Choice |
|---|---|
| Orchestration | LangGraph, LangChain (`create_agent`, middleware) |
| LLM | Gemini `gemini-3.5-flash`, rotating across several API keys |
| RAG | `gemini-embedding-001`, Qdrant (embedded) |
| Web search | Tavily |
| Persistence | SQLite checkpointer |
| Backend | FastAPI, Pydantic |
| Frontend | React, TypeScript, Vite, Tailwind CSS |
| Packaging | Docker Compose: backend (uvicorn) and frontend (nginx), one volume |
| Tests | pytest with a fake LLM; live tests and an eval script against real services |

## Getting started

Requires Python 3.11, Node.js, a [Tavily](https://tavily.com) key and at least one [Google AI Studio](https://aistudio.google.com/apikey) key.

```bash
# backend
cd backend
python -m venv .venv && ./.venv/Scripts/activate   # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env                                # set TAVILY_API_KEY, GEMMA_API_KEY_1, ...
python -m app.rag.vectorstore                       # build the knowledge index
uvicorn app.main:app --reload                       # http://127.0.0.1:8000

# frontend
cd frontend
npm install
npm run dev                                         # http://localhost:5173
```

## Running with Docker

```bash
cp backend/.env.example backend/.env   # set the keys
docker compose up -d --build           # http://localhost:8080
docker compose logs -f backend         # JSON logs
```

| Container | Role |
|---|---|
| `frontend` | nginx: serves the built app and proxies `/api` to the backend (SSE unbuffered, 300 s read timeout, 16 KB body limit); the only published port |
| `backend` | uvicorn, one worker, non-root; `APP_ENV=production`, JSON logs. Builds the knowledge index on first start |

Runtime state (checkpoints, knowledge index) is kept in the `app-data` volume. Check readiness with `docker compose exec backend python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health/ready').read())"`.

## Testing

```bash
cd backend
pytest                    # offline: full graph with a fake LLM, API, guards
pytest -m live            # real Gemini/Tavily/index; uses API quota
python -m evals.run_eval  # 20 labeled queries against live services
python -m evals.check_judge      # LLM judge vs. hand-labeled recommendations
python -m evals.check_injection  # prompt-injection attempts against the real nodes
```

Dataset, metrics and how to read them: [docs/eval.md](docs/eval.md).

## Repository layout

```
backend/
  app/
    graph/      state graph, state, one module per node
    tools/      agent tools, Tavily client, currency/price/spec helpers
    rag/        loading, chunking, embeddings, Qdrant index
    guards/     input, tool results, grounding, budget disclosure
    core/       config, Gemini client + key rotation, errors, checkpointer, logging
    api/        HTTP endpoints and schemas
  data/knowledge/   RAG source documents
  evals/        evaluation script and query set
  tests/
frontend/src/   chat UI, SSE client, conversation state
frontend/nginx.conf   static files and /api proxy in the container
docs/           evaluation guide
compose.yaml    the two containers and the data volume
```

## Design notes

- **One agent.** Only research needs decisions that depend on intermediate results (what to search, where, whether to search again). Every other step is a single structured-output call or plain code.
- **Data bypasses model prose.** Tools return `content_and_artifact`: the agent reads a trimmed summary, while full results go into graph state from `ToolMessage.artifact`.
- **Failure handling by layer.** Invalid structured output is regenerated; a key that hits its quota is rotated out; provider 5xx/timeouts are retried by `RetryPolicy`; an agent failure falls back to a fixed search; anything left is returned as a user-facing error with a retry that resumes from the checkpoint.
- **Measured nodes.** Every LLM node reports its duration and token usage (including the agent's inner calls) as a `node_measured` event, logged by the server and aggregated by the eval.
- **Memory as state.** A follow-up runs the graph again on the same thread: the checkpointer keeps a short `history`, every other field is reset per turn, and `understand` turns the message into a standalone question that the rest of the pipeline reads.
- **Injection defense in code.** Prompts tell the model to treat web results and history as data, but the guarantees come from code: products must be grounded in a retrieved page, the model picks a candidate by id, searches go to retailer domains first, and the agent is limited to 4 tool calls. `evals/check_injection.py` measures what the prompts add.
- **Retention.** Conversations idle for 24 hours are pruned from the checkpoint database at startup and hourly.

## Limitations

- A shopping query takes 60 s at the median and 83 s at p95, about 23k tokens ([eval baseline](docs/eval.md#baseline)).
- Gemini 503 overload errors that outlast the node retries still reach the user (3 of 20 eval cases).
- Memory is the last 5 turns of one conversation; "New chat", a reload or a failed turn starts a new one.
- Laptops only; USD is converted to VND at a fixed rate.
- Some specs (e.g. battery life) rarely appear in listings.
- Single process, no authentication; the rate limit (10 requests/min per client) is kept in memory.

See [backend/README.md](backend/README.md) and [frontend/README.md](frontend/README.md) for details.
