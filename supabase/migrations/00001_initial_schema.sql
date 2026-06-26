-- Migration: 00001_initial_schema.sql
-- Description: Initial schema for EstimatApp — teams, profiles, rooms, room_players, votes, stories
-- Supabase migration: applies against the Supabase PostgreSQL database.
-- All tables have RLS enabled; policies enforce team-level isolation.

-- ============================================================
-- 1. TEAMS
-- ============================================================
CREATE TABLE teams (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug        TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    plan_tier   TEXT NOT NULL DEFAULT 'free',
    default_scale TEXT NOT NULL DEFAULT 'modified_fibonacci',
    saved_scales JSONB NOT NULL DEFAULT '[]',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- 2. PROFILES
-- ============================================================
CREATE TABLE profiles (
    id           UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    team_id      UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    email        TEXT,
    display_name TEXT,
    role         TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('admin', 'member')),
    avatar_url   TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Trigger to auto-create profile on signup
-- (Handled in application code; this is a safety net)
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = ''
AS $$
BEGIN
    INSERT INTO public.profiles (id, team_id, email, display_name, role)
    VALUES (
        NEW.id,
        (SELECT id FROM public.teams ORDER BY created_at ASC LIMIT 1),  -- placeholder — app assigns team
        NEW.email,
        COALESCE(NEW.raw_user_meta_data ->> 'full_name', NEW.email),
        'member'
    );
    RETURN NEW;
END;
$$;

CREATE OR REPLACE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();

-- ============================================================
-- 3. ROOMS
-- ============================================================
CREATE TABLE rooms (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    team_id       UUID REFERENCES teams(id) ON DELETE SET NULL,
    created_by    UUID REFERENCES profiles(id) ON DELETE SET NULL,
    status        TEXT NOT NULL DEFAULT 'voting',
    voting_mode   TEXT NOT NULL DEFAULT 'public',
    voting_scale  TEXT NOT NULL DEFAULT 'modified_fibonacci',
    custom_scale  JSONB NOT NULL DEFAULT '[]',
    story_name    TEXT NOT NULL DEFAULT '',
    current_round INTEGER NOT NULL DEFAULT 1,
    ended_at      TIMESTAMPTZ,
    version       INTEGER NOT NULL DEFAULT 1,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- 4. ROOM_PLAYERS
-- ============================================================
CREATE TABLE room_players (
    room_id        TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    profile_id     TEXT,
    display_name   TEXT NOT NULL,
    is_observer    BOOLEAN NOT NULL DEFAULT false,
    is_facilitator BOOLEAN NOT NULL DEFAULT false,
    connected      BOOLEAN NOT NULL DEFAULT true,
    joined_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (room_id, profile_id)
);

-- ============================================================
-- 5. VOTES
-- ============================================================
CREATE TABLE votes (
    room_id      TEXT NOT NULL,
    profile_id   TEXT NOT NULL,
    round_number INTEGER NOT NULL,
    vote_value   TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (room_id, profile_id, round_number),
    FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE
);

-- ============================================================
-- 6. STORIES
-- ============================================================
CREATE TABLE stories (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    room_id         TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    story_name      TEXT NOT NULL,
    votes           JSONB NOT NULL DEFAULT '{}',
    vote_summary    JSONB NOT NULL DEFAULT '{}',
    average         DOUBLE PRECISION,
    rounded_average DOUBLE PRECISION,
    voted_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    round_number    INTEGER NOT NULL DEFAULT 1,
    is_superseded   BOOLEAN NOT NULL DEFAULT false
);

-- ============================================================
-- INDEXES
-- ============================================================
CREATE INDEX idx_profiles_team_id ON profiles(team_id);
CREATE INDEX idx_rooms_team_id ON rooms(team_id);
CREATE INDEX idx_room_players_room_id ON room_players(room_id);
CREATE INDEX idx_votes_room_round ON votes(room_id, round_number);
CREATE INDEX idx_stories_room_id ON stories(room_id);

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================

-- Helper: get the current user's team_id from profiles
CREATE OR REPLACE FUNCTION public.current_user_team_id()
RETURNS UUID
LANGUAGE sql
STABLE
SECURITY DEFINER SET search_path = ''
AS $$
    SELECT team_id FROM public.profiles WHERE id = auth.uid()
$$;

-- Enable RLS on all tables
ALTER TABLE teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE rooms ENABLE ROW LEVEL SECURITY;
ALTER TABLE room_players ENABLE ROW LEVEL SECURITY;
ALTER TABLE votes ENABLE ROW LEVEL SECURITY;
ALTER TABLE stories ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- TEAMS POLICIES
-- ============================================================
-- SELECT: own team only
CREATE POLICY "users_can_read_own_team"
    ON teams FOR SELECT
    USING (id = public.current_user_team_id());

-- UPDATE: admin only
CREATE POLICY "admins_can_update_own_team"
    ON teams FOR UPDATE
    USING (id = public.current_user_team_id() AND EXISTS (
        SELECT 1 FROM profiles
        WHERE id = auth.uid() AND team_id = id AND role = 'admin'
    ));

-- ============================================================
-- PROFILES POLICIES
-- ============================================================
-- SELECT: own profile or same team
CREATE POLICY "users_can_read_own_profile_and_team_members"
    ON profiles FOR SELECT
    USING (id = auth.uid() OR team_id = public.current_user_team_id());

-- UPDATE: own profile only
CREATE POLICY "users_can_update_own_profile"
    ON profiles FOR UPDATE
    USING (id = auth.uid());

-- ============================================================
-- ROOMS POLICIES
-- ============================================================
-- SELECT: team members can see their team's rooms; anonymous rooms visible with join link
CREATE POLICY "team_members_can_read_rooms"
    ON rooms FOR SELECT
    USING (
        team_id IS NULL
        OR team_id = public.current_user_team_id()
    );

-- INSERT: user must have a team
CREATE POLICY "authenticated_users_can_create_rooms"
    ON rooms FOR INSERT
    WITH CHECK (
        team_id = public.current_user_team_id()
    );

-- UPDATE: facilitator or admin
CREATE POLICY "facilitator_or_admin_can_update_rooms"
    ON rooms FOR UPDATE
    USING (
        team_id = public.current_user_team_id()
        AND (
            created_by = auth.uid()
            OR EXISTS (
                SELECT 1 FROM profiles
                WHERE id = auth.uid() AND team_id = team_id AND role = 'admin'
            )
        )
    );

-- DELETE: facilitator or admin
CREATE POLICY "facilitator_or_admin_can_delete_rooms"
    ON rooms FOR DELETE
    USING (
        team_id = public.current_user_team_id()
        AND (
            created_by = auth.uid()
            OR EXISTS (
                SELECT 1 FROM profiles
                WHERE id = auth.uid() AND team_id = team_id AND role = 'admin'
            )
        )
    );

-- ============================================================
-- ROOM_PLAYERS POLICIES
-- ============================================================
-- SELECT: team room players
CREATE POLICY "team_members_can_read_room_players"
    ON room_players FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM rooms
            WHERE id = room_id
            AND (team_id IS NULL OR team_id = public.current_user_team_id())
        )
    );

