"""Manim source wrapper for Chemistry Episode 0040: How to think like a chemist.
Run from this directory with:
  EPISODE_NUMBER=40 manim -qh --disable_caching ../../chemistry_scene.py ChemistryEpisode
"""
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ["EPISODE_NUMBER"] = "40"
from chemistry_scene import ChemistryEpisode
