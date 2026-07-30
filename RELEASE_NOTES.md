# HireSense AI 3D Maya Interviewer

Release date: 2026-07-30

## Local 3D interview experience

- Replaced the inline SVG interviewer with a real lightweight Three.js Maya.
- Builds the face, hair, eyes, mouth, blazer, lighting, and upper body locally
  from optimized WebGL geometry. No paid avatar service or external character
  model is required.
- Adds natural blinking, direct gaze, restrained breathing and head movement,
  listening nods, and a thoughtful processing state.
- Uses browser speech word boundaries for best-effort vowel mouth shapes and
  procedural jaw motion when boundary events are unavailable.
- Connects Ready, Speaking, Listening, Thinking, Paused, audio-error, and
  offline states to the real voice lifecycle.
- Gives Maya a subtly warmer expression when the existing opt-in Viva Defense
  support mode is active, without changing question difficulty or scoring.
- Adds automatic local 2D fallback for failed WebGL initialization or context
  loss.
- Removes the visible fixed question counter from the voice-only interview so
  the conversation feels less scripted.
- Keeps natural interview progression, Web Speech API, Viva Defense, private
  Supabase resume storage, and the Google OAuth fix unchanged.

# Previous HireSense AI Viva Defense Integration

Release date: 2026-07-30

## Facial-expression coaching

- Integrated the trained Viva Defense CNN into the focused Live Voice
  Interview flow.
- Added explicit camera opt-in and an in-app camera/model readiness check.
- Runs face detection and TensorFlow.js inference locally in the browser.
- Does not upload or save frames, photos, face crops, or video.
- Shows confident-like, uncertain, and stressed-like expression states with a
  green, amber, or red face box.
- Records one genuine numeric checkpoint when each answer is submitted.
- Uses two consecutive high stressed-like checkpoints only to make Maya's
  wording calmer and clearer. Planned competency and difficulty remain
  unchanged.
- Keeps the facial signal completely separate from transcript evidence scores,
  speaking-delivery scores, hiring decisions, and follow-up selection.
- Adds a final private coaching summary based on question-level checkpoints.
- Documents the correct reported results: about 85.1% test accuracy and 0.9349
  ROC AUC.
- Preserves the natural eight-stage interview, Web Speech API, private
  Supabase resume storage, and Google OAuth popup fix.

# Previous Natural Voice Interview Release

Release date: 2026-07-30

## Human-style interview flow

- Replaced the fixed five-question structure with eight deliberate stages:
  introduction, motivation, relevant experience, behavioural evidence, role
  depth, problem solving, advanced challenge, and closing.
- Added an explicit easy-to-hard difficulty progression and natural
  acknowledgments between answers.
- Stopped preparing the next question before the current answer is submitted,
  so every new question can use what the candidate actually said.
- Limited targeted follow-ups to three across the entire interview and removed
  follow-ups from the introduction, motivation, and closing stages.
- Increased adaptive silence tolerance from 900 ms to 1.9 seconds so a normal
  thinking pause is less likely to end an answer.

## Explainable confidence coaching

- Added a practice-only speaking-delivery model using filler words, pace,
  response timing, pauses, completeness, and transcript evidence.
- Added Web Speech telemetry for recognition certainty, answer start time,
  speaking duration, pause count, and pause duration.
- Uses browser recognition confidence only to describe data reliability, never
  as candidate confidence.
- Rounds estimates to five-point increments, shows reliability and limitations,
  and does not score typed fallback answers.
- Excludes facial appearance, pitch, accent, identity, and inferred emotion.

## Supabase resume persistence

- Saves extracted resume text to the RLS-protected application record.
- Saves the original PDF synchronously to the signed-in user's private Supabase
  Storage path when the interview starts.
- Keeps the interview usable with a clear warning if the PDF upload fails after
  the extracted text has been saved.
- Stores per-answer coaching signals inside the existing `speech_stats` JSONB
  field and the rounded interview summary inside final metrics.

# Previous HireSense AI Open-Source Release

Release date: 2026-07-29

## Live Voice Interview focus

- Reduced the public product to one candidate journey: upload a resume, paste
  the job description, optionally change language, and start.
- Fixed the public interview to live voice, five mixed questions, one adaptive
  follow-up, general company context, and transcript-based feedback.
- Removed public navigation to text interviews, history, skill analysis,
  coaching, coding, company preparation, webcam signals, video recording, and
  nonverbal analysis.
- Replaced the four-part setup, interview-focus selector, review metrics, and
  advanced settings with one short preparation card.
