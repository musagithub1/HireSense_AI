"""Manim source wrapper for Chemistry Episode 0186: Periodic trends as competing effects.
Run from this directory with:
  EPISODE_NUMBER=186 manim -qh --disable_caching ../../chemistry_scene.py ChemistryEpisode
"""
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ["EPISODE_NUMBER"] = "186"
from chemistry_scene import ChemistryEpisode
