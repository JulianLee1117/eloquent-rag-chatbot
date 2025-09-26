# Eloquent RAG Chatbot

An AI-powered chatbot for fintech FAQs with Retrieval-Augmented Generation (RAG), built with FastAPI (Python) and Next.js (TypeScript). It supports anonymous and authenticated users, multiple persisted chat sessions, streaming responses via SSE, and a Pinecone-backed retriever. Production-ready Docker setup and an AWS deployment plan are included.

## Features
- Anonymous and returning users (JWT for registered users; anon cookie for first-time users)
- Multiple chat sessions per user with soft-delete and titles
- Persistent message history in Postgres
- RAG: Pinecone dense retrieval with category-aware heuristics
- OpenAI streaming completions over Server-Sent Events (SSE)
- Token counting via tiktoken (with fallback)
- Clean Next.js chat UI with live token streaming

## Monorepo Layout
```
app/
  backend/              # FastAPI app, DB, RAG, LLM
    app/
      api/              # REST endpoints (auth, sessions, chat, health, sse utils)
      core/             # settings, security (JWT, bcrypt)
      db/               # SQLAlchemy models, CRUD, session factory
      llm/              # OpenAI client w/ tuned timeouts
      rag/              # embedder, retriever, prompt, types
      services/         # ChatService: builds context, retrieves, streams LLM
      utils/            # token counting
      main.py           # FastAPI app factory, CORS, routers, logging
    alembic/            # DB migrations
    requirements.txt
    tests/              # CRUD tests & seed utility
  frontend/             # Next.js app (React 19 + RQ v5)
    app/                # /chat route, layout, styles
    components/         # Chat UI, sidebar, auth modal
    lib/api.ts          # Client API & SSE stream parser
    package.json

docker/
  backend.Dockerfile
  frontend.Dockerfile

docker-compose.yml
```

## Prerequisites
- Docker (and Docker Compose)
- OpenAI API key
- Pinecone account and index access (with GRPC host)

Optional local tools: Python 3.11+, Node 20+

## Quick Start (Docker)
1) Create a `.env` file in the repo root (see Environment Variables below). At minimum set:
```
LLM_API_KEY=sk-...
# Pinecone (required for full RAG)
PINECONE_API_KEY=...
PINECONE_HOST=...
# Optional overrides
LLM_MODEL=gpt-4o-mini
EMBEDDING_MODEL=llama-text-embed-v2
```

2) Start the stack:
```bash
docker compose up --build
```
- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- Postgres: localhost:5432 (inside Docker network as `db`)

The backend container runs Alembic migrations automatically on startup.

## Local Development (without Docker)
Backend:
```bash
cd app/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Set env vars (see below) and ensure Postgres is running
alembic -c alembic.ini upgrade head
uvicorn app.main:app --reload --port 8000
```

Frontend:
```bash
cd app/frontend
npm install
# point to API
export NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
npm run dev
```

## Environment Variables
Settings are loaded via `pydantic-settings` from the process env (and `.env` if present).

Backend (commonly set in docker-compose or shell):
- POSTGRES_URL: e.g. `postgresql+psycopg://postgres:postgres@db:5432/eloquent`
- CORS_ORIGINS: JSON array of allowed origins, e.g. `["http://localhost:3000"]`
- JWT_SECRET: secret for HS256 JWT signing
- JWT_EXPIRE_MIN: e.g. `30`
- LLM_API_KEY: OpenAI API key
- LLM_MODEL: e.g. `gpt-4o-mini`
- PINECONE_API_KEY: Pinecone key
- PINECONE_INDEX: Pinecone index name (optional; retriever uses host)
- PINECONE_HOST: Pinecone index host (GRPC-compatible)
- EMBEDDING_MODEL: defaults to `llama-text-embed-v2`

Frontend:
- NEXT_PUBLIC_API_BASE_URL: API base URL (defaults to `http://localhost:8000`)

## Backend Overview
- `main.py`: FastAPI app with lifespan-based logging setup and CORS.
- `api/`
  - `auth.py`: register/login/logout (JWT in HttpOnly cookie) + `whoami` (JWT or anon id)
  - `sessions.py`: create/list/update/delete sessions; list messages with pagination
  - `chat.py`: POST `/chat` → SSE stream of tokens and final `done` payload
  - `health.py`: health check
  - `sse.py`: helper to format SSE frames
