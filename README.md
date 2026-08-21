# Operator AI — v2

AI Chief-of-Staff platform, rebuilt from scratch to match the product spec
and fix the issues found in the previous implementation.

## Quick start

```bash
cp .env.example .env          # fill in JWT_SECRET, optionally AI_PROVIDER + API key, Google OAuth
docker compose up --build
```
- Backend: http://localhost:8000/docs
- Frontend: http://localhost:3000

Without any AI key set (`AI_PROVIDER=none`), the app still runs fully:
task/priority logic uses the deterministic heuristic in `ai/prioritizer.py`.
Set `AI_PROVIDER=openai` or `anthropic` + the matching API key for real LLM
classification, briefings, and chat.

**Free AI provider (default in `.env.example`):** `AI_PROVIDER=openai` with
`OPENAI_BASE_URL=https://api.groq.com/openai/v1` and
`OPENAI_MODEL=llama-3.3-70b-versatile` - Groq's free tier (no credit card,
~14,400 req/day). Get a key at https://console.groq.com and put it in
`OPENAI_API_KEY`. It's OpenAI-compatible so no code change was needed, just
config. The only thing Groq doesn't support is the embeddings endpoint, so
Knowledge search falls back to keyword matching instead of vector search
(everything else - chat, tool calls, classification, briefings - runs
normally). Neither Groq nor Anthropic offer an embeddings endpoint; if
vector search in Knowledge matters more than staying fully free, switch to
a real `OPENAI_API_KEY` + `OPENAI_BASE_URL=https://api.openai.com/v1`.

## What changed vs. the previous project

**1. Priority is no longer silently stuck at "medium".**
`ai/prioritizer.py::score_priority()` is now the single function that scores
every task, and it's called from every creation path: direct task creation
(`POST /tasks`), Inbox confirmation (`POST /inbox/{id}/confirm`), and the
assistant's `create_task` tool. Previously, only the Inbox flow ran AI
classification — creating a task directly on the Tasks page always defaulted
to `priority=medium` with no analysis. Each task now stores
`priority_source` (`ai` vs `user` vs `default`) and `priority_reason`, so the
UI can show *why* the AI picked a priority, and a manual edit always
overrides it going forward.

**2. Removed the dead mock layer.**
The previous backend had a second, fully hardcoded implementation
(`services/agent_system.py`, `vector_rag_service.py`, `google_integration.py`)
mounted on its own `/operator` router — outside the shared API prefix,
returning fake emails, a fake `"mock_access_token"`, and invented
risks/opportunities. None of that exists here. There is one Google client
(`integrations/google.py`) and it only ever returns real API responses or an
explicit "not connected" result.

**3. Consistent routing.** All 48 endpoints live under `/api/v1/...`
(see `main.py`) — no separately-prefixed shadow router.

**4. Priority scoring now covers what the ТЗ actually asked for.**
`score_priority()` weighs urgency/importance language, deadline proximity,
project `business_impact`, and (hook is in place for) blocking-task count —
the previous `priorities.py` only used priority + deadline despite a comment
claiming otherwise.

**5. Real Google integration, separated by purpose.**
`/auth/google/login` — identity-only login (existing behavior, kept).
`/integrations/google/connect` — separate OAuth flow requesting Gmail /
Calendar / Drive scopes, storing real tokens in `integration_accounts`, used
by `/calendar/sync` and `/integrations/gmail/scan` (real Gmail API calls →
AI risk/opportunity detection, never fabricated).

## Scope notes / what's intentionally not included

- Voice input and Telegram integration from the old project were dropped —
  they weren't in the ТЗ and were adding surface area without matching spec
  requirements. Easy to re-add as a new `api/v1` router + tool if needed.

## Finished in this pass (previously listed as follow-ups)

- **Embeddings + vector search.** `ai/provider.py::embed_texts()` calls
  OpenAI's embeddings endpoint (Anthropic has none, so that provider and the
  heuristic fallback return `None` on purpose). `knowledge.py::index_document`
  embeds every chunk on ingest; `meetings.py::_find_related_knowledge` runs a
  real pgvector cosine-distance search (`KnowledgeChunk.embedding.cosine_distance(...)`)
  when embeddings are available, and only falls back to keyword matching
  when they're not (no provider configured, or nothing indexed yet) — never
  a silent, permanent stub.
- **Encryption at rest for OAuth tokens.** `core/crypto.py` wraps
  `cryptography`'s Fernet, keyed from `ENCRYPTION_KEY` (falls back to
  `JWT_SECRET` for local dev, but set a dedicated value in production).
  `integrations.py` encrypts on write and decrypts right before each Google
  API call; a token that fails to decrypt (wrong key, or written before
  encryption existed) is treated as "not connected" rather than used as-is.
- **Initial Alembic migration.** `alembic/versions/0001_initial.py` is
  generated directly from the SQLAlchemy models (all 19 enum types, all 18
  tables, all indexes), not hand-transcribed — it was built by compiling
  each model's `CREATE TABLE`/`CREATE TYPE`/`CREATE INDEX` DDL against the
  Postgres dialect, so it can't drift from what `Base.metadata` actually
  declares. Tables are created in dependency order (verified by
  `tests/test_migration_ddl.py` — every `REFERENCES` points at a table
  created earlier in the script). `main.py`'s `create_all` fallback is now
  for first-run local dev only; run `alembic upgrade head` for anything
  else, including CI and production.

## Tests

```bash
cd backend && pip install -r requirements.txt && pytest tests/ -v
```
9 tests: priority scoring (4), token encryption round-trip (3), and
migration-file integrity (2) — all pass with zero external services or API
keys required.

## Structure

```
backend/app/
  models/        SQLAlchemy models (workspace-scoped everywhere)
  schemas/       Pydantic request/response models
  repositories/  generic workspace-scoped CRUD (tenant isolation lives here)
  ai/            provider.py (OpenAI/Anthropic/heuristic), prioritizer.py
                 (shared scoring), tools.py (assistant + inbox actions),
                 context_builder.py (shared "what matters now" query)
  integrations/  real Google Gmail/Calendar/Drive REST client
  api/v1/        one router per resource, all under /api/v1
  workers/       automation_runner.py, scheduled every 15 min
frontend/app/    Next.js 14 app router; (dashboard) group = authenticated shell
```

