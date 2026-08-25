"""Manim source wrapper for Chemistry Episode 0163: Metals, nonmetals, and metalloids.
Run from this directory with:
  EPISODE_NUMBER=163 manim -qh --disable_caching ../../chemistry_scene.py ChemistryEpisode
"""
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ["EPISODE_NUMBER"] = "163"
from chemistry_scene import ChemistryEpisode
