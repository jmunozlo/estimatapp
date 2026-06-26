# Proposal: Supabase Migration (PG + Auth) — Phase 1

## Intent

EstimatApp has no persistence (rooms lost on restart), no auth, and no way to enforce limits. Without these, it cannot operate as a SaaS. This phase migrates from in-memory to Supabase PostgreSQL and adds auth — the foundation for all future phases (Stripe, Next.js).

## Scope

### In Scope
- Supabase PostgreSQL as persistent storage (PostgresRoomRepository)
- Supabase Auth (email + Google OAuth) with JWT validation
- Team-based multi-tenant model with RLS policies
- Required auth for creating rooms; anonymous join via link
- Migration of RoomManager and all REST/WS routes to async PG reads
- SQL migrations for initial schema (teams, profiles, rooms, room_players, votes, stories)
- Connection pool management (asyncpg)

### Out of Scope
- Stripe subscriptions and payments (Phase 2)
- Next.js frontend (Phase 3)
- UI redesign or component migration
- Horizontal scaling / Redis cache
- Supabase Realtime (keeping FastAPI WebSockets)

## Capabilities

### New Capabilities
- `auth`: User authentication via Supabase Auth (email + Google OAuth), JWT validation middleware in FastAPI, profile creation on first login
- `team-management`: Team-based multi-tenant isolation with profiles, membership roles (admin/member), and team-scoped operations
- `postgres-persistence`: PostgresRoomRepository implementing RoomRepository ABC, async connection pool, full CRUD for rooms/players/votes/stories
- `rls-authorization`: Row Level Security policies enforcing team-level data isolation across all tables

### Modified Capabilities
- None — this is the first spec-level capability for the project. Existing code is pre-alpha with no formal specs.

## Approach

Replace `InMemoryRoomRepository` with `PostgresRoomRepository` via the existing ABC interface. Inject via `RoomManager` based on environment (production → PG, dev/tests → in-memory). Keep FastAPI WebSockets — no Supabase Realtime. Auth middleware validates JWTs at REST endpoints and WS connect. RLS enforces team isolation at the DB layer. Cutover is direct (no dual-write) since no prod data exists.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/infrastructure/repositories/` | New | PostgresRoomRepository, connection pool |
| `app/infrastructure/auth/` | New | JWT validator, middleware |
| `app/infrastructure/__init__.py` | Modified | Export new repo + auth modules |
| `app/manager.py` | Modified | Inject repository by env; async methods |
| `app/main.py` | Modified | Startup/shutdown pool lifecycle; register auth middleware |
| `app/routes/rooms.py` | Modified | Auth required for create/delete; async repo calls |
| `app/routes/websocket.py` | Modified | JWT validation on connect; async PG reads |
| `supabase/migrations/` | New | Initial schema SQL migrations |
| `pyproject.toml` | Modified | Add asyncpg + supabase-py deps |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| WS latency from PG reads | Low | Queries are simple PK lookups; cache with Redis later if needed |
| Pool exhaustion under load | Low | Pool size 5-10; monitor with pgBouncer if needed |
| JWT val blocks WS connect | Medium | Validate once at connect, not per message; cache JWKS |
| Sync→async method ripple | Medium | RoomRepository methods become async; domain ABC changes propagate to InMemoryRepo too |

## Rollback Plan

1. Revert `RoomManager` to inject `InMemoryRoomRepository`
2. Remove auth middleware from `app/main.py`
3. Remove pool init/shutdown in startup/events
4. Revert `pyproject.toml` deps — all rooms go back to in-memory

## Dependencies

- Supabase project (configured with `opencode.json` — project `uwtnajjterqdlamjzzuo`)
- `asyncpg` for async PostgreSQL connection (or `supabase-py` with REST fallback)
- JWKS endpoint from Supabase Auth for token validation

## Success Criteria

- [ ] All existing tests pass with no modifications (tests use InMemoryRepository)
- [ ] PostgresRoomRepository coverage ≥ 85% (integration tests with testcontainers or mock PG)
- [ ] Rooms persist across server restart (create → restart → GET returns room)
- [ ] Unauthenticated requests to POST/DELETE /rooms return 401
- [ ] WebSocket connect with invalid JWT is rejected
- [ ] WebSocket broadcasts complete with latency < 200ms (measured)
