-- 002_universal.sql
-- Add new columns to problems if it exists, or create problems table.
-- The prompt mentions: problems(id, session_id, problem_type, subject, topic, difficulty, language, solution_plan jsonb, tutor_confidence)
create table problems (
    id uuid primary key default gen_random_uuid(),
    session_id uuid references sessions(id) on delete cascade,
    problem_type text not null,
    subject text not null,
    topic text not null,
    difficulty text,
    language text,
    solution_plan jsonb,
    tutor_confidence numeric
);

-- RLS for solution_plan (deny client, allow service role)
alter table problems enable row level security;
create policy "hide_solution_plan" on problems for select using (auth.role() = 'service_role');

create table subjects (
    id uuid primary key default gen_random_uuid(),
    name text not null unique
);

create table concept_prerequisites (
    concept_id uuid references concepts(id) on delete cascade,
    prerequisite_id uuid references concepts(id) on delete cascade,
    primary key (concept_id, prerequisite_id)
);

create table attempts (
    id uuid primary key default gen_random_uuid(),
    session_id uuid references sessions(id) on delete cascade,
    step_text text,
    outcome text,
    hint_level integer,
    concept_id uuid references concepts(id),
    created_at timestamptz default now()
);

create table misconceptions (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references users(id) on delete cascade,
    concept_id uuid references concepts(id) on delete cascade,
    description text not null,
    count integer default 1,
    last_seen timestamptz default now()
);

-- Alter sessions
alter table sessions add column mode text default 'explore';
alter table sessions add column problem_type text;
