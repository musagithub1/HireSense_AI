"""Manim source wrapper for Chemistry Episode 0898: Beer-Lambert law.
Run from this directory with:
  EPISODE_NUMBER=898 manim -qh --disable_caching ../../chemistry_scene.py ChemistryEpisode
"""
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ["EPISODE_NUMBER"] = "898"
from chemistry_scene import ChemistryEpisode
