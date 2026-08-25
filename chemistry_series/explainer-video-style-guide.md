---
name: 3b1b-style-explainer-video
description: Style, structure, and process guide for producing short vertical explainer videos in a 3Blue1Brown-inspired visual style. Use this whenever given a prompt to make an explainer or educational video.
---

# Explainer Video Production Guide

Reference spec for a numbered series of short, Manim-animated explainer
videos in a 3Blue1Brown-inspired style. Follow this whenever asked to
turn a topic into a video — the goal is a consistent look, pacing, and
quality across the whole series, without needing the style re-explained
every time.

## 1. Output spec

| | |
|---|---|
| Format | MP4 |
| Aspect ratio | **Vertical 9:16** by default (matches the series) |
| Resolution | 1080 × 1920 |
| Frame rate | 30 fps |
| Duration | ~45–75s; default to ~60s unless told otherwise |
| Tool | Manim Community Edition (Python) |
| Audio | None by default — captions carry the narration (see §8) |

If a prompt asks for landscape / YouTube / desktop instead, switch to
16:9 (e.g. 1920×1080) and re-flow the layout — don't just letterbox
the vertical version. **If the format is ambiguous or the prompt
contradicts itself (e.g. "reel format, 16:9"), ask which one before
building.** The aspect ratio decides the whole layout, so getting it
wrong means redoing every scene.

## 2. Visual identity

- **Background:** near-black navy, `#0b0e14` — never pure `#000000`,
  it reads as flat on camera.
- **Palette:**
  - Blue `#58C4DD` — primary accent, titles, key concept
  - Yellow `#FFD966` — highlight / "the answer" / the thing to notice
  - Green `#83C167`, Orange `#FF8C69`, Purple `#C792EA` — categorical
    accents (distinct items: tokens, variables, options)
  - White `#F2F2F2` — primary text
  - Grey `#9AA0A6` — captions / secondary text
- **Type:** plain sans-serif via Manim `Text` (Pango) for ~95% of the
  video. Reserve `MathTex`/LaTeX for genuine math notation only — it
  renders slower and adds failure risk, so don't reach for it by
  default.
- **Motion:** fades and staggered ("lagged") reveals, not hard cuts.
  Elements enter with `FadeIn` / `Write` / `Create`, morph into related
  ideas with `Transform` where it's visually honest, and are explicitly
  `FadeOut` before the next beat — see the gotcha in §7 about objects
  left on screen.

## 3. Structure

Every video follows the same three-part shape:

1. **Title card** (~4–6s) — the hook/question the video answers, 2–3
   short lines, the biggest text in the video.
2. **3–5 concept beats** — one idea per beat: one visual + one caption.
   Hold each beat ~2–4s after it settles so it's readable at a glance,
   not just a flash.
3. **Closing card** (~4–6s) — one line that answers the hook from the
   title card.

## 4. Captions

- Bottom third of the frame, grey, ~30–36pt, centered.
- Under ~40 characters where possible; auto-scale down if a line runs
  wider than the frame (snippet in §6).
- Captions are the *entire* script — there's no voice track, so each
  one has to stand alone. Write them short and plain, like subtitles,
  not like essay sentences.
- Cross-fade between captions (old fades out as new fades in) rather
  than cutting.

## 5. Visual idiom library

Pick 3–5 of these per topic (or invent a new one in the same style) to
build the concept beats. Swap the labels/colors per topic — the
mechanics stay the same:

- **Decomposition** — break a whole into labeled colored chips
  (e.g. sentence → tokens). Worked code in §6.
- **Space / similarity** — related items as dots on a faint grid;
  closer together = more related (e.g. word embeddings).
- **Relationship network** — a thin mesh of lines between every pair
  of items, then fade to highlight one strong connection
  (e.g. attention, cause → effect, dependency graphs).
- **Stacking / depth** — vertically stacked labeled boxes connected by
  arrows, for repetition, layers, or iteration.
- **Distribution / selection** — a small bar chart of candidates with
  one highlighted as "the pick" (e.g. next-word prediction, A/B
  choices, ranking).

## 6. Reusable code

Vertical config — put this at the top of every script:

```python
from manim import *

config.pixel_width = 1080
config.pixel_height = 1920
config.frame_height = 16
config.frame_width = config.frame_height * config.pixel_width / config.pixel_height
config.frame_rate = 30

BG = "#0b0e14"
BLUE_MAIN, YELLOW_MAIN = "#58C4DD", "#FFD966"
GREEN_MAIN, ORANGE_MAIN, PURPLE_MAIN = "#83C167", "#FF8C69", "#C792EA"
GREY_TXT, WHITE_TXT = "#9AA0A6", "#F2F2F2"
```

