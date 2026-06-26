# Auth Specification

## Purpose

User authentication via Supabase Auth (email/password + Google OAuth), JWT validation middleware in FastAPI, and automatic profile creation on first login. Room creation/management requires auth; joining rooms via link does not.

## Requirements

### Requirement: Auth Endpoints

The system MUST expose auth endpoints for registration, login, logout, and profile retrieval.

| Endpoint | Auth | Request | Response |
|----------|------|---------|----------|
| POST /auth/register | No | `{email, password}` | `{access_token, user}` |
| POST /auth/login | No | `{email, password}` | `{access_token, user}` |
| POST /auth/logout | Yes | — | `{ok: true}` |
| GET /auth/me | Yes | — | `{user: Profile}` |

#### Scenario: Register new user

- GIVEN a new email and password
- WHEN POST /auth/register is called
- THEN Supabase Auth creates the user AND a profiles row is inserted AND an access_token is returned

#### Scenario: Login with wrong password returns 401

- GIVEN an existing email with wrong password
- WHEN POST /auth/login is called
- THEN the server returns 401 and does NOT create a session token

### Requirement: JWT Validation Middleware

A FastAPI middleware MUST validate Supabase JWTs via JWKS on every request except /auth/* routes.

#### Scenario: Valid JWT passes middleware

- GIVEN a request with `Authorization: Bearer {valid_jwt}`
- WHEN any protected endpoint is called
- THEN the middleware decodes the JWT, injects `request.user`, and passes to the handler

#### Scenario: Missing or malformed token returns 401

- GIVEN a request with no Authorization header or an unparseable token
- WHEN POST /rooms is called
- THEN the server returns 401 with `{"detail": "Invalid or expired token"}`

### Requirement: WebSocket JWT Validation

The system MUST validate JWT as a query parameter on WebSocket connect and reject invalid tokens with close code 4001.

#### Scenario: WS connect with valid JWT

- GIVEN a client with a valid Supabase JWT
- WHEN connecting to `ws://host/ws?token={jwt}`
- THEN the connection is accepted and `request.user` is set from the token

#### Scenario: WS connect with expired JWT

- GIVEN a client with an expired JWT
- WHEN connecting to `ws://host/ws?token={expired_token}`
- THEN the server closes with code 4001 and the connection is rejected

### Requirement: Profile Auto-Creation

The system MUST auto-create a profiles row for every new Supabase Auth user on first login, and MUST NOT create duplicates for existing users.

#### Scenario: First-ever login creates profile

- GIVEN a brand new Supabase Auth user (no existing profile)
- WHEN POST /auth/register succeeds
- THEN a profiles row is inserted with the user's id, default role 'member', and an auto-created team_id

#### Scenario: Subsequent login skips profile creation

- GIVEN an existing user with a profile row
- WHEN POST /auth/login succeeds
- THEN the server returns the existing profile and does NOT insert a new row
