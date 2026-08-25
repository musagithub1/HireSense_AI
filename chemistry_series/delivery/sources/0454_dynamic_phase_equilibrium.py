"""Manim source wrapper for Chemistry Episode 0454: Dynamic phase equilibrium.
Run from this directory with:
  EPISODE_NUMBER=454 manim -qh --disable_caching ../../chemistry_scene.py ChemistryEpisode
"""
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ["EPISODE_NUMBER"] = "454"
from chemistry_scene import ChemistryEpisode
