# Supabase setup for HireSense AI

This release includes Supabase Auth, PostgreSQL persistence, Row Level
Security, private resume storage, interview recovery, and cross-device
history. No service-role key is used by the Streamlit app.

## 1. Create a Supabase project

1. Create a project at <https://supabase.com/dashboard>.
2. Open **Project Settings**, then **API**.
3. Copy the Project URL.
4. Copy the public publishable key. A legacy anon key also works, but the
   publishable key is preferred.
5. Never copy the `service_role` key into HireSense or Streamlit Secrets.

## 2. Install the database schema

1. Open **SQL Editor** in the Supabase dashboard.
2. Create a new query.
3. Run these files in order:
   - `supabase/migrations/202607280001_hiresense_core.sql`
   - `supabase/migrations/202607290001_google_auth_profile.sql`
   - `supabase/migrations/202607300001_natural_voice_defaults.sql`
4. Select **Run** after pasting each file.

The migration creates:

- `profiles`
- `jobs`
- `applications`
- `interviews`
- `interview_turns`
- `evaluation_scores`
- `audit_events`
- A private `resumes` Storage bucket
- Row Level Security policies
- The one-request `start_practice_interview` function

The policies let candidates read and change only their own data. Recruiters
can read interview data only when they own the related job. New accounts are
always candidates. Promote a trusted recruiter manually in the Supabase table
editor or through a future admin workflow.

## 3. Configure Google authentication

Google sign-in uses Supabase Auth with PKCE. The Google client secret belongs
in the Supabase dashboard and is never added to Streamlit Secrets or this
repository.

### Google Cloud

1. Open **Google Auth Platform**, then create or rotate a **Web application**
   OAuth client.
2. Add the origin of the deployed Streamlit app under **Authorized JavaScript
   origins**, for example:
   `https://your-app.streamlit.app`
3. Under **Authorized redirect URIs**, add the Supabase callback shown on the
   Supabase Google provider page. Its standard form is:
   `https://your-project-ref.supabase.co/auth/v1/callback`
4. Configure the consent screen with `openid`, email, and profile scopes.
5. Keep the new client ID and secret private.

If credentials were pasted into a message, issue tracker, repository, or
public deployment log, rotate them before using this flow.

### Supabase

1. Open **Authentication**, **Providers**, then **Google**.
2. Enable Google and paste the rotated Google client ID and client secret.
3. Open **Authentication**, then **URL Configuration**.
4. Set **Site URL** to the exact deployed Streamlit app URL.
5. Add the same exact app URL under **Redirect URLs**.
6. Keep Email enabled if email/password should remain available.
7. Keep email confirmation enabled for public deployments.

The Google callback creates a normal Supabase Auth session. The same Supabase
JWT is therefore used for Row Level Security, cloud history, recovery, and
private resume access.

## 4. Add local secrets

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and replace
the placeholders:

```toml
OPENROUTER_API_KEY = "replace-with-your-real-key"
OPENROUTER_MODEL = "deepseek/deepseek-v4-flash"
OPENROUTER_EVALUATION_MODEL = "deepseek/deepseek-v4-flash"

SUPABASE_URL = "https://your-project-ref.supabase.co"
SUPABASE_PUBLISHABLE_KEY = "replace-with-your-public-publishable-key"
HIRESENSE_SUPABASE_AUTH_REQUIRED = "true"
HIRESENSE_GOOGLE_AUTH_ENABLED = "true"
SUPABASE_OAUTH_REDIRECT_URL = "https://your-app.streamlit.app/"
```

`.streamlit/secrets.toml` is ignored by Git and must not be added to the ZIP or
repository.

Do not add `GOOGLE_CLIENT_SECRET` to Streamlit when Supabase Auth is enabled.
The deployed app needs only the public Supabase key. The redirect URL setting
is optional when the browser can determine the parent app URL, but setting it
explicitly is recommended in production.

Environment variables can be used instead:

```dotenv
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_PUBLISHABLE_KEY=your_public_publishable_key
HIRESENSE_SUPABASE_AUTH_REQUIRED=true
HIRESENSE_GOOGLE_AUTH_ENABLED=true
SUPABASE_OAUTH_REDIRECT_URL=http://localhost:8501/
```

## 5. Run and verify

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

Verify this flow:

1. Select **Continue with Google** and complete the Google consent screen.
2. Confirm the sidebar shows the Google account name and email.
3. Sign out, sign in again, and confirm session recovery works.
4. Also verify email sign-in if it remains enabled.
5. Add a resume and job description.
6. Start an interview.
7. Submit one answer.
8. Open Supabase Table Editor and confirm the `applications` row contains
   extracted resume text and a private `resume_path`.
9. Open Supabase Storage and confirm the PDF is under
   `resumes/<user-id>/<application-id>/`.
10. Confirm an `interviews` row and an `interview_turns` row exist.
11. Refresh the browser and select **Resume saved interview**.
12. Finish the interview and generate the evidence assessment.
13. Open Interview history on a second device after signing in with the same
    Google account.

## What is saved

- Extracted resume text and the job-description snapshot used for that
  interview
- Interview language, type, model, mode, progress, and timestamps
- Only submitted and confirmed transcripts
- Per-answer speaking-delivery coaching signals and their reliability metadata
- Evidence scores, verified excerpts, reasons, and reliability
- The final report and summary metrics
- The original resume PDF in the signed-in user's private Storage path

Partial microphone transcripts and raw microphone samples are not saved. The
speaking-delivery signal is not an emotion reading or hiring score.

## Failure behavior

If the original PDF upload fails, the extracted resume text remains saved in
the RLS-protected application record and HireSense shows a private-storage
warning. Confirmed-answer writes run outside the critical speech-response path.

## Production checklist

- Keep Row Level Security enabled on every public table.
- Keep the Storage bucket private.
- Use only the publishable key in the Streamlit deployment.
- Keep the Google client secret only in the Supabase provider configuration.
- Use the exact production app URL rather than a wildcard redirect.
- Keep email confirmation enabled.
- Review data retention and privacy terms before accepting real applicants.
- Test candidate and recruiter access with two separate accounts.
- Do not use facial appearance, accent, emotion, or vocal confidence for
  hiring scores.

Official references:

- <https://supabase.com/docs/guides/database/postgres/row-level-security>
- <https://supabase.com/docs/guides/auth>
- <https://supabase.com/docs/guides/auth/social-login/auth-google>
- <https://supabase.com/docs/guides/auth/redirect-urls>
- <https://supabase.com/docs/guides/storage/security/access-control>
- <https://docs.streamlit.io/develop/tutorials/databases/supabase>
