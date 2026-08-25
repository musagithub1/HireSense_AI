# Chemistry Explainer Series — 1,000 Episodes

This repository contains a complete first-draft production library for 1,000 short chemistry explainers based on the attached `explainer-video-style-guide.md`. The sequence progresses from chemistry foundations through measurement, atomic structure, bonding, solutions, gases, thermodynamics, kinetics, equilibrium, acids and bases, electrochemistry, inorganic chemistry, organic chemistry, analytical chemistry, biochemistry, materials, environmental chemistry, nuclear chemistry, and laboratory safety.

## Output standard

The renderer targets vertical MP4 video at **1080×1920, 30 fps, approximately 45–75 seconds**, with the style guide’s dark navy background, restrained palette, animated particle or molecular diagrams, cross-fading bottom captions, and no fabricated voiceover. Captions are provided separately as SRT files, and every episode has a Markdown timed script and a Manim source wrapper.

## Contents

| Path | Contents |
|---|---|
| `curriculum.json` | Ordered list of all 1,000 topics |
| `curriculum.md` | Human-readable curriculum index |
| `episode_specs.json` | Hook, teaching claim, misconception, beats, visual actions, and takeaway for each episode |
| `chemistry_scene.py` | Shared Manim renderer |
| `delivery/sources/` | 1,000 numbered Manim source wrappers |
| `delivery/scripts/` | 1,000 timed Markdown scripts |
| `delivery/captions/` | 1,000 SRT caption tracks |
| `delivery/descriptions/` | 1,000 episode descriptions and learning outcomes |
| `delivery/videos/` | Rendered MP4 outputs; episode 0001 is included as the validated pilot |
| `review_assets/` | Pilot contact sheet and QA notes |
| `delivery/manifest.json` | Machine-readable delivery manifest |

## Render one episode

From the project directory:

```bash
EPISODE_NUMBER=1 manim -qh --disable_caching --media_dir render_media chemistry_scene.py ChemistryEpisode
```

The output will be written under `render_media/videos/chemistry_scene/1920p30/ChemistryEpisode.mp4`. Copy it to the corresponding path under `delivery/videos/` using the filename in `delivery/manifest.json`.

## Render the complete queue

The batch script renders the episodes sequentially, preserves successful outputs, writes a per-episode log, and can resume after interruption:

```bash
bash render_all.sh
```

The full queue is intentionally not launched automatically in this environment because 1,000 full-resolution Manim renders are a long-running workload. The complete curriculum, episode specifications, scripts, captions, descriptions, source wrappers, and the resumable render queue are included.

## Educational review

The episode library is a **first-draft production package**. Episode 0001 has been rendered and visually checked for framing, motion, captions, resolution, frame rate, and duration. The remaining episodes are renderable from the same renderer, but chemistry educators should review the explanations—especially advanced, nuclear, environmental, and safety topics—before public release. Any future voiced edition should use separately generated or recorded narration and then be synchronized to the existing caption timings.

## References

The curriculum architecture follows broad chemistry education categories described by the [American Chemical Society curriculum guidelines](https://www.acs.org/education/policies/acs-recognition-of-global-programs/guidelines/curriculum.html), uses the foundational progression represented by [OpenStax Chemistry 2e](https://openstax.org/books/chemistry-2e/pages/index), and includes systems-thinking and sustainability contexts aligned with [IUPAC chemistry-education guidance](https://iupac.org/systems-thinking-in-chemistry-education-call-for-cti-papers/).
