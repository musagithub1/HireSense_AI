"""Manim source wrapper for Chemistry Episode 0338: Mole-to-mole calculations.
Run from this directory with:
  EPISODE_NUMBER=338 manim -qh --disable_caching ../../chemistry_scene.py ChemistryEpisode
"""
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ["EPISODE_NUMBER"] = "338"
from chemistry_scene import ChemistryEpisode
