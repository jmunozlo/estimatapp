# Tasks: Supabase Migration — PG + Auth

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 850–1000 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (Foundation) → PR 2 (Repo + Auth) → PR 3 (Integration) |
| Delivery strategy | ask-on-risk |
| Chain strategy | stacked-to-main |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Schema, deps, pool, domain ABC, InMemory async | PR 1 | base=main; tests included |
| 2 | PostgresRoomRepository, JWT validator, wiring routes | PR 2 | base=main or PR1 branch; tests included |
| 3 | Integration + E2E tests | PR 3 | base=main or PR2 branch; depends on PR 2 |

## Phase 1: Foundation (PR 1) — ✅ COMPLETE

- [x] 1.1 Create `supabase/migrations/00001_initial_schema.sql` (6 tables + RLS policies)
- [x] 1.2 Add `asyncpg>=0.30`, `pyjwt[crypto]>=2.10` to `pyproject.toml`
- [x] 1.3 Create `app/infrastructure/database/__init__.py` and `connection.py` with pool init/acquire/close
- [x] 1.4 Convert `RoomRepository` ABC to async def; add `list_by_team()`, `count_by_team()`
- [x] 1.5 Add `team_id`, `created_by`, `ended_at` fields to `Room` aggregate
- [x] 1.6 Wrap `InMemoryRoomRepository` methods with async stubs
- [x] 1.7 **Test**: Pool init/close (mock asyncpg); InMemory async compat with existing tests

## Phase 2: PostgresRepo + Auth + Wiring (PR 2) — ✅ COMPLETE

- [x] 2.1 Create `postgres_room_repository.py` — full save/load with tx, optimistic lock
- [x] 2.2 Create `jwt_validator.py` — JWKS fetch with 1hr TTL cache, RS256 decode
- [x] 2.3 Register FastAPI auth middleware (protect /rooms POST/DELETE, skip /auth/*)
- [x] 2.4 Update `manager.py` — select repo by REPOSITORY env var; async methods
- [x] 2.5 Update `main.py` — pool init/close lifecycle; mount auth middleware
- [x] 2.6 Update `routes/rooms.py` — auth guard on create/delete, async repo calls
- [x] 2.7 Update `routes/websocket.py` — validate JWT on connect; persist vote on WS message
- [x] 2.8 **Test**: PostgresRepo CRUD mock-based; optimistic lock conflict raises
- [x] 2.9 **Test**: JWT valid/expired/malformed; route 401 without token; WS 4001 on bad JWT

## Phase 3: Integration + Verification (PR 3) — ✅ COMPLETE

- [x] 3.1 **Integration**: Full save→load→verify identical aggregate; 3p/2v/1s round-trip
- [x] 3.2 **Integration**: Cascade delete removes all room data
- [x] 3.3 **Integration**: Auth middleware with TestClient — sign test JWT, verify 401/200
- [x] 3.4 **Integration**: WS connect with valid/invalid JWT, verify accept/close 4001
- [x] 3.5 Verify all pre-existing tests pass with InMemoryRoomRepository