- Simplified the active interview header and final report so disabled product
  concepts cannot reappear through stale browser state.
- Added regression checks for the public setup, router, fixed product defaults,
  and voice-only header.

## Google sign-in hotfix

- Restored the secure new-tab OAuth flow that was lost during open-source
  packaging.
- Fixed **Continue with Google** doing nothing inside Streamlit Community
  Cloud's sandboxed component iframe.
- Added source and compiled-bundle regression checks so blocked `_top`
  navigation cannot return in a future release.

## Open-source packaging

- Added the MIT license, contributor guide, code of conduct, security policy,
  responsible-use guide, architecture guide, and third-party notices.
- Added issue and pull-request templates for consistent community reports.
- Added GitHub Actions checks for Python tests, linting, browser-component
  builds, model verification, and the optional mobile wrapper.
- Expanded ignore rules for credentials, candidate uploads, recordings, logs,
  local environments, caches, and dependency folders.
- Corrected public setup and deployment documentation for the repository root,
  both Supabase migrations, and Google authentication variables.

# Previous Supabase Google Auth Release

Release date: 2026-07-29

## Google authentication

- Added Google sign-in through Supabase Auth while retaining email/password
  access.
- Uses the browser PKCE flow and exchanges the callback for a normal Supabase
  session, preserving Row Level Security for every Google account.
- Keeps the Google client secret exclusively in Supabase provider settings.
- Validates and bounds callback codes and PKCE flow identifiers before
  exchange.
- Processes OAuth callbacks before restoring an older browser session,
  preventing a stale account from overriding a new Google sign-in.
- Stores only Supabase access and refresh tokens used by the existing secure
  session recovery flow. Google provider tokens are not retained.
- Clears temporary PKCE artifacts after success, failure, cancellation, and
  sign-out.
- Adds a profile-trigger migration that supports Google `full_name` and `name`
  metadata.
- Adds an exact Google/Supabase/Streamlit setup checklist and regression
  coverage.

# Previous Supabase Database Release

Release date: 2026-07-28

## Supabase database and authentication

- Added Supabase Auth with email sign-in and candidate account creation.
- Added normalized PostgreSQL tables for profiles, jobs, applications,
  interviews, confirmed turns, evidence scores, and audit events.
- Added Row Level Security policies for candidate ownership and authorized
  recruiter reads.
- Added one-request interview creation, background confirmed-turn writes,
  cloud history, evidence-report persistence, and unfinished-session recovery.
- Added optional private resume-PDF storage with explicit candidate selection.
- Added permanent cloud-history deletion with confirmation and storage cleanup.
- Kept browser persistence as a fallback when Supabase is not configured or is
  temporarily unavailable.
- Preserved original Hindi and Urdu interview text alongside explicit language
  and locale fields.
- Uses only the public publishable key and the signed user access token. The
  app never requires the service-role key.
- Fixed the optional JavaScript mobile wrapper's validation command so it does
  not require an undeclared TypeScript compiler.

# Previous Animated Interviewer Release

Release date: 2026-07-28

## Animated interviewer

- Adds `InterviewAvatar.tsx`, a self-contained animated SVG interviewer named
  Maya with no external avatar service or runtime cost.
- Connects Ready, Speaking, Listening, Thinking, Paused, audio-error, and
  offline states to the real interview lifecycle.
- Adds explicit speech start, end, pause, resume, and error handlers.
- Adds an optional **Interrupt interviewer** control that stops the current
  question and starts listening without losing interview state.
- Replaces failed or blocked audio with a focused, complete written question
  while keeping microphone and typed-answer controls available.
- Uses local microphone volume only to animate the listening ring. Audio
  samples are not stored or uploaded by the avatar.
- Adds responsive, reduced-motion, keyboard, and screen-reader treatment.
- Adds React as the local avatar renderer and regression coverage for the
  avatar, lifecycle handlers, interruption boundary, and built bundle.

# Previous Low-Latency Voice Release

Release date: 2026-07-28

## Latency improvements

- Starts the first live question when the candidate selects **Start
  interview**, then prefetches each next base question while the candidate
  answers the current question.
- Uses a 1.25-second bounded prefetch hand-off and a disclosed built-in
  question if the provider is still unavailable, preventing silent stalls.
- Adds browser-side Web Audio voice activity detection with a default
  900-millisecond end-of-speech window and a 2.2-second safety fallback.
- Keeps fixed 3, 4, 6, and 10-second timing plus manual submission for
  accessibility.
- Warms microphone input while the current question is spoken and preserves
  the browser audio session across turns.
