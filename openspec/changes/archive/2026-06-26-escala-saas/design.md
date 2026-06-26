# Design: Supabase Migration — PG + Auth

## Technical Approach

Replace `InMemoryRoomRepository` with `PostgresRoomRepository` via the existing ABC interface. The ABC goes async — every repository method becomes `async def`. `RoomManager` selects implementation by `REPOSITORY` env var. Auth middleware validates Supabase JWTs at REST/WS entry points. RLS provides DB-layer isolation. Direct cutover (no prod data yet).

## Architecture Decisions

| Decision | Options | Choice | Rationale |
|----------|---------|--------|-----------|
| Pool library | `asyncpg` vs `supabase-py` REST | **asyncpg** | Direct PG protocol — no HTTP overhead. Same latency as in-memory for PK lookups (<5ms). |
| Aggregate save | Full upsert vs diff-based | **Full upsert per table** | Room aggregates are small (~5-50 rows). Diff tracking adds complexity with zero perf gain at this scale. |
| Concurrency control | Optimistic (version col) vs pessimistic (SELECT FOR UPDATE) | **Optimistic with retry** | FOR UPDATE blocks other WS messages for same room. Optimistic: read version, write checks version, retry on conflict. Simpler for current scale. |
| JWKS cache | TTL-based vs fetch-per-request | **TTL-based cache (1hr)** | JWKS keys rarely rotate. Cache in module-level dict, refresh on expiry. No external cache needed. |
| WS auth | Query param JWT vs First WS message | **Query param JWT** | FastAPI WebSocket handshake can inspect query params before accept. Simpler than two-phase handshake. |
| Domain `current_round` | Domain field vs repo-internal | **Repo-internal counter on rooms** | Round tracking is a persistence concern. Domain Room doesn't need it — status + story_name + players[].vote define the current round fully. |

## Data Flow

```
Room Creation (REST):
  Client → POST /rooms (JWT) → AuthMiddleware → CreateRoomUseCase
    → PostgresRoomRepository.save(room) → PG tx (rooms + room_players)
    → 200 {room_id}

WebSocket Connect:
  Client → ws://host/ws/{room_id}/{player_id}?token={jwt}
    → WebSocket handler validates token
    → PG: SELECT room + players + votes + stories
    → Reconstruct Room aggregate
    → ws_manager.connect() → accept
    → Broadcast room_update

Vote Flow (WS):
  Client → {action: "vote", vote: "5"}
    → handler: player.set_vote("5")
    → broadcast_room_state()
    → (vote stored in Room aggregate, not yet in PG)
    → save happens on reveal/reset?  
  
  Wait — this is a key design question. Currently votes are stored directly on Player objects
  in-memory. With PG, when do we persist? Options:
  
  Option A: Persist on every vote (writes on every WS message)
  Option B: Persist only at reveal/reset boundaries
  
  Choice: Option A — persist on every vote. Rationale: if server crashes mid-round,
  votes are not lost. The cost is small (single upsert per vote).

Vote Flow (revised):
  Client → {action: "vote", vote: "5"}
    → handler: player.set_vote("5")
    → PostgresRoomRepository.save(room) — upserts vote row
    → broadcast_room_state()
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/domain/repositories/room_repository.py` | Modify | All methods become async. Add `list_by_team()`, `count_by_team()` |
| `app/domain/aggregates/room.py` | Modify | Add `team_id`, `created_by`, `ended_at` fields |
| `app/infrastructure/repositories/in_memory_room_repository.py` | Modify | Methods become async (trivially — no I/O) |
| `app/infrastructure/repositories/postgres_room_repository.py` | Create | `asyncpg` pool, full aggregate save/load |
| `app/infrastructure/database/__init__.py` | Create | Package init |
| `app/infrastructure/database/connection.py` | Create | Pool lifecycle (init, acquire, close) |
| `app/infrastructure/auth/__init__.py` | Create | Package init |
| `app/infrastructure/auth/jwt_validator.py` | Create | JWKS fetch, cache, decode; FastAPI middleware |
| `app/infrastructure/web/connection_manager.py` | Modify | No changes needed (already async) |
| `app/infrastructure/__init__.py` | Modify | Export PostgresRoomRepository, pool, auth middleware |
| `app/manager.py` | Modify | Select repo by env var; async methods |
| `app/main.py` | Modify | Startup/shutdown pool lifecycle; register auth middleware |
| `app/routes/rooms.py` | Modify | Auth guard on create/delete; async await on repo calls |
| `app/routes/websocket.py` | Modify | JWT validation on connect; async repo calls; persist on vote |
| `supabase/migrations/00001_initial_schema.sql` | Create | 6 tables + RLS policies |
| `pyproject.toml` | Modify | Add `asyncpg>=0.30`, `pyjwt[crypto]>=2.10` |

