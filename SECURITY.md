# Security Policy

## Supported version

Security fixes are applied to the current `main` branch and the newest
published release.

## Report a vulnerability

Do not disclose a suspected vulnerability in a public issue, discussion, pull
request, or chat.

Use GitHub's private vulnerability-reporting option from the repository
**Security** tab. Include:

- A clear description of the issue
- A minimal reproduction
- The affected file, route, or component
- The likely impact
- Any safe mitigation you already tested

If private reporting is not available, open a public issue containing only a
request for a private contact method. Do not reveal exploit details,
credentials, personal data, or candidate information.

## Sensitive values

Never commit or share:

- OpenRouter or LangSmith API keys
- Supabase service-role keys
- Google OAuth client secrets
- Firebase service-account keys
- `.env` or `.streamlit/secrets.toml`
- Resume files, interview recordings, or candidate transcripts

The Supabase publishable key is designed for client use, but it is safe only
when Row Level Security remains enabled and correctly configured.

If a private credential is exposed, revoke and rotate it immediately. Removing
it from the latest commit is not enough if it remains in Git history.

## Deployment boundary

HireSense is an interview-practice application. Deployers are responsible for
access control, data retention, consent, regional privacy requirements, model
provider terms, and monitoring their own infrastructure.
