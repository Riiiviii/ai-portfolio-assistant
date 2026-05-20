# Design Notes

Decisions made during initial development, with reasoning preserved for
future reference. Captures intentional v1 scope and the conditions under
which each decision should be revisited.

## Request/response shape

`ChatRequest` and `ChatResponse` are intentionally minimal: a message
string in plus a session ID, a response string out.

The user message is not echoed in the response payload. The frontend
already holds the input it sent, and the locked-input UI guarantees only
one in-flight request at a time, so request-response matching is implicit.

**Revisit if:** the UI moves away from locked-input semantics, or
streaming/concurrent requests are introduced. At that point a
`request_id` field becomes the right pattern, not echoing the message.

## Conversation memory

Implemented via the OpenAI Agents SDK's `SQLiteSession`. Each `/chat`
request instantiates a session keyed by `session_id` (UUID v4) from the
request body. The SDK transparently fetches prior conversation items
before each turn and persists new items after.

Storage is a SQLite file at `/data/sessions.db` inside the container.
The `/data` directory is owned by the non-root container user
(`ai-chatbot`) and created in the Dockerfile.

Session IDs are validated using Pydantic's `UUID4` type — invalid IDs
return 422 before the request reaches the agent.

**TTL strategy:** none explicit. Sessions persist for the lifetime of
the Fly machine. When the machine auto-stops after idle, `/data` is
wiped and all sessions reset. This is the natural TTL for a portfolio
chatbot with infrequent traffic.

**Revisit if:**
- A Fly Volume is mounted at `/data`, making the SQLite file
  persistent across machine recycles. Explicit cleanup would then be
  needed (cron-style task or per-request cleanup of rows older than
  N minutes).
- Traffic grows past the point where session accumulation matters.
  Move to Redis (Upstash on Fly) for native TTL support and
  multi-process session sharing.
- The SDK adds compaction or summarisation features that would benefit
  long-running conversations.

## Agent instance scoping

A single shared `GraduateAgent` instance lives on `app.state` and is
used for every request. Per-request session state is held in the
`SQLiteSession` keyed by the request's `session_id`, not on the agent
itself. The shared-agent + per-request-session pattern is the
Agents SDK's intended usage.

**Revisit if:** the agent's configuration ever needs to vary per
request (e.g., different system prompts per user type).

## Configuration

Environment variables are loaded via a hand-rolled `Settings` class in
`settings.py`. Currently exposes `mcp_server_url` and `cors_origins`,
both required via a `_required()` helper that crashes startup if a
variable is missing.

`CORS_ORIGINS` is comma-separated; values are split and stripped of
whitespace at load time.

**Revisit when:** the env var count grows past ~5, validation becomes
non-trivial (typed values, optional vs required complexity), or
inter-service config is introduced. At that point migrate to
`pydantic-settings` (`BaseSettings`) — same library family already in
use for request/response models.

## CORS configuration

`CORSMiddleware` allows `GET` and `POST` from configured origins, with
`allow_credentials=False` and `allow_headers=["*"]`. The chatbot is
stateless from an auth perspective (no cookies, no auth headers), so
credentials are deliberately disabled.

`allow_headers=["*"]` is acceptable for v1 because the only route
accepts a JSON body validated by Pydantic — header content does not
influence handler logic.

**Revisit if:** authentication is introduced (credentials may need to
become `True` and origins must remain exact rather than wildcard), or
sensitive endpoints are added that warrant least-privilege header
restriction (`["Content-Type", "Authorization"]`).

## Schemas directory

Pydantic models live in `schemas/` grouped by domain (`schemas/chat.py`).
Models are kept here rather than alongside their consuming routes, to
prepare for reuse as the project adds endpoints.

**Revisit if:** the project remains at one schema file for a long time
and the directory feels like over-structure. For now, the structure is
preserved in anticipation of additional endpoints.

## Container process orchestration

The container runs two processes side-by-side: FastAPI (port 8000,
public) and FastMCP (port 8001, container-local only). Both are started
by `entrypoint.sh` which:

1. Starts the FastMCP server in the background, capturing its PID.
2. Polls TCP port 8001 with a bash-native probe (`/dev/tcp`) until the
   MCP server is accepting connections, with a 30-attempt cap.
3. Starts FastAPI in the background, capturing its PID.
4. `wait -n` exits as soon as either process exits, with that process's
   status code propagated to the container.
5. A `trap` handler forwards SIGTERM/SIGINT to both child processes for
   graceful shutdown.

**Revisit if:** the MCP server is needed by additional services, at
which point it moves to its own container with Docker Compose or a
separate Fly app.

## HEALTHCHECK

Not defined in the Dockerfile. Fly.io performs its own HTTP health
checks against `/` as configured in `fly.toml`. A Dockerfile
`HEALTHCHECK` would be redundant for this deployment target.

**Revisit if:** deploying to a platform that doesn't perform its own
health checks (e.g., self-hosted Docker, bare ECS).

## Out of scope for v1

- Authentication (no user accounts; chatbot is public)
- Rate limiting beyond the OpenAI spending cap (acceptable risk for a
  portfolio project; spending cap acts as a hard ceiling on abuse)
- Streaming responses (tokens delivered as one block)
- Multi-agent orchestration (single agent only)
- Observability beyond standard logging
- Persistent sessions across machine recycles (natural TTL via Fly
  auto-stop is sufficient for current traffic)