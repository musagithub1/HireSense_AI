"""Manim source wrapper for Chemistry Episode 0735: Cell notation.
Run from this directory with:
  EPISODE_NUMBER=735 manim -qh --disable_caching ../../chemistry_scene.py ChemistryEpisode
"""
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ["EPISODE_NUMBER"] = "735"
from chemistry_scene import ChemistryEpisode
