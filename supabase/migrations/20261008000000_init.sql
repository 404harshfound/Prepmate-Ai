-- PrepMate AI: core schema
--
-- Security model, in three layers:
--   1. Everything lives in the `app` schema, which Supabase's public Data API
--      does not expose. The browser can only reach this data through our API.
--   2. Row-level security is on for every table, and no policy means no access.
--      Signed-in users may read their own rows; they may write almost nothing.
--   3. The API logs in as `prepmate_api`, a role that owns nothing. It steps
--      down to `authenticated` for user requests, and uses its own narrow
--      grants only for work a user must not do (saving scores, counting usage).

create schema if not exists app;

-- The API's login role. It is created without a password and cannot log in
-- until one is set by hand (see README), so no credential lives in git.
do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'prepmate_api') then
    create role prepmate_api nologin noinherit;
  end if;
end
$$;

-- prepmate_api may *become* authenticated, but does not inherit its rights.
grant authenticated to prepmate_api with inherit false, set true;

revoke all on schema app from public;
grant usage on schema app to authenticated, prepmate_api;

-- Tables created here later must not pick up default grants by accident.
alter default privileges in schema app revoke all on tables from public, anon, authenticated;
alter default privileges in schema app revoke all on sequences from public, anon, authenticated;
alter default privileges in schema app revoke execute on functions from public, anon, authenticated;

create function app.touch_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.updated_at := now();
  return new;
end
$$;

------------------------------------------------------------------------------
-- profiles: one row per user
------------------------------------------------------------------------------
create table app.profiles (
  user_id          uuid primary key references auth.users (id) on delete cascade,
  display_name     text check (char_length(display_name) between 1 and 80),
  target_role      text check (char_length(target_role) between 1 and 80),
  experience_level text not null default 'student'
                   check (experience_level in ('student', 'fresher', 'experienced')),
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);

create trigger profiles_touch_updated_at
  before update on app.profiles
  for each row execute function app.touch_updated_at();

alter table app.profiles enable row level security;

-- Column-level grants: a user can never write user_id or the timestamps
-- of an existing row, whatever the request body says.
grant select on app.profiles to authenticated;
grant insert (user_id, display_name) on app.profiles to authenticated;
grant update (display_name, target_role, experience_level) on app.profiles to authenticated;

create policy profiles_select_own on app.profiles
  for select to authenticated
  using (user_id = (select auth.uid()));

create policy profiles_insert_own on app.profiles
  for insert to authenticated
  with check (user_id = (select auth.uid()));

create policy profiles_update_own on app.profiles
  for update to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));

------------------------------------------------------------------------------
-- questions: the question bank
-- Users get no access at all: reference answers must never reach the browser.
-- (The embedding column for similarity search is added with the question
-- bank itself, in a later migration.)
------------------------------------------------------------------------------
create table app.questions (
  id               uuid primary key default gen_random_uuid(),
  round_type       text not null check (round_type in ('hr', 'behavioural', 'technical', 'aptitude')),
  topic            text not null check (char_length(topic) between 1 and 80),
  difficulty       smallint not null check (difficulty between 1 and 3),
  prompt           text not null check (char_length(prompt) between 10 and 1000),
  reference_answer text not null check (char_length(reference_answer) between 10 and 6000),
  source           text check (char_length(source) <= 200),
  is_active        boolean not null default true,
  created_at       timestamptz not null default now()
);

create index questions_pick_idx on app.questions (round_type, difficulty) where is_active;

alter table app.questions enable row level security;

grant select on app.questions to prepmate_api;

create policy questions_api_read on app.questions
  for select to prepmate_api
  using (true);

------------------------------------------------------------------------------
-- practice_sessions: one sitting of practice
------------------------------------------------------------------------------
create table app.practice_sessions (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references auth.users (id) on delete cascade,
  round_type   text not null check (round_type in ('hr', 'behavioural', 'technical', 'aptitude')),
  status       text not null default 'in_progress'
               check (status in ('in_progress', 'completed', 'abandoned')),
  started_at   timestamptz not null default now(),
  completed_at timestamptz,
  check (completed_at is null or completed_at >= started_at)
);

create index practice_sessions_user_idx on app.practice_sessions (user_id, started_at desc);

alter table app.practice_sessions enable row level security;

grant select on app.practice_sessions to authenticated;
grant select, insert, update on app.practice_sessions to prepmate_api;

create policy practice_sessions_select_own on app.practice_sessions
  for select to authenticated
  using (user_id = (select auth.uid()));

create policy practice_sessions_api_all on app.practice_sessions
  for all to prepmate_api
  using (true) with check (true);

------------------------------------------------------------------------------
-- answers: one answered question, with its feedback
-- Only the API writes here, so a user cannot invent their own scores.
------------------------------------------------------------------------------
create table app.answers (
  id               uuid primary key default gen_random_uuid(),
  session_id       uuid not null references app.practice_sessions (id) on delete cascade,
  -- Repeated from the session so the security policy is a single comparison.
  user_id          uuid not null references auth.users (id) on delete cascade,
  question_id      uuid not null references app.questions (id),
  input_mode       text not null default 'text' check (input_mode in ('text', 'voice')),
  transcript       text not null check (char_length(transcript) between 1 and 8000),
  duration_seconds integer check (duration_seconds between 0 and 600),
  feedback_status  text not null default 'pending'
                   check (feedback_status in ('pending', 'ready', 'failed')),
  scores           jsonb,
  feedback         jsonb,
  model            text check (char_length(model) <= 80),
  created_at       timestamptz not null default now(),
  check (feedback_status <> 'ready' or (scores is not null and feedback is not null))
);

create index answers_session_idx on app.answers (session_id);
create index answers_user_idx on app.answers (user_id, created_at desc);
create index answers_question_idx on app.answers (question_id);

alter table app.answers enable row level security;

grant select on app.answers to authenticated;
grant select, insert, update on app.answers to prepmate_api;

create policy answers_select_own on app.answers
  for select to authenticated
  using (user_id = (select auth.uid()));

create policy answers_api_all on app.answers
  for all to prepmate_api
  using (true) with check (true);

------------------------------------------------------------------------------
-- daily_usage: the per-user daily quota counter
-- Stored in Postgres (not in server memory) so restarts cannot reset it.
------------------------------------------------------------------------------
create table app.daily_usage (
  user_id        uuid not null references auth.users (id) on delete cascade,
  usage_date     date not null default ((now() at time zone 'utc')::date),
  feedback_calls integer not null default 0 check (feedback_calls >= 0),
  audio_seconds  integer not null default 0 check (audio_seconds >= 0),
  primary key (user_id, usage_date)
);

alter table app.daily_usage enable row level security;

grant select on app.daily_usage to authenticated;
grant select, insert, update on app.daily_usage to prepmate_api;

create policy daily_usage_select_own on app.daily_usage
  for select to authenticated
  using (user_id = (select auth.uid()));

create policy daily_usage_api_all on app.daily_usage
  for all to prepmate_api
  using (true) with check (true);
