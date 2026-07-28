-- Keep profile creation compatible with Google OAuth metadata.
-- Run after 202607280001_hiresense_core.sql.

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.profiles (id, email, full_name, role)
  values (
    new.id,
    new.email,
    coalesce(
      nullif(trim(new.raw_user_meta_data ->> 'full_name'), ''),
      nullif(trim(new.raw_user_meta_data ->> 'name'), ''),
      nullif(split_part(coalesce(new.email, ''), '@', 1), ''),
      'HireSense User'
    ),
    'candidate'
  )
  on conflict (id) do update
    set email = excluded.email,
        full_name = case
          when trim(public.profiles.full_name) = '' then excluded.full_name
          else public.profiles.full_name
        end;
  return new;
end;
$$;
