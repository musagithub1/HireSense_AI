"""Manim source wrapper for Chemistry Episode 0280: A force-based view of matter.
Run from this directory with:
  EPISODE_NUMBER=280 manim -qh --disable_caching ../../chemistry_scene.py ChemistryEpisode
"""
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ["EPISODE_NUMBER"] = "280"
from chemistry_scene import ChemistryEpisode
