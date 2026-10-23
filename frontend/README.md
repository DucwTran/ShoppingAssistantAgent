# Frontend

React + TypeScript chat client for the backend's streaming API. Built with Vite and Tailwind CSS.

## Setup

Requires the backend running on `http://127.0.0.1:8000` (set `VITE_API_BASE_URL` in `.env.development` to change it).

```bash
npm install
npm run dev       # http://localhost:5173
npm run build     # type check + production build
npm run lint      # oxlint
```

## Behavior

- Shows each pipeline step and the agent's search queries while a request runs.
- Renders the recommendation with price, link, reasons, trade-offs, alternative and quality score; a score below the threshold is highlighted with the evaluator's concern.
- Accept or reject with feedback; a rejection continues the same conversation.
- On failure, shows a plain-language message. For network or server-side failures it offers **Try again**, which resumes a server-side failure from the failed step and resends a request that never reached the server. The input stays usable after any error.
- Nothing is persisted in the browser; reloading starts a new chat.

## Structure

| Path | Contents |
|---|---|
| `src/App.tsx` | Layout and rendering of each chat turn |
| `src/hooks/useShoppingConversation.ts` | Conversation state, progress, errors and retry |
| `src/api/shoppingClient.ts` | SSE client for `query`, `resume` and `retry` |
| `src/components/` | Messages, progress steps, recommendation card, decision controls, error banner |
| `src/types/shopping.ts` | Types mirroring the backend schemas |