## Interfaces / Contracts

### RoomRepository ABC (modified)

```python
from abc import ABC, abstractmethod

class RoomRepository(ABC):
    @abstractmethod
    async def save(self, room: Room) -> None: ...

    @abstractmethod
    async def get_by_id(self, room_id: str) -> Room | None: ...

    @abstractmethod
    async def delete(self, room_id: str) -> bool: ...

    @abstractmethod
    async def list_all(self) -> list[Room]: ...

    @abstractmethod
    async def exists(self, room_id: str) -> bool: ...

    @abstractmethod
    async def count(self) -> int: ...

    @abstractmethod
    async def list_by_team(self, team_id: str) -> list[Room]: ...

    @abstractmethod
    async def count_by_team(self, team_id: str) -> int: ...
```

### Connection Pool

```python
# app/infrastructure/database/connection.py
import asyncpg

pool: asyncpg.Pool | None = None

async def init_pool(
    dsn: str,
    min_size: int = 5,
    max_size: int = 10,
) -> None:
    global pool
    pool = await asyncpg.create_pool(dsn, min_size=min_size, max_size=max_size)

async def close_pool() -> None:
    global pool
    if pool:
        await pool.close()
        pool = None

def get_pool() -> asyncpg.Pool:
    assert pool is not None, "Pool not initialized"
    return pool
```

### JWT Validator

```python
# app/infrastructure/auth/jwt_validator.py
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import time

import httpx
from jose import jwk, jwt
from jose.constants import Algorithms

@dataclass
class JWTClaims:
    sub: str          # user_id (UUID)
    email: str | None
    aud: str
    exp: int
    team_id: str | None = None

class JWKSValidator:
    """Validates Supabase JWTs with cached JWKS."""
    
    JWKS_URL: str  # f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
    CACHE_TTL = 3600  # 1 hour
    
    def __init__(self, supabase_url: str, anon_key: str):
        self.supabase_url = supabase_url
        self.anon_key = anon_key
        self._jwks_cache: tuple[dict, float] | None = None  # (keys, fetched_at)
    
    async def _fetch_jwks(self) -> dict:
        """Fetch JWKS with caching."""
        now = time.time()
        if self._jwks_cache and (now - self._jwks_cache[1]) < self.CACHE_TTL:
            return self._jwks_cache[0]
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.supabase_url}/auth/v1/.well-known/jwks.json")
            resp.raise_for_status()
            keys = resp.json()
            self._jwks_cache = (keys, now)
            return keys
    
    async def validate(self, token: str) -> JWTClaims:
        """Validate JWT and return claims. Raises on invalid."""
        keys = await self._fetch_jwks()
        unverified_header = jwt.get_unverified_header(token)
        key = next(k for k in keys["keys"] if k["kid"] == unverified_header["kid"])
        rsa_key = jwk.construct(key)
        payload = jwt.decode(
            token, rsa_key, algorithms=[Algorithms.RS256],
            audience="authenticated",
        )
        return JWTClaims(
            sub=payload["sub"],
            email=payload.get("email"),
            aud=payload["aud"],
            exp=payload["exp"],
        )
```

