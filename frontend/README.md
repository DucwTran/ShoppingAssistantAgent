# AI Shopping Assistant — Frontend

The frontend is a single-page chat interface for the backend service, built with React, TypeScript, Vite and Tailwind CSS. The overall system is described in the [project report](../README.md).

## 1. Functionality

- **Question entry and live progress.** While a request is processed, the interface lists each pipeline step as it completes, together with the search queries issued by the research agent.
- **Recommendation card.** Shows the recommended product with price, link, reasons, trade-offs, an alternative and the quality score. A score below the configured threshold is highlighted together with the evaluator's main concern.
- **User decision.** The user accepts the recommendation or rejects it with feedback; a rejection starts a refinement round in the same conversation.
- **Error handling.** Failures are reported in plain language. When the cause is temporary (network interruption, an overloaded or exhausted AI service), a **Try again** action is offered. A request that failed on the server continues from the step where it stopped, so completed work is not repeated; a request that never reached the server is sent again. After any failure the input field is available again, so the user can always continue with a new question.
- **Session scope.** Conversations are not stored in the browser; reloading the page starts a new chat.

## 2. Code organization

| Path | Responsibility |
|---|---|
| `src/App.tsx` | Chat layout; renders each turn type (question, decision, recommendation, error) |
| `src/hooks/useShoppingConversation.ts` | Conversation state: current phase, active conversation, progress events, last error and retry |
| `src/api/shoppingClient.ts` | HTTP client for the streaming endpoints; parses Server-Sent Events and error frames |
| `src/components/` | Messages, progress steps, recommendation card, decision controls, error banner |
| `src/types/shopping.ts` | Data types matching the backend's request and response schemas |

## 3. Running

The backend must be running (see [backend/README.md](../backend/README.md)).

```bash
npm install
cp .env.example .env.development   # VITE_API_BASE_URL, http://127.0.0.1:8000 by default
npm run dev                        # http://localhost:5173
```

| Script | Purpose |
|---|---|
| `npm run dev` | Development server |
| `npm run build` | Type check and production build |
| `npm run lint` | Static analysis (oxlint) |
| `npm run preview` | Serves the production build locally |