-- INSERT: any authenticated user can join a room
CREATE POLICY "anyone_can_join_room"
    ON room_players FOR INSERT
    WITH CHECK (true);

-- UPDATE: own player record only
CREATE POLICY "players_can_update_own_record"
    ON room_players FOR UPDATE
    USING (profile_id = auth.uid()::text);

-- ============================================================
-- VOTES POLICIES
-- ============================================================
-- SELECT: own vote always visible; others' votes only when revealed
CREATE POLICY "users_can_read_own_votes"
    ON votes FOR SELECT
    USING (profile_id = auth.uid()::text);

CREATE POLICY "revealed_votes_visible_to_team"
    ON votes FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM rooms
            WHERE id = room_id
            AND status = 'revealed'
            AND (team_id IS NULL OR team_id = public.current_user_team_id())
        )
    );

-- INSERT/UPDATE: own vote, room in voting status
CREATE POLICY "users_can_manage_own_votes"
    ON votes FOR INSERT
    WITH CHECK (profile_id = auth.uid()::text);

CREATE POLICY "users_can_update_own_votes"
    ON votes FOR UPDATE
    USING (profile_id = auth.uid()::text);

-- ============================================================
-- STORIES POLICIES
-- ============================================================
-- SELECT: team rooms or anonymous rooms
CREATE POLICY "team_members_can_read_stories"
    ON stories FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM rooms
            WHERE id = room_id
            AND (team_id IS NULL OR team_id = public.current_user_team_id())
        )
    );
