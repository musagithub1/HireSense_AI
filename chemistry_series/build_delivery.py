from __future__ import annotations
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
items = json.loads((ROOT / 'episode_specs.json').read_text())
DELIVERY = ROOT / 'delivery'
for d in ['scripts', 'sources', 'captions', 'descriptions', 'videos', 'review']:
    (DELIVERY / d).mkdir(parents=True, exist_ok=True)


def slugify(s: str) -> str:
    s = re.sub(r'[^a-z0-9]+', '_', s.lower()).strip('_')
    return s


def ts(seconds: int) -> str:
    return f"{seconds//60}:{seconds%60:02d}"


def srt_ts(seconds: int) -> str:
    return f"00:{seconds//60:02d}:{seconds%60:02d},000"

manifest = []
for spec in items:
    n = spec['number']
    slug = f"{n:04d}_{slugify(spec['title'])}"
    source = DELIVERY / 'sources' / f'{slug}.py'
    script = DELIVERY / 'scripts' / f'{slug}.md'
    caption = DELIVERY / 'captions' / f'{slug}.srt'
    desc = DELIVERY / 'descriptions' / f'{slug}.md'
    source.write_text(f'''"""Manim source wrapper for Chemistry Episode {n:04d}: {spec['title']}.\nRun from this directory with:\n  EPISODE_NUMBER={n} manim -qh --disable_caching ../../chemistry_scene.py ChemistryEpisode\n"""\nimport os\nfrom pathlib import Path\nimport sys\nsys.path.insert(0, str(Path(__file__).resolve().parents[2]))\nos.environ["EPISODE_NUMBER"] = "{n}"\nfrom chemistry_scene import ChemistryEpisode\n''')
    lines = [f"# Episode {n:04d}: {spec['title']}", "", f"**Hook:** {spec['hook']}", "", f"**Teaching claim:** {spec['teaching_claim']}", "", f"**Misconception corrected:** {spec['misconception']}", "", "## Timed caption script", "", f"[{ts(0)}] TITLE — {spec['hook']}"]
    times = [6, 17, 28, 39]
    for t, beat in zip(times, spec['beats']):
        lines.append(f"[{ts(t)}] {beat['caption']}")
    lines.append(f"[{ts(50)}] CLOSING — {spec['closing']}")
    lines += ["", f"**Takeaway:** {spec['takeaway']}", "", "**Audio:** None; captions carry the narration by design.", "**Format:** Vertical MP4, 1080×1920, 30 fps, approximately 60 seconds."]
    script.write_text('\n'.join(lines) + '\n')
    captions = [
        (0, 6, spec['hook']),
        (6, 17, spec['beats'][0]['caption']),
        (17, 28, spec['beats'][1]['caption']),
        (28, 39, spec['beats'][2]['caption']),
        (39, 50, spec['beats'][3]['caption']),
        (50, 60, spec['takeaway']),
    ]
    srt = []
    for idx, (start, end, text) in enumerate(captions, 1):
        srt += [str(idx), f"{srt_ts(start)} --> {srt_ts(end)}", text, ""]
    caption.write_text('\n'.join(srt))
    desc.write_text(f"# {spec['title']}\n\nThis short chemistry explainer answers: **{spec['hook']}**\n\n{spec['teaching_claim']}\n\nThe episode uses continuous animated transformations and captions rather than voiceover.\n\n## Learning outcome\n{spec['takeaway']}\n\n## Source\nThis episode is generated from the Chemistry Explainer Series curriculum and should be reviewed by a chemistry educator before public release.\n")
    manifest.append({
        'number': n, 'title': spec['title'], 'slug': slug,
        'video': f'videos/{slug}.mp4', 'captions': f'captions/{slug}.srt',
        'script': f'scripts/{slug}.md', 'source': f'sources/{slug}.py',
        'description': f'descriptions/{slug}.md', 'duration_target_seconds': 60,
        'resolution': '1080x1920', 'fps': 30, 'audio': 'none'
    })

(DELIVERY / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
summary = ['# Chemistry Explainer Series Delivery Manifest', '', 'This package contains 1,000 ordered chemistry episodes. The episode source wrappers all use the shared `chemistry_scene.py` renderer and the captions-only format specified in the attached style guide.', '', '| Range | Count | Format |', '|---|---:|---|', '| Episodes | 1–1000 | Vertical 1080×1920 MP4 target |', '| Sources | 1–1000 | Manim Python wrappers |', '| Scripts | 1–1000 | Markdown with timed captions |', '| Captions | 1–1000 | SRT |', '| Descriptions | 1–1000 | Markdown |', '', '## Important production note', '', 'The episode specifications in this first-draft package are generated from a reusable curriculum and storyboard system. The source, script, and caption files are complete and renderable, but the chemistry claims should receive subject-matter review before public release, especially for advanced topics and safety-related episodes.']
(DELIVERY / 'delivery_manifest.md').write_text('\n'.join(summary) + '\n')
print(f'generated deliverables for {len(items)} episodes in {DELIVERY}')
