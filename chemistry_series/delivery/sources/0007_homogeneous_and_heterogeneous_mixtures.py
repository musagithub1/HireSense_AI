"""Manim source wrapper for Chemistry Episode 0007: Homogeneous and heterogeneous mixtures.
Run from this directory with:
  EPISODE_NUMBER=7 manim -qh --disable_caching ../../chemistry_scene.py ChemistryEpisode
"""
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ["EPISODE_NUMBER"] = "7"
from chemistry_scene import ChemistryEpisode
