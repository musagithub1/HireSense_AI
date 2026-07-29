# HireSense AI

![CI](https://github.com/musagithub1/HireSense_AI/actions/workflows/ci.yml/badge.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-4f46e5.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-0891b2.svg)](https://www.python.org/)
[![Live demo](https://img.shields.io/badge/Live_demo-Streamlit-ff4b4b.svg)](https://hiresenseay.streamlit.app/)

HireSense AI is an open-source live voice interview-practice application. A
candidate uploads a resume, pastes a job description, completes a personalized
voice interview, and receives feedback grounded in the confirmed transcript.

**[Try HireSense AI](https://hiresenseay.streamlit.app/)** ·
**[Deployment guide](docs/DEPLOYMENT.md)** ·
**[Contributing guide](CONTRIBUTING.md)**

> [!IMPORTANT]
> HireSense AI is an educational practice tool. It is not a validated hiring
> decision system and should not be used to accept, reject, rank, or screen
> candidates.

## One focused candidate flow

The public app intentionally exposes one feature: **Live Voice Interview**.

1. Sign in.
2. Upload a resume PDF.
3. Paste the job description.
4. Start the live voice interview.
5. Move through eight natural interview stages with focused follow-ups.
6. Generate transcript-grounded feedback.

HireSense automatically uses:

- Live voice mode
- A mixed interview question set
- Eight main stages from introduction to closing
- Up to three focused follow-ups across the full interview
- General company context
- Browser speech playback and recognition
- An explainable speaking-delivery coaching signal
- Transcript-based feedback

The candidate does not need to choose an interview type, company, mode,
question count, webcam setting, recording option, or scoring method.

## Disabled public features

The public interface does not expose:

- Text interviews
- Coding practice
- Skill-gap dashboards
- Company preparation
- Coaching or copilot pages
- Interview-history navigation
- Webcam or facial scoring
- Video recording
- Nonverbal scoring

Some older modules remain in the repository temporarily for migration
reference, but the application router cannot open them.

## Live voice behavior

- Maya, the HireSense AI interviewer, speaks every visible question.
- Browser speech recognition creates an editable transcript.
- Candidates can interrupt, pause, replay, rephrase, or correct the transcript.
- The interview starts with introduction and motivation, then progresses through
  experience, behavioural evidence, role depth, problem solving, an advanced
  challenge, and closing.
- HireSense waits for the confirmed answer before preparing the next question,
  allowing Maya to acknowledge and respond to what the candidate actually said.
- The speaking-delivery model uses observable transcript and timing features
  for private practice feedback. It does not infer emotion or make hiring
  recommendations.
- A built-in question is disclosed and used if personalized generation fails.
- Resume text, the private PDF, and confirmed answers are saved to the signed-in
  user's Supabase account when cloud persistence is configured.
- Feedback is scored only when an exact supporting excerpt can be verified
  against the transcript.

Browser-native speech recognition works best in a current Chrome, Edge, or
Chromium browser. Support and transcription behavior vary by browser,
operating system, and language.

## Requirements

- Python 3.11 or 3.12
- An OpenRouter API key for personalized questions and feedback
- A current Chromium-based browser for the best voice experience
- Node.js 20.19 or newer only when rebuilding browser components

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

Set the local values in `.env`:

```dotenv
OPENROUTER_API_KEY=your_real_key
OPENROUTER_MODEL=deepseek/deepseek-v4-flash
OPENROUTER_EVALUATION_MODEL=deepseek/deepseek-v4-flash
HIRESENSE_AUTH_REQUIRED=false
```

Then run:

```bash
streamlit run app.py
```

Open `http://localhost:8501`.

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

## Supabase and Google sign-in

For secure cross-device authentication and interview recovery, run the
included migrations in timestamp order and configure:

```dotenv
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_PUBLISHABLE_KEY=your_public_publishable_key
HIRESENSE_SUPABASE_AUTH_REQUIRED=true
HIRESENSE_GOOGLE_AUTH_ENABLED=true
SUPABASE_OAUTH_REDIRECT_URL=https://your-app.streamlit.app/
```

Google credentials belong in the Supabase Google provider, not in Streamlit
Secrets. The Google button opens OAuth in a new tab because Streamlit custom
components run inside a sandboxed iframe.

See [Supabase setup](docs/SUPABASE_SETUP.md) and
[deployment](docs/DEPLOYMENT.md) for the complete configuration.

## Main configuration

| Variable | Required | Purpose |
|---|---:|---|
| `OPENROUTER_API_KEY` | For AI features | Personalized questions and feedback |
| `OPENROUTER_MODEL` | No | Question model |
| `OPENROUTER_EVALUATION_MODEL` | No | Transcript-grounded feedback model |
| `OPENROUTER_QUESTION_TIMEOUT_SECONDS` | No | Interactive question timeout |
| `SUPABASE_URL` | For cloud accounts | Supabase project URL |
| `SUPABASE_PUBLISHABLE_KEY` | For cloud accounts | Public RLS-protected browser key |
| `HIRESENSE_SUPABASE_AUTH_REQUIRED` | No | Require Supabase sign-in |
| `HIRESENSE_GOOGLE_AUTH_ENABLED` | No | Show Google sign-in |
| `SUPABASE_OAUTH_REDIRECT_URL` | For Google | Exact deployed app URL |
| `HIRESENSE_DEVELOPER_MODE` | No | Show maintainer diagnostics |

Never commit `.env`, `.streamlit/secrets.toml`, private API keys, Google client
secrets, or a Supabase service-role key.

## Tests

Install development dependencies and run:

```bash
python -m pip install -r requirements-dev.txt
pytest -q
ruff check .
```

The regression suite verifies the natural interview-stage order, confidence
signal boundaries, private resume path, voice telemetry validation, disabled
feature routes, and the Google OAuth `_blank` navigation required by
Streamlit's component sandbox.

Rebuild browser components only when their source changes:

```bash
cd voice_input/frontend
npm install
npm run build

cd ../../persistence/frontend
npm install
npm run build
```

Do not package `node_modules`.

## Privacy and responsible use

Resume text, job-description text, transcripts, and feedback are sensitive.
Deployers should use HTTPS, Supabase Row Level Security, a private resume
bucket, clear retention rules, and an accessible deletion process. Read
[Privacy and responsible use](docs/PRIVACY_AND_RESPONSIBLE_USE.md) before
sharing the app publicly.

## License

HireSense AI is released under the [MIT License](LICENSE). Third-party
packages and assets retain their own licenses. See
[Third-party notices](THIRD_PARTY_NOTICES.md).
