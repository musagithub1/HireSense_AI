#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$ROOT/delivery/videos" "$ROOT/render_logs"
for n in $(seq 1 1000); do
  row=$(python3 - "$ROOT/delivery/manifest.json" "$n" <<'PY'
import json, sys
manifest=json.load(open(sys.argv[1]))
row=next(x for x in manifest if x['number']==int(sys.argv[2]))
print(row['title'])
print(row['video'])
PY
)
  title=$(printf '%s\n' "$row" | sed -n '1p')
  rel=$(printf '%s\n' "$row" | sed -n '2p')
  target="$ROOT/delivery/$rel"
  if [ -s "$target" ]; then
    echo "SKIP $n $title"
    continue
  fi
  echo "RENDER $n $title"
  log="$ROOT/render_logs/$(printf '%04d' "$n").log"
  if EPISODE_NUMBER="$n" manim -qh --disable_caching --media_dir "$ROOT/render_media_batch" "$ROOT/chemistry_scene.py" ChemistryEpisode >"$log" 2>&1; then
    src="$ROOT/render_media_batch/videos/chemistry_scene/1920p30/ChemistryEpisode.mp4"
    if [ -s "$src" ]; then
      cp "$src" "$target"
      ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1 "$target" >>"$log" 2>&1 || true
    else
      echo "MISSING_OUTPUT" >>"$log"
    fi
  else
    echo "FAILED $n; continue to next episode" | tee -a "$log"
  fi
done
