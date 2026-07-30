# Free deployment on Streamlit Community Cloud

HireSense is prepared for Streamlit Community Cloud. Hosting can be free, while
OpenRouter model usage is billed or rate-limited separately by the model
provider.

## 1. Prepare the GitHub repository

1. Create a new GitHub repository.
2. Upload the contents of the `HireSense_AI` folder so
   `app.py` is at the repository root.
3. Keep the included `requirements.txt`, `.streamlit/config.toml`, compiled
   component `dist` folders, and model files.
4. Do not upload `.env`, `.streamlit/secrets.toml`, virtual environments,
   caches, or `node_modules`.

The production browser-component bundles are included, so Streamlit Community
Cloud does not need Node.js or an npm build step.

## 2. Create the app

1. Open [share.streamlit.io](https://share.streamlit.io/).
2. Select **Create app**.
3. Choose the repository and branch.
4. Set the entrypoint file to `app.py`.
5. Choose a memorable `streamlit.app` subdomain if one is available.
6. Open **Advanced settings** and select Python 3.12.

Streamlit currently defaults to Python 3.12, but selecting it explicitly keeps
the deployment aligned with the tested project version.

## 3. Add secrets

Paste the following into the **Secrets** field in Advanced settings:

```toml
OPENROUTER_API_KEY = "replace-with-your-real-key"
OPENROUTER_MODEL = "deepseek/deepseek-v4-flash"
OPENROUTER_EVALUATION_MODEL = "deepseek/deepseek-v4-flash"
OPENROUTER_TIMEOUT_SECONDS = "45"
OPENROUTER_MAX_RETRIES = "2"
OPENROUTER_QUESTION_TIMEOUT_SECONDS = "8"
OPENROUTER_QUESTION_MAX_RETRIES = "0"
OPENROUTER_FOLLOWUP_TIMEOUT_SECONDS = "8"
OPENROUTER_INTERACTIVE_REASONING_EFFORT = "none"
HIRESENSE_PREFETCH_WAIT_SECONDS = "1.25"

SUPABASE_URL = "https://your-project-ref.supabase.co"
SUPABASE_PUBLISHABLE_KEY = "replace-with-your-public-publishable-key"
HIRESENSE_SUPABASE_AUTH_REQUIRED = "true"
HIRESENSE_GOOGLE_AUTH_ENABLED = "true"
SUPABASE_OAUTH_REDIRECT_URL = "https://your-app.streamlit.app/"

HIRESENSE_DEVELOPER_MODE = "false"
LANGCHAIN_TRACING_V2 = "false"
```

Keep every setting at the root level. Streamlit exposes root-level secrets as
environment variables, which matches HireSense configuration handling.

Do not commit the real API key to GitHub.

## 4. Deploy and verify

Select **Deploy**, then test the public HTTPS address:

1. The setup page opens without a configuration warning.
2. Resume PDF upload and the job-description text field both work.
3. Maya's 3D face appears, blinks, and changes state without downloading a
   character model.
4. The browser asks for microphone permission in live voice mode.
5. Maya speaks the question, then the candidate's words appear in the editable
   transcript.
6. Adaptive timing submits shortly after speech ends, while fixed and manual
   timing remain available.
7. The next adaptive question or disclosed backup question appears without
   silent delay.
8. Evidence assessment either cites verified transcript text or reports that
   evidence is unavailable.
9. Interview history remains available after signing in from another browser
   or device.
10. The setup and interview screens remain usable on a phone-sized display.

Before deploying, run
`supabase/migrations/202607280001_hiresense_core.sql` in the Supabase SQL
Editor, followed by
`supabase/migrations/202607290001_google_auth_profile.sql`, then
`supabase/migrations/202607300001_natural_voice_defaults.sql`. See
`docs/SUPABASE_SETUP.md` for the complete setup and verification flow.

## Authentication note

Supabase Auth is enabled when Supabase is configured. It supplies the signed
user identity required by Row Level Security. The public publishable key is
safe to expose to the app when RLS policies remain enabled. Never add a
service-role key to Streamlit Secrets.

## Data and privacy note

The current build saves extracted resume text, job-description snapshots,
confirmed transcripts, reports, and evidence scores in the user's private
Supabase account. Partial microphone transcripts are not saved. The original
resume PDF is stored in the signed-in user's private resume bucket when the
interview starts. Browser storage remains a fallback if cloud sync is
unavailable.

The optional Viva Defense signal requires explicit camera opt-in. Frames and
face crops stay in the browser and are never saved. A question-level numeric
summary may be stored with the private practice report, but it is excluded
from evidence scoring and must not be used for hiring decisions.

## Useful official references

- [Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud)
- [Deploy an app](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
- [Manage deployment secrets](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)
- [Configure app dependencies](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies)
- [Understand Streamlit secrets](https://docs.streamlit.io/develop/concepts/connections/secrets-management)
- [Supabase Row Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security)
