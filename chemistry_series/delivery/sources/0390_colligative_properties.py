"""Manim source wrapper for Chemistry Episode 0390: Colligative properties.
Run from this directory with:
  EPISODE_NUMBER=390 manim -qh --disable_caching ../../chemistry_scene.py ChemistryEpisode
"""
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ["EPISODE_NUMBER"] = "390"
from chemistry_scene import ChemistryEpisode
