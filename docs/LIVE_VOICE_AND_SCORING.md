# Live Voice and Evidence Scoring

## Conversation loop

The live interview keeps one Streamlit component instance for the full session:

1. HireSense selects the current interview stage and generates one question.
2. Maya, the local animated HireSense AI interviewer, enters Speaking while
   browser speech synthesis reads the current question aloud.
3. Browser speech recognition streams interim and final transcript text.
4. The candidate may correct the transcript before submission.
5. Adaptive voice activity detection normally submits about 1.9 seconds after the
   candidate finishes. Fixed timing and manual submission remain available.
6. A local answer-structure check looks for context, ownership, results, and
   reasoning.
7. When one important element is missing, HireSense may generate one targeted
   follow-up, subject to a session-wide limit of three.
8. After the answer is confirmed, HireSense prepares the next stage using the
   answer as conversation context. It never pre-generates an answer-blind
   question while the candidate is still speaking.

Only question wording uses a network model call. The follow-up decision itself
is deterministic and does not add a separate analysis request.

## Natural interview progression

| Stage | Difficulty | Purpose |
|---|---|---|
| Introduction | Easy | Establish background and help the candidate settle in |
| Motivation and fit | Easy | Understand genuine interest in the role |
| Relevant experience | Medium | Explore resume evidence and personal ownership |
| Behavioural evidence | Medium | Examine teamwork, judgment, or a difficult situation |
| Role depth | Medium | Test practical use of an important job requirement |
| Problem solving | Hard | Explore a structured response to ambiguity |
| Advanced challenge | Hard | Probe constraints, tradeoffs, scaling, and risk |
| Closing | Reflection | Give the candidate one final opportunity to add evidence |

Maya briefly acknowledges the previous response before moving forward. The
stage plan controls the gradual increase in complexity, while a follow-up
stays tied to evidence missing from the candidate's latest answer.

## Animated interviewer

`voice_input/frontend/src/InterviewAvatar.tsx` contains the interviewer as an
inline animated SVG. It does not call an avatar service, download video, inspect
the candidate, or add network latency.

The voice lifecycle drives the avatar directly:

- Speech start: Speaking animation and waveform
- Speech end: Ready, followed by Listening
- Candidate microphone activity: Listening pulse and subtle nod
- Answer submission: Thinking while Streamlit prepares the next turn
- Pause and resume: preserved speech and transcript state
- Playback error: written-question fallback with continued answer controls
- Offline: connection-recovery state

During Speaking, **Interrupt interviewer** cancels the current utterance and
starts the microphone. The control is optional at the Python component boundary
and is enabled for live mode only.

## Visible states

The browser component always exposes one of these states:

- Ready
- Listening
- Processing
- Speaking
- Paused
- Audio unavailable
- Connection lost

The current transcript is preserved when the user pauses or temporarily loses
connectivity.

## Accessibility

- The question is visible as a caption by default.
- The candidate can replay or rephrase the current question.
- The candidate can interrupt spoken playback and answer immediately.
- A blocked or failed voice always falls back to the complete written question.
- Speech speed can be set to slower, normal, or faster.
- Adaptive end-of-speech timing is the default.
- Fixed silence timing can be 3, 4, 6, or 10 seconds.
- Manual submission disables automatic silence submission.
- The transcript is editable and spellcheck-enabled.
- All controls are keyboard reachable and use visible focus styles.
- Reduced-motion browser preferences are respected.
- Interview language controls both recognition and spoken-question language.

## Speaking-delivery confidence signal

`confidence_model.py` creates an explainable coaching estimate from observable
answer features:

- Filler-word ratio
- Speaking pace
- Time before the answer starts
- Pause frequency and duration
- Answer completeness
- Transcript evidence for context, personal action, reasoning, and results

The browser's speech-recognition confidence value describes transcription
certainty. It is retained only as a reliability signal and never increases or
decreases the candidate's delivery score.

Scores are rounded to five-point increments and paired with a reliability
label, strengths, improvement areas, and a visible limitation statement.
Typed fallback answers do not receive a speaking-delivery score. The model
does not inspect pitch, accent, gender, identity, facial appearance, or
emotion. It must not be used for hiring, ranking, screening, or psychological
judgment.

## Evidence scoring

The final assessment uses seven dimensions:

1. Relevance
2. Specificity
3. Demonstrated skills
4. Reasoning quality
5. Ownership and self-awareness
6. Communication clarity
7. Evidence of results

The evaluator must return a score from 1 to 5 together with an exact candidate
excerpt and answer index. HireSense normalizes whitespace and verifies that the
excerpt exists in the referenced candidate answer. A score with missing or
invented evidence is discarded.

Reliability is calculated locally:

- High: at least two verified excerpts from different answers
- Medium: one verified excerpt of at least eight words
- Low: one shorter verified excerpt
- Unavailable: no verified scoring evidence

Overall reliability also considers rubric coverage and how many answers support
the assessment. Missing dimensions show **Insufficient evidence**. There is no
neutral default score.

## Technical boundary

This build uses browser-native speech recognition, not raw-audio WebRTC
streaming. Local Web Audio volume samples are used only to identify the end of
speech while the Listening state is active, and are neither stored nor sent to
HireSense. The app provides real-time transcript events and rapid turn
submission, but speech-service availability depends on the browser and
operating system. Chrome, Edge, and other current Chromium browsers provide the
best support.