### PostgresRoomRepository Key Methods

```python
class PostgresRoomRepository(RoomRepository):
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def save(self, room: Room) -> None:
        """Full aggregate save in a single transaction."""
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                # Upsert room
                await conn.execute("""
                    INSERT INTO rooms (id, name, team_id, created_by, status,
                        voting_mode, voting_scale, custom_scale, story_name,
                        current_round, ended_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    ON CONFLICT (id) DO UPDATE SET
                        status = EXCLUDED.status,
                        story_name = EXCLUDED.story_name,
                        current_round = EXCLUDED.current_round,
                        ended_at = EXCLUDED.ended_at
                """, room.id, room.name, getattr(room, 'team_id', None),
                     getattr(room, 'created_by', None),
                     room.status.value, room.voting_mode.value,
                     room.voting_scale, json.dumps(room.custom_scale),
                     room.story_name, _get_current_round(room),
                     getattr(room, 'ended_at', None))
                
                # Upsert players (delete + insert)
                await conn.execute(
                    "DELETE FROM room_players WHERE room_id = $1", room.id)
                for player in room.players.values():
                    await conn.execute("""
                        INSERT INTO room_players (room_id, profile_id, display_name,
                            is_observer, is_facilitator, connected, joined_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """, room.id, player.id, player.name,
                         player.is_observer, player.is_facilitator,
                         player.connected, player.joined_at)
                
                # Upsert current round votes
                for player in room.players.values():
                    if player.vote is not None:
                        await conn.execute("""
                            INSERT INTO votes (room_id, profile_id, round_number, vote_value)
                            VALUES ($1, $2, $3, $4)
                            ON CONFLICT (room_id, profile_id, round_number)
                            DO UPDATE SET vote_value = EXCLUDED.vote_value
                        """, room.id, player.id, _get_current_round(room), player.vote)

    async def get_by_id(self, room_id: str) -> Room | None:
        """Reconstruct full Room aggregate from relational rows."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM rooms WHERE id = $1", room_id)
            if not row:
                return None
            
            room = Room(
                id=row["id"],
                name=row["name"],
                team_id=row["team_id"],
                created_by=row["created_by"],
                status=RoomStatus(row["status"]),
                voting_mode=VotingMode(row["voting_mode"]),
                voting_scale=row["voting_scale"],
                custom_scale=json.loads(row["custom_scale"] or "[]"),
                story_name=row["story_name"] or "",
                created_at=row["created_at"],
                ended_at=row["ended_at"],
            )
            
            # Load players
            player_rows = await conn.fetch(
                "SELECT * FROM room_players WHERE room_id = $1", room_id)
            for pr in player_rows:
                player = Player(
                    id=pr["profile_id"],   # Player.id = profile_id for linked users
                    name=pr["display_name"],
                    is_observer=pr["is_observer"],
                    is_facilitator=pr["is_facilitator"],
                    connected=pr["connected"],
                    joined_at=pr["joined_at"],
                )
                room.add_player(player)
            
            # Load current round votes
            vote_rows = await conn.fetch("""
                SELECT v.* FROM votes v
                WHERE v.room_id = $1 AND v.round_number = $2
            """, room_id, row["current_round"] or 1)
            for vr in vote_rows:
                player = room.get_player(vr["profile_id"])
                if player:
                    player.vote = vr["vote_value"]
            
            # Load story history
            story_rows = await conn.fetch(
                "SELECT * FROM stories WHERE room_id = $1 ORDER BY voted_at",
                room_id)
            for sr in story_rows:
                room.history.append(StoryHistory(
                    story_name=sr["story_name"],
                    votes=sr.get("votes", {}),
                    vote_summary=sr.get("vote_summary", {}),
                    average=sr["average"],
                    rounded_average=sr["rounded_average"],
                    voted_at=sr["voted_at"],
                    round_number=sr["round_number"],
                    is_superseded=sr["is_superseded"],
                ))
            
            return room
```

