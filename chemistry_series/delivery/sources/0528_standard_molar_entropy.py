"""Manim source wrapper for Chemistry Episode 0528: Standard molar entropy.
Run from this directory with:
  EPISODE_NUMBER=528 manim -qh --disable_caching ../../chemistry_scene.py ChemistryEpisode
"""
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ["EPISODE_NUMBER"] = "528"
from chemistry_scene import ChemistryEpisode