- Replaces full-document question prompts with compact locally extracted
  profile facts, four bounded recent messages, and lower output limits.
- Reduces interactive question and follow-up timeouts to 8 seconds with no
  retries.
- Disables optional reasoning effort for time-sensitive spoken questions while
  leaving detailed post-interview evaluation independent.
- Keeps final evidence scoring after the interview so it never blocks the next
  question.
- Scopes orchestrator caches to the current interview session, preventing
  cross-session context reuse.
- Adds content-free generation, prefetch, transcript, and end-of-speech timing
  diagnostics behind developer mode.
- Adds latency regression tests and a dedicated latency guide.

# Previous Logo and DeepSeek V4 Flash Release

Release date: 2026-07-26

## Main changes

- Added the supplied HireSense AI logo to the sidebar, authentication screen,
  focused interview room, browser icon, README, and optional mobile wrapper.
- Set `deepseek/deepseek-v4-flash` as the default OpenRouter model for
  questions, follow-ups, role analysis, coaching, coding support, nonverbal
  practice feedback, and transcript-grounded evaluation.
- Removed every legacy Gemini default from source, examples, and deployment
  documentation.
- Added provider-response normalization for reasoning wrappers, content blocks,
  JSON surrounded by prose, question prefixes, and accidental extra questions.
- Rebuilds the cached interview orchestrator when its model or temperature
  changes, preventing a stale provider configuration from surviving a switch.
- Moved raw resume and job-description text out of the system instruction and
  added prompt-injection boundaries around candidate-controlled content.
- Removed the hidden 50% role-match fallback. Failed role analysis now reports
  unavailable and never draws a zero-filled radar chart.
- Keeps the app usable without an API key through clearly disclosed built-in
  questions while model scoring and analysis remain unavailable.
- Added bounded PDF processing with a 10 MB, 75-page, and 60,000-character
  ceiling, plus readable upload errors instead of a page crash.
- Added safe built-in fallback questions for every follow-up type.
- Changed LangSmith tracing to explicit opt-in and stopped loading unrelated
  home-directory environment files.
- Removed the mobile wrapper's hardcoded public deployment URL. It now requires
  an explicit HTTPS URL and displays a branded setup state when missing.
- Pinned the patched UUID dependency in the optional mobile wrapper.
- Fixed the interview setup progress indicator so all four steps render as
  cards instead of exposing raw HTML in a code panel.
- Routed the progress indicator through Streamlit's direct HTML renderer and
  added regression coverage for the rendering path.
- Added a cohesive responsive design system across every Streamlit page.
- Reorganized interview setup into four clearly labelled sections.
- Simplified the sidebar and removed candidate-facing technical status clutter.
- Added a focused interview room that hides workspace navigation.
- Redesigned the live voice interface with a stronger question hierarchy,
  microphone state, transcript surface, and mobile behavior.
- Added branded report, history, empty-state, metric, form, and navigation
  components.
- Added reduced-motion behavior and accessible focus treatment.
- Added a current Streamlit Community Cloud deployment guide.
- Replaced deprecated raw HTML embedding with Streamlit's current iframe API.
- Renamed the pipeline to **HireSense Interview Engine** throughout the project.
- Added a conversational live voice loop with automatic end-of-answer timing.
- Added one targeted follow-up when context, ownership, results, or reasoning is
  missing.
- Added visible Ready, Listening, Processing, Speaking, Paused, and Connection
  lost states.
- Replaced the read-only transcript with a live, editable transcript.
- Added question replay and accessibility rephrasing.
- Added captions, adjustable speech speed, extra response time, manual
  submission, keyboard focus styles, and reduced-motion support.
- Replaced response-length grading with transcript-verified evidence scoring.
- Added seven scoring dimensions, exact answer excerpts, reasons, coverage, and
  reliability labels.
- Invalid or invented scoring excerpts are rejected. Missing evidence remains
  unavailable.
- Kept the optional facial practice signal out of scores, question difficulty,
  and follow-up selection.

## Current validation

- 82 Python regression tests pass.
- Python compilation passes.
- Ruff linting passes.
- All three browser-component production builds pass.
- The trained browser GraphModel integrity check passes.
- The Android Expo export passes.
- All browser-component and mobile dependency audits report zero known
  vulnerabilities.
- Streamlit setup rendering, missing-key fallback, health startup, and static
  logo serving pass.
- The startup log contains no deprecated HTML-component warning.

## Browser note

Live transcription uses the browser Speech Recognition API. Current Chrome,
Edge, and other Chromium browsers provide the best support. The transcript can
always be corrected before submission.