## Sequence Diagrams

### Room Creation Flow
```
Client                    AuthMiddleware            RoomManager           PG            WSManager
  │                            │                       │                   │               │
  │ POST /rooms (JWT)          │                       │                   │               │
  │ ──────────────────────────►│                       │                   │               │
  │                            │ Validate JWT          │                   │               │
  │                            │──────────────────────►│                   │               │
  │                            │ user.sub              │                   │               │
  │                            │◄──────────────────────│                   │               │
  │                            │ Pass through           │                   │               │
  │                            ├──────────────────────►│ CreateRoomUC      │               │
  │                            │                       │  .execute(name)   │               │
  │                            │                       │    │              │               │
  │                            │                       │    ├─────────────►│ INSERT rooms   │
  │                            │                       │    │              │  + room_players│
  │                            │                       │    │◄─────────────│ OK             │
  │                            │                       │  Room aggregate   │               │
  │                            │◄──────────────────────│                   │               │
  │ 200 {room_id, ...}         │                       │                   │               │
  │◄───────────────────────────│                       │                   │               │
```

### WebSocket Connect Flow
```
Client                    WebSocket Route            PG              WSManager
  │                            │                     │                  │
  │ ws://host/ws/{rid}/{pid}   │                     │                  │
  │   ?token={jwt}             │                     │                  │
  │ ───────────────────────────►                     │                  │
  │                            │ Validate JWT        │                  │
  │                            │────────────────────►│ JWKS fetch/cache │
  │                            │◄────────────────────│ sub, exp, ...    │
  │                            │                     │                  │
  │                            │ If exp/close 4001   │                  │
  │                            │                     │                  │
  │                            │ SELECT room +       │                  │
  │                            │ players + votes +   │                  │
  │                            │ stories FOR room_id │                  │
  │                            │────────────────────►│                  │
  │                            │◄────────────────────│ Full aggregate   │
  │                            │                     │                  │
  │                            │ ws_manager.connect  │                  │
  │                            ├──────────────────────────────────────►│ accept + store  │
  │                            │                     │                  │
  │                            │ broadcast_room_state│                  │
  │                            │                     │                  │
  │◄───────────────────────────│ room_update msg     │                  │
  │                            │                     │                  │
  │         [bidirectional messages]                 │                  │
```

### Vote Flow (WS)
```
Client                    WebSocket Route            PG              WSManager
  │                            │                     │                  │
  │ {"action":"vote",          │                     │                  │
  │  "vote":"5"}               │                     │                  │
  │ ───────────────────────────►                     │                  │
  │                            │ Validate: vote in   │                  │
  │                            │ current_scale       │                  │
  │                            │                     │                  │
  │                            │ player.set_vote(5)  │                  │
  │                            │                     │                  │
  │                            │ PostgresRepo.save() │                  │
  │                            │ ───────────────────►│ TX: upsert vote  │
  │                            │◄────────────────────│ OK               │
  │                            │                     │                  │
  │                            │ broadcast_state()   │                  │
  │                            ├──────────────────────────────────────►│ to all clients  │
  │◄───────────────────────────│ room_update         │                  │
  │◄───────────────────────────│ (same broadcast)    │                  │
  │                            │                     │                  │
```

