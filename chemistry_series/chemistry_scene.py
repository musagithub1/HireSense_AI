from __future__ import annotations

import json
import os
import math
from pathlib import Path
from manim import *

config.pixel_width = 1080
config.pixel_height = 1920
config.frame_height = 16
config.frame_width = config.frame_height * config.pixel_width / config.pixel_height
config.frame_rate = 30

BG = "#0b0e14"
BLUE = "#58C4DD"
YELLOW = "#FFD966"
GREEN = "#83C167"
ORANGE = "#FF8C69"
PURPLE = "#C792EA"
GREY = "#9AA0A6"
WHITE = "#F2F2F2"
GRID = "#202733"
COLORS = [BLUE, GREEN, YELLOW, ORANGE, PURPLE]
ROOT = Path(__file__).parent


def fit_text(text: str, size: float, max_width: float = 8.2, color: str = WHITE) -> Text:
    obj = Text(text, font="DejaVu Sans", color=color, font_size=size)
    if obj.width > max_width:
        obj.scale(max_width / obj.width)
    return obj


class ChemistryEpisode(Scene):
    def setup(self):
        self.camera.background_color = BG
        self.caption_obj = None
        self.spec = self.load_spec()

    def load_spec(self):
        path = Path(os.getenv("EPISODE_FILE", str(ROOT / "episode_specs.json")))
        number = int(os.getenv("EPISODE_NUMBER", "1"))
        data = json.loads(path.read_text())
        return next(x for x in data if x["number"] == number)

    def caption(self, text: str):
        new = fit_text(text, 34, 8.35, GREY)
        new.to_edge(DOWN, buff=1.05)
        if self.caption_obj is None:
            self.play(FadeIn(new, shift=UP * 0.15), run_time=0.55)
        else:
            self.play(FadeOut(self.caption_obj, shift=UP * 0.15), FadeIn(new, shift=UP * 0.15), run_time=0.55)
        self.caption_obj = new

    def label(self, text: str, color: str = WHITE, size: float = 30):
        return fit_text(text, size, 7.8, color)

    def title_card(self):
        spec = self.spec
        series = self.label(f"CHEMISTRY • EPISODE {spec['number']:04d}", BLUE, 25)
        series.to_edge(UP, buff=0.42)
        hook = fit_text(spec["hook"], 56, 8.3, WHITE)
        hook.next_to(series, DOWN, buff=0.55)
        rule = Line(LEFT * 3.6, RIGHT * 3.6, color=BLUE, stroke_width=3).next_to(hook, DOWN, buff=0.52)
        self.play(FadeIn(series), Write(hook), Create(rule), run_time=1.1)
        self.caption(spec["hook"])
        self.wait(3.0)
        self.play(FadeOut(series), FadeOut(hook), FadeOut(rule), FadeOut(self.caption_obj), run_time=0.55)
        self.caption_obj = None

    def particle_visual(self, phase: int):
        pts = VGroup()
        shifts = [(-2.1, 1.2), (-1.2, 0.6), (-0.4, 1.45), (0.6, 0.65), (1.7, 1.25), (-1.55, -0.55), (-0.5, -1.2), (0.7, -0.6), (1.7, -1.25)]
        for i, (x, y) in enumerate(shifts):
            dx = 0.22 * math.sin(phase + i)
            dy = 0.18 * math.cos(phase * 0.8 + i)
            pts.add(Dot(point=RIGHT * (x + dx) + UP * (y + dy), radius=0.16, color=COLORS[i % len(COLORS)]))
        box = RoundedRectangle(width=5.8, height=4.7, corner_radius=0.2, color=GRID, stroke_width=2)
        box.set_fill(GRID, opacity=0.12)
        title = self.label(["particles", "motion", "collisions", "observable effect"][phase], YELLOW, 31)
        title.next_to(box, UP, buff=0.32)
        return VGroup(box, pts, title)

    def molecular_visual(self, phase: int):
        centers = [LEFT * 1.8 + UP * 0.7, ORIGIN + DOWN * 0.45, RIGHT * 1.8 + UP * 0.7]
        if phase % 2:
            centers = [LEFT * 1.3 + UP * 0.95, ORIGIN + DOWN * 0.45, RIGHT * 1.3 + UP * 0.95]
        atoms = VGroup()
        bonds = VGroup()
        for i, p in enumerate(centers):
            atoms.add(Circle(radius=0.55, color=COLORS[(i + phase) % len(COLORS)], fill_opacity=0.22, stroke_width=4).move_to(p))
        for a, b in [(0, 1), (1, 2)]:
            bonds.add(Line(centers[a], centers[b], color=WHITE, stroke_width=5))
        tag = self.label(["structure", "bonding", "shape", "property"][phase], YELLOW, 31)
        tag.next_to(VGroup(*atoms), UP, buff=0.35)
        return VGroup(bonds, atoms, tag)

    def network_visual(self, phase: int):
        pos = [LEFT * 2.0 + UP * 0.9, LEFT * 1.5 + DOWN * 0.9, ORIGIN + UP * 0.3, RIGHT * 1.6 + DOWN * 0.8, RIGHT * 2.0 + UP * 1.0]
        nodes = VGroup(*[Dot(p, radius=0.18, color=COLORS[(i + phase) % len(COLORS)]) for i, p in enumerate(pos)])
        edges = VGroup()
        for i in range(len(pos)):
            for j in range(i + 1, len(pos)):
                edge = Line(pos[i], pos[j], color=GRID, stroke_width=2)
                edges.add(edge)
        highlight = Line(pos[phase % 3], pos[(phase + 2) % 5], color=YELLOW, stroke_width=7)
        tag = self.label(["neighbors", "relationships", "strong link", "prediction"][phase], YELLOW, 31)
        tag.next_to(nodes, UP, buff=0.38)
        return VGroup(edges, nodes, highlight, tag)

    def stack_visual(self, phase: int):
        cards = VGroup()
        names = ["input", "change", "result"]
        for i, name in enumerate(names):
            card = RoundedRectangle(width=4.6, height=0.82, corner_radius=0.12, color=COLORS[(i + phase) % len(COLORS)], stroke_width=4, fill_opacity=0.16)
            card.shift(UP * (1.35 - 1.25 * i))
            txt = self.label(name, COLORS[(i + phase) % len(COLORS)], 30).move_to(card)
            cards.add(VGroup(card, txt))
        arrows = VGroup(*[Arrow(cards[i].get_bottom(), cards[i + 1].get_top(), color=WHITE, buff=0.08, stroke_width=3) for i in range(2)])
        tag = self.label(["start", "intermediate", "constraint", "takeaway"][phase], YELLOW, 31)
        tag.next_to(cards, UP, buff=0.4)
        return VGroup(cards, arrows, tag)

    def distribution_visual(self, phase: int):
        bars = VGroup()
        heights = [1.0, 2.0, 1.35, 2.8, 1.6]
        for i, h in enumerate(heights):
            bar = Rectangle(width=0.62, height=h, color=COLORS[i], fill_opacity=0.25, stroke_width=3)
            bar.move_to(LEFT * 2.1 + RIGHT * i * 1.05 + DOWN * (1.0 - h / 2))
            bars.add(bar)
        axis = Line(LEFT * 2.55 + DOWN * 1.5, RIGHT * 2.55 + DOWN * 1.5, color=GREY, stroke_width=2)
        bars[phase % len(bars)].set_fill(YELLOW, opacity=0.75)
        tag = self.label(["options", "weights", "selection", "prediction"][phase], YELLOW, 31)
        tag.next_to(bars, UP, buff=0.45)
        return VGroup(axis, bars, tag)

    def visual_for(self, idiom: str, phase: int):
        if idiom == "molecular model":
            return self.molecular_visual(phase)
        if idiom == "relationship network":
            return self.network_visual(phase)
        if idiom == "stacking":
            return self.stack_visual(phase)
        if idiom == "distribution":
            return self.distribution_visual(phase)
        return self.particle_visual(phase)

    def construct(self):
        self.title_card()
        current = None
        beats = self.spec["beats"]
        for i, beat in enumerate(beats):
            visual = self.visual_for(beat.get("idiom", "particles"), i)
            if current is None:
                self.play(FadeIn(visual, scale=0.85), run_time=0.9)
            else:
                self.play(ReplacementTransform(current, visual), run_time=0.95)
            current = visual
            self.caption(beat["caption"])
            self.wait(8.0)
        closing = fit_text(self.spec["closing"], 47, 8.2, YELLOW)
        closing.move_to(UP * 3.05)
        check = Circle(radius=0.42, color=GREEN, stroke_width=5).next_to(closing, DOWN, buff=0.45)
        tick = VGroup(Line(check.get_left() + RIGHT * 0.15, check.get_center() + DOWN * 0.12, color=GREEN, stroke_width=5), Line(check.get_center() + DOWN * 0.12, check.get_right() + LEFT * 0.12 + UP * 0.2, color=GREEN, stroke_width=5))
        self.play(FadeIn(closing, shift=UP * 0.2), Create(check), Create(tick), run_time=0.8)
        self.caption(self.spec["takeaway"])
        self.play(Indicate(check, color=YELLOW), run_time=0.55)
        self.wait(4.8)
        self.play(FadeOut(VGroup(current, closing, check, tick, self.caption_obj)), run_time=0.65)
