create index if not exists sessions_user_started_idx
  on sessions (user_id, started_at desc);
create index if not exists messages_session_created_idx
  on messages (session_id, created_at);
create index if not exists problems_session_idx
  on problems (session_id);

alter table sessions
  add column if not exists learning_state jsonb not null default '{}'::jsonb;

alter table users enable row level security;
alter table sessions enable row level security;
alter table messages enable row level security;
alter table concepts enable row level security;
alter table user_concepts enable row level security;
alter table assessments enable row level security;
alter table attempts enable row level security;
alter table misconceptions enable row level security;
alter table subjects enable row level security;
alter table concept_prerequisites enable row level security;

drop policy if exists "users_read_own_profile" on users;
create policy "users_read_own_profile"
  on users for select to authenticated
  using (id = auth.uid());

drop policy if exists "sessions_access_own" on sessions;
create policy "sessions_access_own"
  on sessions for select to authenticated
  using (user_id = auth.uid());

drop policy if exists "messages_access_own_sessions" on messages;
create policy "messages_access_own_sessions"
  on messages for select to authenticated
  using (
    exists (
      select 1 from sessions
      where sessions.id = messages.session_id
        and sessions.user_id = auth.uid()
    )
  );

drop policy if exists "user_concepts_access_own" on user_concepts;
create policy "user_concepts_access_own"
  on user_concepts for select to authenticated
  using (user_id = auth.uid());

drop policy if exists "misconceptions_access_own" on misconceptions;
create policy "misconceptions_access_own"
  on misconceptions for select to authenticated
  using (user_id = auth.uid());

drop policy if exists "assessments_access_own_sessions" on assessments;
create policy "assessments_access_own_sessions"
  on assessments for select to authenticated
  using (
    exists (
      select 1 from sessions
      where sessions.id = assessments.session_id
        and sessions.user_id = auth.uid()
    )
  );

drop policy if exists "attempts_access_own_sessions" on attempts;
create policy "attempts_access_own_sessions"
  on attempts for select to authenticated
  using (
    exists (
      select 1 from sessions
      where sessions.id = attempts.session_id
        and sessions.user_id = auth.uid()
    )
  );

create table if not exists reward_ledger (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  session_id uuid not null references sessions(id) on delete cascade,
  reason text not null check (reason in ('verified_problem_solved')),
  points integer not null check (points > 0 and points <= 100),
  evidence jsonb not null,
  created_at timestamptz not null default now(),
  unique (user_id, session_id, reason)
);

alter table reward_ledger enable row level security;
drop policy if exists "rewards_read_own" on reward_ledger;
create policy "rewards_read_own"
  on reward_ledger for select to authenticated
  using (user_id = auth.uid());