### First Login Flow
```
Client                  FastAPI            Supabase Auth       PG
  │                        │                    │               │
  │ POST /auth/register    │                    │               │
  │ {email, password}      │                    │               │
  │ ───────────────────────►                    │               │
  │                        │ POST /auth/v1/signup               │
  │                        │ ──────────────────►                │
  │                        │◄─────────────────── {user, token}  │
  │                        │                    │               │
  │                        │ TX:                │               │
  │                        │ INSERT teams       │               │
  │                        │   (slug from email)│               │
  │                        │ ────────────────────────────────►  │
  │                        │◄────────────────────────────────   │
  │                        │                    │               │
  │                        │ INSERT profiles    │               │
  │                        │   (user_id,        │               │
  │                        │    team_id,        │               │
  │                        │    role='admin')   │               │
  │                        │ ────────────────────────────────►  │
  │                        │◄────────────────────────────────   │
  │                        │                    │               │
  │◄───────────────────────│ {access_token, user}               │
```

## Testing Strategy

| Layer | What | How |
|-------|------|-----|
| Unit | PostgresRoomRepository CRUD | Mock `asyncpg.Pool.acquire` with `AsyncMock`. Test that SQL runs in transactions. |
| Unit | JWT validate/expire | Mock JWKS fetch. Test valid, expired, malformed tokens. |
| Unit | InMemoryRepository stays sync-compatible | Existing tests unchanged — methods become async but still return immediately. |
| Integration | Full create → save → load → delete | Local PG via testcontainers or supabase local. Test aggregate hydration. |
| Integration | Auth middleware with TestClient | Create valid JWT (sign with known key), test 401/200 for protected endpoints. |
| E2E | WS connect with JWT | Connect with valid/invalid token in query param, verify accept/close. |
| Existing | All pre-existing tests | Must pass with InMemoryRoomRepository unchanged (async wrappers). |

### Key Test Cases

- `save(room)` → `get_by_id(room_id)` returns identical aggregate
- Two concurrent `save()` calls on same room — optimistic lock conflict
- `get_by_id(nonexistent)` returns None
- Room with 3 players, 2 votes, 1 story — full round-trip
- Delete room with players/votes — cascade verification
- Auth: POST /rooms without JWT → 401
- Auth: WS connect with expired JWT → close 4001

## Environment & Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SUPABASE_URL` | Yes (prod) | — | Supabase project URL (e.g. `https://cqeidzpalepjevotgdbu.supabase.co`) |
| `SUPABASE_ANON_KEY` | Yes (prod) | — | Supabase anon/publishable key for JWT validation |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes (prod) | — | Service role key for admin operations (bypass RLS) |
| `DATABASE_URL` | Yes (prod) | — | Full PG connection string (`postgresql://user:pass@host:port/db`) |
| `REPOSITORY` | No | `inmemory` | `postgres` or `inmemory` |
| `POOL_MIN_SIZE` | No | `5` | Minimum asyncpg pool connections |
| `POOL_MAX_SIZE` | No | `10` | Maximum asyncpg pool connections |
| `SUPABASE_JWT_SECRET` | No (prod) | — | Fallback HS256 key for JWT decode if JWKS unavailable |

## Migration / Rollout

**No data migration needed** — no prod data exists. Direct cutover:

1. Apply SQL migrations via Supabase CLI or `apply_migration` tool
2. Deploy app with `REPOSITORY=postgres` and `DATABASE_URL` set
3. Rollback: set `REPOSITORY=inmemory`, remove `DATABASE_URL`

## Open Questions

- [ ] Player identity model: does anonymous WS join require auth? Current design says anonymous join via link is allowed (no auth). But `room_players` FK references `profiles`, which requires an auth user. Decision: make `profile_id` nullable in `room_players` for anonymous players, using a session-based UUID instead.
- [ ] How does `current_round` increment in the domain? If the repo tracks it as a column on `rooms`, the domain needs to signal round transitions. Options: (a) add `current_round` to Room aggregate, (b) infer from max round in votes table on load. Prefer (b) — load-time inference avoids domain pollution.
- [ ] Optimistic concurrency version: add `version` integer column to `rooms`? Simple integer incremented on every `save()`. The repo checks `WHERE version = $1` on write, raises on mismatch. This protects against two WS messages overwriting each other.
