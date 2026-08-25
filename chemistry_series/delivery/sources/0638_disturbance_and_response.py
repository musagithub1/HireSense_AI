"""Manim source wrapper for Chemistry Episode 0638: Disturbance and response.
Run from this directory with:
  EPISODE_NUMBER=638 manim -qh --disable_caching ../../chemistry_scene.py ChemistryEpisode
"""
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ["EPISODE_NUMBER"] = "638"
from chemistry_scene import ChemistryEpisode
