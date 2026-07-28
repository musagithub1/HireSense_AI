# Live Interview Latency

HireSense keeps the working Streamlit architecture while moving the
time-sensitive parts of a live turn off the critical path.

## Optimized turn path

1. The first question begins generating as soon as the candidate selects
   **Start interview**.
2. The current question is spoken in the persistent browser component.
3. The next base question starts generating in a bounded background worker.
4. Browser speech recognition streams the editable transcript locally.
5. Web Audio voice activity detection identifies the end of speech.
6. The final transcript is submitted after about 900 ms of detected silence.
7. A local structure check decides whether a targeted follow-up is needed.
8. If no follow-up is needed, the prefetched base question is handed to the
   browser immediately.
9. If a prefetched question is still unavailable after the bounded hand-off
   wait, HireSense uses a disclosed built-in question instead of leaving the
   candidate in unexplained silence.

The 2.2-second adaptive fallback timer protects browsers or microphones where
volume-based detection is unreliable. Candidates can still select fixed
3, 4, 6, or 10-second timing, or manual submission.

## Model request changes

- Content, skill, impact, and strategy analysis remain local.
- Each displayed generated question uses one OpenRouter call.
- Base-question generation overlaps the candidate's answer time.
- Question prompts use compact locally extracted facts rather than resending
  the full resume and job description.
- Only the four most recent conversation entries are included, each with a
  strict length bound.
- Question output is capped at 140 tokens.
- Follow-up output is capped at 120 tokens and receives only the current
  question, the latest bounded answer, and the missing evidence target.
- Interactive DeepSeek reasoning effort defaults to `none`; detailed
  post-interview evaluation keeps its independent model configuration.
- Interactive question and follow-up timeouts default to 8 seconds with no
  retries.

Detailed transcript scoring remains a post-interview operation and never
blocks delivery of the next question.

## Configuration

```dotenv
OPENROUTER_QUESTION_TIMEOUT_SECONDS=8
OPENROUTER_QUESTION_MAX_RETRIES=0
OPENROUTER_FOLLOWUP_TIMEOUT_SECONDS=8
OPENROUTER_INTERACTIVE_REASONING_EFFORT=none
HIRESENSE_PREFETCH_WAIT_SECONDS=1.25
```

`HIRESENSE_PREFETCH_WAIT_SECONDS` is the maximum foreground wait for a
background question that is almost complete. The accepted range is 0 to 3
seconds.

## Timing diagnostics

Set `HIRESENSE_DEVELOPER_MODE=true` to show the latency panel during a live
session. It records:

- Question generation time
- Prefetch hand-off wait
- Voice capture duration
- End-of-speech submission delay
- Transcript finalization delay

These records contain timing values and delivery labels only. They do not copy
resume or transcript text.

## Practical targets

| Phase | Target |
|---|---:|
| End-of-speech submission | About 0.9 to 1.5 seconds |
| Prefetched question hand-off | Under 100 ms in the usual path |
| Maximum prefetch hand-off wait | 1.25 seconds by default |
| Unexplained silence | None |

Actual model response time still depends on OpenRouter, the selected provider,
deployment region, and network conditions. Prefetching hides most of that time
behind the candidate's answer rather than promising a provider speed the app
cannot control.
