-- Natural Live Voice Interview defaults.
--
-- The application passes the question count explicitly. This default keeps
-- direct inserts and future integrations aligned with the eight-stage flow.

alter table public.interviews
  alter column total_questions set default 8;

comment on column public.interviews.total_questions is
  'Number of main interview stages. The public natural voice flow uses eight.';
