from pathlib import Path
import json

root = Path(__file__).parent
items = json.loads((root / 'curriculum.json').read_text())
assert len(items) == 1000
assert [x['number'] for x in items] == list(range(1, 1001))
assert len(json.loads((root / 'episode_specs.json').read_text())) == 1000
manifest = json.loads((root / 'delivery/manifest.json').read_text())
assert len(manifest) == 1000
for folder, suffix in [('scripts', '.md'), ('sources', '.py'), ('captions', '.srt'), ('descriptions', '.md')]:
    files = list((root / 'delivery' / folder).glob(f'*{suffix}'))
    assert len(files) == 1000, (folder, len(files))
video_files = list((root / 'delivery/videos').glob('*.mp4'))
assert len(video_files) >= 1
print('curriculum=1000')
print('specifications=1000')
print('manifest=1000')
print('scripts=1000 sources=1000 captions=1000 descriptions=1000')
print(f'rendered_videos={len(video_files)}')
