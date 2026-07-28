# Live Voice and Evidence Scoring

## Conversation loop

The live interview keeps one Streamlit component instance for the full session:

1. HireSense generates and displays one question.
2. The next base question begins generating in the background.
3. Maya, the local animated HireSense AI interviewer, enters Speaking while
   browser speech synthesis reads the current question aloud.
4. Browser speech recognition streams interim and final transcript text.
5. The candidate may correct the transcript before submission.
6. Adaptive voice activity detection normally submits about 900 ms after the
   candidate finishes. Fixed timing and manual submission remain available.
7. A local answer-structure check looks for context, ownership, results, and
   reasoning.
8. When one important element is missing, HireSense generates one targeted
   follow-up. Otherwise it hands off the prefetched base question.

Only question wording uses a network model call. The follow-up decision itself
is deterministic and does not add a separate analysis request.

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