- `services/chat_service.py`: Orchestrates RAG
  - Builds recent history window
  - Retrieves Pinecone docs via `rag/retriever.py`
  - Assembles messages with `rag/prompt.py`
  - Streams OpenAI chat completions, tracking `tokens_in/tokens_out`
- `rag/`
  - `embedder.py`: query embeddings via Pinecone Inference
  - `retriever.py`: category-aware, multi-clause retrieval; soft category filters; diversification
  - `prompt.py`: strict system prompt + context formatting with inline `[FAQ n]` citations
  - `types.py`: `Doc` dataclass and citation conversion
- `db/`
  - `models.py`: `User`, `Session` (soft-delete via `deleted_at`), `Message`
  - `crud.py`: users, sessions (anon/user), messages, pagination, soft delete
  - `schemas.py`: Pydantic v2 models for API responses
  - `base.py`: SQLAlchemy engine and session factory
- `llm/client.py`: OpenAI client with extended read timeouts for streaming
- `utils/tokens.py`: token counting via tiktoken (fallback to whitespace)

## Frontend Overview (Next.js)
- `/app/chat/page.tsx`: Main chat experience
  - Loads sessions, messages; ensures anon cookie; streams assistant tokens
  - Optimistically inserts user messages and updates session title
- `components/`
  - `SessionSidebar`: session list/selector, `AuthModal` launcher
  - `MessageList`: ordered rendering, Markdown for assistant messages
  - `Composer`: sticky textarea + send button
  - `auth/AuthModal`: email/password auth with JWT via cookies
- `lib/api.ts`: fetch helpers and typed SSE stream parser

## API Summary
- Auth
  - POST `/auth/register` → sets `id_token` cookie
  - POST `/auth/login` → sets `id_token` cookie
  - POST `/auth/logout` → clears `id_token`
  - GET `/auth/whoami` → `{ user_id? | anon_id? }`
- Sessions
  - POST `/sessions` → create session (user or anon)
  - GET `/sessions` → list sessions for current identity
  - PATCH `/sessions/{id}` → update session title
  - DELETE `/sessions/{id}` → soft delete
  - GET `/sessions/{id}/messages?limit=&before=` → paginated messages
- Chat
  - POST `/chat` (body: `{ session_id?, message }`) → SSE: `token`, `done`, `error`

## Data Model
- `users`: id, email, hashed_password, created_at
- `sessions`: id, user_id nullable, anon_id nullable, title, created_at, deleted_at nullable
- `messages`: id, session_id, role (user/assistant/system), content, tokens_in, tokens_out, created_at

Alembic migrations live in `app/backend/alembic/versions/` and are applied on container start.

## Running Tests
```bash
cd app/backend
pytest -q
```


## Approach & Architectural Decisions

### How I approached the problem
I approached this project iteratively by leveraging GPT and Claude to research design patterns and generate initial plans. I refined these plans through multiple rounds of questioning—gauging best practices for this specific use case—and then implemented the system step by step, validating decisions along the way. Search tools and up-to-date references helped ensure the design aligned with current standards.

### Why these architectural choices (beyond the baseline requirements)
- SSE for token streaming vs WebSockets: simpler ops and CDN/proxy friendly for one-way token delivery.
- JWT in HttpOnly cookies + anon cookie: secure-by-default credentials with a smooth path from first-time anonymous to registered users.
- Soft-delete (`deleted_at`) for sessions: safer UX and easier analytics without irreversible data loss.
- Strict system prompt with inline `[FAQ n]` citations: improves trust and encourages grounded, non-hallucinated answers.
- Category-aware retrieval with synonym-based soft filters and diversification: when a query clearly maps to one category, apply a filter; otherwise search broadly and retry unfiltered if empty; diversify across clauses to cover multi-intent queries.
- Token accounting using `tiktoken` approximation: lightweight observability and cost awareness without impacting latency.
- Lifespan-based logging setup: reliable startup-time configuration and consistent logger behavior for RAG/services modules.
- DB-level pagination for messages: efficient, deterministic scrollback with clear limits and ordering.
- React Query client cache: minimal glue code with built-in invalidation and optimistic updates for a snappy chat experience.
- Alembic migrations on startup in dev/compose: keeps local environments consistent; in prod this can be a one-off job for stricter control.
- Pinecone GRPC host and category heuristics: low-overhead queries and simple domain heuristics that boost early precision for fintech FAQs.


