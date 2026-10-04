drop function if exists complete_independent_session(uuid, uuid, text);

alter table sessions
  add column if not exists completion_kind text,
  add column if not exists tutor_personality text;

alter table users
  add column if not exists tutor_personality text not null default 'chill_senior';

drop index if exists sessions_user_daily_challenge_idx;

alter table sessions
  drop column if exists daily_challenge_id,
  drop column if exists streak_recorded_at;

alter table users
  drop column if exists nickname,
  drop column if exists grade_band,
  drop column if exists preferred_subjects,
  drop column if exists timezone;

drop table if exists user_streaks;
drop table if exists daily_challenges;
