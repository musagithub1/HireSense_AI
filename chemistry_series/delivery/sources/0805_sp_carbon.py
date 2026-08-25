"""Manim source wrapper for Chemistry Episode 0805: sp carbon.
Run from this directory with:
  EPISODE_NUMBER=805 manim -qh --disable_caching ../../chemistry_scene.py ChemistryEpisode
"""
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ["EPISODE_NUMBER"] = "805"
from chemistry_scene import ChemistryEpisode
