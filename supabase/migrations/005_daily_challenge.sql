create table if not exists daily_challenges (
  id uuid primary key default gen_random_uuid(),
  challenge_date date not null,
  subject text not null,
  grade_band text not null,
  problem_text text not null,
  problem_type text not null,
  topic text not null,
  difficulty text not null,
  solution_plan jsonb not null,
  created_at timestamptz not null default now(),
  unique (challenge_date, subject, grade_band)
);

alter table daily_challenges enable row level security;
drop policy if exists "daily_challenges_service_role_only" on daily_challenges;
create policy "daily_challenges_service_role_only"
  on daily_challenges for all to service_role
  using (true) with check (true);

alter table sessions
  add column if not exists daily_challenge_id uuid
    references daily_challenges(id) on delete set null,
  add column if not exists completion_kind text,
  add column if not exists tutor_personality text,
  add column if not exists streak_recorded_at timestamptz;

create unique index if not exists sessions_user_daily_challenge_idx
  on sessions (user_id, daily_challenge_id)
  where daily_challenge_id is not null;

alter table users
  add column if not exists nickname text,
  add column if not exists grade_band text,
  add column if not exists preferred_subjects text[],
  add column if not exists timezone text,
  add column if not exists tutor_personality text not null default 'chill_senior';

create table if not exists user_streaks (
  user_id uuid primary key references users(id) on delete cascade,
  current_streak integer not null default 0 check (current_streak >= 0),
  longest_streak integer not null default 0 check (longest_streak >= current_streak),
  last_independent_solve_date date
);

alter table user_streaks enable row level security;
drop policy if exists "user_streaks_service_role_only" on user_streaks;
create policy "user_streaks_service_role_only"
  on user_streaks for all to service_role
  using (true) with check (true);

create or replace function complete_independent_session(
  p_session_id uuid,
  p_user_id uuid,
  p_timezone text
)
returns table(current_streak integer, longest_streak integer, last_independent_solve_date date)
language plpgsql
security definer
set search_path = public
as $$
declare
  local_date date;
  completed_id uuid;
begin
  begin
    local_date := (now() at time zone coalesce(nullif(p_timezone, ''), 'UTC'))::date;
  exception when invalid_parameter_value then
    local_date := (now() at time zone 'UTC')::date;
  end;

  update sessions
  set status = 'completed',
      completion_kind = 'independent_solve',
      completed_at = coalesce(completed_at, now()),
      streak_recorded_at = now()
  where id = p_session_id and user_id = p_user_id and status <> 'completed'
  returning id into completed_id;

  if completed_id is null then
    if exists (
      select 1 from sessions
      where id = p_session_id and user_id = p_user_id
        and status = 'completed' and completion_kind = 'independent_solve'
        and streak_recorded_at is not null
    ) then
      return query select streaks.current_streak, streaks.longest_streak,
        streaks.last_independent_solve_date
      from user_streaks as streaks where streaks.user_id = p_user_id;
      return;
    end if;
    raise exception 'Session cannot be completed as an independent solve';
  end if;

  return query
  insert into user_streaks as streaks (
    user_id, current_streak, longest_streak, last_independent_solve_date
  )
  values (p_user_id, 1, 1, local_date)
  on conflict (user_id) do update set
    current_streak = case
      when streaks.last_independent_solve_date = local_date then streaks.current_streak
      when streaks.last_independent_solve_date = local_date - 1 then streaks.current_streak + 1
      else 1
    end,
    longest_streak = greatest(
      streaks.longest_streak,
      case
        when streaks.last_independent_solve_date = local_date then streaks.current_streak
        when streaks.last_independent_solve_date = local_date - 1 then streaks.current_streak + 1
        else 1
      end
    ),
    last_independent_solve_date = greatest(
      streaks.last_independent_solve_date, local_date
    )
  returning streaks.current_streak, streaks.longest_streak,
    streaks.last_independent_solve_date;
end;
$$;

revoke all on function complete_independent_session(uuid, uuid, text) from public, anon, authenticated;
grant execute on function complete_independent_session(uuid, uuid, text) to service_role;
