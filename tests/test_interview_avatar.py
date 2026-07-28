"""Regression coverage for the local animated AI interviewer."""

from __future__ import annotations

import json
from pathlib import Path

import voice_input_component

ROOT = Path(__file__).parents[1]
FRONTEND = ROOT / "voice_input" / "frontend"


def test_avatar_is_a_local_accessible_svg_component() -> None:
    source = (FRONTEND / "src" / "InterviewAvatar.tsx").read_text(
        encoding="utf-8"
    )

    assert "export type InterviewState" in source
    for state in (
        "ready",
        "listening",
        "processing",
        "speaking",
        "paused",
        "error",
        "offline",
    ):
        assert f'"{state}"' in source
    assert "<svg" in source
    assert "HireSense AI interviewer" in source
    assert "Interrupt interviewer" in source
    assert "http://" not in source
    assert "https://" not in source


def test_voice_lifecycle_drives_avatar_and_recovery_controls() -> None:
    source = (FRONTEND / "src" / "main.js").read_text(encoding="utf-8")
    markup = (FRONTEND / "index.html").read_text(encoding="utf-8")

    assert "let interviewState" in source
    assert "function handleSpeechStart" in source
    assert "function handleSpeechEnd" in source
    assert "function handleSpeechPause" in source
    assert "function handleSpeechError" in source
    assert "function interruptInterviewer" in source
    assert "function showAudioFallback" in source
    assert 'id="interview-avatar"' in markup
    assert 'id="audio-fallback"' in markup
    assert 'id="question" tabindex="-1"' in markup


def test_live_mode_enables_interrupt_without_exposing_it_to_speaker_mode(
    monkeypatch,
) -> None:
    captured: list[dict] = []

    def fake_component(**kwargs):
        captured.append(kwargs)
        return None

    monkeypatch.setattr(voice_input_component, "_voice_component", fake_component)

    voice_input_component.render_voice_input(
        key="live",
        mode="live",
        question_text="Tell me about a difficult engineering decision.",
        interviewer_name="Maya",
        allow_interrupt=True,
    )
    voice_input_component.render_voice_input(
        key="speaker",
        mode="speaker",
        question_text="Tell me about a difficult engineering decision.",
        interviewer_name="Maya",
        allow_interrupt=True,
    )

    assert captured[0]["interviewer_name"] == "Maya"
    assert captured[0]["allow_interrupt"] is True
    assert captured[1]["allow_interrupt"] is False


def test_frontend_manifest_pins_react_runtime() -> None:
    package = json.loads((FRONTEND / "package.json").read_text(encoding="utf-8"))

    assert package["dependencies"]["react"] == "19.1.1"
    assert package["dependencies"]["react-dom"] == "19.1.1"


def test_built_voice_bundle_contains_avatar_controls() -> None:
    bundles = list((FRONTEND / "dist" / "assets").glob("*.js"))
    assert len(bundles) == 1
    bundle = bundles[0].read_text(encoding="utf-8")

    assert "HireSense AI interviewer" in bundle
    assert "Interrupt interviewer" in bundle
    assert "Audio unavailable" in bundle
