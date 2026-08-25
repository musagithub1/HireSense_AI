"""Manim source wrapper for Chemistry Episode 0744: Faraday's law.
Run from this directory with:
  EPISODE_NUMBER=744 manim -qh --disable_caching ../../chemistry_scene.py ChemistryEpisode
"""
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ["EPISODE_NUMBER"] = "744"
from chemistry_scene import ChemistryEpisode
