# AI Shopping Assistant — Frontend

Chat UI đơn giản cho backend LangGraph (xem `../README.md` cho kiến trúc đầy đủ). React 19 + TypeScript + Vite + Tailwind, request/response thuần qua `/api/v1/shopping/*` — không streaming, không lưu hội thoại (refresh trang = chat mới).

## Setup

```bash
npm install
cp .env.example .env.development   # VITE_API_BASE_URL, mặc định http://127.0.0.1:8000
npm run dev
```

Cần backend đang chạy (`uvicorn app.main:app --reload` ở `../backend`).

## Cấu trúc

```
src/
├── App.tsx               Khung chat, render từng loại turn (user/assistant/pending-approval/error)
├── hooks/useShoppingConversation.ts   State machine của cuộc hội thoại (in-memory, không persist)
├── api/shoppingClient.ts  HTTP client gọi backend
├── components/            Bubble chat, recommendation card, nút approve/reject, error banner
└── types/shopping.ts      DTO khớp field-for-field với backend
```

## Script

```bash
npm run dev       # dev server
npm run build     # type-check (tsc) + build production
npm run lint      # oxlint
npm run preview   # xem thử bản build
```
