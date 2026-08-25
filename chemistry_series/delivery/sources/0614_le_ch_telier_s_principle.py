"""Manim source wrapper for Chemistry Episode 0614: Le Châtelier's principle.
Run from this directory with:
  EPISODE_NUMBER=614 manim -qh --disable_caching ../../chemistry_scene.py ChemistryEpisode
"""
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ["EPISODE_NUMBER"] = "614"
from chemistry_scene import ChemistryEpisode
