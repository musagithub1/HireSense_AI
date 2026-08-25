"""Manim source wrapper for Chemistry Episode 0052: Percent difference.
Run from this directory with:
  EPISODE_NUMBER=52 manim -qh --disable_caching ../../chemistry_scene.py ChemistryEpisode
"""
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ["EPISODE_NUMBER"] = "52"
from chemistry_scene import ChemistryEpisode
