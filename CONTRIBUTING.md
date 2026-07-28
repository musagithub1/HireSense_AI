# Contributing to HireSense AI

Thank you for helping improve HireSense AI. Contributions should preserve the
project's core principle: interview feedback must be transparent,
transcript-grounded, privacy-conscious, and useful for practice.

## Good contribution areas

- Bug fixes with a regression test
- Accessibility and multilingual improvements
- Documentation and setup corrections
- Browser compatibility fixes
- Safer data handling and clearer consent
- Evidence-scoring reliability
- Performance improvements that preserve behavior

Do not add hiring scores based on facial appearance, inferred emotion, accent,
gender, age, race, disability, or other protected or biometric traits.

## Local setup

```bash
git clone https://github.com/musagithub1/HireSense_AI.git
cd HireSense_AI
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

Use placeholder or personal test credentials only. Never commit `.env`,
`.streamlit/secrets.toml`, service-role keys, OAuth secrets, resumes,
recordings, or candidate transcripts.

## Run the app

```bash
streamlit run app.py
```

Model-backed features need an OpenRouter key. The app should still start and
show its disclosed fallback behavior without one.

## Validate changes

Run the Python checks:

```bash
pytest -q
ruff check .
python -m compileall -q .
```

Rebuild a browser component only when its source changes:

```bash
cd emotion_detector/frontend
npm ci
npm run build
npm run verify:model

cd ../../voice_input/frontend
npm ci
npm run build

cd ../../persistence/frontend
npm ci
npm run build
```

Validate the optional mobile wrapper when it changes:

```bash
cd mobile
npm ci
npm run check
```

Do not commit `node_modules`.

## Pull requests

1. Open an issue first for a large behavioral or architectural change.
2. Keep each pull request focused on one problem.
3. Explain the user impact and the approach.
4. Include tests for changed behavior.
5. Update documentation and compiled component assets when relevant.
6. Confirm that no credentials or candidate data are included.
7. Complete the pull-request checklist.

By contributing, you agree that your contribution is licensed under the
project's MIT License.
