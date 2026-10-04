-- 001_initial_schema.sql
create table users (
  id uuid primary key,
  email text unique not null,
  created_at timestamptz default now()
);

create table sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  problem_text text not null,
  subject text not null,
  topic text not null,
  status text not null default 'active',
  started_at timestamptz default now(),
  completed_at timestamptz
);

create table messages (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references sessions(id) on delete cascade,
  role text not null,
  content text not null,
  hint_level integer default 0,
  created_at timestamptz default now()
);

create table concepts (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  topic text
);

create table user_concepts (
  user_id uuid references users(id) on delete cascade,
  concept_id uuid references concepts(id) on delete cascade,
  mastery_score numeric not null default 0.5,
  status text not null default 'not_assessed',
  updated_at timestamptz default now(),
  primary key (user_id, concept_id)
);

create table assessments (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references sessions(id) on delete cascade,
  concept_id uuid references concepts(id) on delete cascade,
  evidence text,
  score_delta numeric,
  created_at timestamptz default now()
);