Caption helper — auto-scales to fit, cross-fades between calls:

```python
def set_caption(self, text, run_time=0.6):
    new_caption = Text(text, font_size=34, color=GREY_TXT, line_spacing=1.2)
    new_caption.to_edge(DOWN, buff=1.1)
    if new_caption.width > 8.4:
        new_caption.scale(8.4 / new_caption.width)
        new_caption.to_edge(DOWN, buff=1.1)
    if self.caption is None:
        self.play(FadeIn(new_caption, shift=UP * 0.15), run_time=run_time)
    else:
        self.play(FadeOut(self.caption, shift=UP * 0.15),
                   FadeIn(new_caption, shift=UP * 0.15), run_time=run_time)
    self.caption = new_caption
```

Scene skeleton — one method per beat, called in order from `construct`:

```python
class Explainer(Scene):
    def construct(self):
        self.camera.background_color = BG
        self.caption = None
        self.section_title()
        self.section_beat_one()
        # ... one method per beat ...
        self.section_closing()
```

Worked idiom — decomposition into chips:

```python
def section_tokens(self):
    words, colors = ["Claude", "is", "think", "ing"], \
        [BLUE_MAIN, GREEN_MAIN, YELLOW_MAIN, ORANGE_MAIN]
    boxes = VGroup()
    for w, c in zip(words, colors):
        box = RoundedRectangle(corner_radius=0.12, height=0.9, width=1.7,
                                color=c, fill_color=c, fill_opacity=0.18,
                                stroke_width=3)
        txt = Text(w, font_size=24, color=c).move_to(box.get_center())
        boxes.add(VGroup(box, txt))
    boxes.arrange(RIGHT, buff=0.2).move_to(UP * 3)
    self.play(LaggedStart(*[FadeIn(b, scale=0.8) for b in boxes], lag_ratio=0.15))
    self.set_caption("...broken into tokens.")
```

For a relationship-network beat, connect every pair with
`itertools.combinations` (not a double loop — that draws every
connection twice, mirrored), style each `ArcBetweenPoints` with
`.set_stroke(color=..., width=..., opacity=...)` after construction
rather than as constructor kwargs, and highlight one pair by
redrawing it with a brighter color and thicker stroke.

## 7. Engineering gotchas

- **Fade out everything before leaving a section.** Scaling or moving
  an object out of the way isn't enough — if it's not explicitly
  `FadeOut`, it silently persists into every later scene. (This is a
  real bug hit while building this guide: a set of token boxes stayed
  on screen for the rest of a video because they were shrunk and
  parked in a corner but never faded out.)
- Render a fast low-quality pass first to catch errors —
  `manim -ql --disable_caching file.py SceneName` — then the real pass:
  `manim -qh -r 1080,1920 --fps 30 --disable_caching file.py SceneName`.
- After the final render, check actual duration with
  `ffprobe -show_entries format=duration file.mp4` and nudge
  `self.wait()` calls to hit the target — nominal durations drift
  slightly from the real render.
- Pull a handful of frames across the timeline
  (`ffmpeg -ss T -vframes 1 -i file.mp4 out.png`) and actually look at
  them before calling it done. That's how the leftover-object bug
  above was caught — it wasn't visible in the render log, only in the
  frames.

## 8. Optional narration

Default is captions-only, no audio. If a prompt asks for a voiced
version, don't fabricate a voice — output the caption list as a timed
script (format in §9) so it can be fed to a TTS tool or recorded by a
person, and say plainly that's what was done instead of a real
voiceover.

## 9. Deliverables

Every video ships as three files, numbered as a series
(`01_`, `02_`, ...; increment per new topic, not per revision):

- `NN_topic-slug_vN.mp4` — the rendered video
- `NN_topic-slug_script.md` — captions with timecodes, e.g.:
  ```
  [0:00] TITLE — <hook line>
  [0:06] <caption 1>
  [0:10] <caption 2>
  ...
  [0:53] CLOSING — <closing line>
  ```
- `NN_topic-slug_vN.py` — the Manim source, so a video can be revised
  later instead of rebuilt from scratch

## 10. Process for a new prompt

1. Confirm the format (default vertical 9:16, ~60s); ask if the
   prompt is ambiguous about aspect ratio (§1).
2. Pick the single hook question the video will answer — that's the
   title card and, answered, the closing card.
3. Break the topic into 3–5 beats; map each to an idiom from §5 (or a
   new one in the same visual language).
4. Write the caption line for each beat *first*, short and plain — the
   captions are the script, not an afterthought.
5. Build title → beats → closing as one `Scene`, one method per beat.
6. Fast test render → fix errors → full render → verify duration and
   spot-check frames (§7) → adjust → ship the three deliverables (§9).
