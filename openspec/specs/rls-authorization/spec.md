# RLS Authorization Specification

## Purpose

Row Level Security policies enforcing team-level data isolation across all tables. The auth middleware sets `request.user` from JWT; RLS policies at the database layer prevent cross-team data access as a defense-in-depth measure.

## Requirements

### Requirement: RLS Enabled on All Tables

The system MUST enable RLS on teams, profiles, rooms, room_players, votes, and stories, and MUST provide policies enforcing team isolation.

| Table | SELECT policy | INSERT policy | UPDATE policy | DELETE policy |
|-------|--------------|---------------|---------------|---------------|
| teams | Own team only | — (server-side) | Admin only | — |
| profiles | Own + team members | — (server-side) | Own only | — |
| rooms | Team members | team_id matches user's team | Facilitator or admin | Facilitator or admin |
| room_players | Team room players | Any (join) | Own player only | — |
| votes | Revealed rooms only | Own vote | Own vote (unrevealed) | — |
| stories | Team rooms | — (server-side) | — | — |

#### Scenario: User can only see own team rooms

- GIVEN two teams, each with one room
- WHEN a user from team A calls list_by_team()
- THEN only team A's room is returned
- AND the room from team B is not visible

#### Scenario: Admin can update team settings

- GIVEN a user with role='admin' on team A
- WHEN they UPDATE teams SET name WHERE id = team_a_id
- THEN the update succeeds (RLS policy allows admin updates)

#### Scenario: Member cannot update team settings

- GIVEN a user with role='member' on team A
- WHEN they UPDATE teams SET name WHERE id = team_a_id
- THEN RLS blocks the update (returns 0 rows affected)

### Requirement: Auth Context Propagation

The system MUST propagate the authenticated user context from JWT middleware into the database session for RLS evaluation.

#### Scenario: JWT user ID maps to RLS current user

- GIVEN an authenticated request with a valid JWT containing user_id
- WHEN any database query runs within that request
- THEN `auth.uid()` resolves to the JWT's user_id for RLS evaluation

#### Scenario: Public endpoint bypasses RLS

- GIVEN an unauthenticated request to GET /rooms/{id}?join_link=xyz
- WHEN the room is accessed via a valid join link
- THEN the query uses service_role to bypass RLS and read the specific room

### Requirement: Vote Visibility Rules

The system MUST restrict vote visibility to after the room is revealed; unrevealed votes are only visible to the voter.

#### Scenario: Voter sees own unrevealed vote

- GIVEN a room in 'voting' status
- WHEN a user queries votes for their own profile_id
- THEN their own vote_value is returned

#### Scenario: Other members cannot see unrevealed votes

- GIVEN a room in 'voting' status
- WHEN a user queries votes for other members' profile_ids
- THEN they see only that the vote exists but not the vote_value (NULL or obscured)
