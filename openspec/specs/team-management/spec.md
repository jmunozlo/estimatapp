# Team Management Specification

## Purpose

Team-based multi-tenant isolation with membership roles (admin/member). Every user belongs to exactly one team, created automatically on first login. No team switching in v1.

## Requirements

### Requirement: Team Auto-Creation on First Login

The system MUST create a team for each new user on first login and bind the user's profile to that team.

| Table | Column | Type | Constraints |
|-------|--------|------|-------------|
| teams | id | uuid | PK, DEFAULT gen_random_uuid() |
| teams | name | text | NOT NULL |
| teams | slug | text | NOT NULL, UNIQUE |
| teams | plan_tier | text | NOT NULL, DEFAULT 'free' |
| teams | default_scale | text | NOT NULL, DEFAULT 'modified_fibonacci' |
| teams | saved_scales | jsonb | NOT NULL, DEFAULT '[]' |
| teams | created_at | timestamptz | DEFAULT now() |

#### Scenario: User registers, team is created

- GIVEN a new user registering for the first time
- WHEN POST /auth/register succeeds
- THEN a new team is inserted with name "user's team" and slug from the user's email
- AND the user's profile is linked to that team via team_id

#### Scenario: Team slug collision is handled

- GIVEN two users with emails that would produce the same slug
- WHEN the second user registers
- THEN the system appends a suffix (e.g. -2) to ensure slug uniqueness

### Requirement: Role-Based Access Control

The system MUST enforce two roles on team members: admin (can manage team settings and members) and member (can create rooms and join rooms within the team).

| Table | Column | Type | Constraints |
|-------|--------|------|-------------|
| profiles | id | uuid | PK, REFERENCES auth.users |
| profiles | display_name | text | NULLABLE |
| profiles | avatar_url | text | NULLABLE |
| profiles | team_id | uuid | FK REFERENCES teams, NOT NULL |
| profiles | role | text | NOT NULL, DEFAULT 'member', CHECK IN ('admin','member') |
| profiles | created_at | timestamptz | DEFAULT now() |

#### Scenario: Admin can update team settings

- GIVEN a user with role 'admin' on their team
- WHEN PATCH /teams/{id} is called with team settings
- THEN the server updates the team record and returns the updated team

#### Scenario: Member cannot update team settings

- GIVEN a user with role 'member'
- WHEN PATCH /teams/{id} is called
- THEN the server returns 403 Forbidden

### Requirement: Team Endpoints

The system MUST expose endpoints for reading team info and listing members.

| Endpoint | Auth | Description |
|----------|------|-------------|
| GET /teams/{id} | Yes | Team details (name, slug, plan_tier, default_scale, saved_scales) |
| PATCH /teams/{id} | Yes (admin) | Update team name, default_scale, saved_scales |
| GET /teams/{id}/members | Yes | List team members with roles |

#### Scenario: Get own team info

- GIVEN an authenticated user
- WHEN GET /teams/{my_team_id} is called
- THEN the server returns team details including name, slug, and plan_tier

#### Scenario: Get another team's info returns 403

- GIVEN an authenticated user
- WHEN GET /teams/{other_team_id} is called
- THEN the server returns 403 Forbidden (RLS enforces team isolation)

### Requirement: Team Default Scale Preference

The system MUST allow each team to set a default voting scale. When a new room is created, it uses the team's default_scale instead of always defaulting to "modified_fibonacci". Teams can also save custom scales for reuse.

| Column | Type | Description |
|--------|------|-------------|
| default_scale | text | Scale name (predefined key or 'custom') |
| saved_scales | jsonb | Array of {name: str, values: [str]} for saved custom scales |

#### Scenario: New room uses team's default scale

- GIVEN a team with default_scale = 't_shirt'
- WHEN a member creates a new room
- THEN the room's voting_scale is 't_shirt'
- AND custom_scale is empty

#### Scenario: Admin changes team default scale

- GIVEN an admin user
- WHEN PATCH /teams/{id} sets default_scale to 'powers_of_2'
- THEN all NEW rooms will use 'powers_of_2' by default
- AND existing rooms keep their current scale

#### Scenario: Save custom scale for reuse

- GIVEN a team with saved_scales = []
- WHEN an admin saves a custom scale with name "Sprint Values" and values ["1","2","3","5","8"]
- THEN the new scale is appended to saved_scales
- AND it becomes selectable when creating new rooms

#### Scenario: Delete a saved custom scale

- GIVEN a team with a saved custom scale "Sprint Values"
- WHEN an admin deletes it from saved_scales
- THEN it is removed from the list
- AND rooms already using it keep working (they store their own custom_scale)

### Requirement: Free Tier Plan Limits

The system MUST enforce plan_tier limits: free tier allows up to 5 active rooms and 10 members.

#### Scenario: Free tier room limit reached

- GIVEN a team on the 'free' plan with 5 active rooms
- WHEN a member tries to create room number 6
- THEN the server returns 402 Payment Required with a message about upgrading

#### Scenario: Member count within limit

- GIVEN a team on the 'free' plan with 8 existing members
- WHEN an admin invites 2 more members
- THEN the invite is accepted (total would be 10, within limit)
