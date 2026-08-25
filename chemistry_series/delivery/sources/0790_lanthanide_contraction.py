"""Manim source wrapper for Chemistry Episode 0790: Lanthanide contraction.
Run from this directory with:
  EPISODE_NUMBER=790 manim -qh --disable_caching ../../chemistry_scene.py ChemistryEpisode
"""
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ["EPISODE_NUMBER"] = "790"
from chemistry_scene import ChemistryEpisode
