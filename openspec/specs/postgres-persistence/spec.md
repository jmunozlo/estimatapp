# PostgreSQL Persistence Specification

## Purpose

PostgresRoomRepository implementing the existing RoomRepository ABC via asyncpg. Full CRUD for rooms, players, votes, and stories with transactional consistency. Connection pool lifecycle managed by the FastAPI app startup/shutdown events.

## Requirements

### Requirement: Database Schema

The system MUST create the following tables with the specified constraints.

| Table | PK | FKs | Unique |
|-------|----|-----|--------|
| rooms | id text (8-char short id) | team_id → teams, created_by → profiles | — |
| room_players | id uuid | room_id → rooms ON DELETE CASCADE, profile_id → profiles | — |
| votes | id uuid | room_id → rooms ON DELETE CASCADE, profile_id → profiles | (room_id, profile_id, round_number) |
| stories | id uuid | room_id → rooms ON DELETE CASCADE | — |

Additional column details: rooms MUST have name, team_id, status (DEFAULT 'voting'), voting_mode (DEFAULT 'public'), voting_scale (DEFAULT 'modified_fibonacci'), custom_scale (jsonb DEFAULT '[]'), story_name (DEFAULT ''), created_by, created_at, ended_at (nullable). All NOT NULL except nullable columns.

When creating a room, voting_scale MUST default to the team's default_scale from the teams table, not hardcoded to 'modified_fibonacci'. The TeamRepository provides the team's default_scale at room creation time.

#### Scenario: Schema migration creates all tables

- GIVEN a fresh Supabase PostgreSQL database
- WHEN the initial migration runs
- THEN all 6 tables exist with correct PKs, FKs, NOT NULL constraints, and defaults

#### Scenario: Cascade delete removes room data

- GIVEN a room with players, votes, and stories
- WHEN the room is deleted
- THEN all associated room_players, votes, and stories are cascade deleted
- AND teams and profiles are NOT affected

### Requirement: Connection Pool

The system MUST manage an asyncpg connection pool with configurable pool_size (default 5) and max_size (default 10), configured via DATABASE_URL env var, initialized on app startup and closed on shutdown.

#### Scenario: Pool initializes on startup

- GIVEN the FastAPI app starts
- WHEN the startup event fires
- THEN an asyncpg pool is created from DATABASE_URL with pool_size=5 and max_size=10

#### Scenario: Pool closes on shutdown

- GIVEN the app is shutting down
- WHEN the shutdown event fires
- THEN all pool connections are gracefully closed

### Requirement: PostgresRoomRepository

The repository MUST implement RoomRepository ABC with all methods operating as async and using the connection pool.

| Method | Description |
|--------|-------------|
| save(room) | Upsert room + players + votes in a single transaction |
| get_by_id(room_id) | Return full Room aggregate with players, votes, story history |
| delete(room_id) | Cascade-delete the room |
| list_all() | List rooms (optionally filtered by team) |
| list_by_team(team_id) | List rooms belonging to a team |
| count_by_team(team_id) | Count active rooms for free tier limit enforcement |

#### Scenario: Full aggregate save and retrieval

- GIVEN a Room aggregate with players, votes, and story history
- WHEN save(room) is called
- THEN a transaction inserts/updates all related rows atomically
- AND get_by_id(room_id) returns the complete aggregate with all associations

#### Scenario: Room does not exist

- GIVEN a room_id that has no matching row
- WHEN get_by_id(room_id) is called
- THEN the method returns None (not raises)

### Requirement: InMemoryRepository Compatibility

The system MUST ensure all existing tests pass with InMemoryRoomRepository unchanged; the repository switcher in RoomManager selects implementation by environment variable.

#### Scenario: Tests use in-memory by default

- GIVEN the test environment with no DATABASE_URL or REPOSITORY=inmemory
- WHEN the test suite creates a RoomManager
- THEN it injects InMemoryRoomRepository
- AND all pre-existing tests pass without modification

#### Scenario: Production uses Postgres

- GIVEN REPOSITORY=postgres and DATABASE_URL set
- WHEN the app starts
- THEN RoomManager injects PostgresRoomRepository with active connection pool
