"""Manim source wrapper for Chemistry Episode 0071: Dimensional analysis for recipes.
Run from this directory with:
  EPISODE_NUMBER=71 manim -qh --disable_caching ../../chemistry_scene.py ChemistryEpisode
"""
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ["EPISODE_NUMBER"] = "71"
from chemistry_scene import ChemistryEpisode
